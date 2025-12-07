# Rookie NL2SQL - 自然语言转 SQL 实战项目

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目概述

### 基本信息

**目标**：构建一套从自然语言到 SQL（NL2SQL）的端到端实战项目

**范围**：覆盖需求理解、提示工程、工具集成、SQL生成与校验、结果执行与可视化、评估与迭代。

### 背景与意义

- **降低门槛**：非技术/业务用户可以用中文提问，系统自动生成可执行 SQL，提升数据可访问性。
- **提效分析**：缩短"问题→查询→结果"的路径，减少手写 SQL 的时间成本与错误率。
- **业务落地**：广泛适用于运营分析、BI自助查询、客服质检、数据探索与问答型分析助理等场景。

### 为什么要做

- **系统性强**：NL2SQL兼具"模型+工具+安全+评估"的系统性，能形成可交付的最小可用产品（MVP）。
- **快速闭环**：基于 MySQL 数据库，快速实现"自然语言→SQL→结果→评估→优化"的闭环。

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MySQL 8.0+
- 一个 LLM API Key（DeepSeek / Qwen / OpenAI）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd rookie-nl2sql-main
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install pymysql  # MySQL 驱动
   ```

4. **配置环境变量**

   创建 `.env` 文件：
   ```env
   # LLM 配置（选择其中一个）
   LLM_PROVIDER=qwen  # 或 deepseek, openai
   
   # Qwen 配置
   QWEN_API_KEY=your_qwen_api_key
   QWEN_MODEL=qwen-max
   
   # DeepSeek 配置
   # DEEPSEEK_API_KEY=your_deepseek_api_key
   # DEEPSEEK_MODEL=deepseek-chat
   
   # OpenAI 配置
   # OPENAI_API_KEY=your_openai_api_key
   # OPENAI_MODEL=gpt-4
   
   # MySQL 数据库配置
   DB_TYPE=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=chinook
   ```

5. **准备数据库**

   确保 MySQL 中已创建 `chinook` 数据库并导入数据。可以使用项目提供的迁移脚本（如果有）。

6. **运行测试**
   ```bash
   python test_graph.py
   ```

### 使用示例

```python
from graphs.base_graph import run_query

# 运行一个自然语言查询
result = run_query("查询前5个客户的名字和邮箱")

# 查看结果
print(result['candidate_sql'])  # 生成的 SQL
print(result['execution_result'])  # 执行结果
```

或使用命令行测试：
```bash
python test_graph.py "查询所有艺术家的名字"
```

## 项目结构

```
rookie-nl2sql-main/
├── configs/              # 配置文件
│   ├── config.py        # 配置管理器
│   └── dev.yaml         # 开发环境配置
├── data/                # 数据目录
│   └── schema.json     # 数据库 Schema（自动生成）
├── graphs/              # LangGraph 流程定义
│   ├── base_graph.py   # 主流程图
│   ├── state.py        # 状态定义
│   └── nodes/          # 节点实现
│       ├── generate_sql.py   # SQL 生成节点
│       └── execute_sql.py     # SQL 执行节点
├── tools/               # 工具模块
│   ├── db.py           # 数据库客户端（MySQL）
│   ├── llm_client.py   # LLM 客户端
│   └── schema_manager.py # Schema 管理器
├── prompts/             # Prompt 模板
│   └── nl2sql.txt      # SQL 生成提示词
├── logs/                # 日志目录
├── test_graph.py        # 测试脚本
├── requirements.txt     # 依赖列表
└── README.md           # 项目说明
```

## 核心功能

### 已实现功能

1. **意图解析** (`parse_intent_node`)
   - 识别问题类型（聚合、排名、查询等）
   - 提取数量限制、时间范围等关键信息

2. **智能 Schema 匹配** (`schema_manager`)
   - 根据问题自动匹配相关表
   - 支持字段别名和模糊匹配
   - 生成优化的 Schema 提示

3. **SQL 生成** (`generate_sql_node`)
   - 基于 LLM 和 Schema 生成 SQL
   - 支持多种 LLM 提供商（DeepSeek / Qwen / OpenAI）
   - 自动提取和清理 SQL 代码

4. **SQL 执行** (`execute_sql_node`)
   - 安全的只读查询执行
   - 结果格式化返回
   - 错误处理和日志记录

5. **日志记录** (`log_node`)
   - 记录所有查询到 JSONL 文件
   - 包含会话ID、问题、意图等信息

### 工作流程

```
用户问题 
  ↓
意图解析 (parse_intent)
  ↓
日志记录 (log)
  ↓
SQL 生成 (generate_sql) ← 智能 Schema 匹配
  ↓
SQL 执行 (execute_sql)
  ↓
结果输出 (echo)
```

## 技术栈

### 核心框架

- **LangGraph**: 状态图编排框架，用于构建 NL2SQL 工作流
- **LangChain**: LLM 应用开发框架
- **pymysql**: MySQL 数据库驱动

### 配置管理

- **python-dotenv**: 环境变量管理（`.env` 文件）
- **PyYAML**: YAML 配置解析

### 数据库

- **MySQL**: 当前支持的数据库（已从 SQLite 迁移）

### LLM 支持

- **DeepSeek**: 支持 DeepSeek API
- **Qwen (通义千问)**: 支持阿里云 Qwen API
- **OpenAI**: 支持 OpenAI API（兼容其他 OpenAI 兼容服务）

## 配置说明

### 环境变量配置

主要配置项在 `.env` 文件中：

```env
# LLM 提供商选择
LLM_PROVIDER=qwen  # deepseek / qwen / openai

# 数据库配置
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=chinook
```

### YAML 配置

`configs/dev.yaml` 包含开发环境的详细配置，包括：
- LLM 模型和参数
- 数据库连接参数
- 系统行为配置

## 如何实现

### 核心架构

- **模型层**：将自然语言解析为 SQL 意图（表/字段选择、过滤、聚合、排序、连接）。
- **工具层**：集成数据库 Schema 管理、智能表匹配、字段检索等工具。
- **执行层**：在只读通道执行校验后的 SQL，返回结果集。
- **验证层**：进行语法/语义检查、字段/表存在性校验（规划中）。
- **展示层**：命令行输出查询、SQL、日志与结果（未来可扩展为 Web 界面）。

### 技术路线

- **解析策略**：基于关键词和模式的意图识别，支持问题类型分类。
- **提示工程**：注入数据库 schema 与示例查询，约束输出仅产出 SQL。
- **安全与健壮**：只读白名单、拒绝 DML（增删改），仅允许 SELECT 查询。
- **反馈闭环**：错误捕获→分析→重写→再次校验执行（规划中）。
- **评估机制**：测试脚本支持端到端验证，衡量可执行率、正确率与耗时。

## 通过本项目可以学到

- **提示工程与工具协作**：让模型"理解数据库"，尊重工具边界，遵循安全校验。
- **数据库 Schema 理解**：表、字段、主外键、范式、索引对 SQL 生成与性能的影响。
- **应用工程化**：从 Notebook 原型到可复用模块（工具、执行、评估、日志），形成可上线的最小产品。
- **LangGraph 应用**：使用状态图编排复杂工作流，实现可维护的 AI 应用。
- **错误处理与鲁棒性**：语法错误、字段缺失、歧义查询的处理策略与交互设计。
- **评估与度量**：测试用例构建、指标设计、不同提示策略的效果对比。

## 测试

项目提供了完整的测试脚本 `test_graph.py`，可以：

1. 测试数据库连接
2. 测试 Schema Manager
3. 测试 LLM 客户端
4. 测试完整 Graph 流程

运行测试：
```bash
python test_graph.py
```

使用自定义问题测试：
```bash
python test_graph.py "查询所有艺术家的名字"
```

## 扩展方向

- ✅ **MySQL 支持**：已完成从 SQLite 到 MySQL 的迁移
- **多数据库支持**：PostgreSQL、云数据仓库，跨库 NL2SQL
- **SQL 验证**：语法/语义检查、字段/表存在性校验
- **语义增强**：加入实体词典/领域术语映射，减少歧义
- **可视化模板**：自动选择图表类型（柱状、折线、饼图）与维度聚合
- **Web 界面**：基于 FastAPI 的 Web API 和前端界面
- **权限与审计**：提供数据访问控制与操作日志，满足企业级需求
- **任务编排**：批量 NL2SQL、报表定时生成与订阅
- **多轮对话**：支持上下文理解和对话历史

## 许可证

本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！
