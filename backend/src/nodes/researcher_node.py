from __future__ import annotations

from typing import Dict

from src.state import AgentState


def researcher_node(state: AgentState) -> Dict:
    """
    Placeholder for a future ReAct-style researcher:
    - query expansion
    - cloud search orchestration (Semantic Scholar / arXiv)
    - dedup with Zotero
    """

    query = (state.get("query") or "").strip()
    return {
        "query": query,
        "candidate_papers": state.get("candidate_papers", []),
    }

