"""测试用例相关 API 路由"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import StreamingResponse

from ..auth import get_current_user

from ..models import (
    TestCase, TestCaseUpdate, GenerateRequest, GenerateResponse,
    BatchDeleteRequest, DocumentType,
)
from ..database import (
    get_document, insert_testcase, insert_testcases_batch,
    get_testcases, get_testcase, update_testcase,
    delete_testcase, delete_testcases_batch,
    get_testcases_by_ids, log_operation,
    save_testcase_history, get_testcase_history, restore_from_history,
    get_db,
)
from ..parsers import parse_openapi
from ..generators import AITestCaseGenerator
from ._shared import generate_limiter, invalidate_stats_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["testcases"])


# ========== Helper ==========

def _format_openapi_for_ai(parsed: dict) -> str:
    """将 OpenAPI 文档格式化为 AI 可理解的文本"""
    lines = [f"API 名称: {parsed['title']}", f"版本: {parsed['version']}"]
    if parsed.get("description"):
        lines.append(f"描述: {parsed['description']}")
    lines.append("")

    for ep in parsed["endpoints"]:
        lines.append(f"## {ep['method']} {ep['path']}")
        if ep.get("summary"):
            lines.append(f"说明: {ep['summary']}")
        if ep.get("description"):
            lines.append(f"描述: {ep['description']}")
        if ep.get("tags"):
            lines.append(f"标签: {', '.join(ep['tags'])}")
        if ep.get("parameters"):
            lines.append("请求参数:")
            for p in ep["parameters"]:
                required = "（必填）" if p["required"] else ""
                lines.append(f"  - {p['name']} ({p['in']}, {p['type']}) {required}: {p.get('description', '')}")
        if ep.get("request_body"):
            lines.append(f"请求体 ({ep['request_body']['content_type']}):")
            lines.append(f"  {ep['request_body'].get('schema', {})}")
        if ep.get("responses"):
            lines.append("响应:")
            for resp in ep["responses"]:
                lines.append(f"  - {resp['status_code']}: {resp['description']}")
        lines.append("")

    return "\n".join(lines)


async def _get_doc_content(document_id: int) -> tuple:
    """获取文档内容，处理 OpenAPI 格式化"""
    doc = await get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    content = doc["content"]
    doc_type = doc["doc_type"]
    if doc_type == DocumentType.OPENAPI:
        try:
            parsed = parse_openapi(content)
            content = _format_openapi_for_ai(parsed)
        except Exception as e:
            logger.warning(f"OpenAPI 解析失败，使用原始内容: {e}")
    return content, doc_type


# ========== 生成 API ==========

@router.post("/testcases/generate", response_model=GenerateResponse)
async def generate_testcases(request: Request, body: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """根据文档 AI 生成测试用例"""
    client_ip = request.client.host if request else "unknown"
    if not generate_limiter.is_allowed(client_ip or "unknown"):
        raise HTTPException(status_code=429, detail="生成请求过于频繁，请1分钟后再试")

    content, doc_type = await _get_doc_content(body.document_id)
    test_types = [t.value for t in body.test_types]

    custom_prompt = getattr(body, 'custom_prompt', None)
    generator = AITestCaseGenerator(custom_prompt=custom_prompt, user_id=current_user["id"])

    try:
        test_cases = await generator.generate(
            content=content, test_types=test_types,
            doc_type=doc_type, document_id=body.document_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    count = await insert_testcases_batch(test_cases)
    invalidate_stats_cache()
    logger.info(f"已保存 {count} 条测试用例（文档ID: {body.document_id}）")
    await log_operation("generate", "testcase", body.document_id, f"AI生成 {count} 条用例")

    saved_cases = await get_testcases(document_id=body.document_id)
    tc_models = [TestCase(**tc) for tc in saved_cases["testcases"]]

    return GenerateResponse(
        document_id=body.document_id,
        total_generated=count,
        test_cases=tc_models
    )


@router.post("/testcases/generate/stream")
async def generate_testcases_stream(request: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """SSE 流式生成测试用例（真正的实时流式输出）"""
    content, doc_type = await _get_doc_content(request.document_id)
    test_types = [t.value for t in request.test_types]
    custom_prompt = getattr(request, 'custom_prompt', None)

    generator = AITestCaseGenerator(custom_prompt=custom_prompt, user_id=current_user["id"])

    async def event_stream():
        collected_cases = []
        try:
            async for event in generator.generate_stream(
                content=content, test_types=test_types,
                doc_type=doc_type, document_id=request.document_id
            ):
                event_type = event.get("type", "unknown")

                # 每收到一条用例，立即保存到数据库
                if event_type == "testcase":
                    tc_data = event["data"]
                    try:
                        new_id = await insert_testcase(tc_data)
                        tc_data["id"] = new_id
                        collected_cases.append(tc_data)
                    except Exception as e:
                        logger.error(f"保存用例失败: {e}")

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 全部完成后使缓存失效
            if collected_cases:
                invalidate_stats_cache()
                logger.info(f"流式生成完成，共保存 {len(collected_cases)} 条用例（文档ID: {request.document_id}）")
                await log_operation("generate", "testcase", request.document_id, f"AI流式生成 {len(collected_cases)} 条用例")

        except Exception as e:
            logger.error(f"流式生成异常: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'fatal', 'message': f'生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@router.post("/testcases/{tc_id}/regenerate")
async def regenerate_single_testcase(tc_id: int, current_user: dict = Depends(get_current_user)):
    """重新生成单条测试用例"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")

    doc = await get_document(tc["document_id"]) if tc.get("document_id") else None
    if not doc:
        raise HTTPException(status_code=404, detail="关联文档不存在")

    generator = AITestCaseGenerator(user_id=current_user["id"])
    try:
        new_cases = await generator.generate(
            content=doc["content"],
            test_types=[tc.get("case_type", "功能测试")],
            doc_type=doc["doc_type"],
            document_id=tc["document_id"],
            count=1
        )
        if new_cases:
            new_tc = new_cases[0]
            new_tc["case_id"] = tc["case_id"]
            await update_testcase(tc_id, new_tc)
            updated = await get_testcase(tc_id)
            return {"message": "重新生成成功", "testcase": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")

    raise HTTPException(status_code=500, detail="重新生成失败：AI 未返回结果")


# ========== 管理 API ==========

@router.get("/testcases")
async def list_testcases(
    document_id: Optional[int] = Query(None, description="按文档 ID 筛选"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
    case_type: Optional[str] = Query(None, description="按用例类型筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("priority", description="排序字段: priority/id/title/module/case_type/created_at"),
    sort_order: str = Query("asc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
):
    """获取测试用例列表（支持筛选、搜索、排序、分页）"""
    return await get_testcases(
        document_id=document_id, priority=priority,
        case_type=case_type, search=search,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order
    )


@router.get("/testcases/{tc_id}")
async def get_testcase_detail(tc_id: int):
    """获取单个测试用例"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    return tc


@router.put("/testcases/{tc_id}")
async def update_testcase_api(tc_id: int, updates: TestCaseUpdate):
    """更新测试用例"""
    current = await get_testcase(tc_id)
    if not current:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    await save_testcase_history(tc_id, current, edit_reason="user edit")
    success = await update_testcase(tc_id, update_dict)
    if not success:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    invalidate_stats_cache()
    return {"message": "更新成功", "id": tc_id}


@router.delete("/testcases/{tc_id}")
async def delete_testcase_api(tc_id: int):
    """删除测试用例（移入回收站）"""
    success = await delete_testcase(tc_id)
    if not success:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    invalidate_stats_cache()
    await log_operation("delete", "testcase", tc_id, f"移入回收站")
    return {"message": "删除成功", "id": tc_id}


@router.post("/testcases/batch-delete")
async def batch_delete_testcases(request: BatchDeleteRequest):
    """批量删除测试用例"""
    count = await delete_testcases_batch(request.ids)
    invalidate_stats_cache()
    return {"message": f"成功删除 {count} 条测试用例", "deleted": count}


@router.delete("/testcases")
async def delete_all_testcases(
    document_id: Optional[int] = Query(None, description="按文档 ID 筛选删除"),
    priority: Optional[str] = Query(None, description="按优先级筛选删除"),
    case_type: Optional[str] = Query(None, description="按用例类型筛选删除"),
):
    """清空测试用例（支持按条件筛选删除）"""
    async with get_db() as db:
        where_clause = "WHERE 1=1"
        params = []
        if document_id:
            where_clause += " AND document_id = ?"
            params.append(document_id)
        if priority:
            where_clause += " AND priority = ?"
            params.append(priority)
        if case_type:
            where_clause += " AND case_type = ?"
            params.append(case_type)

        cursor = await db.execute(f"DELETE FROM testcases {where_clause}", params)
        await db.commit()
        deleted = cursor.rowcount

    invalidate_stats_cache()
    logger.info(f"清空测试用例: 删除 {deleted} 条")
    return {"message": f"成功删除 {deleted} 条测试用例", "deleted": deleted}


# ========== 复制 & 导入 ==========

@router.post("/testcases/{tc_id}/copy")
async def copy_testcase(tc_id: int):
    """复制测试用例"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")

    new_tc = {
        "case_id": tc.get("case_id", "") + " (副本)",
        "document_id": tc.get("document_id"),
        "module": tc.get("module", ""),
        "title": tc["title"] + " (副本)",
        "precondition": tc.get("precondition", ""),
        "steps": tc["steps"],
        "expected_result": tc["expected_result"],
        "priority": tc.get("priority", "P2"),
        "case_type": tc.get("case_type", "功能测试"),
    }
    new_id = await insert_testcase(new_tc)
    invalidate_stats_cache()
    await log_operation("copy", "testcase", new_id, f"复制用例: {tc['title']}")
    return {"message": "复制成功", "testcase": {**new_tc, "id": new_id}}


@router.post("/testcases/batch-copy")
async def batch_copy_testcases(request: BatchDeleteRequest):
    """批量复制测试用例"""
    tcs = await get_testcases_by_ids(request.ids)
    if not tcs:
        raise HTTPException(status_code=404, detail="没有找到测试用例")
    new_tcs = []
    for tc in tcs:
        new_tcs.append({
            "case_id": tc.get("case_id", "") + " (副本)",
            "document_id": tc.get("document_id"),
            "module": tc.get("module", ""),
            "title": tc["title"] + " (副本)",
            "precondition": tc.get("precondition", ""),
            "steps": tc["steps"],
            "expected_result": tc["expected_result"],
            "priority": tc.get("priority", "P2"),
            "case_type": tc.get("case_type", "功能测试"),
        })
    count = await insert_testcases_batch(new_tcs)
    invalidate_stats_cache()
    await log_operation("copy", "testcase", None, f"批量复制 {count} 条用例")
    return {"message": f"成功复制 {count} 条测试用例", "copied": count}


@router.post("/testcases/import")
async def import_testcases(data: dict):
    """导入测试用例（JSON 格式）"""
    cases = data.get("testcases", [])
    document_id = data.get("document_id")
    if not cases:
        raise HTTPException(status_code=400, detail="没有可导入的用例")

    for tc in cases:
        if document_id:
            tc["document_id"] = document_id

    count = await insert_testcases_batch(cases)
    invalidate_stats_cache()
    await log_operation("import", "testcase", None, f"导入 {count} 条用例")
    return {"message": f"成功导入 {count} 条测试用例", "imported": count}


# ========== 版本历史 ==========

@router.get("/testcases/{tc_id}/history")
async def get_testcase_history_api(tc_id: int):
    """获取测试用例的版本历史"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    history = await get_testcase_history(tc_id)
    return {"testcase_id": tc_id, "history": history, "total": len(history)}


@router.post("/history/{history_id}/restore")
async def restore_from_history_api(history_id: int):
    """从历史版本恢复测试用例"""
    result = await restore_from_history(history_id)
    if not result:
        raise HTTPException(status_code=404, detail="历史记录不存在或关联的测试用例已删除")
    invalidate_stats_cache()
    await log_operation("restore_history", "testcase", result["id"], f"从历史版本恢复 (history_id={history_id})")
    return {"message": "恢复成功", "testcase_id": result["id"]}
