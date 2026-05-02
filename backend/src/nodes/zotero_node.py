from __future__ import annotations

import asyncio
import json
import os
import re # 正则表达式库
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Tuple
import time # 导入时间模块
from src.state import AgentState


def _tokenize(text: str) -> List[str]: # 将文本转换为小写，并去除非字母和数字的字符
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text) # 将文本中的非字母和数字的字符替换为空格
    return [t for t in text.split() if t] # 将文本按空格分隔，并去除空字符串


def _csljson_authors(item: Dict[str, Any]) -> str: # 获取作者信息
    # 1. 适配 BetterBibTeX JSON 的键名 'creators'
    authors = item.get("creators") or item.get("author") or item.get("creator") or [] 
    
    parts: List[str] = []
    for a in authors:
        if isinstance(a, str):
            parts.append(a)
            continue
        
        # 2. 优先提取 BetterBibTeX 的 firstName 和 lastName
        first = (a.get("firstName") or "").strip()
        last = (a.get("lastName") or "").strip()
        
        # 3. 兼容原始 CSL-JSON 的 given 和 family
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        
        # 4. 获取 literal (机构名或单姓名)
        literal = (a.get("literal") or "").strip()
        
        if literal:
            parts.append(literal)
        elif first or last:
            # 拼接 BetterBibTeX 格式：名字 + 姓氏
            parts.append(f"{first} {last}".strip())
        elif given or family:
            # 拼接 CSL 格式
            parts.append(f"{given} {family}".strip())
    return ", ".join([p for p in parts if p]) # 将列表中的所有作者信息拼接成一个字符串，并使用逗号分隔


def _csljson_year(item: Dict[str, Any]) -> int | None: # 获取出版年份
    # 1. 优先尝试获取 BetterBibTeX 的字符串日期 'date': '12/2019'
    date_str = item.get("date")
    if isinstance(date_str, str) and date_str:
        # 使用正则表达式提取 4 位连续数字（年份）
        match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if match:
            return int(match.group(0))
    # 2. 兼容原始 CSL-JSON 逻辑 (以防万一)        
    issued = item.get("issued") or {} # 获取出版年份。尝试从 item 字典中获取 issued（发行日期）
    date_parts = issued.get("date-parts") if isinstance(issued, dict) else None # date-parts 是 CSL 标准中存放日期数字的地方，获取出版年份的date-parts
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]: # 如果出版年份的date-parts是列表，并且列表不为空，并且列表的第一个元素是列表，并且列表的第一个元素不为空
        y = date_parts[0][0] # 获取出版年份的第一个元素
        if isinstance(y, int):
            return y # 如果出版年份的第一个元素是整数，则返回整数
    return None


def _fetch_bbt_pull_export(pull_url: str) -> List[Dict[str, Any]]: # 获取 Better BibTeX 导出
    """
    Better BibTeX 'pull export' returns an export in the requested format.
    We expect CSL-JSON (`.json`) which yields a list of items.
    """
    if not pull_url:
        return []  # 返回空列表
    req = urllib.request.Request(pull_url, headers={"User-Agent": "Scholar-Agent/0.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list): # 如果 data 是字典，并且 "items" 键存在，并且 "items" 键的值是列表
        # Some exports wrap items under a key # 有些导出将 items 包裹在一个键下
        return data["items"]
    if isinstance(data, list): # 如果 data 是列表，则返回列表
        return data
    raise ValueError("Unexpected Better BibTeX export JSON structure") # 如果 data 不是字典或列表，则抛出异常


async def _mcp_search(server_script_path: str, tool_name: str, query: str) -> Any: # 通过 MCP 搜索
    """
    Best-effort MCP client call (stdio transport).

    Environment:
    - ZOTERO_MCP_SERVER_SCRIPT: path to your MCP server script (.py/.js)
    - ZOTERO_MCP_TOOL_NAME: tool name exposed by that server (default: zotero.search) 
    """
    from contextlib import AsyncExitStack # 异步上下文管理器

    from mcp import ClientSession, StdioServerParameters # MCP 客户端会话和标准输入输出服务器参数
    from mcp.client.stdio import stdio_client # 标准输入输出客户端

    is_python = server_script_path.lower().endswith(".py") # 如果服务器脚本路径以 .py 结尾，则认为是 Python 脚本
    command = "python" if is_python else "node" # 如果服务器脚本路径以 .py 结尾，则使用 Python 命令，否则使用 Node.js 命令

    server_params = StdioServerParameters( # 创建标准输入输出服务器参数
        command=command,
        args=[server_script_path], # 服务器脚本路径
        env=os.environ.copy(), # 复制环境变量
    ) 

    async with AsyncExitStack() as stack: # 异步上下文管理器
        stdio, write = await stack.enter_async_context(stdio_client(server_params)) # 创建标准输入输出客户端
        session = await stack.enter_async_context(ClientSession(stdio, write)) # 创建 MCP 客户端会话
        await session.initialize() # 初始化 MCP 客户端会话
        result = await session.call_tool(tool_name, {"query": query}) # 调用 MCP 工具
        return result # 返回 MCP 工具结果


def _try_search_via_mcp(query: str) -> Tuple[List[Dict[str, Any]] | None, List[str]]: # 尝试通过 MCP 搜索
    server_script = (os.getenv("ZOTERO_MCP_SERVER_SCRIPT") or "").strip() # 获取 MCP 服务器脚本路径
    tool_name = (os.getenv("ZOTERO_MCP_TOOL_NAME") or "zotero.search").strip() 
    if not server_script: # 如果 MCP 服务器脚本路径为空，则返回空列表
        return None, []

    try:
        result = asyncio.run(_mcp_search(server_script, tool_name, query)) # 运行 MCP 搜索
        # Python SDK returns a CallToolResult with `.content` blocks.
        content = getattr(result, "content", result) # 获取 MCP 工具结果的 content 属性
        # 一个工具的返回结果（result）会被拆分成多个 “块 (Blocks)”
        # content:是一个 列表 (List)。
        # b (Block): 货架上的一个个“纸箱”。每个纸箱里可能装的是文本（Text Block），也可能装的是图片（Image Block）。
        # 例如content = [
        # 块 1 (b1): [{"title": "Paper A", "year": 2023},
        # 块 2 (b2): {"title": "Paper B", "year": 2024}]
        # ]

        # Try to extract a JSON payload.
        if isinstance(content, str): # 如果 content 是字符串，把 JSON 字符串“加载”（Load）成 Python 对象（链表或者字符串或者其他）
            payload = json.loads(content)
        elif isinstance(content, list) and content: # 如果 content 是列表，并且列表不为空，则将 content 转换为 JSON 对象
            # Concatenate text blocks if present
            texts: List[str] = [] # 创建一个空列表，用于存储文本
            for b in content:
                t = getattr(b, "text", None) # 获取文本
                if t: # 如果文本不为空，则将文本添加到列表中
                    texts.append(t)
                elif isinstance(b, dict) and "text" in b: # 如果文本是字典，并且 "text" 键存在，则将文本添加到列表中
                    texts.append(str(b["text"])) # 将文本转换为字符串，并添加到列表中
            payload = json.loads("\n".join(texts)) if texts else content # 将列表中的所有文本拼接成一个字符串，重新还原成 Python 数据结构（链表或者字符串或者其他）
        else:
            payload = content # 如果 content 不是字符串或列表，则将 content 赋值给 payload

        if isinstance(payload, list): # 如果 payload 是列表，则返回列表
            # Assume already list[dict] 遍历 payload 列表中的每一个元素 p，如果是字典：直接保留原样 p；如果 p 不是字典，把它塞进一个字典里，起名叫 raw
            return [p if isinstance(p, dict) else {"raw": p} for p in payload], [] 
        if isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list): # 如果 payload 是字典，并且 "items" 键存在，并且 "items" 键的值是列表，则返回列表
            return [p if isinstance(p, dict) else {"raw": p} for p in payload["items"]], []
        return None, [f"mcp_unexpected_payload_type: {type(payload)}"] # 如果 payload 不是字典或列表，则返回空列表和错误信息
    except Exception as e:  # noqa: BLE001 - best-effort
        return None, [f"mcp_failed: {e}"]


def _format_match(item: Dict[str, Any]) -> Dict[str, Any]: # 格式化匹配
    title = (item.get("title") or "").strip() # 获取标题
    abstract = (item.get("abstract") or item.get("abstractNote") or "").strip() # 获取摘要

    # 尝试从 CSL/Better BibTeX 导出的条目中恢复“本地 PDF 文件路径”（如果存在）
    local_pdf_path = ""
    attachments = item.get("attachments") or item.get("attachment") or [] # 有些导出使用 attachments / attachment 字段保存附件信息
    if isinstance(attachments, list):
        for a in attachments:
            if not isinstance(a, dict): # 跳过非字典类型的附件描述
                continue
            mime = (a.get("mimeType") or "").lower()
            path = (a.get("path") or a.get("localPath") or "").strip() # path/localPath 通常是 Zotero 存储的相对或绝对路径
            if path and ("pdf" in mime or path.lower().endswith(".pdf")): # 只关心 PDF 附件
                local_pdf_path = path
                break

    # 某些导出会把附件写进 file 字段（例如 'C:\\...\\paper.pdf' 或 'storage:XYZ.pdf'）
    if not local_pdf_path:
        file_field = (item.get("file") or "").strip()
        if file_field:
            local_pdf_path = file_field

    # 为了后续 benchmark_node._paper_full_text 可以优先读取本地 PDF，
    # 我们把解析出的路径塞回 raw 里（不改变原始 JSON 结构的其它字段）
    if local_pdf_path:
        try:
            if isinstance(item, dict):
                item["local_pdf_path"] = local_pdf_path
        except Exception:  # noqa: BLE001 - best-effort enrichment
            pass
    return {
        "title": title, # 设置标题
        "authors": _csljson_authors(item), # 设置作者
        "year": _csljson_year(item), # 设置出版年份
        "venue": (item.get("publicationTitle") or item.get("journalAbbreviation") or item.get("conferenceName") or item.get("proceedingsTitle") or "").strip(), # 设置出版物
        "doi": (item.get("DOI") or item.get("doi") or "").strip(), # 设置 DOI
        "url": (item.get("URL") or item.get("url") or "").strip(), # 设置 URL
        "abstract": abstract, # 设置摘要
        "tags": item.get("keyword") or item.get("tags") or [], # 设置标签
        "source": "zotero_better_bibtex", # 设置来源    
        "raw": item, # 设置原始数据 
        "local_pdf_path": local_pdf_path, # 如果存在，则暴露一个显式的本地 PDF 路径字段，便于调试与下游使用
    }


def search_local_zotero(query: str, *, top_k: int = 5) -> List[Dict[str, Any]]: # 搜索本地 Zotero
    """
    Search local Zotero via Better BibTeX pull export (recommended) or a local JSON cache.

    Setup (recommended):
    - Install Better BibTeX in Zotero
    - Right click Library/Collection -> "Download Better BibTeX export..." -> copy URL
    - Put it in env `ZOTERO_BBT_PULL_URL` (CSL-JSON `.json` suggested)
    """
    query = (query or "").strip()
    if not query:
        return []

    # Option A: MCP (if user has a Zotero MCP server configured) MCP 选项
    mcp_items, mcp_errors = _try_search_via_mcp(query) # 尝试通过 MCP 搜索
    if mcp_items is not None: # 如果 MCP 搜索结果不为空，则将 MCP 搜索结果赋值给 items
        items = mcp_items # 将 MCP 搜索结果赋值给 items
        errors = mcp_errors # 将 MCP 搜索错误赋值给 errors
    else:
        items = [] # 将空列表赋值给 items
        errors = mcp_errors # 将 MCP 搜索错误赋值给 errors

    pull_url = (os.getenv("ZOTERO_BBT_PULL_URL") or "").strip() # 获取 Better BibTeX 导出 URL
    if not items and pull_url: # 如果 items 为空，并且 pull_url 不为空，则尝试通过 Better BibTeX 导出 URL 获取数据
        try:
            items = _fetch_bbt_pull_export(pull_url) # 通过 Better BibTeX 导出 URL 获取数据
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
            errors.append(f"bbt_pull_url_failed: {e}")

    if not items: # 如果 items 为空，则尝试通过 JSON 快照获取数据
        # Optional fallbacks: user may export JSON snapshots here. 
        fallback_candidates = [
            os.path.join("data", "zotero_export.json"), # data/zotero_export.json：首选路径，通常放在专门的数据文件夹里。
            os.path.join("zotero.json"), # zotero.json：备用路径，通常放在项目根目录下。
            os.path.join(os.path.expanduser("~"), "Desktop", "zoteroData.json"), # 你的本地导出：桌面上的 zoteroData.json
        ]
        for fallback_path in fallback_candidates:
            if not os.path.exists(fallback_path): # 如果 fallback_path 不存在，则跳过
                continue
            try:
                with open(fallback_path, "r", encoding="utf-8") as f: # 打开 JSON 快照文件
                    data = json.load(f) # 加载 JSON 快照文件
                if isinstance(data, list):
                    items = data # 如果 data 是列表，则将 data 赋值给 items
                elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                    items = data["items"] # 如果 data 是字典，并且 "items" 键存在，并且 "items" 键的值是列表，则将 "items" 键的值赋值给 items
                if items: # 如果 items 不为空，则跳出循环
                    break
            except Exception as e:  # noqa: BLE001 - best-effort fallback
                errors.append(f"fallback_json_failed:{os.path.basename(fallback_path)}:{e}")

    if not items: # 如果 items 为空，则返回空列表
        return []

    q_tokens = _tokenize(query) # 将查询转换为小写，并去除非字母和数字的字符
    scored: List[Tuple[float, Dict[str, Any]]] = [] # 创建一个空列表，用于存储得分和匹配项
    for it in items:
        hay = " ".join( # 将查询中的所有单词拼接成一个字符串
            [
                str(it.get("title") or ""), # 获取标题
                str(it.get("abstract") or it.get("abstractNote") or ""), # 获取摘要
                str(it.get("container-title") or ""), # 获取出版物
                str(it.get("DOI") or it.get("doi") or ""), # 获取 DOI
                _csljson_authors(it), # 获取作者
            ]
        )
        h_tokens = set(_tokenize(hay)) # 将 hay 转换为集合
        if not h_tokens: # 如果 h_tokens 为空，则跳过
            continue

        hits = sum(1 for t in q_tokens if t in h_tokens) # 计算查询中的单词在 hay 中出现的次数
        if hits == 0: # 如果 hits 为 0，则跳过
            continue
        score = hits / max(len(q_tokens), 1) # 计算得分
        scored.append((score, it)) # 将得分和匹配项添加到列表中

    scored.sort(key=lambda x: x[0], reverse=True) # 将列表按得分排序
    matches = [_format_match(it) for _, it in scored[:top_k]] # 将列表中的所有匹配项格式化
    if errors:
        # attach a lightweight hint on first item to help debugging without bloating state
        if matches:
            matches[0]["_debug"] = {"errors": errors, "count_items_seen": len(items)}
    return matches


def zotero_search_node(state: AgentState) -> Dict[str, Any]: # 搜索本地 Zotero
    start = time.time()

    query = (state.get("query") or "").strip() # 获取查询
    matches = search_local_zotero(query) # 搜索本地 Zotero 并返回匹配结果

    duration = round(time.time() - start, 2)
    # 更新 state 中的耗时记录
    metrics = state.get("metrics_log", {"total_tokens": {}, "node_durations": {}}) 
    metrics["node_durations"]["zotero_search"] = duration
    metrics["total_tokens"]["zotero_search"] = 0
    return {"zotero_matches": matches, "metrics_log": metrics} # 返回本地 Zotero 匹配结果

