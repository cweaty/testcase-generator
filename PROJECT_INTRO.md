# AI 测试用例生成器 - 项目详细介绍

## 1. 项目概述

**AI 测试用例生成器** 是一个基于 AI 的测试用例自动生成工具，能够解析需求文档（PRD）或接口文档（OpenAPI/Swagger），自动生成结构化的测试用例，并支持导出为专业格式的 Excel 文件。

### 核心功能
- 多格式文档解析（Markdown、Word、OpenAPI JSON、PDF）
- AI 智能生成测试用例（支持 OpenAI 兼容 API）
- 测试用例在线管理与编辑
- Playwright 自动化测试执行
- 测试套件管理与定时任务
- 专业格式导出（Excel、PDF）

---

## 2. 技术架构

### 技术栈
| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11+ / FastAPI |
| 数据库 | SQLite + aiosqlite（异步操作，支持连接池） |
| AI 接口 | OpenAI 兼容 API（支持 DeepSeek、Moonshot、Ollama 等） |
| 文档解析 | python-docx、PyMuPDF、markdown |
| 自动化测试 | Playwright |
| 导出格式 | openpyxl（Excel）、FPDF2（PDF） |
| 前端 | 原生 HTML + CSS + JavaScript（单页面应用） |

### 项目结构
```
testcase-generator/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理（支持 .env）
│   ├── models.py            # Pydantic 数据模型
│   ├── database.py          # SQLite 数据库操作
│   ├── parsers/             # 文档解析器
│   │   ├── markdown_parser.py
│   │   ├── docx_parser.py
│   │   ├── openapi_parser.py
│   │   ├── pdf_parser.py
│   │   └── spreadsheet.py
│   ├── generators/
│   │   └── ai_generator.py  # AI 生成核心逻辑
│   ├── exporters/           # 导出器
│   │   ├── excel_exporter.py
│   │   └── pdf_exporter.py
│   ├── executor/            # 自动化测试执行
│   │   ├── runner.py        # Playwright 执行器
│   │   ├── suites.py        # 测试套件管理
│   │   ├── report.py        # 测试报告生成
│   │   ├── env_check.py     # 环境检测
│   │   └── prompts.py       # 执行提示词
│   ├── routers/             # API 路由模块
│   │   ├── documents.py     # 文档管理
│   │   ├── testcases.py    # 测试用例管理
│   │   ├── config.py       # AI 配置
│   │   ├── export.py        # 导出功能
│   │   ├── templates.py    # Prompt 模板
│   │   ├── executor.py     # 测试执行
│   │   ├── suites.py       # 测试套件
│   │   ├── trash.py        # 回收站
│   │   ├── tasks.py        # 任务队列
│   │   ├── logs.py         # 操作日志
│   │   └── system.py       # 系统信息
│   └── utils/
│       └── sanitizer.py     # 数据净化工具
├── frontend/
│   ├── index.html           # 主页面
│   ├── style.css            # 样式文件
│   └── app.js               # 前端逻辑
├── uploads/                 # 上传文件目录
├── requirements.txt         # Python 依赖
├── run.py                   # 启动脚本
└── data.db                  # SQLite 数据库
```

---

## 3. 功能模块详解

### 3.1 文档解析模块 (`backend/parsers/`)

| 解析器 | 支持格式 | 功能说明 |
|--------|----------|----------|
| Markdown Parser | `.md` | 解析 Markdown 格式的需求文档 |
| DOCX Parser | `.docx` | 解析 Word 文档 |
| OpenAPI Parser | `.json` | 解析 Swagger/OpenAPI 3.0 接口文档 |
| PDF Parser | `.pdf` | 解析 PDF 文档 |
| Spreadsheet Parser | `.xlsx`/.csv | 解析表格数据 |

### 3.2 AI 生成模块 (`backend/generators/ai_generator.py`)

**核心特性：**
- 支持流式和非流式两种生成模式
- 5 种测试用例类型自动生成：
  - 功能测试（Happy Path）
  - 边界测试
  - 异常测试
  - 流程测试（E2E）
  - 接口测试
- 自动重试机制（最多 3 次）
- 增强的 JSON 解析（处理各种 AI 输出格式）
- 支持自定义 Prompt 模板

**输出字段：**
```json
{
  "case_id": "TC-001",
  "module": "模块名称",
  "title": "测试用例标题",
  "priority": "P0/P1/P2/P3",
  "case_type": "功能测试/边界测试/异常测试/流程测试/接口测试",
  "precondition": "前置条件",
  "steps": "1. 步骤一\n2. 步骤二",
  "expected_result": "预期结果"
}
```

### 3.3 测试用例管理 (`backend/routers/testcases.py`)

**功能：**
- 查看、编辑、删除测试用例
- 多维度筛选（文档、优先级、类型）
- 全文搜索（FTS5 全文索引）
- 版本历史管理（支持回滚）
- 回收站功能（误删恢复）

**优先级定义：**
| 优先级 | 说明 |
|--------|------|
| P0 | 冒烟测试，阻塞级 |
| P1 | 核心功能，必须通过 |
| P2 | 一般功能测试 |
| P3 | 边界/低优先级场景 |

### 3.4 自动化测试执行 (`backend/executor/`)

**核心功能：**
- 将测试用例自动转换为 Playwright 代码
- 支持单条执行、批量执行、套件执行
- SSE 流式返回执行进度
- 自动截图捕获失败场景
- 执行历史记录与回放

**执行结果包含：**
- 通过/失败状态
- 执行耗时
- 完成步数/总步数
- 错误信息
- 截图列表
- 完整日志（stdout/stderr）

### 3.5 测试套件管理 (`backend/routers/suites.py`)

**功能：**
- 创建测试套件（自定义名称、描述、基础 URL、超时时间）
- 批量添加/移除测试用例
- 套件级别执行与统计
- 定时任务支持（基于 cron 表达式）
- HTML 测试报告生成

### 3.6 导出功能 (`backend/exporters/`)

**支持格式：**
| 格式 | 说明 |
|------|------|
| Excel (.xlsx) | 带颜色、合并单元格、自动列宽的专业格式 |
| PDF (.pdf) | 便携式文档格式 |

**导出特性：**
- 按筛选条件导出
- 批量导出
- 自定义模板支持

---

## 4. 数据库设计

### 核心表结构

```sql
-- 文档表
documents (
  id, filename, doc_type, content, file_size, created_at
)

-- 测试用例表
testcases (
  id, case_id, document_id, module, title, precondition,
  steps, expected_result, priority, case_type,
  created_at, updated_at
)

-- 回收站表
deleted_testcases (...)

-- Prompt 模板表
prompt_templates (
  id, name, content, is_default, created_at
)

-- 操作日志表
operation_logs (
  id, action, target_type, target_id, detail, created_at
)

-- 测试用例历史表
testcase_history (
  id, testcase_id, case_id, module, title, precondition,
  steps, expected_result, priority, case_type,
  edited_by, edit_reason, created_at
)

-- 生成任务表
generation_tasks (
  id, status, task_type, document_id, progress, total,
  result, error, created_at, completed_at
)

-- 测试执行记录表
test_executions (
  id, case_id, tc_id, title, passed, message,
  steps_completed, steps_total, duration_ms,
  run_dir, code, stdout, stderr, screenshots, executed_at
)

-- 测试套件表
test_suites (
  id, name, description, base_url, timeout, created_at, updated_at
)

-- 套件成员表
suite_members (
  id, suite_id, testcase_id, sort_order
)

-- 定时任务表
scheduled_tasks (
  id, suite_id, cron_expr, enabled, last_run, next_run, created_at
)

-- 执行报告表
execution_reports (
  id, suite_id, suite_name, total, passed, failed,
  duration_ms, report_html, base_url, created_at
)

-- 应用配置表
app_config (
  key, value
)
```

---

## 5. API 接口

### 主要接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/documents/upload | 上传文档文件 |
| POST | /api/documents/text | 提交文本内容 |
| GET | /api/documents | 文档列表 |
| DELETE | /api/documents/{id} | 删除文档 |
| POST | /api/testcases/generate | AI 生成测试用例 |
| GET | /api/testcases | 测试用例列表（支持筛选） |
| PUT | /api/testcases/{id} | 更新测试用例 |
| DELETE | /api/testcases/{id} | 删除测试用例 |
| GET | /api/export/excel | 导出 Excel |
| GET | /api/config | 获取 AI 配置 |
| PUT | /api/config | 更新 AI 配置 |
| GET | /api/templates | Prompt 模板列表 |
| POST | /api/templates | 创建模板 |
| POST | /api/executor/run/{tc_id} | 执行单个测试用例 |
| POST | /api/executor/run/batch | 批量执行 |
| POST | /api/executor/preview/{tc_id} | 代码预览 |
| GET | /api/suites | 套件列表 |
| POST | /api/suites | 创建套件 |
| POST | /api/suites/{id}/run | 执行套件 |
| GET | /api/reports | 执行报告列表 |
| GET | /api/env/check | 环境检测 |

---

## 6. Prompt 模板系统

系统内置 7 种 Prompt 模板：

| 模板名称 | 说明 |
|----------|------|
| 默认模板 | 系统内置标准模板 |
| 详细用例 | 生成详细步骤（≥5步），覆盖所有边界条件 |
| 精简用例 | 聚焦核心功能，步骤精简（2-3步） |
| 接口专项 | API 接口测试，覆盖 HTTP 方法、参数校验、错误码 |
| 安全测试 | XSS、CSRF、SQL 注入、越权访问等 |
| 性能测试 | 负载测试、压力测试、并发测试 |
| 兼容性测试 | 浏览器、分辨率、操作系统兼容性 |

---

## 7. 配置管理

### 环境变量配置（.env）
```env
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=16000
```

### 支持的 AI 服务
- OpenAI GPT-4o / GPT-4 / GPT-3.5
- DeepSeek
- Moonshot
- 本地 Ollama
- 任何 OpenAI 兼容 API

---

## 8. 快速开始

### 1. 安装依赖
```bash
cd testcase-generator
pip install -r requirements.txt
```

### 2. 配置 AI
创建 `.env` 文件并配置 API Key

### 3. 启动服务
```bash
python run.py
```

### 4. 访问应用
- 前端界面：http://localhost:8088
- API 文档：http://localhost:8088/docs

---

## 9. 版本信息

- **当前版本**：v4.0.0
- **构建时间**：2026-05-02
- **主要更新**：新增测试套件管理、自动化执行、环境检测、报告系统

---

## 10. 扩展功能

### 计划中的功能
- [ ] 定时任务自动执行
- [ ] CI/CD 集成支持
- [ ] 测试用例评审工作流
- [ ] 团队协作功能
- [ ] 更多导出格式（Word、HTML）
