from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage

# TypedDict规定字典必须包含哪些特定的键以及每个键对应的数据类型
# 设置 total=False 时，它允许字典中缺失某些定义的键
class AgentState(TypedDict, total=False):
    """
    LangGraph state for Scholar-Agent.

    total=False keeps the workflow flexible during early scaffolding:
    nodes can progressively add fields without having to populate everything up-front.
    """

    query: str

    chat_history: List[BaseMessage]  # 存储对话上下文

    # Local Zotero matches (prior knowledge / MCP)
    zotero_matches: List[Dict[str, Any]]

    # Cloud / external candidates (e.g., Semantic Scholar)
    candidate_papers: List[Dict[str, Any]]

    # After weighted filtering
    top_tier_papers: List[Dict[str, Any]]

    processed_titles: List[str]      # 新增：记录所有已输出过的论文标题

    # Extracted quantitative metrics from papers
    paper_metrics: Dict[str, Any]

    # Local experiment evaluation output (e.g., RMSE)
    experiment_results: Dict[str, Any]

    # Final synthesized report
    analysis_report: str

    # Loop control for multi-iteration benchmark runs
    # 当前调用是第几轮流水线（从 1 开始计数）
    iteration: int
    # 允许的最多循环次数（可以在初始 state 中设置）
    max_iterations: int
    # 本轮是否已经获得“足够的信息”给出结论
    done: bool

    # --- High-level control / reasoning ---
    # Parsed user intent, e.g. "literature", "experiment", "answer"
    intent: str

    # Expanded academic-style queries for cloud search
    expanded_queries: List[str]
    current_queries: List[str]
    # Lightweight memory checklist to avoid state bloat
    memory_checklist: List[Dict[str, Any]]

    # Optional: raw text used for metric extraction
    paper_texts: List[Dict[str, Any]]

    # Optional: debug info
    debug: Dict[str, Any]
    
    metrics_log: Dict[str, Any] # 用于存放：{"tokens": {}, "node_durations": {}}

    domain_metrics: List[str] # 例如 ["RMSE", "MAE", "Accuracy", "F1-score"]