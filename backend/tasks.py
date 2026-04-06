import asyncio
import base64
import json
import os
import time
import traceback

import celery
from redis import Redis

from celery_app import celery_app
from database import Literature, Project, Report, SessionLocal
from schemas import NodeStatusEvent, ResearchRequest

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

NODE_LABELS = {
    "assistant": "分析用户研究意图",
    "zotero": "检索 Zotero 本地文献库",
    "query_expansion": "生成扩展搜索关键词",
    "cloud_search": "执行云端学术数据库检索",
    "filter": "根据期刊分区(CCF/CAS)等信息过滤高价值论文",
    "evaluator": "提取 SOTA 指标并与本地实验对标",
}

def publish_status(project_id: int, event: NodeStatusEvent):
    """Publish real-time status to Redis, so FastAPI can broadcast it via Websocket."""
    redis_client.publish(f"ws_project_{project_id}", event.model_dump_json())

@celery_app.task(bind=True, name="run_research_task")
def run_research_task(self, project_id: int, req_dict: dict):  
    # Lazy import graph to speed up worker start
    from main import build_graph

    db = SessionLocal()
    req = ResearchRequest(**req_dict)
    
    try:
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return
            
        proj.status = "running"
        db.commit()

        os.environ["SELECTED_MODEL_NAME"] = req.model_name
        os.environ["USE_OCR"] = "1" if req.use_ocr else "0"

        if req.csv_data:
            csv_path = os.path.join("data", f"upload_{project_id}.csv")
            os.makedirs("data", exist_ok=True)
            with open(csv_path, "wb") as f:
                f.write(base64.b64decode(req.csv_data))
            os.environ["EXPERIMENT_CSV_PATH"] = csv_path

        thread_id = f"project_{project_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # We explicitly clear cancellation flag when starting a task
        cancel_key = f"cancel_project_{project_id}"
        redis_client.delete(cancel_key)

        graph_app = build_graph()

        current_state = graph_app.get_state(config)
        if not current_state.values:
            run_input = {
                "query": req.query,
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
                "user_metrics": req.user_metrics,
                "run_benchmark": req.run_benchmark,
            }
        else:
            run_input = {"query": req.query}

        total_steps = 6
        current_step = 0
        final_state_snapshot = {}
        start_time = time.time()

        loop = asyncio.new_event_loop()
        
        try:
            for event in graph_app.stream(run_input, config=config, stream_mode="updates"):
                # VERY IMPORTANT: check redis for cancellation flag iteratively
                # This is safe across OS (esp. Windows) since SIGTERM isn't always reliable here
                if redis_client.get(cancel_key) == "1":
                    raise Exception("CANCELLED_BY_USER")

                for node_name, node_output in event.items():
                    current_step += 1
                    detail = NODE_LABELS.get(node_name, node_name)
                    progress = min(current_step / total_steps, 1.0)

                    status_event = NodeStatusEvent(
                        type="node_status",
                        node_name=node_name,
                        status="done",
                        detail=f"✅ 已完成: {detail}",
                        progress=progress,
                    )
                    publish_status(project_id, status_event)
                    final_state_snapshot.update(node_output)
        except Exception as e:
            if str(e) == "CANCELLED_BY_USER":
                print(f"Task {project_id} gracefully aborted.")
                proj = db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    proj.status = "cancelled"
                    db.commit()
                publish_status(project_id, NodeStatusEvent(
                    type="error", node_name="", status="error", detail="任务已被用户取消", progress=0
                ))
                return
            else:
                raise e
        finally:
            loop.close()

        # State persistent recovery
        full_state = graph_app.get_state(config).values

        end_time = time.time()
        durations = full_state.get("metrics_log", {}).get("node_durations", {})
        total_tokens = full_state.get("metrics_log", {}).get("total_tokens", {})

        used_model = os.getenv("SELECTED_MODEL_NAME", "Unknown")
        time_cost = sum(durations.values())
        tokens_cost = sum(total_tokens.values()) if isinstance(total_tokens, dict) else 0

        perf_lines = [
            "",
            "---",
            "### 📈 System Performance Metrics",
            f"- 🧠 `LLM Model`: `{used_model}`",
            f"- 👁️ `OCR Mode`: {'Enabled' if req.use_ocr else 'Disabled'}",
            f"- ⏱️ `Total Latency`: {round(time_cost, 2)}s",
            f"- 🎟️ `Total Tokens`: {tokens_cost} tokens",
        ]
        for nk, label in NODE_LABELS.items():
            _map = {"assistant": "assistant", "zotero": "zotero_search",
                     "query_expansion": "query_expansion", "cloud_search": "cloud_search",
                     "filter": "filter", "evaluator": "benchmark_node"}
            real_key = _map.get(nk, nk)
            t = durations.get(real_key, 0)
            tk = total_tokens.get(real_key, 0) if isinstance(total_tokens, dict) else 0
            perf_lines.append(f"  - `{nk}`: {t}s, ({tk} tokens)")

        report_md = full_state.get("analysis_report", "") + "\n".join(perf_lines)

        # Persistence to DB
        for paper in full_state.get("top_tier_papers", []):
            lit = Literature(
                project_id=project_id,
                title=paper.get("title", ""),
                authors=", ".join(paper.get("authors", [])) if isinstance(paper.get("authors"), list) else str(paper.get("authors", "")),
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

        metrics_payload = {
            "node_durations": durations,
            "total_tokens": total_tokens,
            "total_latency": round(end_time - start_time, 2),
        }
        report_row = Report(
            project_id=project_id,
            content_markdown=report_md,
            metrics_json=json.dumps(metrics_payload, ensure_ascii=False),
        )
        db.add(report_row)
        
        proj.status = "done"
        db.commit()

        publish_status(project_id, NodeStatusEvent(
            type="complete", node_name="", status="done",
            detail="研究任务已完成", progress=1.0
        ))
        
    except Exception as exc:
        traceback.print_exc()
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            proj.status = "error"
            proj.error_message = str(exc)[:2000]
            db.commit()

        publish_status(project_id, NodeStatusEvent(
            type="error", node_name="", status="error", detail=str(exc)[:500], progress=0
        ))
    finally:
        db.close()
