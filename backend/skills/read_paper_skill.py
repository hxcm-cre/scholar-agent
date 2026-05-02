"""
Read Paper Skill — retrieves a paper's full text from the database.

Used by the ChatManager when the user asks about a specific paper.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from database import Literature, SessionLocal


def read_paper_content(paper_id: int) -> Dict[str, Any]:
    """
    Read a paper's full text and metadata from the Literature table.

    Returns:
        {
            "success": bool,
            "title": str,
            "authors": str,
            "year": int | None,
            "venue": str,
            "abstract": str,
            "full_text": str,
            "url": str,
            "error": str | None,
        }
    """
    db = SessionLocal()
    try:
        lit = db.query(Literature).filter(Literature.id == paper_id).first()
        if not lit:
            return {
                "success": False,
                "title": "", "authors": "", "year": None, "venue": "",
                "abstract": "", "full_text": "", "url": "",
                "error": f"Paper with id={paper_id} not found.",
            }

        content = lit.full_text or ""
        if not content:
            content = f"Title: {lit.title}\nAbstract: {lit.abstract}"

        return {
            "success": True,
            "title": lit.title,
            "authors": lit.authors,
            "year": lit.year,
            "venue": lit.venue,
            "abstract": lit.abstract,
            "full_text": content,
            "url": lit.url,
            "error": None,
        }
    finally:
        db.close()
