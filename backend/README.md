🎓 Scholar-Agent: 自动化学术调研与实验对标助手
Scholar-Agent 是一个基于 AI Agent 架构的科研闭环工具。它能够自动连接本地文献库、云端学术资源与个人实验数据，通过多源检索和深度解析，生成包含 SOTA 指标对标的量化调研报告。

![Scholar-Agent Demo](./assets/1.png)

🌟 核心功能
多维学术检索：协同搜索本地 Zotero 库与 arXiv 云端资源。支持 DOI/标题自动去重，确保文献覆盖的全面性与唯一性。

学术权重过滤：内置筛选逻辑，优先推荐顶会/顶刊、高被引及提供开源实现的优质论文。

高精度指标抓取：利用深度学习模型从论文全文中精准提取 RMSE、MAE、计算开销等核心 SOTA 性能指标。

自动化实验对标 (Benchmark)：

自动解析本地实验数据（CSV 格式）。

智能匹配本地结果与论文公开指标。

生成定量分析报告，从噪声建模、算法参数等多维度提供诊断建议。

链接直达报告：生成的报告直接关联论文的 Web URL 和本地 PDF 路径，实现从结论到原始证据的一键跳转。

🚀 快速开始
1. 环境配置
克隆项目到本地后，安装核心依赖：

```Bash
pip install -r requirements.txt
```
2. 配置环境变量
复制 .env.example 为 .env，并配置以下关键项：

API_KEY OpenAI 兼容接口。

ZOTERO_CONFIG：配置本地文献库关联。

USE_OCR：针对扫描件 PDF，可开启 OCR 增强识别（默认为关闭以节省资源）。

3. 使用方法
模式 A：命令行
适用于调试，系统将自动迭代检索并生成 Markdown 报告。

```Bash
python main.py --query "您的科研课题 (例如: EKF attitude estimation)"
```

模式 B：交互式 Web 界面（Streamlit）
适用于可视化操作，支持实时上传实验数据并查阅对标报告。

```Bash
streamlit run app.py
```
⚖️ 许可证与原创声明
本项目采用 GPL-3.0 License 开源。

原创性：本项目包含作者原创的学术解析逻辑与实验对标算法。

引用说明：欢迎用于学术研究。如在项目、论文或商业产品中引用/修改本代码，必须保留原作者署名，并按照 GPL-3.0 协议要求开源您的衍生作品。


Developed by [hxcm-cre] @ 2026