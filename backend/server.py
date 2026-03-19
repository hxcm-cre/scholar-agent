"""
FastAPI server for Scholar-Agent.

Exposes REST endpoints + WebSocket for real-time agent status.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import traceback
from collections import defaultdict
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Project, Literature, Report, SessionLocal, get_db, init_db
from schemas import (
    NodeStatusEvent,
    ProjectDetail,
    ProjectOut,
    ResearchRequest,
)

load_dotenv()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Scholar-Agent API", version="1.0.0")

# Allow origins from environment variable, stripping spaces
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
if cors_env == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in cors_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    """Manages per-project WebSocket connections."""

    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, project_id: int, ws: WebSocket):
        await ws.accept()
        self._connections[project_id].append(ws)

    def disconnect(self, project_id: int, ws: WebSocket):
        if project_id in self._connections:
            if ws in self._connections[project_id]:
                self._connections[project_id].remove(ws)
            if not self._connections[project_id]:
                del self._connections[project_id]

    async def broadcast(self, project_id: int, event: NodeStatusEvent):
        dead: list[WebSocket] = []
        for ws in self._connections.get(project_id, []):
            try:
                await ws.send_text(event.model_dump_json())
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(project_id, ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Node label mapping (for UI display)
# ---------------------------------------------------------------------------
NODE_LABELS: Dict[str, str] = {
    "assistant": "分析用户研究意图",
    "zotero": "检索 Zotero 本地文献库",
    "query_expansion": "生成扩展搜索关键词",
    "cloud_search": "执行云端学术数据库检索",
    "filter": "根据期刊分区(CCF/CAS)等信息过滤高价值论文",
    "evaluator": "提取 SOTA 指标并与本地实验对标",
}


# ---------------------------------------------------------------------------
# Background agent runner
# ---------------------------------------------------------------------------
def _run_agent_sync(project_id: int, req: ResearchRequest):
    """
    Runs the LangGraph agent synchronously (called via asyncio.to_thread).
    Broadcasts node status via the WebSocket manager.
    """
    # --- lazy import so server startup stays fast ---
    from main import build_graph

    db: Session = SessionLocal()
    try:
        # Update project status → running
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return
        proj.status = "running"
        db.commit()

        # Configure env
        os.environ["SELECTED_MODEL_NAME"] = req.model_name
        os.environ["USE_OCR"] = "1" if req.use_ocr else "0"

        # Handle optional CSV upload
        csv_path = None
        if req.csv_data:
            csv_path = os.path.join("data", f"upload_{project_id}.csv")
            os.makedirs("data", exist_ok=True)
            with open(csv_path, "wb") as f:
                f.write(base64.b64decode(req.csv_data))
            os.environ["EXPERIMENT_CSV_PATH"] = csv_path

        # Build & run graph
        thread_id = f"project_{project_id}"
        config = {"configurable": {"thread_id": thread_id}}
        graph_app = build_graph()

        run_input: Dict[str, Any] = {
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
        }

        total_steps = 6
        current_step = 0
        final_state_snapshot: Dict[str, Any] = {}
        start_time = time.time()

        loop = asyncio.new_event_loop()

        for event in graph_app.stream(run_input, config=config, stream_mode="updates"):
            for node_name, node_output in event.items():
                current_step += 1
                detail = NODE_LABELS.get(node_name, node_name)
                progress = min(current_step / total_steps, 1.0)

                # Broadcast via WebSocket
                status_event = NodeStatusEvent(
                    type="node_status",
                    node_name=node_name,
                    status="done",
                    detail=f"✅ 已完成: {detail}",
                    progress=progress,
                )
                loop.run_until_complete(manager.broadcast(project_id, status_event))

                final_state_snapshot.update(node_output)

        # Full state from checkpointer
        full_state = graph_app.get_state(config).values

        end_time = time.time()
        durations = full_state.get("metrics_log", {}).get("node_durations", {})
        total_tokens = full_state.get("metrics_log", {}).get("total_tokens", {})

        # Build performance footer
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

        # --- Persist to DB ---
        # 1. Literature
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

        # 2. Report
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

        # 3. Update project status
        proj.status = "done"
        db.commit()

        # Broadcast completion
        loop.run_until_complete(
            manager.broadcast(
                project_id,
                NodeStatusEvent(type="complete", node_name="", status="done",
                                detail="研究任务已完成", progress=1.0),
            )
        )
        loop.close()

    except Exception as exc:
        traceback.print_exc()
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            proj.status = "error"
            proj.error_message = str(exc)[:2000]
            db.commit()

        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                manager.broadcast(
                    project_id,
                    NodeStatusEvent(type="error", node_name="", status="error",
                                    detail=str(exc)[:500], progress=0),
                )
            )
            loop.close()
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# REST Endpoints - Projects
# ---------------------------------------------------------------------------
@app.post("/api/research", response_model=ProjectOut)
async def create_research(req: ResearchRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a project and start the agent in background."""
    import json as _json

    project = Project(
        query=req.query,
        model_name=req.model_name,
        status="pending",
        weights_json=_json.dumps(req.weights.model_dump(), ensure_ascii=False),
        user_metrics=req.user_metrics,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Launch background thread
    bg.add_task(asyncio.to_thread, _run_agent_sync, project.id, req)

    return project


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    """Return all projects, newest first."""
    return db.query(Project).order_by(Project.created_at.desc()).all()


@app.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Return full project detail including literature and reports."""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete project and all related data."""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(proj)
    db.commit()
    return {"detail": "deleted"}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/research/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    await manager.connect(project_id, websocket)
    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
