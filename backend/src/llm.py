from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def make_qwen_llm(model_name: str, temperature: float = 0.0) -> ChatOpenAI:
    """创建 ChatOpenAI 客户端，支持动态传入模型名称"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Qwen API key is not configured. "
            "Please set OPENAI_API_KEY in your environment/.env."
        )
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=temperature,
    )

