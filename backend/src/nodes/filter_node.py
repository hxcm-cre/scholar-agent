from __future__ import annotations

import gc
import math
import os
import re
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from src.state import AgentState
import time # 导入时间模块
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup  # type: ignore[import-not-found]
# 引入 Docling 相关组件
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# --- 分数配置表 ---
RANK_SCORES = {
    "CCF_A": 1.00, "CAS_1": 1.00,
    "CCF_B": 0.85, "CAS_2": 0.85,
    "CCF_C": 0.70, "CAS_3": 0.70,
    "CAS_4": 0.50,
    "DEFAULT": 0.25
}

class VenueRanker:
    """使用 LangChain BM25Retriever 封装的期刊等级评价器"""
    def __init__(self, csv_path: str = "data/venues_db.csv"):
        self.csv_path = csv_path
        self.retriever = None
        self.exact_map = {}  # 用于存放精确匹配的字典 (全称/缩写 -> 元数据)
        self._initialize_retriever()

    def _initialize_retriever(self):
        if not os.path.exists(self.csv_path):
            print(f"⚠️ 未找到分区表: {self.csv_path}，将使用默认评分。")
            return

        df = pd.read_csv(self.csv_path, encoding='gbk')
        # 将 NaN 替换为空字符串，避免产生 "nan" 字符串污染
        df = df.fillna("")
        documents = []
        for _, row in df.iterrows():
            # 将简称和全称组合，构建检索用的 Document
            # 解决 CAS 没有 abbr 的问题：如果是 NaN 则只用 full_name
            abbr = str(row.get('abbr', '')).strip()
            full_name = str(row.get('full_name', '')).strip()
            
            v_type = str(row['type'])
            v_rank = str(row['rank'])

            # 2. 构建精确匹配地图 (Priority 1)
            if abbr:
                self.exact_map[abbr.lower()] = {"type": v_type, "rank": v_rank}
            if full_name:
                self.exact_map[full_name.lower()] = {"type": v_type, "rank": v_rank}

            # 3. 构建模糊检索文档 (Priority 2)
            # 只在有内容时拼接，严禁出现 "nan"
            content = f"{abbr} {full_name}".strip()
            if content:
                metadata = {"type": v_type, "rank": v_rank, "official": full_name}
                documents.append(Document(page_content=content, metadata=metadata))

        if documents:
            # 初始化 LangChain 的 BM25Retriever
            self.retriever = BM25Retriever.from_documents(documents)
            # 我们可以设置返回最相关的 1 个匹配
            self.retriever.k = 1

    def get_rank_info(self, venue_name: str) -> Dict[str, Any]:
        """获取期刊的详细排名信息"""
        default_info = {"score": RANK_SCORES["DEFAULT"], "type": "None", "rank": "N/A"}
        
        if not self.retriever or not venue_name or str(venue_name).lower() == "nan":
            return default_info
        v_name_clean = str(venue_name).lower().strip()
        # 1. 显式过滤 arXiv 或预印本
        if "arxiv" in v_name_clean or "preprint" in v_name_clean:
            return default_info
        v_name_clean = str(venue_name).strip()
        v_lower = v_name_clean.lower()
        # 策略 B：精确匹配优先 (解决你提到的 IEEE TAC 搜不到的问题)
        if v_lower in self.exact_map:
            res = self.exact_map[v_lower]
            rank_key = f"{res['type']}_{res['rank']}"
            return {
                "score": RANK_SCORES.get(rank_key, RANK_SCORES["DEFAULT"]),
                "type": res['type'],
                "rank": res['rank']
            }

        # 策略 C：模糊匹配 (BM25)
        if self.retriever:
            results = self.retriever.invoke(v_name_clean)
            if results:
                best = results[0]
                # 最后的防线：校验相似度（例如重合单词比例）
                input_words = set(re.findall(r'\w+', v_lower))
                match_words = set(re.findall(r'\w+', best.page_content.lower()))
                if not input_words.intersection(match_words):
                    return default_info

                m = best.metadata
                rank_key = f"{m['type']}_{m['rank']}"
                return {
                    "score": RANK_SCORES.get(rank_key, RANK_SCORES["DEFAULT"]),
                    "type": m['type'],
                    "rank": m['rank']
                }
        return default_info

# 全局单例
ranker = VenueRanker()


# --- 辅助计算函数 ---

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
            if regex_patterns==[]:
                return md
            else:
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
                if regex_patterns==[]:
                    return md
                else:
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

def _smart_extract_markdown(source: str | bytes) -> str:
    """使用 Docling 将 PDF 转换为 Markdown, 处理复杂排版。含 OCR 软着陆逻辑。"""
    if not DOCLING_AVAILABLE:
        return "Error: docling not installed. Please run 'pip install docling'."
    # 1. 从环境变量获取 UI 配置
    use_ocr_config = os.getenv("USE_OCR") == "1"
    # 2. 配置 OCR 选项 (工程化降级策略)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = use_ocr_config
    # 把渲染放大倍率缩小，直接能省出一半以上的内存！
    pipeline_options.images_scale = 1.0  
    
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
        # 捕捉内存溢出关键词 (bad_alloc, out of memory, runtimeerror)
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
        return markdown_text[:5000] # 退回到前 15k 字符
        
    return "\n\n---\n\n".join(selected_blocks)[:30000] # 限制长度

def _calculate_relevance_score(text: str, query_keywords: List[str]) -> float:
    """计算关键词在全文中出现的频率评分 (归一化)"""
    if not text or not query_keywords:
        return 0.0
    
    text_lower = text.lower()
    count = 0
    for kw in query_keywords:
        # 使用正则查找单词全匹配，避免子串干扰
        count += len(re.findall(rf"\b{re.escape(kw.lower())}\b", text_lower))
    
    # 使用对数缩放防止长文本刷分，并归一化到 0-1 之间
    # 假设命中 20 次关键词为“满分”水平
    score = math.log1p(count) / math.log1p(20)
    return min(1.0, score)


def _citation_count(paper: Dict[str, Any]) -> int:
    for k in ("citationCount", "citations", "citation_count", "numCitedBy"):
        v = paper.get(k)
        if v is not None:
            try: return int(float(v))
            except: pass
    return 0

def _paper_year(paper: Dict[str, Any]) -> int | None:
    y = paper.get("year")
    try:
        y_int = int(float(y))
        return y_int if 1600 <= y_int <= 2100 else None
    except:
        return None

def score_papers(
    papers: List[Dict[str, Any]],
    query_keywords: List[str],
    *,
    w_venue: float = 0.30,
    w_citation: float = 0.10,
    w_reproducibility: float = 0.10,
    w_relevance: float = 0.50   # 匹配度权重
) -> List[Dict[str, Any]]:
    if not papers: return []
  
    now_year = datetime.utcnow().year
    scored = []
    for p in papers:
        # 1. 基础信息评分 (期刊、引用、开源)
        venue_str = str(p.get("venue") or p.get("publicationVenue") or "")
        rank_info = ranker.get_rank_info(venue_str)
        venue_score = rank_info["score"]

        c = _citation_count(p)
        # 引用评分简化处理：500次以上计为1.0
        citation_norm = min(1.0, math.log1p(c) / math.log1p(500))
        
        has_code = "github.com" in str(p).lower()
        repo_w = 1.0 if has_code else 0.0

        # 2. 全文匹配度评分 (核心修改)
        # 注意：此处调用全文提取逻辑，会产生解析耗时
        # 我们传入空的 regex_patterns 因为此时只为了算词频
        full_text = _paper_full_text(p, []) 
        relevance_score = _calculate_relevance_score(full_text, query_keywords)

        # 3. 计算加权总分
        total_score = (w_venue * venue_score) + \
                      (w_citation * citation_norm) + \
                      (w_reproducibility * repo_w) + \
                      (w_relevance * relevance_score)

        # 4. 时效性奖励 (作为微调项)
        y = _paper_year(p)
        if y and (now_year - y <= 2):
            total_score += 0.01
        # 封装结果
        enriched = dict(p)
        enriched["scholar_score"] = round(float(total_score), 4) # 将总分四舍五入到小数点后四位
        # 保存 type 和 rank 到外层和 breakdown 中
        enriched["venue_type"] = rank_info["type"]
        enriched["venue_rank"] = rank_info["rank"]

        enriched["score_breakdown"] = {
            "venue_level_score": venue_score,
            "venue_type": rank_info["type"],
            "venue_rank": rank_info["rank"],
            "citation_count": c,
            "has_code": has_code,
        }
        enriched["full_text_cache"] = full_text # 缓存全文供 benchmark_node 使用，避免重复解析
        scored.append(enriched)

    # 按分数降序排列
    scored.sort(key=lambda x: x["scholar_score"], reverse=True)
    return scored


def filter_node(state: AgentState) -> Dict[str, Any]: # 过滤论文
    start = time.time()
    # Prefer cloud candidates; if not available yet, fall back to Zotero matches.
    candidates = state.get("candidate_papers") or [] # 获取网络上的候选论文
    zotero = state.get("zotero_matches") or [] # 获取 Zotero 匹配

    # 从 state 中获取查询关键词 (由上游 query_expansion 产生)
    # 如果没有，则退回到原始 query 的切分
    query_keywords = state.get("keywords") or state.get("query", "").split()
    # 从环境变量或 state 获取权重配置（支持界面自定义）
    weights = state.get("scoring_weights", {
        "w_venue": float(os.getenv("W_VENUE", 0.3)),
        "w_citation": float(os.getenv("W_CITATION", 0.1)),
        "w_reproducibility": float(os.getenv("W_REPRO", 0.1)),
        "w_relevance": float(os.getenv("W_RELEVANCE", 0.5))
    })

    # Normalize a bit so the scorer can read venue/citation/year fields.
    combined: List[Dict[str, Any]] = [] # 创建一个空列表，用于存储论文
    for p in candidates: # 遍历候选论文
        combined.append(p) # 将 p 添加到 combined 列表中
    for z in zotero: # 遍历 Zotero 匹配
        combined.append( # 将 z 添加到 combined 列表中
            {
                "title": z.get("title"), # 获取标题
                "venue": z.get("venue"), # 获取出版物
                "year": z.get("year"), # 获取年份
                "citationCount": z.get("citationCount") or z.get("citations") or 0, # 获取引用次数
                "source": z.get("source", "zotero"), # 获取来源
                "abstract": z.get("abstract"), # 获取摘要
                "raw": z.get("raw"), # 获取原始数据
                "local_pdf_path": z.get("local_pdf_path"),
            }
        ) # 将 z 添加到 combined 列表中

    # 2. 【核心去重】剔除历史已展示过的标题
    # history_titles = set(state.get("processed_titles") or [])
    history_titles = []
    unique_candidates = [
        p for p in combined 
        if p.get("title", "").strip().lower() not in history_titles
    ]

    ranked = score_papers(unique_candidates, query_keywords, **weights)
    top = ranked[:10] # 获取得分最高的论文
    # 更新已处理名单：将本轮选出的 top 论文标题加入历史记录
    new_titles = [p.get("title", "").strip().lower() for p in top]
    #updated_history = list(history_titles.union(new_titles))
    updated_history = []
    duration = round(time.time() - start, 2)
    # 更新 state 中的耗时记录
    metrics = state.get("metrics_log")
    metrics["node_durations"]["filter"] = duration
    metrics["total_tokens"]["filter"] = 0
    return {"top_tier_papers": top, 
        "metrics_log": metrics,
        "processed_titles": updated_history  
    } # 状态回传，实现持久化

