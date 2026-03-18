# 🚀 Scholar-Agent 云端部署详细指南

本指南将指导您如何将 Scholar-Agent 部署到云端（Render + Vercel），使其他用户可以通过网址直接访问，并利用已集成的注册登录系统进行内测。

---

## 1. 后端部署 (Render)

后端使用 FastAPI 和 SQLite，建议部署在 [Render.com](https://render.com)。

### 步骤：
1.  **准备代码**：将代码推送到您的 GitHub 仓库。
2.  **创建 Web Service**：
    *   登录 Render，点击 **New > Web Service**。
    *   选择包含项目的 GitHub 仓库。
3.  **基本设置**：
    *   **Name**: `scholar-agent-backend` (或您喜欢的名字)
    *   **Root Directory**: `backend` (非常重要)
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4.  **配置环境变量 (Environment Variables)**：
    点击 **Advanced > Add Environment Variable**：
    *   `OPENAI_API_KEY`: 您的 OpenAI API 密钥。
    *   `SECRET_KEY`: 设置一个随机的长字符串（用于 JWT 加密，如 `your-super-secret-key-123`）。
    *   `CORS_ORIGINS`: 填写您**前端部署后的 Vercel 网址** (例如 `https://scholar-agent-frontend.vercel.app`)。
5.  **部署**：点击 **Create Web Service**。等待部署完成后，记录下 Render 分配的 URL（例如 `https://scholar-agent-backend.onrender.com`）。

---

## 2. 前端部署 (Vercel)

前端使用 Vite + React，建议部署在 [Vercel](https://vercel.com)。

### 步骤：
1.  **创建项目**：
    *   登录 Vercel，点击 **Add New > Project**。
    *   导入您的 GitHub 仓库。
2.  **基本设置**：
    *   **Project Name**: `scholar-agent-frontend`
    *   **Root Directory**: `frontend` (非常重要)
    *   **Framework Preset**: `Vite`
3.  **配置环境变量 (Environment Variables)**：
    *   添加 `VITE_API_BASE_URL`：填写您在 **步骤 1 中获得的后端 URL**。
4.  **部署**：点击 **Deploy**。
5.  **处理路由 (重要)**：
    由于是单页应用 (SPA)，Vercel 默认不支持直接访问子路由（如 `/login`）。项目中已包含 `frontend/vercel.json`，它会自动处理重定向。

---

## 3. 使用说明

1.  **首位管理员**：首个访问并注册的用户将自动获得管理员权限，可以查看所有注册用户。
2.  **内测模式**：您的 `OPENAI_API_KEY` 已在后端安全配置。其他用户注册并登录后即可直接运行研究任务，无需再输入 API Key。
3.  **本地 Zotero 说明**：云端版本无法直接搜索您的本地电脑 Zotero。建议用户使用 `ZOTERO_USER_ID` 和 `ZOTERO_API_KEY` （如需共享文献库）。

---

## 4. 后续维护
*   **数据库**：本部署方案默认使用 Render 实例文件系统中的 SQLite。若实例重启，数据可能会重置。如需永久存储，请在 Render 中挂载 **Disk** 到 `/app/scholar_agent.db` 或使用 Render 提供的 **Postgres** 数据库。
*   **版本更新**：只需将新代码推送到 GitHub，Render 和 Vercel 会自动触发重新部署。

---

## 5. 常见问题排查 (Troubleshooting)

### 🔴 错误：`Access to fetch at ... has been blocked by CORS policy`
这是最常见的跨域错误，意味着后端 Render 没有允许前端 Vercel 的访问请求。

*   **解决方法**：
    1.  前往 Render 项目控制台：**Environment**。
    2.  确保添加了 `CORS_ORIGINS` 环境变量。
    3.  它的值必须包含您的前端完整网址（例如 `https://scholar-agent-three.vercel.app`）。如果有多个，请用英文逗号隔开。
    4.  **调试技巧**：如果配置后仍然报错，可以将 `CORS_ORIGINS` 的值暂时设为 `*`（通配符），然后**重新部署 (Manual Deploy)**。如果 `*` 能通，说明是之前的网址拼写或格式有问题。

### 🔴 错误：`405 Method Not Allowed` / `404 Not Found` (对于 `/projects` 或 `/research`)
这通常是由于前端请求的路径不正确导致的。
*   **修复**：代码已统一适配。请确保您的 `VITE_API_BASE_URL` **只包含主域名**（例如 `https://xxx.onrender.com`），不要在末端添加 `/api`，代码会自动补全。

### 🔴 数据库持久化提示 (重要)
Render 的免费版和基础版实例在每次自动休眠或重新部署时会**清空文件系统**。
*   如果您发现注册过的账号“消失”了，是因为 SQLite 文件被重置。
*   **解决方法**：在 Render 侧边栏选择 **Disks**，创建一个挂载到 `/backend/data` (并修改代码中的 DB 路径) 的磁盘，或使用 Render 的托管 **PostgreSQL** 服务。

---

祝您的项目圆满上线！
