"""
FastAPI server for Scholar-Agent (OpenClaw-style conversational mode).

Exposes chat-centric REST endpoints + legacy project endpoints.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import traceback
import uuid
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import (
    ChatMessage, ChatSession, Literature, Project, Report,
    SessionLocal, get_db, init_db,
)
from schemas import (
    ChatMessageOut,
    ChatMessageRequest,
    ChatReply,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionOut,
    LiteratureOut,
    NodeStatusEvent,
    ProjectDetail,
    ProjectOut,
    ResearchRequest,
)
from models_config import AVAILABLE_MODELS

load_dotenv()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Scholar-Agent API", version="2.0.0")

@app.get("/api/models")
def get_available_models():
    """List all available AI models for both search and chat."""
    return {"models": AVAILABLE_MODELS}

# CORS
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
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    init_db()


# =========================================================================
# NEW: Chat Session API (OpenClaw-style conversational endpoints)
# =========================================================================

@app.post("/api/chat/sessions", response_model=ChatSessionOut)
def create_chat_session(req: ChatSessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session."""
    session = ChatSession(
        id=str(uuid.uuid4()),
        title="新对话",
        model_name=req.model_name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/api/chat/sessions", response_model=List[ChatSessionOut])
def list_chat_sessions(db: Session = Depends(get_db)):
    """List all chat sessions, newest first."""
    return (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


@app.get("/api/chat/sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Get a session with its full message history and associated papers."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build messages output with parsed paper_refs
    messages_out = []
    all_paper_ids = set()
    for m in session.messages:
        try:
            refs = json.loads(m.paper_refs) if m.paper_refs else []
        except (json.JSONDecodeError, TypeError):
            refs = []
        messages_out.append(ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_name=m.tool_name,
            paper_refs=refs,
            created_at=m.created_at,
        ))
        all_paper_ids.update(refs)

    # Load associated papers
    papers = []
    if all_paper_ids:
        lits = db.query(Literature).filter(Literature.id.in_(all_paper_ids)).all()
        papers = [LiteratureOut.model_validate(lit) for lit in lits]

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        model_name=session.model_name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages_out,
        papers=papers,
    )


@app.delete("/api/chat/sessions/{session_id}")
def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session and all its messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"detail": "deleted"}


@app.post("/api/chat/sessions/{session_id}/message", response_model=ChatReply)
async def send_chat_message(
    session_id: str,
    req: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message to a chat session.
    The ChatManager decides whether to invoke skills or answer directly.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update model if changed
    if req.model_name and req.model_name != session.model_name:
        session.model_name = req.model_name
        db.commit()

    from chat_manager import ChatManager

    manager = ChatManager(
        session_id=session_id,
        model_name=req.model_name or session.model_name,
    )

    # Run in thread to avoid blocking the event loop
    result = await asyncio.to_thread(manager.process_message, req.message)

    # Refresh session for updated title
    db.refresh(session)

    return ChatReply(
        reply=result["reply"],
        tool_used=result.get("tool_used"),
        papers=result.get("papers", []),
        paper_detail=result.get("paper_detail"),
        session=ChatSessionOut(
            id=session.id,
            title=session.title,
            model_name=session.model_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
        ),
    )


# =========================================================================
# WebSocket: Real-time status for Chat
# =========================================================================

@app.websocket("/ws/chat/{session_id}")
async def chat_status_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat status updates (e.g. Skill progress).
    """
    await websocket.accept()

    import os
    from redis import Redis
    redis_client = Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"), decode_responses=True)
    pubsub = redis_client.pubsub()
    channel = f"chat_status_{session_id}"
    pubsub.subscribe(channel)

    try:
        while True:
            # We use a non-blocking check with sleep to stay responsive to disconnects
            message = pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        pubsub.unsubscribe(channel)
        try:
            await websocket.close()
        except:
            pass


# =========================================================================
# LEGACY: Project-based endpoints (kept for backward compatibility)
# =========================================================================

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

    from tasks import run_research_task
    try:
        req_dict = req.model_dump()
    except AttributeError:
        req_dict = req.dict()
    run_research_task.delay(project.id, req_dict)
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


# =========================================================================
# Paper detail endpoint (used by PaperPanel)
# =========================================================================

@app.get("/api/lit/{lit_id}", response_model=LiteratureOut)
def get_literature(lit_id: int, db: Session = Depends(get_db)):
    """Get a single literature item by ID."""
    lit = db.query(Literature).filter(Literature.id == lit_id).first()
    if not lit:
        raise HTTPException(status_code=404, detail="Paper not found")
    return lit
