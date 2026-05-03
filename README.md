# 🧪 AI 测试用例生成器

基于 AI 的智能测试用例自动生成工具，能够解析需求文档（PRD）、接口文档（OpenAPI/Swagger）或 Word 文档，自动生成结构化的测试用例，并导出为专业格式的 Excel 文件。

[English](./README.md) | 简体中文

---

## 📌 目录

- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [使用流程](#-使用流程)
- [项目结构](#-项目结构)
- [API 文档](#-api-文档)
- [测试用例格式](#-测试用例格式)
- [AI 配置](#-ai-配置)
- [常见问题](#-常见问题)

---

## ✨ 功能特性

### 📄 文档解析

| 格式 | 支持情况 | 说明 |
|------|----------|------|
| Markdown (.md) | ✅ 完全支持 | 解析 PRD、需求文档 |
| Word (.docx) | ✅ 完全支持 | 解析需求规格说明书 |
| OpenAPI/Swagger (.json) | ✅ 完全支持 | 解析 API 接口定义 |
| 纯文本 | ✅ 完全支持 | 直接粘贴文本内容 |

### 🤖 AI 智能生成

- **多类型测试用例**：支持 5 种测试用例类型的智能生成
  - 功能测试（Happy Path）
  - 边界测试（Boundary Testing）
  - 异常测试（Error Testing）
  - 流程测试（User Flow）
  - 接口测试（API Testing）

- **灵活的 AI 配置**：支持任何 OpenAI 兼容 API
  - OpenAI GPT-4 / GPT-4o
  - DeepSeek V3 / Codestral
  - Moonshot (月之暗面)
  - 本地 Ollama
  - 其他兼容 API

### 📊 测试用例管理

- **在线管理**：Web UI 直接查看、编辑、删除测试用例
- **多维度筛选**：按文档、模块、优先级、类型筛选
- **批量操作**：支持批量删除、批量导出

### 📥 导出功能

- **Excel 导出**：专业格式，带颜色标识和合并单元格
- **PDF 导出**：适合打印和分享
- **按条件导出**：支持筛选后导出

---

## 🔧 技术栈

### 后端

| 技术 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+ | 运行环境 |
| FastAPI | ≥0.115.0 | Web 框架 |
| Pydantic | ≥2.9.0 | 数据验证 |
| OpenAI SDK | ≥1.50.0 | AI 接口调用 |
| python-docx | ≥1.1.0 | Word 文档解析 |
| openpyxl | ≥3.1.5 | Excel 文件生成 |
| aiosqlite | ≥0.20.0 | 异步 SQLite |
| Playwright | ≥1.40.0 | 自动化测试（可选） |

### 前端

- 原生 HTML5 + CSS3 + JavaScript（ES6+）
- 无需任何前端框架
- 响应式设计，支持桌面和移动端

### 数据存储

- **SQLite**：轻量级嵌入式数据库，开箱即用
- **文件存储**：本地文件系统存储上传文档

---

## 🚀 快速开始

### 环境要求

- Python 3.11 或更高版本
- Windows / macOS / Linux

### 1. 克隆项目

```bash
git clone https://github.com/Rue1218/testcase-generator.git
cd testcase-generator
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 uv（推荐，更快）
uv venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate      # Windows

# 或使用 Python 内置 venv
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 AI（可选）

在项目根目录创建 `.env` 文件：

```env
# OpenAI 示例
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o

# 或 DeepSeek 示例
# AI_BASE_URL=https://api.deepseek.com/v1
# AI_API_KEY=your-deepseek-api-key
# AI_MODEL=deepseek-chat

# 或本地 Ollama 示例
# AI_BASE_URL=http://localhost:11434/v1
# AI_API_KEY=ollama
# AI_MODEL=qwen2.5
```

### 5. 启动服务

```bash
python run.py
```

### 6. 访问应用

打开浏览器访问：**http://localhost:8000**

API 文档：**http://localhost:8000/docs**（Swagger UI）

---

## 📖 使用流程

### 步骤 1：上传文档

进入「文档上传」页面，选择以下任一方式：

- **文件上传**：支持 .md、.docx、.json 格式
- **粘贴文本**：直接在文本框输入内容
- **导入 API**：输入 OpenAPI/Swagger URL 或粘贴 JSON

### 步骤 2：AI 生成测试用例

1. 在文档列表中找到刚上传的文档
2. 点击「AI 生成」按钮
3. 选择要生成的测试用例类型：
   - 功能测试
   - 边界测试
   - 异常测试
   - 流程测试
   - 接口测试
4. 设置生成数量（默认 10 条）
5. 点击「开始生成」

### 步骤 3：查看与管理

进入「测试用例」页面：

- **查看**：点击用例查看详细信息
- **编辑**：修改用例的任何字段
- **删除**：删除单个或批量删除
- **筛选**：按文档、模块、优先级、类型筛选

### 步骤 4：导出

1. 选择要导出的用例（可先筛选）
2. 点击「导出 Excel」或「导出 PDF」
3. 文件将自动下载

---

## 📁 项目结构

```
testcase-generator/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理（AI、数据库路径等）
│   ├── models.py               # Pydantic 数据模型
│   ├── database.py             # SQLite 数据库操作
│   │
│   ├── parsers/                # 文档解析器
│   │   ├── __init__.py
│   │   ├── markdown_parser.py # Markdown 解析
│   │   ├── docx_parser.py     # Word 文档解析
│   │   ├── openapi_parser.py  # OpenAPI/Swagger 解析
│   │   ├── pdf_parser.py      # PDF 解析
│   │   └── spreadsheet.py     # 表格数据解析
│   │
│   ├── generators/              # AI 生成器
│   │   ├── __init__.py
│   │   └── ai_generator.py    # AI 测试用例生成核心
│   │
│   ├── exporters/              # 导出器
│   │   ├── __init__.py
│   │   ├── excel_exporter.py  # Excel 导出
│   │   └── pdf_exporter.py    # PDF 导出
│   │
│   ├── routers/                # API 路由
│   │   ├── __init__.py
│   │   ├── _shared.py         # 共享工具
│   │   ├── documents.py       # 文档管理
│   │   ├── testcases.py      # 测试用例
│   │   ├── config.py          # AI 配置
│   │   ├── export.py          # 导出
│   │   ├── executor.py        # 测试执行
│   │   ├── suites.py          # 测试套件
│   │   ├── tasks.py           # 异步任务
│   │   ├── logs.py            # 日志管理
│   │   ├── templates.py       # 模板管理
│   │   ├── trash.py           # 回收站
│   │   └── system.py          # 系统信息
│   │
│   ├── executor/               # 测试执行器
│   │   ├── __init__.py
│   │   ├── runner.py          # 测试运行器
│   │   ├── env_check.py       # 环境检查
│   │   ├── prompts.py         # AI 提示词
│   │   ├── suites.py          # 测试套件
│   │   └── report.py          # 报告生成
│   │
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       └── sanitizer.py        # 输入净化
│
├── frontend/
│   ├── index.html             # 主页面
│   ├── style.css              # 样式文件
│   └── app.js                 # 前端逻辑
│
├── uploads/                    # 上传文件存储
├── backups/                    # 数据库备份
├── test_results/              # 测试结果存储
│
├── requirements.txt           # Python 依赖
├── run.py                     # 启动脚本
├── setup.sh                   # Linux/macOS 安装脚本
├── install_uv.sh              # UV 安装脚本
├── start.bat                  # Windows 启动脚本
│
└── README.md                  # 项目说明文档
```

---

## 🛠 API 文档

启动服务后访问 **http://localhost:8000/docs** 查看完整的 Swagger UI 文档。

### 核心接口

#### 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/documents/upload` | 上传文档文件 |
| POST | `/api/documents/text` | 提交文本内容 |
| GET | `/api/documents` | 获取文档列表 |
| GET | `/api/documents/{id}` | 获取文档详情 |
| DELETE | `/api/documents/{id}` | 删除文档 |

#### 测试用例

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/testcases/generate` | AI 生成测试用例 |
| GET | `/api/testcases` | 获取用例列表（支持筛选） |
| GET | `/api/testcases/{id}` | 获取用例详情 |
| PUT | `/api/testcases/{id}` | 更新用例 |
| DELETE | `/api/testcases/{id}` | 删除用例 |
| DELETE | `/api/testcases` | 批量删除 |

#### 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/export/excel` | 导出 Excel |
| GET | `/api/export/pdf` | 导出 PDF |

#### AI 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取当前配置 |
| PUT | `/api/config` | 更新配置 |
| POST | `/api/config/test` | 测试连接 |

#### 测试执行

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/executor/run` | 运行测试 |
| GET | `/api/executor/status/{task_id}` | 获取执行状态 |
| GET | `/api/executor/logs/{task_id}` | 获取执行日志 |

### 请求示例

#### 生成测试用例

```bash
curl -X POST "http://localhost:8000/api/testcases/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "case_type": "功能测试",
    "count": 10
  }'
```

#### 导出 Excel

```bash
curl -X GET "http://localhost:8000/api/export/excel?document_id=1&priority=P0" \
  -o testcases.xlsx
```

---

## 📋 测试用例格式

每条测试用例包含以下字段：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 用例编号 | string | 唯一标识符 | TC-001 |
| 所属模块 | string | 功能模块名称 | 用户管理 |
| 用例标题 | string | 测试用例名称 | 正确用户名密码登录成功 |
| 前置条件 | string | 执行前提条件 | 用户已注册且未登录 |
| 测试步骤 | string | 详细操作步骤 | 1. 打开登录页<br>2. 输入正确用户名<br>3. 输入正确密码<br>4. 点击登录 |
| 预期结果 | string | 期望结果 | 登录成功，跳转至首页 |
| 优先级 | enum | P0/P1/P2/P3 | P0 |
| 用例类型 | enum | 功能/边界/异常/流程/接口 | 功能测试 |
| 创建时间 | datetime | 创建时间戳 | 2026-05-03 10:00:00 |

### 优先级说明

| 优先级 | 说明 | 典型场景 |
|--------|------|----------|
| P0 | 核心功能 | 登录、支付等关键流程 |
| P1 | 重要功能 | 核心业务逻辑 |
| P2 | 一般功能 | 普通功能模块 |
| P3 | 辅助功能 | 边缘场景、低频功能 |

---

## 🤖 AI 配置

### 支持的 AI 服务商

#### OpenAI

```env
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-xxxxx
AI_MODEL=gpt-4o
```

#### DeepSeek

```env
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=sk-xxxxx
AI_MODEL=deepseek-chat
```

#### Moonshot (月之暗面)

```env
AI_BASE_URL=https://api.moonshot.cn/v1
AI_API_KEY=sk-xxxxx
AI_MODEL=moonshot-v1-8k
```

#### 本地 Ollama

```env
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
AI_MODEL=qwen2.5
```

### 在 Web 界面配置

1. 点击右上角「设置」图标
2. 填写 API Base URL、API Key、Model
3. 点击「测试连接」验证配置
4. 保存配置

---

## ❓ 常见问题

### Q: 启动报错 "ModuleNotFoundError"

确保已激活虚拟环境并安装依赖：

```bash
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Q: AI 生成失败

1. 检查 API Key 是否正确
2. 确认网络可以访问 AI 服务商
3. 查看日志中的具体错误信息
4. 可在设置中点击「测试连接」排查

### Q: Excel 导出格式错乱

尝试以下方法：

1. 使用 Microsoft Excel 打开（而非 WPS）
2. 检查数据中是否有特殊字符
3. 增加列宽设置

### Q: 如何处理大型文档？

- 单个文档建议不超过 1MB
- 大型文档可分批上传
- 或使用文本粘贴方式分段处理

### Q: 数据存储在哪里？

- 数据库：`data.db`（SQLite 文件）
- 上传文件：`uploads/` 目录
- 备份文件：`backups/` 目录

建议定期备份 `data.db` 和 `uploads/` 目录。

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代快速的 Web 框架
- [OpenAI](https://openai.com/) - AI 能力支持
- [python-docx](https://python-docx.readthedocs.io/) - Word 文档处理
- [openpyxl](https://openpyxl.readthedocs.io/) - Excel 文件生成
