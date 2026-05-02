"""
ChatManager — the central AI controller for multi-turn conversation.

Uses LLM Function Calling to decide when to invoke skills
(scholar_search, read_paper_content) vs. answering directly.
Manages session-level paper references with numbered IDs [1], [2], etc.
"""
from __future__ import annotations

import json
import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from database import ChatMessage, ChatSession, Literature, SessionLocal
from src.llm import make_qwen_llm
from skills.scholar_search_skill import scholar_search
from skills.read_paper_skill import read_paper_content

# ---------------------------------------------------------------------------
# Tool definitions for Function Calling
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scholar_search",
            "description": (
                "Search academic papers on a given topic. "
                "Use this tool when the user explicitly asks to search, find, "
                "or look up research papers, literature, or academic publications."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The academic search query or research topic.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper_content",
            "description": (
                "Read the full text content of a specific paper by its database ID. "
                "Use this when the user asks for details about a specific paper "
                "that was previously found, e.g. 'explain paper [2]' or "
                "'summarize the third paper'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "integer",
                        "description": "The database ID of the paper to read.",
                    }
                },
                "required": ["paper_id"],
            },
        },
    },
]

SYSTEM_PROMPT = """\
你是 Scholar-Agent，一个专业的学术研究 AI 助手。你可以帮助用户搜索论文、阅读论文和回答学术问题。

## 你的能力
1. **搜索论文**：当用户要求搜索、查找论文时，调用 `scholar_search` 工具。
2. **阅读论文**：当用户提到论文编号（如"第2篇"、"[2]"）或要求详细解释某篇论文时，调用 `read_paper_content` 工具。
3. **学术问答**：对于一般性学术问题，直接基于你的知识回答。

## 论文引用规则
- 搜索到的论文会被分配编号 [1], [2], [3]...
- 用户可以通过编号引用论文
- 回答时请引用相关论文编号

## 当前会话中已加载的论文
{paper_context}

请用中文回答。保持回答专业、简洁、有条理。
"""


def _build_paper_context(session_papers: List[Dict]) -> str:
    """Build the paper list context string for the system prompt."""
    if not session_papers:
        return "（暂无论文）"
    lines = []
    for p in session_papers:
        lines.append(
            f"[{p['index']}] ID={p['id']} | {p['title']} "
            f"| {p.get('venue', '')} {p.get('year', '')} "
            f"| 引用数: {p.get('citations', 0)}"
        )
    return "\n".join(lines)


def _resolve_paper_reference(user_msg: str, session_papers: List[Dict]) -> Optional[int]:
    """
    Try to resolve a paper reference from user message like '第2篇', '[2]', 'paper 2'.
    Returns the database ID if found, else None.
    """
    import re

    # Match patterns like [2], 第2篇, paper 2, #2
    patterns = [
        r'\[(\d+)\]',
        r'第\s*(\d+)\s*篇',
        r'paper\s*(\d+)',
        r'#(\d+)',
        r'论文\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, user_msg, re.IGNORECASE)
        if match:
            idx = int(match.group(1))
            for p in session_papers:
                if p.get("index") == idx:
                    return p["id"]
    return None


class ChatManager:
    """Central controller for multi-turn conversation with tool calling."""

    def __init__(self, session_id: str, model_name: str = "qwen3-coder-30b-a3b-instruct"):
        self.session_id = session_id
        self.model_name = model_name
        self.session_papers: List[Dict[str, Any]] = []
        self._load_session_papers()

    def _load_session_papers(self):
        """Load paper references from existing messages in this session."""
        db = SessionLocal()
        try:
            msgs = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == self.session_id,
                    ChatMessage.role == "tool",
                    ChatMessage.tool_name == "scholar_search",
                )
                .all()
            )
            for msg in msgs:
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and "papers" in data:
                        for p in data["papers"]:
                            if not any(
                                ep["id"] == p["id"] for ep in self.session_papers
                            ):
                                self.session_papers.append(p)
                except (json.JSONDecodeError, KeyError):
                    pass
        finally:
            db.close()

    def _get_conversation_history(self) -> List[Dict[str, str]]:
        """Load conversation history from DB."""
        db = SessionLocal()
        try:
            msgs = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .order_by(ChatMessage.created_at)
                .all()
            )
            history = []
            for m in msgs:
                if m.role in ("user", "assistant"):
                    history.append({"role": m.role, "content": m.content})
            return history
        finally:
            db.close()

    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.

        Returns:
            {
                "reply": str,           # The assistant's text reply
                "tool_used": str|None,  # "scholar_search" / "read_paper_content" / None
                "papers": list,         # Papers found (if search was performed)
                "paper_detail": dict|None,  # Paper detail (if read was performed)
            }
        """
        # Build messages for LLM
        paper_context = _build_paper_context(self.session_papers)
        system_msg = SYSTEM_PROMPT.format(paper_context=paper_context)

        history = self._get_conversation_history()

        messages = [{"role": "system", "content": system_msg}]
        # Add recent history (limit to last 20 messages to stay in context window)
        for h in history[-20:]:
            messages.append(h)
        messages.append({"role": "user", "content": user_message})

        # Save user message to DB
        self._save_message("user", user_message)

        try:
            llm = make_qwen_llm(model_name=self.model_name, temperature=0.3)

            # Try function calling
            result = self._call_with_tools(llm, messages, user_message)
            return result

        except Exception as e:
            traceback.print_exc()
            error_reply = f"抱歉，处理消息时出错：{str(e)[:200]}"
            self._save_message("assistant", error_reply)
            return {
                "reply": error_reply,
                "tool_used": None,
                "papers": [],
                "paper_detail": None,
            }

    def _call_with_tools(
        self, llm, messages: List[Dict], user_message: str
    ) -> Dict[str, Any]:
        """Call LLM with tool definitions, handle tool calls if any."""
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        # Convert to LangChain messages
        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                lc_messages.append(AIMessage(content=m["content"]))

        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(TOOLS)
        resp = llm_with_tools.invoke(lc_messages)

        # Check if LLM wants to call a tool
        if hasattr(resp, "tool_calls") and resp.tool_calls:
            tool_call = resp.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "scholar_search":
                return self._handle_scholar_search(
                    tool_args.get("query", user_message), messages
                )
            elif tool_name == "read_paper_content":
                paper_id = tool_args.get("paper_id")
                if paper_id is None:
                    # Try to resolve from user message
                    paper_id = _resolve_paper_reference(
                        user_message, self.session_papers
                    )
                if paper_id:
                    return self._handle_read_paper(paper_id, user_message, messages)
                else:
                    reply = '请指定论文编号，例如"请详细解释第 2 篇论文"。'
                    self._save_message("assistant", reply)
                    return {
                        "reply": reply,
                        "tool_used": None,
                        "papers": [],
                        "paper_detail": None,
                    }

        # Fallback for Qwen models outputting raw XML
        content = resp.content or ""
        import re
        match_func = re.search(r'<function=(\w+)>', content)
        if match_func:
            tool_name = match_func.group(1)
            args = {}
            for p_match in re.finditer(r'<parameter=(\w+)>(.*?)</parameter>', content, re.DOTALL):
                args[p_match.group(1)] = p_match.group(2).strip()
                
            if tool_name == "scholar_search":
                return self._handle_scholar_search(
                    args.get("query", user_message), messages
                )
            elif tool_name == "read_paper_content":
                paper_id = args.get("paper_id")
                if paper_id is not None:
                    try:
                        paper_id = int(paper_id)
                    except ValueError:
                        paper_id = None
                if paper_id is None:
                    paper_id = _resolve_paper_reference(user_message, self.session_papers)
                if paper_id:
                    return self._handle_read_paper(paper_id, user_message, messages)
                else:
                    reply = '请指定论文编号，例如"请详细解释第 2 篇论文"。'
                    self._save_message("assistant", reply)
                    return {
                        "reply": reply,
                        "tool_used": None,
                        "papers": [],
                        "paper_detail": None,
                    }

        # No tool call — direct response
        reply = content
        self._save_message("assistant", reply)
        return {
            "reply": reply,
            "tool_used": None,
            "papers": [],
            "paper_detail": None,
        }

    def _handle_scholar_search(
        self, query: str, messages: List[Dict]
    ) -> Dict[str, Any]:
        """Execute the scholar_search skill and format results."""
        # Run the search
        result = scholar_search(
            query=query,
            model_name=self.model_name,
            session_id=self.session_id,
        )

        if not result["success"]:
            reply = f"论文搜索失败：{result['error']}"
            self._save_message("assistant", reply)
            return {
                "reply": reply,
                "tool_used": "scholar_search",
                "papers": [],
                "paper_detail": None,
            }

        papers = result["papers"]

        # Re-index papers for this session
        start_idx = len(self.session_papers) + 1
        for i, p in enumerate(papers):
            p["index"] = start_idx + i
            self.session_papers.append(p)

        # Save tool result message
        self._save_message(
            "tool",
            json.dumps({"papers": papers}, ensure_ascii=False),
            tool_name="scholar_search",
            paper_refs=[p["id"] for p in papers],
        )

        # Build a nice reply using the analysis report
        report_md = result.get("report_markdown", "")
        
        if report_md:
            reply = f"{report_md}\n\n您可以说\"**详细解释第 N 篇**\"来深入了解某篇论文。"
        elif papers:
            lines = [f"为您找到 **{len(papers)}** 篇相关论文：\n"]
            for p in papers:
                lines.append(
                    f"**[{p['index']}]** {p['title']}\n"
                    f"   - {p.get('venue', '')} {p.get('year', '')} "
                    f"| 引用: {p.get('citations', 0)} | 评分: {p.get('score', 0):.1f}\n"
                )
            lines.append('\n您可以说"**详细解释第 N 篇**"来深入了解某篇论文。')
            reply = "\n".join(lines)
        else:
            reply = "搜索完成，但未找到符合条件的高质量论文。请尝试调整搜索关键词。"

        self._save_message("assistant", reply)
        return {
            "reply": reply,
            "tool_used": "scholar_search",
            "papers": papers,
            "paper_detail": None,
        }

    def _handle_read_paper(
        self, paper_id: int, user_message: str, messages: List[Dict]
    ) -> Dict[str, Any]:
        """Read a paper and generate a contextual answer."""
        result = read_paper_content(paper_id)

        if not result["success"]:
            reply = f"无法读取论文：{result['error']}"
            self._save_message("assistant", reply)
            return {
                "reply": reply,
                "tool_used": "read_paper_content",
                "papers": [],
                "paper_detail": None,
            }

        # Build a focused prompt with the paper content
        paper_context = (
            f"论文标题: {result['title']}\n"
            f"作者: {result['authors']}\n"
            f"发表: {result['venue']} {result['year']}\n\n"
            f"内容:\n{result['full_text'][:8000]}"
        )

        focused_prompt = (
            f"以下是系统为您提取的目标论文内容（这正是用户所引用的那篇论文）：\n\n"
            f"<Paper>\n{paper_context}\n</Paper>\n\n"
            f"用户的指令是: {user_message}\n\n"
            f"【重要提示】：如果用户在指令中提到“第 N 篇”（如“第 5 篇”），指的就是上方提供的这整篇论文！请**绝对不要**将其误解为“论文的第五部分”或“第五章”。\n"
            f"请直接忽略用户指令里的序号指代，把注意力集中在动作上（如“详细解释”、“总结”等），并基于上方提供的论文全文为您生成专业的回答。"
        )

        try:
            llm = make_qwen_llm(model_name=self.model_name, temperature=0.1)
            from langchain_core.messages import HumanMessage, SystemMessage

            resp = llm.invoke([
                SystemMessage(content="你是一个学术论文分析专家。请基于提供的论文内容回答问题。"),
                HumanMessage(content=focused_prompt),
            ])
            reply = resp.content or "无法生成回答。"
        except Exception as e:
            reply = f"分析论文时出错：{str(e)[:200]}"

        self._save_message("assistant", reply, paper_refs=[paper_id])
        return {
            "reply": reply,
            "tool_used": "read_paper_content",
            "papers": [],
            "paper_detail": {
                "id": paper_id,
                "title": result["title"],
                "authors": result["authors"],
                "year": result["year"],
                "venue": result["venue"],
                "abstract": result["abstract"],
                "url": result["url"],
            },
        }

    def _save_message(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        paper_refs: Optional[List[int]] = None,
    ):
        """Persist a message to the database."""
        db = SessionLocal()
        try:
            msg = ChatMessage(
                session_id=self.session_id,
                role=role,
                content=content,
                tool_name=tool_name,
                paper_refs=json.dumps(paper_refs or []),
            )
            db.add(msg)
            # Also update session title from first user message
            if role == "user":
                session = (
                    db.query(ChatSession)
                    .filter(ChatSession.id == self.session_id)
                    .first()
                )
                if session and session.title == "新对话":
                    session.title = content[:50]
            db.commit()
        finally:
            db.close()
