# LLM Wikidata Pipeline

[English](README_EN.md) | [中文](README.md)

受Karpathy的LLM Wiki启发，这是一个基于大模型自动理解文档变成知识图谱的项目，所以起名为LLM Wikidata。

核心理念是解决大模型无法处理好大规模entity linking的问题，用ChromaDB向量数据库对已有entity召回，避免模型生成大量雷同的实体。

> ![Knowledge Graph Preview](assets/graph_preview.png)

## 环境要求与安装

1. **克隆项目**:
   ```bash
   git clone https://github.com/QipengGuo/llm-wikidata.git
   cd llm-wikidata
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

## 配置指南

本项目将敏感配置（如 API Key 等）与代码分离。

1. 复制配置模板：
   ```bash
   cp config.example.py config.py
   ```

2. 修改 `config.py`，填入你的 API Key 和接口地址（支持任意兼容 OpenAI SDK 的大模型 API）：
   ```python
   # 你的模型 API Key
   API_KEY = "your_api_key_here"
   
   # 模型基础请求地址和名称等其他配置可按需修改
   ```

## 使用说明

### 1. 运行流水线
主入口为 `main.py`，默认会读取 `data/articles_content.jsonl` 中的数据进行处理。
> **注**：`data/articles_content.jsonl` 中包含从“机器之心”公众号选取的 100 篇文章，作为示例。

- **真实 LLM 模式 (默认)**：默认调用配置文件中的真实大模型 API 进行文本抽取与图谱构建。
  ```bash
  python main.py
  ```

- **Mock 模式**：不调用真实 LLM 接口，适合没有 API Key 时进行本地快速流程调试。
  ```bash
  python main.py --mock
  ```

运行完成后，结果将保存在 `data/pipeline_results.jsonl` 中。

### 2. 生成可视化图谱
在流水线运行完毕后，可生成独立的交互式图谱页面。

```bash
python visualize.py
```
这将在 `data/` 目录下生成一个 `graph.html` 文件。直接用浏览器打开它，即可查看图谱。
> **注**：本项目仓库中已附带了一个基于示例数据生成的 `data/graph.html`，你可以直接下载或在浏览器中打开它，预览最终的可视化效果。

### 3. 数据库管理
使用 `db_manager.py` 可以方便地管理底层的 ChromaDB 数据库：

- **导出数据库**: `python db_manager.py export --file data/db_export.jsonl`
- **导入数据库**: `python db_manager.py import --file data/db_export.jsonl`
- **清空数据库**: `python db_manager.py clear`

## 项目结构

```text
├── config.example.py    # 配置文件模板
├── main.py              # 流水线主入口
├── visualize.py         # 知识图谱 HTML 可视化生成器
├── db_manager.py        # 向量数据库管理工具
├── requirements.txt     # 项目依赖
├── src/                 # 核心代码目录
│   ├── models.py        # Pydantic 数据模型定义
│   ├── pipeline.py      # 抽取、对齐等核心流程逻辑
│   ├── vector_store.py  # ChromaDB 封装
│   └── llm_service.py   # LLM 服务封装（支持 Mock 与 Real）
└── data/                # 数据存储目录（被 Git 忽略大部分文件）
    ├── articles_content.jsonl  # 原始文章数据（示例）
    └── chroma_db/              # ChromaDB 本地持久化目录
```
