from __future__ import annotations

import json
import os
import re
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup  # type: ignore[import-not-found]

from src.state import AgentState
from src.llm import make_qwen_llm
import time # 导入时间模块
from langchain_core.messages import HumanMessage, SystemMessage
# 引入 Docling 相关组件
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False


def _generate_dynamic_prompts(domain_metrics: List[str]) -> Tuple[str, List[str]]:
    """根据领域指标动态生成 LLM Prompt 和正则关键词"""
    metrics_str = ", ".join(domain_metrics)
    
    # 1. 动态生成 LLM 提取 Prompt
    system_prompt = f"""You are a strict scientific information extractor.
Your ONLY job is to extract quantitative metrics relevant to: [{metrics_str}].

Rules:
- Extract values and units exactly as reported.
- If a metric like "{domain_metrics[0]}" is present, capture its value and context.
- If a value is missing, set it to null.
- DO NOT hallucinate. Return ONLY valid JSON.

Return JSON:
{{
  "metrics": [
    {{"name": "string", "value": number|null, "unit": "string", "context": "string"}}
  ],
  "notes": "string"
}}
"""
    # 2. 动态生成正则过滤关键词（增加模糊匹配能力）
    # 将指标名转为小写，并加入通用的学术结果关键词
    base_keywords = ["table", "accuracy", "experimental results"]
    dynamic_keywords = [m.lower() for m in domain_metrics]
    
    # 增加时间相关的模糊扩展
    time_related = ["runtime", "time cost", "seconds"]
    if any(tk in metrics_str.lower() for tk in ["time", "cost", "speed", "latency",'computational complexity']):
        dynamic_keywords.extend(time_related)

    # 去重并构建正则列表
    all_keywords = list(set(base_keywords + dynamic_keywords))
    # 转换为正则支架，例如 r"rmse|mae|table|..."
    regex_patterns = [rf"\b{re.escape(k)}\b" for k in all_keywords]
    
    return system_prompt, regex_patterns


def _smart_extract_markdown(source: str | bytes) -> str:
    """使用 Docling 将 PDF 转换为 Markdown, 处理复杂排版。含 OCR 软着陆逻辑。"""
    if not DOCLING_AVAILABLE:
        return "Error: docling not installed. Please run 'pip install docling'."
    # 1. 从环境变量获取 UI 配置
    use_ocr_config = os.getenv("USE_OCR") == "1"
    # 2. 配置 OCR 选项 (工程化降级策略)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = use_ocr_config
    if use_ocr_config:
        pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=False)
        pipeline_options.num_threads = 1 # 限制线程减少瞬时内存占用

    def try_convert(options, max_pages):
        conv = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        return conv.convert(source, max_num_pages=max_pages).document.export_to_markdown()

    # 3. 实施“软着陆”尝试循环
    try:
        return try_convert(pipeline_options, max_pages=30)
    except Exception as e:
        error_str = str(e).lower()
        # 捕捉内存溢出关键词
        if any(kw in error_str for kw in ["bad_alloc", "out of memory", "runtimeerror"]):
            print(f"⚠️ OCR 内存溢出或解析错误，正在实施软着陆降级解析... (Error: {e})")
            # 降级：强制关闭 OCR 并减少页数重新尝试
            fallback_options = PdfPipelineOptions()
            fallback_options.do_ocr = False
            try:
                return try_convert(fallback_options, max_pages=20)
            except Exception as final_e:
                return f"彻底解析失败 (含降级尝试): {final_e}"
        return f"Docling conversion failed: {e}"

# 按文本块截取关键段落，保留更多信息但是消耗过多的token
def _filter_relevant_context_dynamic(markdown_text: str, regex_patterns: List[str]) -> str:
    """基于动态关键词过滤 Markdown 上下文，保留关键段落"""
    if not markdown_text:
        return ""
    # 拼接成一个正则表达式字符串， re.IGNORECASE: 忽略大小写
    pattern = re.compile("|".join(regex_patterns), re.IGNORECASE)
    # 按双换行符分割 Markdown（通常是段落或表格的分界）
    blocks = markdown_text.split("\n\n")
    # 用来存放那些被判定为“含有重要实验数据”的信息块
    selected_blocks = []
    
    for block in blocks:
        if pattern.search(block):
            # 保留该区块，如果是表格（以 | 开头），通常结构也完整
            selected_blocks.append(block.strip())
            
    # 如果过滤后内容太少，尝试扩大范围（获取标题或摘要附近的块）
    if len(selected_blocks) < 2:
        return markdown_text[:15000] # 退回到前 15k 字符
        
    return "\n\n---\n\n".join(selected_blocks)[:30000] # 限制长度


# 多级回退（Fallback）策略。如果拿不到精细的 PDF 全文，也要拿到网页正文；如果还不行，起码得把摘要（Abstract）保住。
def _paper_full_text(paper: Dict[str, Any], regex_patterns: List[str]) -> str:
    """增强型论文全文抓取流"""
    raw = paper.get("raw") or {}
    # 0) 优先本地 PDF (Docling 处理)
    local_pdf = ""
    if isinstance(raw, dict):
        local_pdf = (raw.get("local_pdf_path") or raw.get("file") or "").strip()
        if not local_pdf:
            atts = raw.get("attachments") or raw.get("attachment") or []
            if isinstance(atts, list):
                for a in atts:
                    path = (a.get("path") or a.get("localPath") or "").strip()
                    if path.lower().endswith(".pdf"):
                        local_pdf = path
                        break
    
    # 优先处理本地 PDF
    if local_pdf and os.path.exists(local_pdf):
        md = _smart_extract_markdown(local_pdf)
        if "Error" not in md[:10]:
            return _filter_relevant_context_dynamic(md, regex_patterns)

    # 1) 尝试网络 PDF
    pdf_url = ""
    if isinstance(raw, dict):
        if isinstance(raw.get("openAccessPdf"), dict):
            pdf_url = (raw["openAccessPdf"].get("url") or "").strip()
        pdf_url = pdf_url or (raw.get("pdfUrl") or raw.get("URL") or paper.get("url") or "").strip()
    if pdf_url:
        low_url = pdf_url.lower()
        if "arxiv.org/abs/" in low_url:
            pdf_url = pdf_url.replace("/abs/", "/pdf/")
            if not pdf_url.lower().endswith(".pdf"):
                pdf_url += ".pdf"

        if pdf_url.lower().endswith(".pdf") or "arxiv.org/pdf/" in pdf_url.lower():
            md = _smart_extract_markdown(pdf_url)
            if "Error" not in md[:10]:
                return _filter_relevant_context_dynamic(md, regex_patterns)
    
    # 2) 尝试 HTML
    url = (paper.get("url") or "").strip()
    if url:
        txt = _fetch_html_text(url)
        if txt: return txt

    return (paper.get("abstract") or "").strip()

# 从杂乱的网页（HTML）中剔除广告、菜单和脚本，只留下最有价值的纯文本内容。
def _fetch_html_text(url: str, max_chars: int = 100000) -> Optional[str]:
    """Best-effort HTML to plain text extraction using BeautifulSoup."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Scholar-Agent/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError):  # type: ignore[arg-type]
        return None

    try:
        soup = BeautifulSoup(html, "html.parser") # 使用系统自带的 HTML 规则来解析
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose() # decompose()：把匹配到的标签（如导航栏 nav、侧边栏 aside、样式表 style）从文档树中彻底切除。
        text = soup.get_text(separator="\n") # 在提取文本时，在原本是 HTML 标签的地方换行
        lines = [ln.strip() for ln in text.splitlines()] # 利用换行符将 字符串变成一个字符串列表
        text_clean = "\n".join(ln for ln in lines if ln)
    except Exception:  # noqa: BLE001
        return None

    if len(text_clean) > max_chars:
        return text_clean[:max_chars]
    return text_clean or None


def compute_local_rmse_from_csv(csv_path: str) -> Dict[str, Any]:
    """计算本地 CSV 的 RMSE (支持 Error 列或 Est/GT 对)"""
    if not os.path.exists(csv_path):
        return {"ok": False, "reason": f"csv_not_found: {csv_path}"}

    df = pd.read_csv(csv_path) # 使用 pd.read_csv 加载数据
    cols = set(df.columns)

    for err_col in ("error", "err", "Error", "Err"): # 直接读取误差列
        if err_col in cols:
            # errors="coerce" 无法转换的非数字设为 NaN。.dropna()把所有 NaN和原本就有的空值删除。to_numpy将 Pandas 的 Series 对象转换成 NumPy 数组
            e = pd.to_numeric(df[err_col], errors="coerce").dropna().to_numpy(dtype=float)
            if e.size == 0:
                return {"ok": False, "reason": "empty_error_column"}
            rmse = float(np.sqrt(np.mean(e**2))) # 计算 RMSE
            return {
                "ok": True,
                "mode": "error_column",
                "rmse": rmse,
                "n": int(e.size),
                "used_columns": [err_col],
            }

    # 模式2: Est/GT 匹配
        dims = [c[:-4] for c in cols if c.endswith("_est") and f"{c[:-4]}_gt" in cols]
        if dims:
            all_err = []
            for d in dims:
                e = (pd.to_numeric(df[f"{d}_est"], errors="coerce") - 
                     pd.to_numeric(df[f"{d}_gt"], errors="coerce")).dropna().to_numpy()
                all_err.append(e)
            stacked = np.concatenate(all_err)
            return {"ok": True, 
                    "rmse": float(np.sqrt(np.mean(stacked**2))),
                    "n": int(stacked.size), 
                    "mode": "est_gt"
                }
            
        return {"ok": False, "reason": "no_matching_columns"}

def _best_paper_rmse(paper_metrics: Dict[str, Any]) -> Optional[float]:
    rmses: List[float] = []
    for m in (paper_metrics.get("papers") or []):
        rmse = (((m or {}).get("metrics") or {}).get("rmse") or {}).get("value")
        if isinstance(rmse, (int, float)) and rmse > 0:
            rmses.append(float(rmse))
    return min(rmses) if rmses else None

def _check_domain_consistency(llm: Any, query: str, csv_info: str) -> bool:
    """Check if the CSV data matches the research query's domain using LLM."""
    prompt = f"""Compare the Research Query with the CSV Data Sample. 
Determine if they belong to the same scientific/technical domain.

Research Query: {query}
CSV Data Sample (Columns & Values): 
{csv_info}

Rules:
- If Query is about "Legal/Law" but CSV is "Sensor/EKF/RMSE", they are INCONSISTENT.
- If Query is about "Vision/CNN" and CSV has "Accuracy/mAP", they are CONSISTENT.
- Return ONLY "CONSISTENT" or "INCONSISTENT".
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="You are a domain classifier. Answer ONLY 'CONSISTENT' or 'INCONSISTENT'."),
            HumanMessage(content=prompt)
        ])
        return "CONSISTENT" in resp.content.upper()
    except:
        return True # Fallback to true if LLM fails

# --- 核心分析节点 ---
def benchmark_node(state: AgentState) -> Dict[str, Any]:
    start_ts = time.time()
    top_papers = state.get("top_tier_papers") or []
    domain_metrics = state.get("domain_metrics") or ["accuracy", "rmse"]
    iteration = int(state.get("iteration") or 0) + 1
    
    # 获取双模式开关
    run_benchmark = state.get("run_benchmark", False)
    query = state.get("query", "")
    
    # 初始化 LLM
    current_model = os.getenv("SELECTED_MODEL_NAME", "qwen2.5-32b-instruct")
    llm = make_qwen_llm(model_name=current_model, temperature=0.0)
    
    # 模式选择与领域检查
    eval_mode = "review"
    csv_path = os.getenv("EXPERIMENT_CSV_PATH", "data/experiment.csv")
    local_data = {"ok": False}
    
    if run_benchmark and os.path.exists(csv_path):
        # 尝试读取 CSV 样本用于领域检查
        try:
            sample_df = pd.read_csv(csv_path, nrows=5)
            csv_info = f"Columns: {list(sample_df.columns)}\nSample Rows:\n{sample_df.to_string(index=False)}"
            if _check_domain_consistency(llm, query, csv_info):
                eval_mode = "benchmark"
                local_data = compute_local_rmse_from_csv(csv_path)
            else:
                eval_mode = "mismatch"
        except:
            eval_mode = "review"
    
    # 如果是 Benchmark 模式，准备提取提示词
    sys_prompt, regex_patterns = _generate_dynamic_prompts(domain_metrics)
    
    # Load previously accumulated results
    previous_metrics = state.get("paper_metrics", {}).get("papers", [])
    extracted_results = list(previous_metrics)
    total_tokens = 0
    
    # Track titles already processed
    existing_titles = {res["title"].lower().strip() for res in extracted_results if "title" in res}
    
    # 1. 提取论文信息 (根据模式调整侧重点)
    for p in top_papers[:10]:
        title = (p.get("title") or "").strip()
        if title.lower() in existing_titles:
            continue
        
        full_text_raw = p.get("full_text_cache") or _paper_full_text(p, [])
        if not full_text_raw: continue
        
        # 过滤相关上下文
        context_for_llm = _filter_relevant_context_dynamic(full_text_raw, regex_patterns)

        try:
            # 如果是 Benchmark 模式，提取数值
            if eval_mode == "benchmark":
                resp = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=context_for_llm)])
                total_tokens += resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
                content = re.sub(r"```json\s?|\s?```", "", resp.content).strip()
                data = json.loads(content)
                valid_m = [m for m in data.get("metrics", []) if m.get("value") is not None]
                if valid_m:
                    extracted_results.append({
                        "title": p.get("title"),
                        "venue": f"{p.get('venue_type', 'N/A')}-{p.get('venue_rank', 'N/A')}",
                        "metrics": valid_m
                    })
            else:
                # Review 模式：提取核心发现与趋势
                review_prompt = f"""You are a senior scientist summarizing a paper's key methodology and findings.
Research Query: {query}
Extract:
1. Core Methodology/Algorithm.
2. Key Achievement or Finding.
3. Relevant Metrics defined in paper.

Return JSON:
{{
  "method": "string",
  "key_finding": "string",
  "metrics_defined": ["string"]
}}
"""
                resp = llm.invoke([SystemMessage(content=review_prompt), HumanMessage(content=context_for_llm)])
                total_tokens += resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
                content = re.sub(r"```json\s?|\s?```", "", resp.content).strip()
                data = json.loads(content)
                
                extracted_results.append({
                    "title": p.get("title"),
                    "venue": f"{p.get('venue_type', 'N/A')}-{p.get('venue_rank', 'N/A')}",
                    "review_data": data
                })
        except:
            continue

    # 3. 构造学术 Markdown 报告
    lines = []
    lines.append(f"# 🎓 Scholar-Agent Research Report ({'Benchmark Mode' if eval_mode == 'benchmark' else 'Qualitative Review'})\n")
    
    if eval_mode == "mismatch":
        lines.append("> [!WARNING]")
        lines.append("> **领域不匹配警告**: 检测到上传的实验数据（CSV）与研究问题领域严重偏离。")
        lines.append("> 系统已自动切换为 **纯文献定性分析 (Qualitative Review)** 模式。\n")

    lines.append(f"**Research Query**: `{query}`")
    if eval_mode == "benchmark":
        lines.append(f"**Target Metrics**: {', '.join([f'`{m}`' for m in domain_metrics])}\n")
    lines.append("")

    # --- Literature References ---
    lines.append("## 📚 Key Literature & References")
    all_accumulated_papers = state.get("candidate_papers", [])[:10] if not top_papers and iteration > 1 else top_papers
    
    if all_accumulated_papers:
        for i, p in enumerate(all_accumulated_papers[:10], 1):
            info = f"{p.get('venue') or p.get('venue_type', 'N/A')}, {p.get('year', 'N/A')}"
            rank = f"`{p.get('venue_type', 'N/A')}-{p.get('venue_rank', 'N/A')}`"
            # Handle potential missing URL/Path
            url = p.get('url') or p.get('link') or ""
            path = p.get('local_pdf_path') or ""
            links = []
            if url: links.append(f"[🔗 Web]({url})")
            if path: links.append(f"[📂 Local]({path})")
            links_str = " | ".join(links) if links else "*No Links*"
            
            lines.append(f"{i}. **{p.get('title')}**")
            lines.append(f"   - {info} | {rank} | {links_str}")
    else:
        lines.append("*No relevant papers found yet.*")
    lines.append("")

    # --- SOTA Comparison (Benchmark vs Review) ---
    if eval_mode == "benchmark":
        lines.append("## 📊 Quantitative Benchmark (SOTA)")
        if extracted_results:
            lines.append("| Paper Title | Extracted Metrics |")
            lines.append("|:---|:---|")
            for res in extracted_results:
                if "metrics" in res:
                    m_str = " ".join([f"`{m['name']}: {m['value']} {m.get('unit','')}`" for m in res['metrics']])
                    lines.append(f"| {res['title'][:60].replace('|',' ')}... | {m_str} |")
        else:
            lines.append("> ⚠️ No numerical metrics were successfully extracted for comparison.")
        
        lines.append("\n## 🧪 Local Experiment Results")
        if local_data.get("ok"):
            lines.append(f"- **Primary Metric (RMSE)**: `{local_data.get('rmse', 0):.6f}`")
            lines.append(f"- **Data Samples**: {local_data.get('n')}")
            lines.append(f"- **Benchmark Status**: `Domain Consistent`")
        else:
            lines.append(f"*Local data unavailable: {local_data.get('reason')}*")
    else:
        # Qualitative Review Mode
        lines.append("## 📖 Qualitative Literature Review")
        if extracted_results:
            for res in extracted_results:
                if "review_data" in res:
                    rd = res["review_data"]
                    lines.append(f"### {res['title']}")
                    lines.append(f"- **Methodology**: {rd.get('method')}")
                    lines.append(f"- **Key Findings**: {rd.get('key_finding')}")
                    if rd.get('metrics_defined'):
                        lines.append(f"- **Defined Metrics**: {', '.join([f'`{m}`' for m in rd.get('metrics_defined', [])])}")
                    lines.append("")
        else:
            lines.append("*No detailed qualitative analysis available for the current papers.*")

    lines.append("")

    # --- AI Analysis Synthesis ---
    lines.append("## 🧠 Technical Analysis & Synthesis")
    try:
        local_val = local_data.get('rmse') if local_data.get('ok') else 'N/A'
        analysis_prompt = f"""You are a senior scientist. Synthesize research results.
Mode: {eval_mode}
Research Query: {query}
Local Data: {local_val}
Findings JSON: (Provided below)

Tasks:
1. Summarize the state-of-the-art based on the extracted findings.
2. If Mode is 'benchmark', compare Local vs SOTA.
3. If Mode is 'review' or 'mismatch', synthesize the qualitative trends and methodology.
4. Provide 3 actionable technical suggestions.
"""
        ana_resp = llm.invoke([
            SystemMessage(content=analysis_prompt), 
            HumanMessage(content=json.dumps({"sota": extracted_results, "local": local_data, "mode": eval_mode}, ensure_ascii=False))
        ])
        total_tokens += ana_resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
        lines.append(ana_resp.content.strip())
    except:
        lines.append("*LLM-analysis synthesis failed.*")

    # 4. Final state update
    report = "\n".join(lines)
    duration = round(time.time() - start_ts, 2)
    
    metrics_log = state.get("metrics_log", {"total_tokens": {}, "node_durations": {}})
    metrics_log["node_durations"]["benchmark_node"] = duration
    metrics_log["total_tokens"]["benchmark_node"] = total_tokens
    
    return {
        "analysis_report": report,
        "iteration": iteration,
        "eval_mode": eval_mode,
        "done": iteration >= int(state.get("max_iterations", 1)) or (len(extracted_results) >= 3 if eval_mode == "benchmark" else len(extracted_results) >= 1),
        "metrics_log": metrics_log,
        "paper_metrics": {"papers": extracted_results}
    }

