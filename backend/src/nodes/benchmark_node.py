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

    def try_convert(options):
        conv = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        return conv.convert(source,max_num_pages=50).document.export_to_markdown()

    # 3. 实施“软着陆”尝试循环
    try:
        return try_convert(pipeline_options)
    except Exception as e:
        error_str = str(e).lower()
        # 捕捉内存溢出关键词
        if "bad_alloc" in error_str or "runtimeerror" in error_str:
            print(f"⚠️ OCR 内存溢出，正在实施软着陆降级解析...")
            # 降级：强制关闭 OCR 并重新尝试
            fallback_options = PdfPipelineOptions()
            fallback_options.do_ocr = False
            try:
                return try_convert(fallback_options)
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
    if pdf_url and pdf_url.lower().endswith(".pdf"):
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

# --- 核心分析节点 ---
def benchmark_node(state: AgentState) -> Dict[str, Any]:
    start_ts = time.time()
    top_papers = state.get("top_tier_papers") or []
    domain_metrics = state.get("domain_metrics") or ["accuracy", "rmse"]
    iteration = int(state.get("iteration") or 0) + 1
    
    # 初始化 LLM
    current_model = os.getenv("SELECTED_MODEL_NAME", "qwen2.5-32b-instruct")
    llm = make_qwen_llm(model_name=current_model, temperature=0.0)
    sys_prompt, regex_patterns = _generate_dynamic_prompts(domain_metrics)
    
    extracted_results = []
    total_tokens = 0
    
    # 1. 提取论文指标
    for p in top_papers[:10]: # 平衡精度与成本
        full_text_raw = p.get("full_text_cache") or _paper_full_text(p, [])
        if not full_text_raw: continue
        context_for_llm = _filter_relevant_context_dynamic(full_text_raw, regex_patterns)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=context_for_llm)])
            total_tokens += resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
            
            content = re.sub(r"```json\s?|\s?```", "", resp.content).strip()
            data = json.loads(content)
            
            # 仅记录包含有效数值的论文
            valid_m = [m for m in data.get("metrics", []) if m.get("value") is not None]
            if valid_m:
                extracted_results.append({
                    "title": p.get("title"),
                    "venue": f"{p.get('venue_type', 'N/A')}-{p.get('venue_rank', 'N/A')}",
                    "metrics": valid_m
                })
        except:
            continue

    # 2. 计算本地实验
    csv_path = os.getenv("EXPERIMENT_CSV_PATH", "data/experiment.csv")
    local_data = compute_local_rmse_from_csv(csv_path)

    # 3. 构造学术 Markdown 报告
    lines = []
    lines.append(f"# 🎓 Scholar-Agent Research Report\n")
    lines.append(f"**Research Query**: `{state.get('query')}`")
    lines.append(f"**Target Metrics**: {', '.join([f'`{m}`' for m in domain_metrics])}\n")
    
    # --- 论文引用列表 ---
    lines.append("## 📚 Key Literature & Venues")
    if top_papers:
        for i, p in enumerate(top_papers[:15], 1):
            info = f"{p.get('venue')}, {p.get('year')}"
            rank = f"`{p.get('venue_type')}-{p.get('venue_rank')}`"

            # 2. 构造链接组
            link_elements = []
            # 网络链接 (Web URL)
            web_url = p.get('url')
            if web_url:
                link_elements.append(f"[🔗 Web]({web_url})")
            
            # 本地 PDF 路径 (Local Path)
            local_path = p.get('local_pdf_path')
            if local_path:
            # 注意：某些操作系统路径包含反斜杠，Markdown 链接中建议保留或处理
                link_elements.append(f"[📂 Local]({local_path})")
            # 拼接链接字符串
            links_str = " | ".join(link_elements) if link_elements else "*No Links*"

            # 3. 组合成最终行
            lines.append(f"{i}. **{p.get('title')}**")
            lines.append(f"   - {info} | {rank} | {links_str}")
    else:
        lines.append("*No relevant papers found.*")
    lines.append("")

    # --- SOTA 指标对比表 ---
    lines.append("## 📊 Quantitative Benchmark (SOTA)")
    if extracted_results:
        lines.append("| Paper Title | Venue Rank | Extracted Metrics |")
        lines.append("|:---|:---|:---|")
        for res in extracted_results:
            m_str = " ".join([f"`{m['name']}: {m['value']} {m.get('unit','')}`" for m in res['metrics']])
            lines.append(f"| {res['title']}... | {res['venue']} | {m_str} |")
    else:
        lines.append("> ⚠️ No numerical metrics were extracted from the current set of papers.")
    lines.append("")

    # --- 本地实验结果 ---
    lines.append("## 🧪 Local Experiment Results")
    if local_data.get("ok"):
        lines.append(f"- **Primary Metric (RMSE)**: `{local_data['rmse']:.6f}`")
        lines.append(f"- **Data Samples**: {local_data['n']}")
        lines.append(f"- **CSV Source**: `{csv_path}`")
    else:
        lines.append(f"*Local data unavailable: {local_data.get('reason')}*")
    lines.append("")

    # --- 专家级 LLM-Analysis ---
    lines.append("## 🧠 Technical Analysis & Synthesis")
    
    try:
        # 准备上下文数据
        local_val = local_data.get('rmse') if local_data.get('ok') else 'N/A'
        target_metrics = ", ".join(domain_metrics)
        # 构造 Prompt
        analysis_prompt = f"""You are a senior multi-disciplinary scientist. 
Your task is to synthesize research results between a User's local experiment and SOTA literature.

### Data Inputs:
- Local Experimental Metric: [RMSE: {local_val}]
- Target Research Metrics: [{target_metrics}]
- Extracted SOTA Results: (Provided in the JSON below)

### Analysis Protocol:
1. **Domain Compatibility Check**: 
   - First, determine if the SOTA papers and the Local Experiment belong to the same domain.
   - If the Local Data is numerical (e.g., RMSE) but the SOTA papers are qualitative or from unrelated fields (e.g., Social Sciences, Arts), DECLARE a "Domain Mismatch".
   
2. **Conditional Comparison**:
   - IF DOMAINS MATCH: Compare the local RMSE with the SOTA values. Identify the leading paper and explain the performance gap.
   - IF DOMAINS MISMATCH: Ignore the local RMSE. Focus entirely on synthesizing the SOTA findings and explaining why the local metric is not applicable to this specific literature.

3. **Technical Synthesis**:
   - Identify the best performing paper/method from the SOTA list.
   - Provide 3 high-level technical or methodological suggestions based on the SOTA findings.

### Constraints:
- Do not output raw JSON tags like "sota: extracted_results".
- Be professional, concise, and academically rigorous.
"""
        ana_resp = llm.invoke([
            SystemMessage(content=analysis_prompt), 
            HumanMessage(content=json.dumps({"sota": extracted_results, "local": local_data}))
        ])
        total_tokens += ana_resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
        lines.append(ana_resp.content.strip())
    except:
        lines.append("*LLM-analysis generation failed.*")

    # 4. 状态更新与返回
    report = "\n".join(lines)
    duration = round(time.time() - start_ts, 2)
    
    # 更新耗时统计
    metrics_log = state.get("metrics_log", {"total_tokens": {}, "node_durations": {}})
    metrics_log["node_durations"]["benchmark_node"] = duration
    metrics_log["total_tokens"]["benchmark_node"] = total_tokens
    
    return {
        "analysis_report": report,
        "iteration": iteration,
        "done": iteration >= int(state.get("max_iterations", 3)) or len(extracted_results) > 0,
        "metrics_log": metrics_log,
        "paper_metrics": {"papers": extracted_results}
    }

