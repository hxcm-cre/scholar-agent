from __future__ import annotations

from typing import Dict, List
import os
from src.state import AgentState
from src.llm import make_qwen_llm
import time # 导入时间模块

ASSISTANT_SYSTEM_PROMPT = """\
You are a professional academic research assistant with deep expertise in the fields of science, engineering, social sciences, and humanities.

Your goal is to preprocess the user's request for a specialized research pipeline.

Tasks:
1. **Query Normalization**: 
   - Extract the exact core search concepts from the user's input.
   - Remove stop words (e.g., "and", "or", "about", "search for") and generic terms (e.g., "accuracy", "evaluation", "papers").
   - **CRITICAL RULE**: Do NOT invent or add new keywords that the user did not explicitly mention. Do NOT copy examples.
   - Combine the remaining core keywords into a single search phrase.
     - *Example*: "Search for papers about AI and legal" -> "AI legal"
   - **OUTPUT FORMAT**: provide the synthesized keywords/phrase.
2. **Intent Classification**: 
   - "literature": Mapping the state-of-the-art (SOTA) or reviewing existing work.
   - "experiment": Comparing local data/results against published benchmarks.
   - "answer": Seeking a factual or theoretical explanation.
3. **Dynamic Metric Identification**: 
   - Based on the specific sub-field identified in the query, list 2-3 standard quantitative or qualitative performance indicators used in top-tier peer-reviewed journals.
   - **DO NOT** limit yourself to common examples. Think about specific units or specialized benchmarks (e.g., "RMSE, ARMSE, time consumption, ATE/RPE ..." for state estimation, "WER..." for Speech, "Gini Coefficient..." for Economics, or "Effect Size..." for Psychology).
   - If the field is purely theoretical, provide methodological keywords.

Return ONLY a valid JSON object:
{
  "normalized_query": string,
  "intent": "literature" | "experiment" | "answer",
  "domain_metrics": string[],
  "field_category": string
}
"""

def assistant_node(state: AgentState) -> Dict:
    """Interpret the raw user query and set high-level intent."""
    start = time.time()
    raw_query = (state.get("query") or "").strip() # strip()移除字符串头尾两端指定的字符（默认为所有的空白字符）
    # 默认值
    intent = "literature"
    normalized = raw_query
    domain_metrics = ["accuracy", "runtime"] # 通用保底指标
    tokens = 0

    # If Qwen is configured, try to refine AI 深度理解与精炼
    if raw_query:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
            current_model = os.getenv("SELECTED_MODEL_NAME", "qwen2.5-32b-instruct")
            llm = make_qwen_llm(model_name=current_model, temperature=0.0)
            messages: List = [
                SystemMessage(content=ASSISTANT_SYSTEM_PROMPT),
                HumanMessage(content=raw_query),
            ]
            resp = llm.invoke(messages)
            tokens = resp.response_metadata.get("token_usage", {}).get("total_tokens", 0)
            content = getattr(resp, "content", "")
            if isinstance(content, str):
                import json

                data = json.loads(content)
                normalized = data.get("normalized_query", normalized)
                intent = data.get("intent", intent)
                domain_metrics = data.get("domain_metrics", domain_metrics)
        except Exception as e:
            print(f"Assistant node Error: {e}")

    # 合并用户输入的指标
    user_metrics_raw = (state.get("user_metrics") or "").strip()
    if user_metrics_raw:
        user_list = [m.strip() for m in user_metrics_raw.split(",") if m.strip()]
        # 使用 set 去重并保持顺序（通过 dict.fromkeys）
        combined = list(dict.fromkeys(domain_metrics + user_list))
        domain_metrics = combined

    duration = round(time.time() - start, 2)
    # 更新 state 中的耗时记录
    metrics = state.get("metrics_log")
    metrics["node_durations"]["assistant"] = duration
    metrics["total_tokens"]["assistant"] = tokens
    # 使用经过 LLM 规范化的 query 替换原始 query，以滤除 "and" 等无用停用词，提升检索准确率
    return {"query": normalized, "user_metrics": user_metrics_raw, "intent": intent, "domain_metrics": domain_metrics, "metrics_log": metrics}

