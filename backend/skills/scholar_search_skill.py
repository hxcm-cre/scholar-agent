"""
Scholar Search Skill — wraps the existing LangGraph pipeline as a callable tool.

Called by the ChatManager when the LLM decides a literature search is needed.
Runs the full pipeline (assistant→zotero→expansion→cloud→filter→evaluator),
persists results to the Literature table, and returns a structured paper list.
"""
from __future__ import annotations

import json
import os
import time
import traceback
from typing import Any, Dict, List, Optional

from database import Literature, Project, Report, SessionLocal


def scholar_search(
    query: str,
    model_name: str = "qwen3-coder-30b-a3b-instruct",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full LangGraph scholar search pipeline synchronously.

    Returns:
        {
            "success": bool,
            "papers": [
                {"id": int, "index": int, "title": str, "authors": str,
                 "year": int, "venue": str, "abstract": str,
                 "citations": int, "score": float, "url": str}
            ],
            "report_markdown": str,
            "error": str | None,
        }
    """
    from main import build_graph

    db = SessionLocal()
    try:
        # Create a lightweight project record so Literature rows have a parent
        project = Project(
            query=query,
            model_name=model_name,
            status="running",
            weights_json=json.dumps({
                "relevance": 0.5, "venue": 0.3,
                "citation": 0.1, "repro": 0.1,
            }),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id

        os.environ["SELECTED_MODEL_NAME"] = model_name

        thread_id = f"chat_skill_{session_id or 'anon'}_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        graph_app = build_graph()

        run_input = {
            "query": query,
            "zotero_matches": [],
            "candidate_papers": [],
            "top_tier_papers": [],
            "paper_metrics": {},
            "experiment_results": {},
            "analysis_report": "",
            "iteration": 0,
            "max_iterations": 2,
            "done": False,
            "metrics_log": {"total_tokens": {}, "node_durations": {}},
            "user_metrics": "",
            "run_benchmark": False,
        }

        from redis import Redis
        redis_client = Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"), decode_responses=True)
        
        # Emit initial status before the graph starts
        if session_id:
            redis_client.publish(f"chat_status_{session_id}", json.dumps({
                "type": "progress", "node": "start", "detail": "正在分析研究意图..."
            }, ensure_ascii=False))

        # In LangGraph stream(stream_mode="updates"), the event key is the node that JUST COMPLETED.
        # So we map the completed node to the action of the NEXT node.
        NEXT_NODE_LABELS = {
            "assistant": "检索 Zotero 知识库",
            "zotero": "生成相关学术搜索词",
            "query_expansion": "检索云端数据库 (arXiv等)",
            "cloud_search": "过滤高质量并计算相关性",
            "filter": "进行深度阅读与分析报告生成",
            "evaluator": "整理文献总结",
        }

        # Run the graph to completion
        for event in graph_app.stream(run_input, config=config, stream_mode="updates"):
            if session_id:
                for node_name in event.keys():
                    action = NEXT_NODE_LABELS.get(node_name, f"处理中 ({node_name})")
                    redis_client.publish(f"chat_status_{session_id}", json.dumps({
                        "type": "progress",
                        "node": node_name,
                        "detail": f"正在{action}...",
                        "progress": 0.5 # Simple placeholder
                    }, ensure_ascii=False))

        full_state = graph_app.get_state(config).values
        report_md = full_state.get("analysis_report", "")

        # Persist papers to DB
        paper_results: List[Dict[str, Any]] = []
        for idx, paper in enumerate(full_state.get("top_tier_papers", []), start=1):
            lit = Literature(
                project_id=project_id,
                title=paper.get("title", ""),
                authors=(
                    ", ".join(paper.get("authors", []))
                    if isinstance(paper.get("authors"), list)
                    else str(paper.get("authors", ""))
                ),
                year=paper.get("year"),
                venue=paper.get("venue", ""),
                doi=paper.get("doi", ""),
                url=paper.get("url", paper.get("link", "")),
                abstract=paper.get("abstract", "")[:2000],
                citations=int(paper.get("citationCount", paper.get("citations", 0)) or 0),
                score=float(paper.get("_score", paper.get("score", 0)) or 0),
                source=paper.get("source", "arxiv"),
                full_text=paper.get("full_text_cache", ""),
            )
            db.add(lit)
            db.flush()  # get the ID

            paper_results.append({
                "id": lit.id,
                "index": idx,
                "title": lit.title,
                "authors": lit.authors,
                "year": lit.year,
                "venue": lit.venue,
                "abstract": lit.abstract,
                "citations": lit.citations,
                "score": lit.score,
                "url": lit.url,
            })

        # Save report
        report_row = Report(
            project_id=project_id,
            content_markdown=report_md,
            metrics_json=json.dumps(
                full_state.get("metrics_log", {}), ensure_ascii=False
            ),
        )
        db.add(report_row)
        project.status = "done"
        db.commit()

        return {
            "success": True,
            "papers": paper_results,
            "report_markdown": report_md,
            "error": None,
        }

    except Exception as exc:
        traceback.print_exc()
        return {
            "success": False,
            "papers": [],
            "report_markdown": "",
            "error": str(exc)[:500],
        }
    finally:
        db.close()
