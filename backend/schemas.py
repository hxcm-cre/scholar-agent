"""
Pydantic schemas for FastAPI request / response validation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Legacy Request (kept for backward compatibility)
# ---------------------------------------------------------------------------
class ResearchWeights(BaseModel):
    relevance: float = Field(0.5, ge=0.0, le=1.0)
    venue: float = Field(0.3, ge=0.0, le=1.0)
    citation: float = Field(0.1, ge=0.0, le=1.0)
    repro: float = Field(0.1, ge=0.0, le=1.0)


class ResearchRequest(BaseModel):
    query: str
    model_name: str = "qwen2.5-32b-instruct"
    weights: ResearchWeights = ResearchWeights()
    use_ocr: bool = False
    user_metrics: str = ""
    run_benchmark: bool = False
    csv_data: Optional[str] = None


class PaperChatRequest(BaseModel):
    literature_id: int
    message: str
    model_name: str = "qwen2.5-32b-instruct"
    history: List[Dict[str, str]] = []

class PaperNoteRequest(BaseModel):
    literature_id: int
    note: str


# ---------------------------------------------------------------------------
# Chat Request / Response (new conversational API)
# ---------------------------------------------------------------------------
class ChatMessageRequest(BaseModel):
    message: str
    model_name: str = "qwen3-coder-30b-a3b-instruct"


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    tool_name: Optional[str] = None
    paper_refs: List[int] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    model_name: str = "qwen3-coder-30b-a3b-instruct"


class ChatSessionOut(BaseModel):
    id: str
    title: str
    model_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionDetail(ChatSessionOut):
    messages: List[ChatMessageOut] = []
    papers: List["LiteratureOut"] = []


class ChatReply(BaseModel):
    """Response from POST /api/chat/sessions/{id}/message"""
    reply: str
    tool_used: Optional[str] = None
    papers: List[Dict[str, Any]] = []
    paper_detail: Optional[Dict[str, Any]] = None
    session: ChatSessionOut


# ---------------------------------------------------------------------------
# Legacy Response (kept)
# ---------------------------------------------------------------------------
class LiteratureOut(BaseModel):
    id: int
    title: str
    authors: str
    year: Optional[int]
    venue: str
    doi: str
    url: str
    abstract: str
    citations: int
    score: float
    source: str
    full_text: str = ""
    user_notes: str = ""

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: int
    content_markdown: str
    metrics_json: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: int
    query: str
    model_name: str
    status: str
    error_message: Optional[str]
    weights_json: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(ProjectOut):
    literature: List[LiteratureOut] = []
    reports: List[ReportOut] = []


# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------
class NodeStatusEvent(BaseModel):
    type: str = "node_status"  # node_status / complete / error
    node_name: str = ""
    status: str = ""           # running / done
    detail: str = ""
    progress: float = 0.0
