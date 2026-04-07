"""
FastAPI server for Scholar-Agent.

Exposes REST endpoints + WebSocket for real-time agent status.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import traceback
from collections import defaultdict
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Project, Literature, Report, SessionLocal, get_db, init_db
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.llm import make_qwen_llm
from schemas import (
    NodeStatusEvent,
    ProjectDetail,
    ProjectOut,
    ResearchRequest,
    PaperChatRequest,
    PaperNoteRequest,
)
from models_config import AVAILABLE_MODELS

load_dotenv()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Scholar-Agent API", version="1.0.0") # 初始化 FastAPI 实例

@app.get("/api/models") # 定义一个处理 GET 请求的路由，路径是 /api/models
def get_available_models(): # 定义一个名为 get_available_models 的函数，用于处理 GET /api/models 请求
    """List all available AI models for both search and chat.""" # 函数的文档字符串，解释函数的功能
    return {"models": AVAILABLE_MODELS} # 返回一个字典，包含所有可用的 AI 模型

# Allow origins from environment variable, stripping spaces
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000") # 从环境变量中获取允许的来源，并去除空格
if cors_env == "*": # 如果环境变量中的允许来源是 "*"，则允许所有来源
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in cors_env.split(",")] # 将允许的来源按逗号分割，并去除空格

app.add_middleware( # 添加中间件，用于处理跨域请求
    CORSMiddleware, # 跨域资源共享中间件
    allow_origins=CORS_ORIGINS, # 允许的来源
    allow_credentials=True, # 允许凭证
    allow_methods=["*"], # 允许的方法
    allow_headers=["*"], # 允许的头
)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
LAST_EVENTS: Dict[int, str] = {} # 存储每个项目的最后一次状态

class ConnectionManager: # WebSocket 连接管理器
    """Manages per-project WebSocket connections.""" # 管理每个项目的 WebSocket 连接

    def __init__(self): # 初始化连接管理器
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list) # 存储每个项目的 WebSocket 连接
    # 一次完整的文献检索任务对应一个 Project，而 ws (WebSocket) 是前端页面与后端建立的通信连接。
    # 它们之间的关系可以理解为 1 对 N（一个项目可以有多个连接）：比如你在电脑浏览器里打开了一个页面在看某个检索进度，这就是一个 ws；如果你同时在手机上也打开了这个页面看同一个检索任务，那就是第二个 ws。
    async def connect(self, project_id: int, ws: WebSocket): # 连接 WebSocket
        await ws.accept() # 接受 WebSocket 连接
        self._connections[project_id].append(ws) # 将 WebSocket 连接添加到连接管理器中
        
        # 补充：当新连接进来时，如果内存中有最后一次的状态，立即发给它，解决前端一进来进度条归 0 的问题
        if project_id in LAST_EVENTS:
            try:
                await ws.send_text(LAST_EVENTS[project_id])
            except Exception:
                pass


    def disconnect(self, project_id: int, ws: WebSocket): # 断开 WebSocket 连接
        if project_id in self._connections: # 如果项目在连接管理器中
            if ws in self._connections[project_id]: # 如果 WebSocket 在连接管理器中
                self._connections[project_id].remove(ws) # 将 WebSocket 从连接管理器中移除
            if not self._connections[project_id]: # 如果连接管理器中没有 WebSocket
                del self._connections[project_id] # 将项目从连接管理器中删除

    async def broadcast(self, project_id: int, event: NodeStatusEvent): # 广播 WebSocket 事件
        dead: list[WebSocket] = [] # 存储死连接
        for ws in self._connections.get(project_id, []): # 遍历每个项目的 WebSocket 连接
            try: # 尝试发送 WebSocket 事件
                await ws.send_text(event.model_dump_json()) # 发送 WebSocket 事件
            except Exception: # 如果发送失败
                dead.append(ws) # 将死连接添加到列表中
        for ws in dead: # 遍历死连接
            self.disconnect(project_id, ws) # 断开 WebSocket 连接


manager = ConnectionManager() # 创建连接管理器实例

# ---------------------------------------------------------------------------
# Node label mapping (for UI display)
# ---------------------------------------------------------------------------
NODE_LABELS: Dict[str, str] = {
    "assistant": "分析用户研究意图",
    "zotero": "检索 Zotero 本地文献库",
    "query_expansion": "生成扩展搜索关键词",
    "cloud_search": "执行云端学术数据库检索",
    "filter": "根据期刊分区(CCF/CAS)等信息过滤高价值论文",
    "evaluator": "提取 SOTA 指标并与本地实验对标",
}


# ---------------------------------------------------------------------------
# Redis Pub/Sub WebSocket Broadcaster
# ---------------------------------------------------------------------------
async def listen_to_redis_for_ws():  # 监听 Redis 的 Pub/Sub 消息
    """Background task to listen to Redis and broadcast to WebSockets."""
    import redis.asyncio as aioredis
    REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0") # 从环境变量中获取 Redis 的 URL
    try:
        redis = aioredis.from_url(REDIS_URL, decode_responses=True) # 创建 Redis 客户端
        pubsub = redis.pubsub() # 创建 Pub/Sub 客户端
        await pubsub.psubscribe("ws_project_*") # 订阅所有以 ws_project_ 开头的频道
        print("Started listening to Redis Pub/Sub for WebSockets...")
        
        async for message in pubsub.listen(): # 监听 Redis 的 Pub/Sub 消息
            if message["type"] == "pmessage": # 如果是 pmessage 类型的消息
                channel = message["channel"] # 获取频道
                data = message["data"] # 获取数据
                try:
                    # extract project_id from ws_project_{id} 
                    project_id = int(channel.split("_")[-1]) # 提取项目 ID
                    # update last known event cache
                    LAST_EVENTS[project_id] = data # 更新最后一次状态缓存
                    # broadcast to all websockets of this project
                    try:
                        event = NodeStatusEvent.model_validate_json(data) # 验证 JSON 数据
                    except AttributeError:
                        # Fallback for older pydantic
                        import json as _json
                        event = NodeStatusEvent(**_json.loads(data))
                    await manager.broadcast(project_id, event) # 广播 WebSocket 事件
                except Exception as e:
                    print(f"Error broadcasting ws message: {e}")
    except Exception as e:
        print(f"Failed to connect to Redis for Pub/Sub: {e}")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup") # 启动时执行
async def on_startup():
    init_db() # 初始化数据库
    asyncio.create_task(listen_to_redis_for_ws()) # 启动 Redis Pub/Sub 监听任务


# ---------------------------------------------------------------------------
# REST Endpoints - Projects
# ---------------------------------------------------------------------------
@app.post("/api/research", response_model=ProjectOut) # 创建研究
async def create_research(req: ResearchRequest, bg: BackgroundTasks, db: Session = Depends(get_db)): # 请求
    """Create a project and start the agent in background."""
    import json as _json

    project = Project(
        query=req.query,
        model_name=req.model_name,
        status="pending",
        weights_json=_json.dumps(req.weights.model_dump(), ensure_ascii=False),
        user_metrics=req.user_metrics,
    )
    db.add(project) # 将项目添加到数据库会话中
    db.commit() # 提交事务
    db.refresh(project) # 刷新项目

    # Launch background thread via Celery
    from tasks import run_research_task # 导入任务
    try:
        req_dict = req.model_dump() # 将请求转换为字典
    except AttributeError:
        req_dict = req.dict() # 将请求转换为字典
    run_research_task.delay(project.id, req_dict) # 延迟执行任务

    return project


@app.get("/api/projects", response_model=list[ProjectOut]) # 获取所有项目
def list_projects(db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Return all projects, newest first."""
    return db.query(Project).order_by(Project.created_at.desc()).all() # 按创建时间倒序排列


@app.get("/api/projects/{project_id}", response_model=ProjectDetail) # 获取项目详情
def get_project(project_id: int, db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Return full project detail including literature and reports."""
    proj = db.query(Project).filter(Project.id == project_id).first() # 查询项目
    if not proj: # 如果项目不存在
        raise HTTPException(status_code=404, detail="Project not found") # 抛出 404 错误
    return proj


@app.delete("/api/projects/{project_id}") # 删除项目
def delete_project(project_id: int, db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Delete project and all related data."""
    proj = db.query(Project).filter(Project.id == project_id).first() # 查询项目
    if not proj: # 如果项目不存在
        raise HTTPException(status_code=404, detail="Project not found") # 抛出 404 错误
    db.delete(proj)
    db.commit()
    return {"detail": "deleted"}

@app.post("/api/projects/{project_id}/cancel") # 取消项目
def cancel_project(project_id: int, db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Cancel a running project by sending a flag to Redis that the Worker intercepts."""
    from redis import Redis
    proj = db.query(Project).filter(Project.id == project_id).first() # 查询项目
    if not proj: # 如果项目不存在
        raise HTTPException(status_code=404, detail="Project not found") # 抛出 404 错误
        
    REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0") # 从环境变量中获取 Redis 的 URL
    r = Redis.from_url(REDIS_URL, decode_responses=True) # 创建 Redis 客户端
    
    # Send cancel flag for tasks.py to catch natively inside the event loop
    r.set(f"cancel_project_{project_id}", "1", ex=3600)  # expires in 1h 
    
    # Broadcast early cancellation to frontend to improve UX
    try:
        r.publish(f"ws_project_{project_id}", NodeStatusEvent( # 广播 WebSocket 事件
            type="error", node_name="", status="error", detail="正在通知 Worker 取消任务...", progress=0
        ).model_dump_json()) # 将 JSON 数据转换为字符串
    except:
        pass
    
    return {"detail": "cancellation requested"}


@app.post("/api/lit/chat") # 论文聊天
async def paper_chat(req: PaperChatRequest, db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Localized chat with a specific paper's full text."""
    lit = db.query(Literature).filter(Literature.id == req.literature_id).first() # 查询论文
    if not lit: # 如果论文不存在
        raise HTTPException(status_code=404, detail="Paper not found") # 抛出 404 错误
    
    if not lit.full_text: # 如果论文没有全文
        # Fallback to abstract if full text is missing
        context = f"Title: {lit.title}\nAbstract: {lit.abstract}" # 使用摘要作为上下文
    else:
        context = lit.full_text # 使用全文作为上下文

    system_prompt = f"""你现在是一个学术审阅助理。你唯一可以引用的知识来源是以下提供的 <Fulltext_Markdown>。
回答用户提问的问题需要基于原文的信息。如果用户提问的问题在原文中没有提及，可以适当扩展，但是不要编造。

<Fulltext_Markdown>
{context}
</Fulltext_Markdown>
"""
    
    messages = [SystemMessage(content=system_prompt)] # 系统消息
    for m in req.history: # 遍历历史消息
        if m["role"] == "user": # 如果是用户消息
            messages.append(HumanMessage(content=m["content"])) # 添加用户消息
        else: # 如果是 AI 消息
            messages.append(AIMessage(content=m["content"])) # 添加 AI 消息
    
    messages.append(HumanMessage(content=req.message)) # 添加用户消息

    # Use the model requested by the user
    model_name = req.model_name
    llm = make_qwen_llm(model_name=model_name, temperature=0.1) # 创建 Qwen LLM 实例
    
    try:
        resp = await asyncio.to_thread(llm.invoke, messages) # 调用 LLM
        return {"answer": resp.content} # 返回答案
    except Exception as e:
        print(f"LLM Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM Error: {e}")


@app.post("/api/lit/note") # 保存论文笔记
def save_paper_note(req: PaperNoteRequest, db: Session = Depends(get_db)): # 依赖注入数据库会话
    """Save user note to a specific paper."""
    lit = db.query(Literature).filter(Literature.id == req.literature_id).first() # 查询论文
    if not lit: # 如果论文不存在
        raise HTTPException(status_code=404, detail="Paper not found") # 抛出 404 错误
    
    # Append the new note to existing notes with a separator
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S") # 获取当前时间
    new_entry = f"\n\n--- Added on {timestamp} ---\n{req.note}" # 添加新笔记
    lit.user_notes = (lit.user_notes or "") + new_entry # 将新笔记添加到现有笔记中
    
    db.commit() # 提交事务
    return {"status": "success", "user_notes": lit.user_notes} # 返回状态和笔记


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/research/{project_id}") # WebSocket
async def websocket_endpoint(websocket: WebSocket, project_id: int): # 依赖注入 WebSocket 和项目 ID
    await manager.connect(project_id, websocket) # 连接到 WebSocket
    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text() # 接收文本
    except WebSocketDisconnect: # 捕获 WebSocket 断开连接异常
        manager.disconnect(project_id, websocket) # 断开连接
