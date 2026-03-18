"""
Pydantic schemas for FastAPI request / response validation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
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
    csv_data: Optional[str] = None  # base64-encoded CSV


# ---------------------------------------------------------------------------
# Response
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
