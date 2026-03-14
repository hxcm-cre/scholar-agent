<div align="center">

# 🎓 Scholar-Agent

**AI 驱动的自动化学术调研与实验对标助手**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL_3.0-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)

</div>

---

Scholar-Agent 是一个基于 **LangGraph Agent** 架构的科研闭环工具。它能够自动连接本地文献库 (Zotero)、云端学术资源 (arXiv) 与个人实验数据，通过多源检索和深度解析，生成包含 **SOTA 指标对标** 的量化调研报告。

![Scholar-Agent Demo](./backend/assets/1.png)

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🔍 **多维学术检索** | 协同搜索本地 Zotero 库与 arXiv 云端资源，DOI/标题自动去重 |
| ⚖️ **学术权重过滤** | 按顶会/顶刊、高被引、开源实现等维度加权评分 |
| 📊 **高精度指标抓取** | 从论文全文中提取 RMSE、MAE、计算开销等 SOTA 性能指标 |
| 🧪 **自动实验对标** | 解析本地 CSV 实验数据，智能匹配论文指标，生成诊断建议 |
| 📋 **实时工作流** | WebSocket 实时推送每个 Agent 节点的执行状态 |
| 💾 **结果持久化** | 报告与论文元数据自动保存至 SQLite，支持历史查看 |

## 🏗️ 技术架构

```
┌──────────────────────────────────────────────────────┐
│  Frontend (React + Tailwind CSS + Vite)  :3000       │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────────┐ │
│  │ 任务看板  │ │ 实时工作流 │ │ Markdown 报告 + 图表  │ │
│  └──────────┘ └───────────┘ └──────────────────────┘ │
└─────────────────────┬────────────────────────────────┘
                      │ REST + WebSocket
┌─────────────────────▼────────────────────────────────┐
│  Backend (FastAPI + LangGraph)  :8000                 │
│  ┌──────────────────────────────────────────────────┐ │
│  │ assistant → zotero → query_expansion →           │ │
│  │ cloud_search → filter → evaluator                │ │
│  └──────────────────────────────────────────────────┘ │
│  SQLite (Projects / Literature / Reports)             │
└──────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一：本地开发

```bash
# 1. 克隆项目
git clone https://github.com/hxcm-cre/scholar-agent.git
cd scholar-agent

# 2. 后端
cd backend
cp .env.example .env          # 编辑 .env 填入你的 API Key
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# 3. 前端（新终端）
cd frontend
npm install
npm run dev
```

打开 **http://localhost:3000** 即可使用。

### 方式二：Docker 一键启动

```bash
# 编辑 backend/.env 填入 API Key，然后：
docker-compose up --build
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/docs

## ⚙️ 环境变量

### 后端 (`backend/.env`)

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `OPENAI_API_KEY` | ✅ | DashScope / 通义千问 API Key |
| `ZOTERO_API_KEY` | ⚠️ | Zotero API 密钥（不用可留空） |
| `ZOTERO_USER_ID` | ⚠️ | Zotero 用户 ID |
| `DATABASE_PATH` | ❌ | SQLite 路径（默认项目根目录） |
| `FRONTEND_URL` | ❌ | CORS 允许的前端地址（默认 `*`） |
| `SELECTED_MODEL_NAME` | ❌ | 默认 LLM 模型名 |

### 前端 (构建参数)

| 变量名 | 说明 |
|--------|------|
| `VITE_API_URL` | 后端地址（留空则走 Vite 代理） |

## 📁 项目结构

```
scholar-agent/
├── backend/
│   ├── server.py            # FastAPI 主入口
│   ├── database.py          # SQLAlchemy ORM
│   ├── schemas.py           # Pydantic 模型
│   ├── main.py              # LangGraph 图构建
│   ├── app.py               # (旧) Streamlit 入口
│   ├── src/
│   │   ├── nodes/           # Agent 节点（核心算法）
│   │   ├── state.py         # Agent 状态定义
│   │   └── llm.py           # LLM 客户端
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # 主应用
│   │   ├── components/       # UI 组件
│   │   ├── services/api.ts   # API 服务层
│   │   └── types.ts          # 类型定义
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── LICENSE
```

## ☁️ 云端部署

支持部署到 **Zeabur** / **Fly.io** / **Railway** 等平台：

1. 将后端和前端分别作为两个服务部署
2. 后端挂载持久化卷到 `/data/db`，设置 `DATABASE_PATH=/data/db/scholar_agent.db`
3. 前端构建时注入 `VITE_API_URL` 指向后端地址

## ⚖️ 许可证

本项目采用 [GPL-3.0 License](./LICENSE) 开源。

- **原创性**：本项目包含作者原创的学术解析逻辑与实验对标算法
- **引用说明**：欢迎用于学术研究。如在论文或产品中使用，必须保留原作者署名并开源衍生作品

---

<div align="center">

Developed by [hxcm-cre](https://github.com/hxcm-cre) · 2026

</div>
