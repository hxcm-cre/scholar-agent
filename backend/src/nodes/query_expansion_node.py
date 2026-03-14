from __future__ import annotations

from typing import Dict, List
import os
from src.state import AgentState
from src.llm import make_qwen_llm
import time # 导入时间模块

QUERY_EXPANSION_SYSTEM_PROMPT = """\
You are a literature search assistant.
Review the original user query and the list of previously tried queries, propose 3-5 concise,
NEW, specific, academic-style search queries suitable for arXiv.
DO NOT repeat the 'ALREADY SEARCHED' list
Return JSON only:
{"expanded_queries": [string, ...]}
"""


def query_expansion_node(state: AgentState) -> Dict:
    start = time.time()
    # 1. 基础信息提取
    original_query = (state.get("query") or "").strip()
    zotero = state.get("zotero_matches") or []
    # 历史已经尝试过的扩展词列表
    history_expanded = state.get("expanded_queries") or [] 
    
    # 本轮新生成的候选词
    new_candidates: List[str] = []
    tokens = 0

    # LLM 智能扩展逻辑
    if original_query:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            current_model = os.getenv("SELECTED_MODEL_NAME", "qwen2.5-32b-instruct")
            llm = make_qwen_llm(model_name=current_model, temperature=0.0)
            titles = [z.get("title", "") for z in zotero[:10]]
            seed_text = "Seed titles from Zotero:\n" + "\n".join(f"- {t}" for t in titles if t)
            history_text = "ALREADY SEARCHED (DO NOT REPEAT):\n" + "\n".join(f"- {h}" for h in history_expanded)

            messages = [
                SystemMessage(content=QUERY_EXPANSION_SYSTEM_PROMPT),
                HumanMessage(content=f"Original Query: {original_query}\n\n{history_text}\n\n{seed_text}")
            ]
            
            resp = llm.invoke(messages)
            
            # 安全提取 Token (量化表达)
            tokens = resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
            content = getattr(resp, "content", "") # 获取内容
            if isinstance(content, str):
                import json

                # 清洗 Markdown 代码块包裹
                clean_json = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                new_candidates = data.get("expanded_queries") or [] # 将模型扩展的查询添加到列表中
        except Exception:  # noqa: BLE001
            pass

    # 4. 增量更新与去重 (保持顺序)
    # 将本轮生成的词与历史记录合并
    # 3. 严格去重：确保 new_candidates 中不包含 history_expanded 里的任何词
    history_set = {h.lower().strip() for h in history_expanded}
    # 仅保留真正“新”的搜索词
    this_round_queries = [q for q in new_candidates if q.lower().strip() not in history_set]
     

    # 累加 Token 消耗
    duration = round(time.time() - start, 2) 
    # 更新 state 中的耗时记录
    metrics = state.get("metrics_log")
    metrics["node_durations"]["query_expansion"] = duration
    metrics["total_tokens"]["query_expansion"] = tokens
    return {
        "expanded_queries": history_expanded + this_round_queries, # 更新历史足迹
        "current_queries": this_round_queries, # 供 paper_search 使用的增量
        "metrics_log": metrics
        }

