from __future__ import annotations

import os
import time # 导入时间模块
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from typing import Optional
from main import build_graph
from src.state import AgentState
from langgraph.checkpoint.memory import MemorySaver

def run_agent_with_streaming(query: str, csv_path: Optional[str] = None):
    """
    使用 LangGraph 的 stream 模式运行 Agent，并在 UI 上实时展示节点流转
    """
    thread_id = st.session_state.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}} # 只要 thread_id 不变，记忆就在
    load_dotenv()
    if csv_path:
        os.environ["EXPERIMENT_CSV_PATH"] = csv_path
    # 记录整体开始时间
    start_time = time.time()
    app = build_graph()
    
    # --- 关键逻辑：判断是新对话还是追问 ---
    # 获取当前图的状态，看是否有历史记录
    current_state = app.get_state(config)
    if not current_state.values:
        # 情况 A: 首轮对话，传入完整 init_state
        run_input = {
            "query": query,
            "zotero_matches": [],
            "candidate_papers": [],
            "top_tier_papers": [],
            "paper_metrics": {},
            "experiment_results": {},
            "analysis_report": "",
            "iteration": 0,
            "max_iterations": 2,
            "done": False,
            "metrics_log": {"total_tokens": {}, "node_durations": {}}
        }
    else:
        # 情况 B: 多轮对话，仅更新 query，LangGraph 会自动合并状态
        # 此时旧的 processed_titles 会保留在 Checkpointer 中
        run_input = {"query": query}
    # 1. 初始化状态

    # 2. 在 UI 上创建状态追踪区域
    with st.expander("🔍 Agent 执行路径追踪", expanded=True):
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        log_messages = []

    # 开始执行
    final_state_snapshot = {}
    
    # 获取总节点数（大致估算用于进度条）
    total_steps = 6 
    current_step = 0

    for event in app.stream(run_input, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            current_step += 1
            # 更新进度与日志
            current_log = f"⚙️ ✅ **已完成**: `{node_name}`"
            detail = ""
            # 针对特定节点输出关键信息
            if node_name == "assistant":
                detail = "✅ **已完成**:分析用户研究意图"
            elif node_name == "zotero":
                detail = "✅ **已完成**:检索 Zotero 本地文献库"
            elif node_name == "query_expansion":
                detail = "✅ **已完成**:生成扩展搜索关键词"
            elif node_name == "cloud_search":
                detail = "✅ **已完成**:执行云端学术数据库检索"
            elif node_name == "filter":
                detail = "✅ **已完成**:根据期刊分区(CCF/CAS)等信息过滤高价值论文"
            elif node_name == "evaluator":
                detail = "✅ **已完成**:提取 SOTA 指标并与本地实验对标"
            
            if detail:
                log_messages.append(f"{current_log}\n   - {detail}")
            else:
                log_messages.append(current_log)
            # 实时刷新 UI 容器
            with status_placeholder.container():
                for msg in log_messages:  # 只保留最近5条，避免太长
                    st.info(msg)
            
            progress_bar.progress(min(current_step / total_steps, 1.0))
            
            # 这里的 node_output 仅包含该节点更新的字段
            final_state_snapshot.update(node_output)
    # 3. 计算最终量化指标
    # 重新获取完整状态以计算 Performance Metrics
    full_state = app.get_state(config).values

    end_time = time.time()
    total_latency = round(end_time - start_time, 2)
    # 获取各个节点的耗时分布
    durations = full_state.get("metrics_log", {}).get("node_durations", {})
    assistant_time = durations.get("assistant", 0)
    zotero_search_time = durations.get("zotero_search", 0)
    query_expansion_time = durations.get("query_expansion", 0)
    cloud_search_time = durations.get("cloud_search", 0)
    filter_time = durations.get("filter", 0)
    benchmark_node_time = durations.get("benchmark_node", 0)
    time_cost = assistant_time + zotero_search_time + query_expansion_time + cloud_search_time + filter_time + benchmark_node_time
    
    total_tokens = full_state.get("metrics_log", {}).get("total_tokens", 0)
    assistant_tokens = total_tokens.get("assistant", 0)
    zotero_search_tokens = total_tokens.get("zotero_search", 0)
    query_expansion_tokens = total_tokens.get("query_expansion", 0)
    cloud_search_tokens = total_tokens.get("cloud_search", 0)
    filter_tokens = total_tokens.get("filter", 0)
    benchmark_node_tokens = total_tokens.get("benchmark_node", 0)
    tokens_cost = assistant_tokens + zotero_search_tokens + query_expansion_tokens + cloud_search_tokens + filter_tokens + benchmark_node_tokens
    # 4. 将量化数据追加到报告末尾
    used_model = os.getenv("SELECTED_MODEL_NAME", "Unknown")
    performance_footer = f"""
---
### 📈 System Performance Metrics
- 🧠 `LLM Model`: `{used_model}`
- 👁️ `OCR Mode`: {'Enabled' if os.getenv('USE_OCR') == '1' else 'Disabled'}
- ⏱️ `Total Latency`: {time_cost}s
- 🎟️ `Total Tokens`: {tokens_cost} tokens
- **Efficiency Breakdown**:
  - 🧠 `assistant`: {assistant_time}s, ({assistant_tokens} tokens)
  - 🔍 `zotero_search`: {zotero_search_time}s, ({zotero_search_tokens} tokens)
  - 🧠 `query_expansion`: {query_expansion_time}s, ({query_expansion_tokens} tokens)
  - 🔍 `cloud_search`: {cloud_search_time}s, ({cloud_search_tokens} tokens)
  - ⏳ `filter`: {filter_time}s, ({filter_tokens} tokens)
  - 🧠 `evaluator`: {benchmark_node_time}s, ({benchmark_node_tokens} tokens)
"""
    report = full_state.get("analysis_report", "") + performance_footer

    progress_bar.progress(1.0)
    st.success(f"✅ 执行完成 ")
    return report


def main() -> None:
    st.set_page_config(page_title="Scholar-Agent", layout="wide")
    st.title("Scholar-Agent 智能科研助手")

    # --- 初始化多轮对话 ID ---
    if "thread_id" not in st.session_state:
        # 使用当前时间戳作为唯一 thread_id
        st.session_state["thread_id"] = f"user_{int(time.time())}"

    # 侧边栏设置
    with st.sidebar:
        if st.button("🗑️ 开启新对话"):
            st.session_state["thread_id"] = f"user_{int(time.time())}"
            st.session_state["report"] = ""
            st.rerun()

        st.header("系统配置")
        # --- 新增：模型选择窗口 ---
        # 可以使用 text_input 手动输入，或者 selectbox 提供常用选项
        model_options = [
            "qwen3.5-flash",
            "qwen2.5-72b-instruct",
            "qwen2.5-coder-32b-instruct",
            "qwen2.5-14b-instruct"
        ]
        selected_model = st.selectbox(
            "选择 LLM 模型",
            options=model_options,
            index=0,
            help="选择可用的模型名称"
        )
        # 也可以支持自定义输入
        custom_model = st.text_input("或手动输入模型 ID (留空则使用上方选择)", "")
        final_model = custom_model if custom_model else selected_model
        
        # 将选中的模型保存到环境变量，方便 build_graph 内部调用
        os.environ["SELECTED_MODEL_NAME"] = final_model
        st.divider()

        # 自定义评分权重
        st.header("⚖️ 论文过滤权重")
        st.caption("调整不同维度在评分系统中的占比")
        
        w_relevance = st.slider("匹配度权重 (全文关键词频率)", 0.0, 1.0, 0.5, help="论文全文与你问题的相关性")
        w_venue = st.slider("期刊等级权重 (CCF/CAS)", 0.0, 1.0, 0.30, help="论文发表平台的影响力")
        w_citation = st.slider("引用次数权重", 0.0, 1.0, 0.10)
        w_repro = st.slider("开源权重 (GitHub)", 0.0, 1.0, 0.10)
        
        # 归一化校验提示
        total_w = w_relevance + w_venue + w_citation + w_repro
        if abs(total_w - 1.0) > 0.01:
            st.warning(f"当前权重总和为 {total_w:.2f}，系统将自动进行归一化处理。")

        st.divider()

        # OCR 动态开关
        use_ocr = st.checkbox("启用 OCR (处理扫描件/图片)", value=False, help="若 PDF 为纯图片或扫描件，请开启此项")
        os.environ["USE_OCR"] = "1" if use_ocr else "0"

        show_graph = st.checkbox("可视化 Agent 架构图", value=False)
        if show_graph:
            try:
                app = build_graph()
                # 渲染 LangGraph 流程图
                st.image(app.get_graph().draw_mermaid_png())
            except Exception as e:
                st.warning(f"无法加载流程图: {e}")
        
        st.divider()
        st.markdown("### 技术栈\n- LangGraph \n- Docling (PDF Parser)\n- LLM")

    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.subheader("任务配置")
        query = st.text_input("研究问题 / 关键词", "EKF state estimation")
        uploaded = st.file_uploader("上传本地实验 CSV", type=["csv"])

        csv_path = None
        if uploaded is not None:
            csv_path = os.path.join("data", "uploaded.csv")
            df = pd.read_csv(uploaded)
            df.to_csv(csv_path, index=False)
            st.caption(f"📍 已保存到 {csv_path}")

        if st.button("🚀 运行 Scholar-Agent", use_container_width=True):
            if not query:
                st.error("请输入研究问题")
            else:
                # 运行并流式展示状态
                report = run_agent_with_streaming(query, csv_path)
                st.session_state["report"] = report

    with col_right:
        st.subheader("📊 综合对比报告")
        report = st.session_state.get("report", "")
        if report:
            # 增加一个导出按钮
            st.download_button("下载 Markdown 报告", report, file_name="scholar_report.md")
            st.markdown("---")
            st.markdown(report)
        else:
            st.info("等待 Agent 执行完成后在此展示分析报告。")


if __name__ == "__main__":
    main()

