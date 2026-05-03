"""多格式导出 API 路由"""
import os
import urllib.parse
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..database import get_testcases, get_document
from ..exporters import export_to_excel, export_to_csv, export_to_json, export_to_markdown, export_to_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["export"])


async def _do_export(document_id, priority, case_type, search, fmt):
    """通用导出逻辑"""
    try:
        result = await get_testcases(
            document_id=document_id, priority=priority,
            case_type=case_type, search=search, page_size=100000
        )
        cases = result["testcases"]
        if not cases:
            raise HTTPException(status_code=404, detail="没有可导出的测试用例")

        title = "测试用例"
        if document_id:
            doc = await get_document(document_id)
            if doc:
                title = os.path.splitext(doc["filename"])[0]

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        if fmt == "excel":
            content_bytes = export_to_excel(cases, title=title)
            filename = f"{title}_测试用例_{ts}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "csv":
            content_bytes = export_to_csv(cases)
            filename = f"{title}_测试用例_{ts}.csv"
            media_type = "text/csv; charset=utf-8-sig"
        elif fmt == "json":
            content_bytes = export_to_json(cases, title=title)
            filename = f"{title}_测试用例_{ts}.json"
            media_type = "application/json; charset=utf-8"
        elif fmt == "markdown":
            content_bytes = export_to_markdown(cases, title=title)
            filename = f"{title}_测试用例_{ts}.md"
            media_type = "text/markdown; charset=utf-8"
        elif fmt == "pdf":
            content_bytes = export_to_pdf(cases, title=title)
            filename = f"{title}_测试用例_{ts}.pdf"
            media_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {fmt}")

        encoded_filename = urllib.parse.quote(filename)
        return StreamingResponse(
            iter([content_bytes]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/export/excel")
async def export_excel(
    document_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """导出测试用例为 Excel 文件"""
    return await _do_export(document_id, priority, case_type, search, "excel")


@router.get("/export/csv")
async def export_csv(
    document_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """导出测试用例为 CSV 文件"""
    return await _do_export(document_id, priority, case_type, search, "csv")


@router.get("/export/json")
async def export_json(
    document_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """导出测试用例为 JSON 文件"""
    return await _do_export(document_id, priority, case_type, search, "json")


@router.get("/export/markdown")
async def export_markdown(
    document_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """导出测试用例为 Markdown 文件"""
    return await _do_export(document_id, priority, case_type, search, "markdown")


@router.get("/export/pdf")
async def export_pdf(
    document_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """导出测试用例为 PDF 文件"""
    return await _do_export(document_id, priority, case_type, search, "pdf")
