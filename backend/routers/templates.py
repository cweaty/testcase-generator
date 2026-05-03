"""Prompt 模板 API 路由"""
import logging

from fastapi import APIRouter, HTTPException

from ..database import (
    get_prompt_templates, get_prompt_template,
    create_prompt_template, update_prompt_template, delete_prompt_template,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["templates"])


@router.get("/prompt-templates")
async def list_prompt_templates():
    """获取所有 Prompt 模板"""
    templates = await get_prompt_templates()
    return {"templates": templates, "total": len(templates)}


@router.post("/prompt-templates")
async def create_prompt_template_api(data: dict):
    """创建 Prompt 模板"""
    name = data.get("name", "").strip()
    content = data.get("content", "").strip()
    is_default = data.get("is_default", False)
    if not name or not content:
        raise HTTPException(status_code=400, detail="名称和内容不能为空")
    try:
        template_id = await create_prompt_template(name, content, is_default)
        return {"message": "创建成功", "id": template_id}
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"模板名称已存在: {name}")


@router.put("/prompt-templates/{template_id}")
async def update_prompt_template_api(template_id: int, data: dict):
    """更新 Prompt 模板"""
    success = await update_prompt_template(
        template_id,
        name=data.get("name"),
        content=data.get("content"),
        is_default=data.get("is_default")
    )
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "更新成功"}


@router.delete("/prompt-templates/{template_id}")
async def delete_prompt_template_api(template_id: int):
    """删除 Prompt 模板"""
    success = await delete_prompt_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "删除成功"}
