# Scholar-Agent

Scholar-Agent is an academic research assistant powered by a LangGraph multi-agent pipeline and local/cloud search integration. It retrieves, filters, and analyzes academic literature (from arXiv, Zotero) to provide quantitative insights.

With the latest refactoring, Scholar-Agent now features a **FastAPI backend** with SQLite persistence, and a **Vite + React frontend** for real-time tracking of agent steps via WebSockets.

## Features

- **Multi-Agent Workflow**: Powered by [LangGraph](https://langchain-ai.github.io/langgraph/). Includes intent parsing, Zotero local search, arXiv cloud search, query expansion, paper filtering, and LLM-based technical benchmarking.
- **Real-Time Kanban & Tracking**: React frontend tracks in-progress jobs and visualizes steps node-by-node.
- **SQLite Persistence**: Automatic DB storage of project queries, research literature, and finalized markdown reports.
- **RAG & OCR Integration**: Uses [Docling](https://github.com/DS4SD/docling) for robust PDF-to-Markdown processing, catching complex tables and applying soft-fallback OCR.
- **Docker Compose Setup**: Simplified one-click deployment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Alternatively, Python 3.11+ and Node.js v18+ for local execution.

## Quick Start (Docker)

The easiest way to run the entire stack is with Docker Compose.

```bash
# 1. Provide your environment variables
cp .env.example .env
# Edit .env and set your LLM API keys (e.g. QWEN_API_KEY)

# 2. Build and run
docker-compose up --build
```

Then open your browser to [http://localhost:3000](http://localhost:3000).

---

## Local Development Setup

If you wish to run the app outside of Docker, follow these steps:

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/Mac: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Or create your own .env in the root dir

# Run server on port 8000
uvicorn server:app --reload --port 8000
```

### 2. Frontend (React)

Open a **new terminal**:

```bash
cd frontend
npm install

# Run dev server on port 3000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Configuration

Scholar-Agent utilizes a central `.env` file (usually at the project root). Below are key variables:

| Variable | Description |
|---|---|
| `QWEN_API_KEY` | Your API key for connecting to Alibaba Qwen services. |
| `SELECTED_MODEL_NAME` | Model explicitly required by the LLM (default `qwen2.5-32b-instruct`). |
| `ZOTERO_BBT_PULL_URL` | Optional URI to pull citations locally (Better BibTeX plugin). |
| `USE_OCR` | Set to `1` to enable RapidOCR layout parsing for document conversion. |

## Architecture

Scholar-Agent separates concerns cleanly:

1. **Frontend**: React SPA serving a kanban board and WebSocket client.
2. **Backend**: FastAPI managing requests, bridging LangGraph invocations into background threads. WebSockets broadcast real-time `NodeStatusEvent` items.
3. **Database**: SQLite tracking metadata over `projects`, `literature`, and `reports` tables, using SQLAlchemy Async Engine.
4. **LangGraph Nodes**: Situated in `backend/src/nodes/`, orchestrating distinct scientific stages (expansion, filtering, markdown extraction, LLM synthesis).
