# AI Test Case Generator

## 项目概述
一个基于AI的测试用例自动生成工具，能够解析需求文档（PRD）或接口文档（API Doc），自动生成结构化的测试用例，并导出为Excel文件。

## 功能需求

### 1. 文档解析
- 支持上传 Markdown (.md) 格式的需求文档
- 支持上传 JSON 格式的接口文档（Swagger/OpenAPI）
- 支持上传 Word (.docx) 格式的需求文档
- 支持直接粘贴文本内容

### 2. AI 测试用例生成
- 基于解析后的文档内容，使用 LLM 自动生成测试用例
- 生成的测试用例类型包括：
  - 正向功能测试（Happy Path）
  - 边界条件测试
  - 异常场景测试
  - 用户流程测试
  - 接口参数校验测试（针对API文档）
- 每条测试用例包含：
  - 用例编号
  - 所属模块/功能
  - 用例标题
  - 前置条件
  - 测试步骤
  - 预期结果
  - 优先级（P0/P1/P2/P3）
  - 用例类型（功能/边界/异常/性能/安全）

### 3. 测试用例管理与编辑
- Web UI 界面展示生成的测试用例
- 支持在线编辑测试用例
- 支持删除/新增测试用例
- 支持按模块、优先级筛选

### 4. 导出功能
- 导出为 Excel (.xlsx) 文件
- 支持自定义导出模板
- 支持按筛选条件导出

## 技术栈

### 后端
- Python 3.11+
- FastAPI 作为 Web 框架
- OpenAI API 兼容接口（支持自定义 base_url 和 api_key）
- python-docx 解析 Word 文档
- openpyxl 生成 Excel 文件

### 前端
- HTML + CSS + JavaScript（单页面应用，不使用复杂框架）
- 使用简洁的 UI 设计

### 数据存储
- SQLite（轻量级，无需额外数据库）

## 项目结构
```
testcase-generator/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── markdown_parser.py
│   │   ├── docx_parser.py
│   │   └── openapi_parser.py
│   ├── generators/
│   │   ├── __init__.py
│   │   └── ai_generator.py  # AI 生成核心逻辑
│   ├── exporters/
│   │   ├── __init__.py
│   │   └── excel_exporter.py
│   └── database.py          # SQLite 数据库操作
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── PROJECT.md
└── README.md
```

## API 设计

### 文档上传
- POST /api/documents/upload - 上传文档文件
- POST /api/documents/text - 直接提交文本内容

### 测试用例生成
- POST /api/testcases/generate - 基于文档生成测试用例
- GET /api/testcases - 获取测试用例列表（支持筛选）
- PUT /api/testcases/{id} - 更新测试用例
- DELETE /api/testcases/{id} - 删除测试用例

### 导出
- GET /api/export/excel - 导出 Excel 文件

### 配置
- GET /api/config - 获取当前 AI 配置
- PUT /api/config - 更新 AI 配置（API Key, Base URL, Model）

## LLM 调用方式
使用 OpenAI 兼容的 API 格式，支持用户自定义：
- base_url（默认 https://api.openai.com/v1）
- api_key
- model（默认 gpt-4o）

## 注意事项
1. 代码要有完善的错误处理
2. 前端界面要简洁美观，中文界面
3. Excel 导出格式要专业、美观
4. AI prompt 要精心设计，确保生成高质量测试用例
5. 所有中文注释和日志
