# 🧪 AI 测试用例生成器

基于 AI 的测试用例自动生成工具，能够解析需求文档（PRD）或接口文档（OpenAPI），自动生成结构化的测试用例，并导出为专业格式的 Excel 文件。

## ✨ 功能特性

- **多格式文档解析** - 支持 Markdown (.md)、Word (.docx)、OpenAPI JSON (.json) 格式
- **AI 智能生成** - 调用 OpenAI 兼容 API 自动生成高质量测试用例
- **五种用例类型** - 功能测试、边界测试、异常测试、流程测试、接口测试
- **在线编辑管理** - 支持查看、编辑、删除测试用例
- **多维度筛选** - 按文档、优先级、类型筛选
- **专业 Excel 导出** - 带颜色、合并单元格、自动列宽的专业格式
- **灵活 AI 配置** - 支持自定义 API 地址、密钥、模型

## 🚀 快速开始

### 1. 安装依赖

```bash
cd testcase-generator
pip install -r requirements.txt
```

### 2. 配置 AI（可选，也可在 Web 页面配置）

创建 `.env` 文件：

```env
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o
```

支持任何 OpenAI 兼容 API，如 DeepSeek、Moonshot、本地 Ollama 等。

### 3. 启动服务

```bash
python run.py
```

浏览器访问 http://localhost:8000 即可使用。

## 📖 使用流程

1. **上传文档** - 在「文档上传」页面上传需求文档或接口文档，或直接粘贴内容
2. **AI 生成** - 点击文档卡片上的「AI 生成」按钮，选择测试用例类型
3. **查看管理** - 在「测试用例」页面查看、编辑、筛选生成的用例
4. **导出 Excel** - 点击「导出 Excel」按钮下载专业格式的测试用例文件

## 🛠 API 接口

启动后访问 http://localhost:8000/docs 查看完整 API 文档（Swagger UI）。

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/documents/upload | 上传文档文件 |
| POST | /api/documents/text | 提交文本内容 |
| GET  | /api/documents | 文档列表 |
| POST | /api/testcases/generate | AI 生成测试用例 |
| GET  | /api/testcases | 测试用例列表（支持筛选） |
| PUT  | /api/testcases/{id} | 更新测试用例 |
| DELETE | /api/testcases/{id} | 删除测试用例 |
| GET  | /api/export/excel | 导出 Excel |
| GET  | /api/config | 获取 AI 配置 |
| PUT  | /api/config | 更新 AI 配置 |

## 📁 项目结构

```
testcase-generator/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── models.py            # Pydantic 数据模型
│   ├── database.py          # SQLite 数据库操作
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── markdown_parser.py
│   │   ├── docx_parser.py
│   │   └── openapi_parser.py
│   ├── generators/
│   │   ├── __init__.py
│   │   └── ai_generator.py  # AI 生成核心逻辑
│   └── exporters/
│       ├── __init__.py
│       └── excel_exporter.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── run.py                   # 启动脚本
└── README.md
```

## 🔧 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLite
- **前端**: 原生 HTML + CSS + JavaScript
- **AI**: OpenAI 兼容 API（支持自定义）
- **导出**: openpyxl
