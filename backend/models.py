"""
数据模型定义
包含 Pydantic 模型用于 API 请求/响应
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """测试用例优先级"""
    P0 = "P0"  # 冒烟测试
    P1 = "P1"  # 核心功能
    P2 = "P2"  # 一般功能
    P3 = "P3"  # 边界/低优先级


class TestCaseType(str, Enum):
    """测试用例类型"""
    FUNCTIONAL = "功能测试"
    BOUNDARY = "边界测试"
    EXCEPTION = "异常测试"
    FLOW = "流程测试"
    API = "接口测试"


class DocumentType(str, Enum):
    """文档类型"""
    MARKDOWN = "markdown"
    DOCX = "docx"
    OPENAPI = "openapi"
    TEXT = "text"
    PDF = "pdf"


# ========== 文档相关 ==========

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    id: int
    filename: str
    doc_type: str
    content_preview: str
    file_size: int
    created_at: str


class TextInput(BaseModel):
    """文本输入请求"""
    title: str = Field(..., description="文档标题", min_length=1)
    content: str = Field(..., description="文档内容", min_length=10)
    doc_type: DocumentType = Field(default=DocumentType.TEXT, description="文档类型")


# ========== 测试用例相关 ==========

class TestCase(BaseModel):
    """测试用例模型"""
    id: Optional[int] = None
    document_id: Optional[int] = None
    module: str = Field(default="", description="所属模块/功能")
    title: str = Field(..., description="用例标题")
    precondition: str = Field(default="", description="前置条件")
    steps: str = Field(..., description="测试步骤")
    expected_result: str = Field(..., description="预期结果")
    priority: Priority = Field(default=Priority.P2, description="优先级")
    case_type: TestCaseType = Field(default=TestCaseType.FUNCTIONAL, description="用例类型")
    case_id: str = Field(default="", description="用例编号")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TestCaseUpdate(BaseModel):
    """测试用例更新请求"""
    module: Optional[str] = None
    title: Optional[str] = None
    precondition: Optional[str] = None
    steps: Optional[str] = None
    expected_result: Optional[str] = None
    priority: Optional[Priority] = None
    case_type: Optional[TestCaseType] = None


class GenerateRequest(BaseModel):
    """生成测试用例请求"""
    document_id: int = Field(..., description="文档ID")
    test_types: List[TestCaseType] = Field(
        default=[TestCaseType.FUNCTIONAL, TestCaseType.BOUNDARY, TestCaseType.EXCEPTION, TestCaseType.FLOW],
        description="需要生成的测试用例类型"
    )
    custom_prompt: Optional[str] = Field(default=None, description="自定义 Prompt 模板")


class GenerateResponse(BaseModel):
    """生成测试用例响应"""
    document_id: int
    total_generated: int
    test_cases: List[TestCase]


# ========== 配置相关 ==========

class AIConfig(BaseModel):
    """AI 配置"""
    ai_base_url: str = Field(..., description="AI API 基础地址")
    ai_api_key: str = Field(..., description="AI API 密钥")
    ai_model: str = Field(..., description="AI 模型名称")
    ai_temperature: Optional[float] = Field(default=None, description="AI 生成温度", ge=0, le=1)
    ai_max_tokens: Optional[int] = Field(default=None, description="AI 最大 Token 数", ge=1000)


class ExportRequest(BaseModel):
    """导出请求"""
    document_id: Optional[int] = None
    priority: Optional[Priority] = None
    case_type: Optional[TestCaseType] = None


# ========== 批量操作 ==========

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[int] = Field(..., description="要删除的ID列表", min_length=1)


# ========== 任务队列相关 ==========

class TaskStatus(BaseModel):
    """生成任务状态"""
    id: int
    status: str
    task_type: str
    document_id: Optional[int] = None
    progress: int = 0
    total: int = 0
    result: str = ""
    error: str = ""
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
