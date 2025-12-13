# NL2SQL - 自然语言转 SQL 实战项目

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **当前版本**: M9.75 - 上下文记忆与澄清集成  
> **状态**: ✅ 核心功能已实现并测试通过  
> **说明**: M6 阶段（RAG增强）暂时跳过，现已完成M9.75阶段（上下文记忆与澄清集成）  
> **TODO**: 优化澄清功能（封闭式提问效果不好）

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

6. **运行程序**
   ```bash
   # 启动用户交互程序（推荐）
   python nl2sql_chat.py
   ```
   
   **使用示例**：
   ```
   💬 请输入您的问题: 查询每个客户的订单数量
   
   🔍 正在处理：查询每个客户的订单数量...
   
   ============================================================
   📊 查询结果
   ============================================================
   
   📌 结论
   ──────────────────────────────────────────────────
   查询结果显示，共有59个客户，每个客户都有订单记录...
   
   📌 关键值
   ──────────────────────────────────────────────────
     - 总客户数: 59
     - 平均订单数: 7.5
     - 最大订单数: 13
   
   📌 SQL说明
   ──────────────────────────────────────────────────
   本次查询通过JOIN customer表和invoice表，统计了每个客户的订单数量...
   
   ============================================================
   
   💬 请输入您的问题: sql
   💡 SQL查询已显示
   
   💬 请输入您的问题: 查询每个客户的订单数量
   ...
   💻 执行的SQL查询：
      SELECT c.CustomerId, c.FirstName, c.LastName, COUNT(i.InvoiceId) as order_count
      FROM customer c
      INNER JOIN invoice i ON c.CustomerId = i.CustomerId
      GROUP BY c.CustomerId, c.FirstName, c.LastName;
   ```
   
 



#### 功能特性

- **自动 Schema 抽取**：首次运行自动生成 `data/schema.json`
- **智能表匹配**：根据问题自动匹配相关表，减少 token 消耗
- **SQL 语法验证**：使用 sqlglot 在执行前验证 SQL 语法
- **自动修复**：SQL 有错误时自动分析并重新生成（最多 3 次）
- **多轮对话澄清** (M7/M9.75)：自动识别模糊问题，生成封闭式澄清问句，支持多轮交互，集成上下文记忆
- **多表 JOIN 生成** (M8)：基于外键关系自动生成 JOIN 路径，支持2-4表联结
- **自然语言答案** (M9)：将SQL结果转换为易读的自然语言答案，包含结论、关键值和SQL说明
- **安全加固** (M9.5)：SQL注入防护、敏感信息保护、输入验证、沙箱增强
- **聊天支持** (M9.5)：智能识别聊天回复，区分SQL查询和普通对话
- **上下文记忆** (M9.75)：跨查询的上下文记忆管理，支持多轮对话中的指代理解

## 项目结构

```
rookie-nl2sql-main/
├── configs/              # 配置文件
│   ├── config.py        # 配置管理器
│   └── dev.yaml         # 开发环境配置
├── data/                # 数据目录
│   └── schema.json     # 数据库 Schema（自动生成）
├── graphs/              # LangGraph 流程定义
│   ├── base_graph.py   # 主流程图 (M9.5: 添加聊天响应路由)
│   ├── state.py        # 状态定义 (M9.5: 添加聊天响应字段)
│   ├── nodes/          # 节点实现
│   │   ├── generate_sql.py   # SQL 生成节点 (M1/M3/M8/M9.5/M9.75: 意图识别、上下文记忆)
│   │   ├── validate_sql.py   # SQL 验证节点 (M4)
│   │   ├── critique_sql.py   # SQL 错误分析节点 (M4)
│   │   ├── clarify.py        # 澄清与消歧节点 (M7/M9.75: 上下文记忆集成)
│   │   ├── execute_sql.py   # SQL 执行节点 (M5)
│   │   └── answer_builder.py # 答案生成节点 (M9/M9.5/M9.75: 聊天响应支持、上下文记忆)
│   └── utils/          # 工具函数
│       ├── performance.py  # 性能监控
│       └── context_memory.py  # 上下文记忆管理器 (M9.75)
├── tools/               # 工具模块
│   ├── db.py           # 数据库客户端（MySQL）(M9.5: 参数化查询、错误处理优化)
│   ├── llm_client.py   # LLM 客户端 (M9.5: timeout处理优化)
│   ├── schema_manager.py # Schema 管理器 (M3/M8: JOIN路径生成, M9.5: 标识符验证)
│   └── sandbox.py      # SQL 沙箱安全模块 (M5/M9.5: 增强检查、日志脱敏)
├── prompts/             # Prompt 模板
│   ├── nl2sql.txt      # SQL 生成提示词
│   ├── critique.txt    # SQL 错误分析提示词 (M4)
│   ├── clarify.txt     # 澄清问题生成提示词 (M7)
│   └── answer.txt      # 答案生成提示词 (M9)
├── logs/                # 日志目录
├── nl2sql_chat.py       # 用户交互程序（推荐使用）
├── test/                # 测试脚本目录
│   ├── interactive_test.py  # 交互式测试工具（支持M9.5聊天功能）
│   ├── test_graph.py         # 完整流程测试脚本
│   ├── test_guardrail.py     # SQL Guardrail 功能测试脚本 (M4)
│   ├── test_sandbox.py       # SQL Sandbox 功能测试脚本 (M5)
│   ├── test_clarify.py       # Dialog Clarification 功能测试脚本 (M7/M9.75: 上下文记忆集成测试)
│   ├── test_join.py          # Multi-Table JOIN 功能测试脚本 (M8)
│   └── test_answer.py        # Answer Builder 功能测试脚本 (M9)
├── requirements.txt     # 依赖列表
└── README.md           # 项目说明
```




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
  ├─ M9.5: LLM意图识别 → 判断是聊天还是查询
  │   ├─ 聊天意图 → 使用通用聊天接口 → 直接返回回复（跳过SQL流程）
  │   └─ 查询意图 → 继续SQL生成流程
  │
  ├─ M9.75: 加载上下文记忆 → 格式化历史上下文 → 注入到Prompt
  │
  ├─ M8: 检测多表查询 → 生成JOIN路径建议 → 增强Prompt
  │
  └─ 调用LLM生成SQL → M9.5: 检测LLM返回是否为有效SQL
      ├─ 是聊天回复 → 直接返回（跳过SQL流程）
      └─ 是SQL查询 → 继续验证流程
  ↓
澄清判断 (clarify) ← M7/M9.75: 判断是否需要澄清（仅SQL查询，集成上下文记忆）
  ↓
  ├─ 需要澄清 → 生成澄清问题（基于上下文） → 输出给用户 → 等待回答
  │
  ├─ 用户已回答 → 更新问题 → 记录到上下文记忆 → 重新生成SQL (generate_sql)
  │
  └─ 不需要澄清 → SQL 验证 (validate_sql) ← 使用 sqlglot 验证语法 (M4)
       ↓
    ├─ ✓ 通过 → SQL 执行 (execute_sql) ← M5/M9.5: 安全沙箱检查（增强）
    │      ↓
    │   M9.5: 参数化查询、标识符验证、敏感信息保护
    │      ↓
    │   答案生成 (answer_builder) ← M9/M9.5/M9.75: 生成自然语言答案（支持聊天响应、上下文记忆）
    │      ↓
    │   M9.75: 更新上下文记忆 → 记录查询、SQL、答案到历史
    │      ↓
    │   结果输出 (echo) → END
    │
    └─ ✗ 失败 → 错误分析 (critique_sql) ← LLM 分析错误 (M4)
         ↓
      SQL 重新生成 (generate_sql) ← 基于 critique 修复
         ↓
      SQL 验证 (validate_sql) ← 再次验证
         ↓
      (循环，最多 3 次)
         ↓
      超过最大次数 → 结果输出 (echo) → END (显示错误)
```

## 技术栈

### 核心框架

- **LangGraph**: 状态图编排框架，用于构建 NL2SQL 工作流
- **LangChain**: LLM 应用开发框架
- **pymysql**: MySQL 数据库驱动（M9.5: 支持参数化查询）
- **sqlglot**: SQL 解析和验证库

### 配置管理

- **python-dotenv**: 环境变量管理（`.env` 文件）
- **PyYAML**: YAML 配置解析

### 数据库

- **MySQL**: 当前支持的数据库（已从 SQLite 迁移）

### LLM 支持

- **DeepSeek**: 支持 DeepSeek API
- **Qwen (通义千问)**: 支持阿里云 Qwen API
- **OpenAI**: 支持 OpenAI API（兼容其他 OpenAI 兼容服务）



## 如何实现

### 核心架构

- **模型层**：将自然语言解析为 SQL 意图（表/字段选择、过滤、聚合、排序、连接）。
- **工具层**：集成数据库 Schema 管理、智能表匹配、字段检索等工具。
- **验证层**：使用 sqlglot 进行 SQL 语法验证，LLM 驱动的错误分析和修复（M4）。
- **执行层**：在只读通道执行校验后的 SQL，返回结果集（M9.5: 参数化查询、安全加固）。
- **展示层**：命令行输出查询、SQL、日志与结果（未来可扩展为 Web 界面）。
- **安全层 (M9.5)**：SQL注入防护、输入验证、敏感信息保护、沙箱增强。
- **意图识别层 (M9.5)**：LLM驱动的意图识别，区分聊天和查询，智能路由。

### 技术路线

- **解析策略**：基于关键词和模式的意图识别，支持问题类型分类（M9.5: 增强LLM意图识别）。
- **提示工程**：注入数据库 schema 与示例查询，约束输出仅产出 SQL。
- **安全与健壮**：只读白名单、拒绝 DML（增删改），仅允许 SELECT 查询。
- **反馈闭环**：错误捕获→分析→重写→再次校验执行（M4 已实现）。
- **SQL Guardrail**：语法验证→错误分析→自动修复→再验证的完整循环（M4）。
- **SQL Sandbox**：危险关键字拦截、行数限制、执行超时、安全日志（M5）。
- **Dialog Clarification**：模糊问题识别→生成澄清问句→多轮对话→问题整合（M7/M9.75：集成上下文记忆）。
- **Multi-Table JOIN**：外键推断→关系图构建→JOIN路径生成→Few-shot增强（M8）。
- **Answer Builder**：数据摘要→关键值提取→LLM生成答案→包含结论、关键值和SQL说明（M9/M9.75：上下文记忆记录）。
- **Security Hardening**：SQL注入防护→参数化查询→标识符验证→敏感信息保护（M9.5）。
- **Chat Support**：聊天响应识别→智能路由→区分查询和对话（M9.5/M9.75：上下文记忆支持）。
- **Context Memory**：上下文记忆管理→跨查询历史维护→指代理解→澄清集成（M9.75）。
- **评估机制**：测试脚本支持端到端验证，衡量可执行率、正确率与耗时（M9.75：测试用例优化，贴近实际数据库内容）。

## 通过本项目可以学到

- **提示工程与工具协作**：让模型"理解数据库"，尊重工具边界，遵循安全校验。
- **数据库 Schema 理解**：表、字段、主外键、范式、索引对 SQL 生成与性能的影响。
- **应用工程化**：从 Notebook 原型到可复用模块（工具、执行、评估、日志），形成可上线的最小产品。
- **LangGraph 应用**：使用状态图编排复杂工作流，实现可维护的 AI 应用。
- **错误处理与鲁棒性**：语法错误、字段缺失、歧义查询的处理策略与交互设计。
- **评估与度量**：测试用例构建、指标设计、不同提示策略的效果对比。

## 版本历史

### M9.75 - 上下文记忆与澄清集成（当前版本）✅

- ✅ 上下文记忆管理器：实现统一的上下文记忆管理器，管理对话历史（查询、澄清、回答、聊天）
- ✅ 跨查询上下文支持：支持多轮对话中的上下文理解，处理指代词（那、他们、刚才等）
- ✅ 澄清功能集成：将澄清功能与上下文记忆管理器集成，澄清判断和问题生成基于历史上下文
- ✅ SQL生成上下文注入：在SQL生成时注入历史上下文，帮助LLM理解用户意图
- ✅ 聊天上下文支持：聊天响应支持上下文记忆，可以基于历史对话进行回复
- ✅ 答案生成上下文记录：答案生成后自动记录到上下文记忆，包含SQL和结果摘要
- ✅ 测试用例优化：调整澄清测试用例，使其更贴近Chinook数据库的实际内容（发票、客户、专辑等）
- ✅ 测试覆盖增强：新增上下文记忆管理器集成测试和多轮对话澄清测试
- ✅ 代码质量提升：完善上下文记忆管理器的功能，支持历史导出/导入、历史修剪等
- ✅ 文档完善：更新README和流程图，反映M9.75的上下文记忆和澄清集成功能

### M9.5 - 安全加固与聊天支持 ✅

- ✅ 安全漏洞修复：修复SQL注入风险，使用参数化查询和标识符验证
- ✅ 敏感信息保护：移除日志和打印中的敏感信息，限制日志长度
- ✅ 输入验证增强：添加用户输入长度限制和字符验证
- ✅ SQL沙箱增强：去除注释后检查，增强危险模式检测，禁止访问系统数据库
- ✅ 错误处理优化：避免泄露系统内部信息，返回用户友好的错误消息
- ✅ 聊天响应支持：使用LLM意图识别，智能区分聊天和查询，聊天问题使用通用接口
- ✅ 测试文件修复：修复所有测试文件的模块导入路径问题
- ✅ 代码质量提升：添加中文注释说明安全修复原因
- ✅ 流程图更新：更新流程图反映M9.5的新功能（意图识别、聊天响应路由）
- ✅ 文档完善：更新README和测试脚本说明，反映M9.5的所有功能

### M9 - Answer Builder ✅

- ✅ 数据摘要格式化：智能处理空结果、小数据集（≤10行）和大数据集（>10行）
- ✅ 关键值提取：自动提取数值字段的统计信息（最大值、最小值、平均值、总计等）
- ✅ 自然语言答案生成：使用LLM将SQL结果转换为易读的自然语言答案
- ✅ 答案结构：包含结论、关键值、数据摘要和SQL说明四个部分
- ✅ 严格约束：确保答案不编造字段，所有数值与实际数据完全一致
- ✅ 用户交互程序：提供 `nl2sql_chat.py` 面向最终用户的简洁交互界面
- ✅ 验收标准：答案含结论、关键值和SQL说明，无编造字段

### M8 - Multi-Table JOIN ✅

- ✅ 外键关系推断：基于字段名模式自动推断外键关系（如CustomerId → customer）
- ✅ 关系图构建：构建双向表关系图，支持BFS路径查找
- ✅ JOIN路径生成：使用BFS算法查找多表之间的最短连接路径
- ✅ JOIN类型判断：根据外键是否允许NULL自动选择INNER/LEFT JOIN
- ✅ Few-shot增强：添加6个多表JOIN示例，涵盖2-4表场景
- ✅ Prompt增强：自动在Prompt中添加JOIN路径建议和连接条件
- ✅ 验收标准：多表用例执行准确率 ≥ 70%

### M7 - Dialog Clarification ✅

- ✅ 澄清判据：自动识别模糊问题（时间范围、聚合方式、字段需求、歧义词汇）
- ✅ 生成澄清问句：LLM 生成封闭式澄清问题，提供3-5个选项
- ✅ 多轮对话：支持最多3轮澄清，维护完整对话历史
- ✅ 问题整合：自动将用户回答整合到原问题中
- ✅ 状态管理：使用 `dialog_history` 和 `user_id` 维护对话上下文
- ✅ 智能路由：根据澄清状态自动路由到不同处理流程

### M6 - RAG 增强 ⏸️

- ⏸️ **暂时跳过**：M6 阶段（RAG增强）暂时跳过，直接进入M7阶段

### M5 - SQL Sandbox ✅

- ✅ SQL 安全检查：拦截危险关键字（DROP, DELETE, UPDATE 等）
- ✅ 行数限制：自动添加 LIMIT，防止大量数据返回
- ✅ 执行超时：设置最大执行时间（默认 3 秒）
- ✅ 安全日志：记录所有被拦截的 SQL 和拦截原因
- ✅ 结构化错误：返回详细的错误代码（SANDBOX_*）和原因
- ✅ 只读账户支持：建议使用只读数据库账户

### M4 - SQL Guardrail ✅

- ✅ SQL 语法验证：使用 sqlglot 进行语法验证
- ✅ 错误分析与修复：LLM 驱动的错误分析和自动修复
- ✅ 自修复循环：验证→分析→修复→再验证的完整流程
- ✅ 重试机制：最多 3 次自动重试，防止无限循环

### M3 - 智能 Schema 匹配 ✅

- ✅ 自动 Schema 抽取：从数据库自动生成 schema.json
- ✅ 智能表匹配：根据问题自动匹配相关表
- ✅ 字段检索匹配：支持精确、别名、模糊匹配
- ✅ 表清单提示：自动生成表清单和格式化 Schema

### M2 - SQL 执行 ✅

- ✅ MySQL 支持：从 SQLite 迁移到 MySQL
- ✅ 安全执行：只读查询执行，拒绝 DML 操作
- ✅ 结果格式化：统一的查询结果格式

### M1 - SQL 生成 ✅

- ✅ 基础 SQL 生成：基于 LLM 和 Prompt 工程
- ✅ 多 LLM 支持：DeepSeek、Qwen、OpenAI

### M0 - 基础框架 ✅

- ✅ LangGraph 工作流
- ✅ 意图解析
- ✅ 日志记录


## 许可证

本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！
