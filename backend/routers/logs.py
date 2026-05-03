"""操作日志 API 路由"""
import logging

from fastapi import APIRouter, Query

from ..database import get_operation_logs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def list_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str = Query("", description="按操作类型筛选"),
):
    """获取操作日志"""
    return await get_operation_logs(page=page, page_size=page_size, action=action)
