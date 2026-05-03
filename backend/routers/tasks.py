"""任务队列 API 路由"""
import logging

from fastapi import APIRouter, HTTPException, Query

from ..database import list_tasks, get_task, delete_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks")
async def list_tasks_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取任务列表"""
    return await list_tasks(page=page, page_size=page_size)


@router.get("/tasks/{task_id}")
async def get_task_api(task_id: int):
    """获取任务状态"""
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/tasks/{task_id}")
async def delete_task_api(task_id: int):
    """删除任务"""
    success = await delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "删除成功", "id": task_id}
