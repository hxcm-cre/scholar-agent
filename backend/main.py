from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from src.nodes.assistant_node import assistant_node
from src.nodes.benchmark_node import benchmark_node
from src.nodes.cloud_search_node import cloud_search_node
from src.nodes.filter_node import filter_node
from src.nodes.query_expansion_node import query_expansion_node
from src.nodes.researcher_node import researcher_node
from src.nodes.zotero_node import zotero_search_node
from src.state import AgentState

def _loop_decider(state: AgentState) -> str:
    """
    控制是否继续跑下一轮流水线：
    - 若 benchmark_node 标记 done=True, 则结束;
    - 若已达到 max_iterations 上限, 也结束;
    - 否则回到 cloud_search 继续下一轮。
    """
    iteration = int(state.get("iteration") or 0)
    max_iterations = int(state.get("max_iterations") or 3)
    done = bool(state.get("done"))

    if done:
        return "end"
    if iteration >= max_iterations:
        return "max_reached"
    return "again"


def build_graph() -> Any:
    graph = StateGraph(AgentState)

    # High-level reasoning: Assistant
    graph.add_node("assistant", assistant_node)

    # Local + cloud search:
    graph.add_node("zotero", zotero_search_node)
    graph.add_node("query_expansion", query_expansion_node)
    # graph.add_node("researcher", researcher_node)  # placeholder for future ReAct loop
    graph.add_node("cloud_search", cloud_search_node)

    # Core "Scholar" logic
    graph.add_node("filter", filter_node)
    graph.add_node("evaluator", benchmark_node)

    # Wiring:
    graph.add_edge(START, "assistant")
    # 当前仅支持“文献检索 + 对标”主路径：assistant 解析意图后直接进入 Zotero 分支
    graph.add_edge("assistant", "zotero")

    # literature branch:
    graph.add_edge("zotero", "query_expansion")
    graph.add_edge("query_expansion", "cloud_search")
    graph.add_edge("cloud_search", "filter")
    graph.add_edge("filter", "evaluator")

    # experiment branch comes from router directly to evaluator
    # After each evaluator run, decide whether to loop or end.
    graph.add_conditional_edges(
        "evaluator",
        _loop_decider,
        {
            "again": "query_expansion",  # 继续从云检索开始新一轮
            "end": END,               # 已经得到足够结论
            "max_reached": END,       # 达到最大循环次数，强制结束
        },
    )

    # 持久化检查点
    conn = sqlite3.connect("scholar_agent_checkpoints.db", check_same_thread=False)
    saver = SqliteSaver(conn)

    return graph.compile(checkpointer=saver)


def main() -> int:
    load_dotenv()
    # argparse 模块创建一个命令行界面 允许你在终端运行程序时，通过参数直接输入你的研究问题，而不是每次都去修改 .py 源代码
    parser = argparse.ArgumentParser(description="Scholar-Agent (LangGraph + Zotero + Benchmark)")
    parser.add_argument("--query", type=str, required=True, help="Research question / keywords")
    args = parser.parse_args() # 读取你在终端输入的所有命令，检查是否符合规则。返回一个 args 对象。可以通过 args.query 拿到用户输入的具体文本。
    thread_id = "thread_id001"
    config = {"configurable": {"thread_id": thread_id}} # 只要 thread_id 不变，记忆就在
    app = build_graph()

    current_state = app.get_state(config)
    if not current_state.values:
        # 情况 A: 首轮对话，传入完整 init_state
        run_input = {
            "query": args.query,
            "zotero_matches": [],
            "candidate_papers": [],
            "top_tier_papers": [],
            "paper_metrics": {},
            "experiment_results": {},
            "analysis_report": "",
            "iteration": 0,
            "max_iterations": 2,
            "done": False,
            "metrics_log": {"total_tokens": {}, "node_durations": {}}
        }
    else:
        # 情况 B: 多轮对话，仅更新 query，LangGraph 会自动合并状态
        # 此时旧的 processed_titles 会保留在 Checkpointer 中
        run_input = {"query": args.query}

    out: Dict[str, Any] = app.invoke(run_input, config=config)
    print(out.get("analysis_report", ""))

    # Small hint for local Zotero configuration
    if not (os.getenv("ZOTERO_BBT_PULL_URL") or "").strip():
        print("\n[hint] Set `ZOTERO_BBT_PULL_URL` in .env to enable local Zotero search via Better BibTeX pull export.\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

