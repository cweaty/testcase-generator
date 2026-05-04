"""回收站 API 路由"""
import logging

from fastapi import APIRouter, HTTPException, Query

from ..models import BatchDeleteRequest
from ..database import (
    get_deleted_testcases, restore_testcase, restore_testcases_batch,
    permanently_delete_testcase, permanently_delete_batch, empty_trash,
    log_operation,
)
from ._shared import invalidate_stats_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trash"])


@router.get("/trash")
async def list_trash(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str = Query("", description="搜索关键词"),
):
    """获取回收站列表"""
    return await get_deleted_testcases(page=page, page_size=page_size, search=search)


@router.post("/trash/{trash_id}/restore")
async def restore_from_trash(trash_id: int):
    """从回收站恢复"""
    success = await restore_testcase(trash_id)
    if not success:
        raise HTTPException(status_code=404, detail="回收站中未找到该用例")
    invalidate_stats_cache()
    await log_operation("restore", "testcase", trash_id, f"从回收站恢复")
    return {"message": "恢复成功", "id": trash_id}


@router.post("/trash/batch-restore")
async def batch_restore_from_trash(request: BatchDeleteRequest):
    """批量从回收站恢复"""
    count = await restore_testcases_batch(request.ids)
    invalidate_stats_cache()
    return {"message": f"成功恢复 {count} 条用例", "restored": count}


@router.delete("/trash/{trash_id}")
async def permanent_delete_from_trash(trash_id: int):
    """永久删除回收站中的用例"""
    success = await permanently_delete_testcase(trash_id)
    if not success:
        raise HTTPException(status_code=404, detail="回收站中未找到该用例")
    return {"message": "永久删除成功", "id": trash_id}


@router.post("/trash/batch-delete")
async def batch_permanent_delete(request: BatchDeleteRequest):
    """批量永久删除"""
    count = await permanently_delete_batch(request.ids)
    return {"message": f"成功永久删除 {count} 条用例", "deleted": count}


@router.delete("/trash")
async def empty_trash_api():
    """清空回收站"""
    count = await empty_trash()
    return {"message": f"成功清空回收站，共删除 {count} 条", "deleted": count}
