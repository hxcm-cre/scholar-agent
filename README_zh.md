<div align="center">

<img src="./logo.png" alt="Scholar-Agent 标志" width="180" />

# 🎓 Scholar-Agent
**全自动学术研究助理**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat&logo=docker)](https://www.docker.com/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL_3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[English](README.md) • [简体中文](README_zh.md)

<p align="center">
    <strong>Scholar-Agent 可以从网络和本地 Zotero 自动检索、过滤并分析前沿论文，提炼量化的 SOTA 对比数据与技术建议。</strong>
</p>
</div>

---

## 📺 演示视频与界面截图

**点击前往 Bilibili 观看完整使用教程:**

[![Scholar-Agent Demo](https://img.shields.io/badge/Bilibili-观看教程视频-fb7299?style=for-the-badge&logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1AmwxzPEBF)

<div align="center">
  <img src="backend/assets/1.png" alt="Scholar-Agent 界面预览" width="90%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br />
  <i>实时工作流跟踪：通过 WebSocket 在前端直观地观察智能体的每一个思考步骤</i>
</div>

---

<div align="center">
  <img src="backend/assets/2.png" alt="Scholar-Agent 界面预览" width="90%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br />
</div>

---

<div align="center">
  <img src="backend/assets/3.png" alt="Scholar-Agent 界面预览" width="90%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br />
</div>

---

<div align="center">
  <img src="backend/assets/4.png" alt="Scholar-Agent 界面预览" width="90%" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br />
</div>

---

## 🚀 极速启动

### 1. 环境变量配置
```bash
# 拷贝预设的环境变量模板
cp .env.example .env
```
---

## ⚙️ 核心环境变量说明

所有的核心配置项均集中在项目根目录（或 `backend` 目录）的 `.env` 配置文件中：

| 变量键值 | 功能说明 |
|---|---|
| `OPENAI_API_KEY` | OpenAI 官方 API 密钥，用于驱动核心 Agent 决策与推理逻辑。 |
| `ZOTERO_API_KEY` | Zotero 个人账号的 API 密钥，用于远程读取文献库数据。|
| `ZOTERO_USER_ID` | 你的 Zotero 用户 ID（UserID），用于定位特定的个人/群组库。 |
| `EXPERIMENT_CSV_PATH` | 用于指定生成的定量分析 CSV 文件的存放目录。（可选） |
---

## 2.  本地开发环境设置

将后端和前端分别启动：

### 依赖要求
- Python 3.11 及以上版本
- Node.js v18 及以上版本

### 后端核心
首先进入 `backend` 目录：
```bash
cd backend
python -m venv venv （只需第一次启动时运行）
pip install -r requirements.txt （只需第一次启动时运行）
.\venv\Scripts\uvicorn server:app --reload --port 8000

```

### 前端看板
打开一个**全新的终端**并进入 `frontend` 目录：
```bash
cd frontend
npm install （只需第一次启动时运行）
npm run dev
```

---

## 3.  运行scholar-agent

现在请打开浏览器并访问 **[http://localhost:3000](http://localhost:3000)**，即可开始使用该平台。
---

<div align="center">
Made with ❤️ for Researchers. 用人工智能加速人类科学进程。
</div>

