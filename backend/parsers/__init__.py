"""
文档解析器包
支持 Markdown、Word (.docx)、OpenAPI、PDF 文档解析
"""
from .markdown_parser import parse_markdown
from .docx_parser import parse_docx
from .openapi_parser import parse_openapi
from .spreadsheet import parse_excel, parse_csv_import

try:
    from .pdf_parser import parse_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

__all__ = [
    "parse_markdown",
    "parse_docx",
    "parse_openapi",
    "parse_excel",
    "parse_csv_import",
    "PDF_AVAILABLE",
]

if PDF_AVAILABLE:
    __all__.append("parse_pdf")
