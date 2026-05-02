<div align="center">

<img src="./logo.png" alt="Scholar-Agent logo" width="180" />

# 🎓 Scholar-Agent
**Conversational AI Academic Research Assistant**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange)](https://langchain-ai.github.io/langgraph/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL_3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[English](README.md) • [简体中文](README_zh.md)

<p align="center">
    <strong>Scholar-Agent is a multi-turn, conversational AI assistant that helps researchers discover, read, and analyze academic papers. It uses a hub-and-spoke architecture where a central LLM manages specialized "Skills" for searching, reading, and reasoning.</strong>
</p>
</div>

---

## ✨ Key Features (V2.0)

- 💬 **Multi-turn Dialogue**: A ChatGPT-like conversational interface for natural research exploration.
- 🤖 **Central LLM Controller**: Decides autonomously when to search for new papers or analyze existing ones using tool calling.
- 🔍 **Scholar Search Skill**: An upgraded LangGraph pipeline that searches across arXiv and local Zotero libraries, filtering for high-value papers.
- 📖 **Deep Reading Skill**: Instantly fetch and analyze full-text content of discovered papers using a side-panel reader.
- 🗂️ **Persistent Knowledge Base**: Maintain multiple chat sessions with persistent memory of found papers.
- 🔢 **Smart Citations**: AI automatically assigns reference numbers `[1]`, `[2]`, etc., across the conversation for easy follow-up.

---

## 📺 Demo and Screenshots

*(Note: Screenshots are being updated to reflect the new conversational UI)*

<div align="center">
  <img src="backend/assets/chat_ui_v2.png" alt="Scholar-Agent V2 Interface" width="90%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br />
  <i>Modern Conversational UI: Multi-turn research dialogue with integrated paper side-panel</i>
</div>

---

## 🚀 Quick Start

### 1. Environment Configuration
```bash
# Copy the environment variable template
cp .env.example .env
```

### ⚙️ Core Environment Variables
Configure these in the `backend/.env` file:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Core Agent logic and reasoning (supporting GPT-4, Qwen, etc.). |
| `ZOTERO_API_KEY` | For local literature integration. |
| `ZOTERO_USER_ID` | Your Zotero account ID. |
| `SELECTED_MODEL_NAME`| Default LLM used by the ChatManager. |

---

## 2. Local Setup

### Step 1: Start Redis (Terminal 1)
```powershell
cd redis
.\redis-server.exe
```

### Step 2: Start Backend Gateway (Terminal 2)
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn server:app --reload
```
🔔 **Success**: Terminal shows `Uvicorn running on http://127.0.0.1:8000`

### Step 3: Start Celery Worker (Terminal 3)
Required for background research tasks.
```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A celery_app worker --loglevel=info --pool=solo
```

### Step 4: Start Frontend (Terminal 4)
```powershell
cd frontend
npm install
npm run dev
```
🔔 **Success**: Terminal shows `VITE v6.x.x ready` and link `http://localhost:3000/`.

---

## 3. Usage

1. Open **[http://localhost:3000](http://localhost:3000)**.
2. Click **"New Chat"** to start a session.
3. Ask questions like: *"Search for latest papers on Transformer efficiency"* or *"Explain the methodology of the second paper"*.

---
