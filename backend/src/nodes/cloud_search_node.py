from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

from src.state import AgentState
import time # 导入时间模块

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _arxiv_http_search(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Search papers on arXiv using the public Atom API.

    Note: This returns arXiv preprints (with direct PDF URLs), which avoids the
    'publisher landing page without PDF' problem common in other APIs.
    """
    if not query.strip():
        return []

    # arXiv API uses a simple query language. We keep it robust by searching over "all" fields.
    params = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(limit),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    url = f"{ARXIV_API_URL}?{params}" # 拼接 URL
    req = urllib.request.Request(url, headers={"User-Agent": "Scholar-Agent/0.1"}) # 创建请求
    with urllib.request.urlopen(req, timeout=15) as resp: # 打开 URL
        return _parse_arxiv_atom(resp.read().decode("utf-8", errors="replace"))

# 解析 arXiv API 返回的 XML 格式（Atom 协议）数据，并将其转化为一个包含论文元数据的字典列表。
def _parse_arxiv_atom(atom_xml: str) -> List[Dict[str, Any]]:
    # 定义 XML 命名空间。'atom' 是标准协议，'arxiv' 是 arXiv 特有的扩展（如 DOI 存储在这里）
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(atom_xml) # 使用 ElementTree (ET) 解析传入的 XML 字符串，获取根节点
    out: List[Dict[str, Any]] = [] # 初始化一个空列表，用于存放最终解析出来的结果
    
    # 遍历 XML 中所有的 <entry> 标签，每个标签代表一篇论文
    for entry in root.findall("atom:entry", ns):
        # 提取论文的唯一 ID URL (例如 http://arxiv.org/abs/2106.15928)
        abs_url = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        # 提取标题，并利用 split() 和 join() 将多余的换行符或空格压缩成单空格
        title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
        # 提取摘要（Summary），同样进行空格压缩处理
        summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
        # 提取发布日期字符串（格式通常为 2021-06-28T...）
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
        year = None
        # 解析年份：如果日期字符串前 4 位是数字，则转为整数保存
        if len(published) >= 4 and published[:4].isdigit():
            year = int(published[:4])
        # 寻找官方 PDF 链接。ArXiv 的 link 标签可能有多个版本（HTML, PDF）
        # Prefer the official PDF link if present; otherwise derive from abs URL.
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            # 方式 A：检查 link 标签是否有 title="pdf"
            if (link.get("title") or "").lower() == "pdf":
                pdf_url = (link.get("href") or "").strip()
                break
            # 方式 B：检查 link 标签的 MIME 类型是否为 PDF
            if (link.get("type") or "").lower() == "application/pdf":
                pdf_url = (link.get("href") or "").strip()
                break
        # 兜底方案：如果标签里没写 PDF 地址，但有网页地址 (/abs/)，
        # 则根据 ArXiv 规则手动拼接成 PDF 地址 (/pdf/...pdf)
        if not pdf_url and "/abs/" in abs_url:
            pdf_url = abs_url.replace("/abs/", "/pdf/") + ".pdf"

        # 从 URL 末尾截取 ArXiv ID（例如 "2106.15928"），用于后续去重
        arxiv_id = abs_url.rsplit("/", 1)[-1].strip()

        # 尝试提取 DOI。注意这里使用的是 'arxiv:' 命名空间，
        # 因为 DOI 不在标准 Atom 字段中，而是 arXiv 自定义扩展
        doi = (entry.findtext("arxiv:doi", default="", namespaces=ns) or "").strip()

        out.append(
            {
                "paperId": arxiv_id,
                "title": title,
                "venue": "arXiv",
                "year": year,
                "citationCount": 0,
                "abstract": summary,
                "doi": doi,
                "url": abs_url,
                "source": "arxiv",
                "raw": {
                    "id": abs_url,
                    "arxivId": arxiv_id,
                    "published": published,
                    "openAccessPdf": {"url": pdf_url} if pdf_url else {},
                    "url": abs_url,
                },
            }
        )
    return out


def _dedup_by_doi_and_id(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]: # 去重
    seen_doi = set() # 创建一个集合，用于存储 DOI
    seen_id = set() # 创建一个集合，用于存储 ID
    result: List[Dict[str, Any]] = [] # 创建一个空列表，用于存储结果
    for p in papers:
        doi = (p.get("doi") or "").lower().strip() # 获取 DOI
        pid = (str(p.get("paperId")) if p.get("paperId") is not None else "").strip() # 获取 ID
        if doi and doi in seen_doi:
            continue # 如果 DOI 已经在集合中，则跳过
        if pid and pid in seen_id:
            continue # 如果 ID 已经在集合中，则跳过
        if doi:
            seen_doi.add(doi) # 将 DOI 添加到集合中
        if pid:
            seen_id.add(pid) # 将 ID 添加到集合中
        result.append(p) # 将 p 添加到结果列表中
    return result # 返回结果列表


def cloud_search_node(state: AgentState) -> Dict[str, Any]: # 云搜索
    """
    Cloud search over arXiv (public Atom API).
    Implements the "after Zotero, then cloud, dedup by DOI" logic.
    """ # 云搜索实现 "在 Zotero 之后，然后是云搜索，去重 by DOI" 逻辑。
    start = time.time()
    base_query = (state.get("query") or "").strip() # 获取查询
    expanded = state.get("current_queries") or [] # 获取扩展查询
    
    # 结合基础查询和扩展查询
    query_parts = []
    if base_query:
        query_parts.append(base_query)
    if expanded:
        query_parts.extend(expanded)
        
    combined_query = " ".join(query_parts)

    zotero = state.get("zotero_matches") or [] # 获取 Zotero 匹配
    zotero_dois = {str(z.get("doi") or "").lower().strip() for z in zotero if z.get("doi")} # 获取 Zotero DOI

    all_candidates: List[Dict[str, Any]] = [] # 创建一个空列表，用于存储候选论文
    errors: List[str] = [] # 创建一个空列表，用于存储错误

    try:
        # 一次性调用搜索接口，获取较多结果
        items = _arxiv_http_search(combined_query, limit=5)
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as e:
        errors.append(f"arxiv_http_failed:{e}")
        items = []

    for p in items:
        doi = (p.get("doi") or "").lower().strip() # 获取 DOI
        if doi and doi in zotero_dois: # 如果 DOI 已经在集合中，则跳过
            # Skip duplicates already present in Zotero library
            continue # 跳过重复的论文
        all_candidates.append(p) # 将论文添加到候选论文列表中

    deduped = _dedup_by_doi_and_id(all_candidates) # 去重

    # Optionally attach debug info in memory_checklist
    mem = state.get("memory_checklist") or [] # 获取记忆清单
    if errors:
        mem.append({"type": "cloud_search", "errors": errors[:5], "n_candidates": len(deduped)}) # 将错误添加到记忆清单中
    duration = round(time.time() - start, 2)
    # 更新 state 中的耗时记录
    metrics = state.get("metrics_log")
    metrics["node_durations"]["cloud_search"] = duration
    metrics["total_tokens"]["cloud_search"] = 0
    return {"candidate_papers": deduped, "memory_checklist": mem, "metrics_log": metrics} # 返回候选论文和记忆清单

