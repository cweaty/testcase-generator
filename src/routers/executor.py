"""
Playwright 自动化测试执行 API 路由
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse

from ..database import get_db, get_testcase, get_testcases, get_document, log_operation
from ..executor.runner import (
    execute_testcase,
    execute_testcases_batch,
    generate_code,
    run_script,
    RESULTS_DIR,
)
from ._shared import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executor", tags=["executor"])


# ========== 代码预览 API（精确路径必须在参数路径之前） ==========

@router.post("/preview/{tc_id}")
async def preview_code(
    tc_id: int,
    base_url: str = Query("http://localhost:3000", description="目标网站 URL"),
    timeout: int = Query(30000, description="超时时间(ms)"),
):
    """为测试用例生成 Playwright 代码（不执行，仅返回代码）"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")

    try:
        code = await generate_code(tc, base_url=base_url, timeout=timeout)
        return {"case_id": tc.get("case_id"), "title": tc.get("title"), "code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代码生成失败: {str(e)}")


# ========== 执行 API ==========
# 重要：精确路径 (/run/stream, /run/batch) 必须在参数路径 (/run/{tc_id}) 之前
# 否则 FastAPI 会把 "stream"/"batch" 匹配成 tc_id 参数

@router.post("/run/stream")
async def run_testcases_stream(request: Request):
    """SSE 流式批量执行 — 逐个用例返回执行进度和结果"""
    body = await request.json()
    tc_ids = body.get("testcase_ids", [])
    base_url = body.get("base_url", "http://localhost:3000")
    timeout = body.get("timeout", 30000)

    if not tc_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个测试用例")
    if len(tc_ids) > 20:
        raise HTTPException(status_code=400, detail="单次最多执行 20 个用例")

    testcases = []
    for tc_id in tc_ids:
        tc = await get_testcase(tc_id)
        if tc:
            testcases.append(tc)

    if not testcases:
        raise HTTPException(status_code=404, detail="没有找到有效的测试用例")

    async def event_stream():
        total = len(testcases)
        passed = 0

        yield f"data: {json.dumps({'type': 'start', 'total': total, 'message': f'开始执行 {total} 个测试用例...'}, ensure_ascii=False)}\n\n"

        for i, tc in enumerate(testcases):
            case_id = tc.get("case_id", f"TC-{i+1}")
            yield f"data: {json.dumps({'type': 'running', 'index': i+1, 'total': total, 'case_id': case_id, 'title': tc.get('title', '')}, ensure_ascii=False)}\n\n"

            try:
                result = await execute_testcase(tc, base_url=base_url, timeout=timeout)
                if result.get("passed"):
                    passed += 1

                # 保存记录
                exec_id = await _save_execution(
                    case_id=case_id,
                    tc_id=tc["id"],
                    title=tc.get("title", ""),
                    result=result,
                )

                # 不发送 code 和 stdout/stderr 给前端（太大）
                frontend_result = {
                    k: v for k, v in result.items()
                    if k not in ("code", "stdout", "stderr", "script_path")
                }
                frontend_result["type"] = "result"
                frontend_result["index"] = i + 1
                frontend_result["total"] = total
                frontend_result["exec_id"] = exec_id

                yield f"data: {json.dumps(frontend_result, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'result', 'index': i+1, 'total': total, 'case_id': case_id, 'passed': False, 'message': str(e), 'screenshots': [], 'duration_ms': 0, 'steps_completed': 0, 'steps_total': 0}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'complete', 'total': total, 'passed': passed, 'failed': total - passed, 'message': f'执行完成: {passed}/{total} 通过'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/run/batch")
async def run_batch_testcases(request: Request):
    """批量执行测试用例（请求体中包含 testcases 列表）"""
    body = await request.json()
    tc_ids = body.get("testcase_ids", [])
    base_url = body.get("base_url", "http://localhost:3000")
    timeout = body.get("timeout", 30000)
    
    if not tc_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个测试用例")
    if len(tc_ids) > 20:
        raise HTTPException(status_code=400, detail="单次最多执行 20 个用例")

    testcases = []
    for tc_id in tc_ids:
        tc = await get_testcase(tc_id)
        if tc:
            testcases.append(tc)

    if not testcases:
        raise HTTPException(status_code=404, detail="没有找到有效的测试用例")

    result = await execute_testcases_batch(testcases, base_url=base_url, timeout=timeout)

    # 保存每个用例的执行记录
    for i, tc in enumerate(testcases):
        if i < len(result.get("results", [])):
            await _save_execution(
                case_id=tc.get("case_id", ""),
                tc_id=tc["id"],
                title=tc.get("title", ""),
                result=result["results"][i],
            )

    passed_count = result.get("passed", 0)
    total_count = result.get("total", 0)
    await log_operation("execute_batch", "testcase", None, 
        f"批量执行 {total_count} 个用例: {passed_count}/{total_count} 通过")

    return result


@router.post("/run/{tc_id}")
async def run_single_testcase(
    tc_id: int,
    base_url: str = Query("http://localhost:3000", description="目标网站 URL"),
    timeout: int = Query(30000, description="超时时间(ms)"),
):
    """对单个测试用例生成 Playwright 脚本并执行"""
    tc = await get_testcase(tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="测试用例不存在")

    try:
        result = await execute_testcase(tc, base_url=base_url, timeout=timeout)

        # 保存执行记录到数据库
        await _save_execution(
            case_id=tc.get("case_id", ""),
            tc_id=tc_id,
            title=tc.get("title", ""),
            result=result,
        )

        await log_operation("execute", "testcase", tc_id, 
            f"自动化执行: {'通过' if result['passed'] else '失败'} - {tc.get('case_id')}")

        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 执行历史 API ==========

@router.get("/history")
async def get_execution_history(
    tc_id: Optional[int] = Query(None, description="按用例 ID 筛选"),
    passed: Optional[bool] = Query(None, description="按结果筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取执行历史"""
    async with get_db() as db:
        where_parts = ["1=1"]
        params = []

        if tc_id is not None:
            where_parts.append("tc_id = ?")
            params.append(tc_id)
        if passed is not None:
            where_parts.append("passed = ?")
            params.append(1 if passed else 0)

        where_clause = " AND ".join(where_parts)

        # 总数
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM test_executions WHERE {where_clause}", params
        )
        total = (await cursor.fetchone())[0]

        # 分页查询
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT * FROM test_executions 
                WHERE {where_clause} 
                ORDER BY executed_at DESC 
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()

        executions = []
        for row in rows:
            executions.append(dict(row))

    return {
        "executions": executions,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/history/{exec_id}")
async def get_execution_detail(exec_id: int):
    """获取单次执行详情（包含代码和日志）"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM test_executions WHERE id = ?", (exec_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="执行记录不存在")
        result = dict(row)

    # 读取执行目录中的截图
    run_dir = result.get("run_dir", "")
    screenshots = []
    if run_dir and os.path.exists(run_dir):
        screenshots = sorted([f for f in os.listdir(run_dir) if f.endswith(".png")])

    result["screenshots"] = screenshots
    return result


@router.delete("/history/{exec_id}")
async def delete_execution(exec_id: int):
    """删除执行记录"""
    async with get_db() as db:
        # 先获取记录，删除关联文件
        cursor = await db.execute("SELECT run_dir FROM test_executions WHERE id = ?", (exec_id,))
        row = await cursor.fetchone()
        if row and row["run_dir"] and os.path.exists(row["run_dir"]):
            import shutil
            shutil.rmtree(row["run_dir"], ignore_errors=True)

        await db.execute("DELETE FROM test_executions WHERE id = ?", (exec_id,))
        await db.commit()

    return {"message": "删除成功"}


@router.delete("/history")
async def clear_execution_history():
    """清空执行历史"""
    async with get_db() as db:
        # 删除所有执行目录
        cursor = await db.execute("SELECT run_dir FROM test_executions")
        rows = await cursor.fetchall()
        for row in rows:
            if row["run_dir"] and os.path.exists(row["run_dir"]):
                import shutil
                shutil.rmtree(row["run_dir"], ignore_errors=True)

        await db.execute("DELETE FROM test_executions")
        await db.commit()

    return {"message": "执行历史已清空"}


# ========== 截图 API ==========

@router.get("/screenshots/{exec_id}/{filename}")
async def get_screenshot(exec_id: int, filename: str):
    """获取执行截图"""
    async with get_db() as db:
        cursor = await db.execute("SELECT run_dir FROM test_executions WHERE id = ?", (exec_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="执行记录不存在")

    run_dir = row["run_dir"]
    filepath = os.path.join(run_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="截图不存在")

    return FileResponse(filepath, media_type="image/png")


# ========== 工具函数 ==========

async def _save_execution(case_id: str, tc_id: int, title: str, result: dict) -> int:
    """保存执行记录到数据库，返回新记录的 ID"""
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO test_executions 
               (case_id, tc_id, title, passed, message, steps_completed, steps_total,
                duration_ms, run_dir, code, stdout, stderr, screenshots, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
            (
                case_id,
                tc_id,
                title,
                1 if result.get("passed") else 0,
                result.get("message", ""),
                result.get("steps_completed", 0),
                result.get("steps_total", 0),
                result.get("duration_ms", 0),
                result.get("run_dir", ""),
                result.get("code", ""),
                result.get("stdout", ""),
                result.get("stderr", ""),
                json.dumps(result.get("screenshots", []), ensure_ascii=False),
            ),
        )
        await db.commit()
        return cursor.lastrowid
