"""
SQLite database layer using SQLAlchemy async engine.
DB file: ../scholar_agent.db (project root)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text,
    create_engine, event,
)
from sqlalchemy.orm import (
    DeclarativeBase, Session, relationship, sessionmaker,
)

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).resolve().parent.parent / "scholar_agent.db"
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better concurrent reads
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    model_name = Column(String(128), default="qwen2.5-32b-instruct")
    status = Column(String(32), default="pending")  # pending / running / done / error
    error_message = Column(Text, nullable=True)
    weights_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    literature = relationship("Literature", back_populates="project",
                              cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project",
                           cascade="all, delete-orphan")


class Literature(Base):
    __tablename__ = "literature"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    authors = Column(Text, default="")
    year = Column(Integer, nullable=True)
    venue = Column(String(256), default="")
    doi = Column(String(256), default="")
    url = Column(Text, default="")
    abstract = Column(Text, default="")
    citations = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    source = Column(String(32), default="arxiv")  # zotero / arxiv

    project = relationship("Project", back_populates="literature")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    content_markdown = Column(Text, default="")
    metrics_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="reports")


# ---------------------------------------------------------------------------
# Create tables
# ---------------------------------------------------------------------------
def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)
