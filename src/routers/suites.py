"""
测试套件 + 环境检测 + 报告 API
"""
import os
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from ..database import get_db, get_testcase, log_operation
from ..executor.suites import (
    create_suite, update_suite, delete_suite, get_suite, list_suites,
    add_suite_member, add_suite_members_batch, remove_suite_member, clear_suite_members,
)
from ..executor.runner import execute_testcase, execute_testcases_batch
from ..executor.report import generate_report_html
from ..executor.env_check import check_all, install_package, install_playwright_browser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["suites"])


# ========== 测试套件 CRUD ==========

@router.get("/suites")
async def api_list_suites():
    """列出所有测试套件"""
    return {"suites": await list_suites()}


@router.post("/suites")
async def api_create_suite(body: dict):
    """创建测试套件"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="套件名称不能为空")
    suite_id = await create_suite(
        name=name,
        description=body.get("description", ""),
        base_url=body.get("base_url", "http://localhost:3000"),
        timeout=body.get("timeout", 30000),
    )
    return {"id": suite_id, "message": "创建成功"}


@router.get("/suites/{suite_id}")
async def api_get_suite(suite_id: int):
    """获取套件详情"""
    suite = await get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")
    return suite


@router.put("/suites/{suite_id}")
async def api_update_suite(suite_id: int, body: dict):
    """更新套件"""
    success = await update_suite(suite_id, **body)
    if not success:
        raise HTTPException(status_code=404, detail="套件不存在或无变更")
    return {"message": "更新成功"}


@router.delete("/suites/{suite_id}")
async def api_delete_suite(suite_id: int):
    """删除套件"""
    success = await delete_suite(suite_id)
    if not success:
        raise HTTPException(status_code=404, detail="套件不存在")
    return {"message": "删除成功"}


# ========== 套件成员管理 ==========

@router.post("/suites/{suite_id}/members")
async def api_add_members(suite_id: int, body: dict):
    """向套件添加用例"""
    suite = await get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    tc_ids = body.get("testcase_ids", [])
    if not tc_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个用例")

    added = await add_suite_members_batch(suite_id, tc_ids)
    return {"message": f"添加了 {added} 个用例", "added": added}


@router.delete("/suites/{suite_id}/members/{tc_id}")
async def api_remove_member(suite_id: int, tc_id: int):
    """从套件移除用例"""
    success = await remove_suite_member(suite_id, tc_id)
    if not success:
        raise HTTPException(status_code=404, detail="成员不存在")
    return {"message": "移除成功"}


@router.delete("/suites/{suite_id}/members")
async def api_clear_members(suite_id: int):
    """清空套件所有成员"""
    count = await clear_suite_members(suite_id)
    return {"message": f"清空了 {count} 个用例"}


# ========== 套件执行 ==========

@router.post("/suites/{suite_id}/run")
async def api_run_suite(suite_id: int, request: Request):
    """SSE 流式执行整个测试套件"""
    body = await request.json()
    base_url_override = body.get("base_url")

    suite = await get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    members = suite.get("members", [])
    if not members:
        raise HTTPException(status_code=400, detail="套件中没有测试用例")

    base_url = base_url_override or suite.get("base_url", "http://localhost:3000")
    timeout = suite.get("timeout", 30000)

    async def event_stream():
        total = len(members)
        passed_count = 0
        all_results = []
        overall_start = datetime.now()

        yield f"data: {json.dumps({'type': 'start', 'total': total, 'suite_name': suite['name'], 'message': f'开始执行套件: {suite["name"]}'}, ensure_ascii=False)}\n\n"

        for i, tc in enumerate(members):
            case_id = tc.get("case_id", f"TC-{i+1}")
            yield f"data: {json.dumps({'type': 'running', 'index': i+1, 'total': total, 'case_id': case_id, 'title': tc.get('title', '')}, ensure_ascii=False)}\n\n"

            try:
                result = await execute_testcase(tc, base_url=base_url, timeout=timeout)
                if result.get("passed"):
                    passed_count += 1

                # 保存记录
                from ..routers.executor import _save_execution
                exec_id = await _save_execution(
                    case_id=case_id, tc_id=tc["id"],
                    title=tc.get("title", ""), result=result,
                )

                frontend_result = {
                    k: v for k, v in result.items()
                    if k not in ("code", "stdout", "stderr", "script_path")
                }
                frontend_result["type"] = "result"
                frontend_result["index"] = i + 1
                frontend_result["total"] = total
                frontend_result["exec_id"] = exec_id
                frontend_result["title"] = tc.get("title", "")

                all_results.append({
                    "case_id": case_id,
                    "title": tc.get("title", ""),
                    "passed": result.get("passed", False),
                    "message": result.get("message", ""),
                    "steps_completed": result.get("steps_completed", 0),
                    "steps_total": result.get("steps_total", 0),
                    "duration_ms": result.get("duration_ms", 0),
                })

                yield f"data: {json.dumps(frontend_result, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'result', 'index': i+1, 'total': total, 'case_id': case_id, 'title': tc.get('title', ''), 'passed': False, 'message': str(e), 'screenshots': [], 'duration_ms': 0, 'steps_completed': 0, 'steps_total': 0, 'exec_id': 0}, ensure_ascii=False)}\n\n"
                all_results.append({
                    "case_id": case_id, "title": tc.get("title", ""),
                    "passed": False, "message": str(e),
                    "steps_completed": 0, "steps_total": 0, "duration_ms": 0,
                })

        overall_ms = int((datetime.now() - overall_start).total_seconds() * 1000)

        # 生成报告
        report_html = generate_report_html(suite["name"], base_url, all_results, overall_ms)
        async with get_db() as db:
            await db.execute(
                "INSERT INTO execution_reports (suite_id, suite_name, total, passed, failed, duration_ms, report_html, base_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (suite_id, suite["name"], total, passed_count, total - passed_count, overall_ms, report_html, base_url)
            )
            await db.commit()

        await log_operation("execute_suite", "suite", suite_id,
            f"执行套件 '{suite['name']}': {passed_count}/{total} 通过, 耗时 {overall_ms/1000:.1f}s")

        yield f"data: {json.dumps({'type': 'complete', 'total': total, 'passed': passed_count, 'failed': total - passed_count, 'duration_ms': overall_ms, 'message': f'执行完成: {passed_count}/{total} 通过'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ========== 执行报告 ==========

@router.get("/reports")
async def api_list_reports(
    suite_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """列出执行报告"""
    async with get_db() as db:
        where = "WHERE 1=1"
        params = []
        if suite_id:
            where += " AND suite_id = ?"
            params.append(suite_id)

        cursor = await db.execute(f"SELECT COUNT(*) FROM execution_reports {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT id, suite_id, suite_name, total, passed, failed, duration_ms, base_url, created_at FROM execution_reports {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        reports = [dict(r) for r in await cursor.fetchall()]

    return {"reports": reports, "total": total, "page": page}


@router.get("/reports/{report_id}")
async def api_get_report(report_id: int):
    """获取报告详情（HTML）"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM execution_reports WHERE id = ?", (report_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="报告不存在")
    return dict(row)


@router.get("/reports/{report_id}/html", response_class=HTMLResponse)
async def api_get_report_html(report_id: int):
    """直接查看 HTML 报告"""
    async with get_db() as db:
        cursor = await db.execute("SELECT report_html FROM execution_reports WHERE id = ?", (report_id,))
        row = await cursor.fetchone()
        if not row or not row["report_html"]:
            raise HTTPException(status_code=404, detail="报告不存在")
    return HTMLResponse(content=row["report_html"])


@router.delete("/reports/{report_id}")
async def api_delete_report(report_id: int):
    """删除报告"""
    async with get_db() as db:
        await db.execute("DELETE FROM execution_reports WHERE id = ?", (report_id,))
        await db.commit()
    return {"message": "删除成功"}


# ========== 环境检测 ==========

@router.get("/env/check")
async def api_env_check():
    """检测所有依赖环境"""
    return check_all()


@router.post("/env/install")
async def api_env_install(body: dict):
    """安装指定依赖"""
    target = body.get("target", "")
    if target == "playwright":
        return install_package("playwright")
    elif target == "pymupdf":
        return install_package("PyMuPDF")
    elif target == "chromium":
        return install_playwright_browser()
    else:
        raise HTTPException(status_code=400, detail=f"未知的安装目标: {target}")


# ========== 执行统计 ==========

@router.get("/executor/stats")
async def api_executor_stats():
    """执行统计数据"""
    async with get_db() as db:
        # 总执行数
        cursor = await db.execute("SELECT COUNT(*) FROM test_executions")
        total_execs = (await cursor.fetchone())[0]

        # 总通过数
        cursor = await db.execute("SELECT COUNT(*) FROM test_executions WHERE passed = 1")
        total_passed = (await cursor.fetchone())[0]

        # 最近 7 天每日统计
        cursor = await db.execute("""
            SELECT DATE(executed_at) as date, 
                   COUNT(*) as total,
                   SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as passed,
                   AVG(duration_ms) as avg_duration
            FROM test_executions
            WHERE executed_at >= datetime('now', '-7 days', 'localtime')
            GROUP BY DATE(executed_at)
            ORDER BY date
        """)
        daily = [dict(r) for r in await cursor.fetchall()]

        # 最近 10 次执行
        cursor = await db.execute("""
            SELECT id, case_id, title, passed, duration_ms, executed_at
            FROM test_executions
            ORDER BY executed_at DESC LIMIT 10
        """)
        recent = [dict(r) for r in await cursor.fetchall()]

    return {
        "total_executions": total_execs,
        "total_passed": total_passed,
        "pass_rate": round(total_passed / total_execs * 100, 1) if total_execs > 0 else 0,
        "daily": daily,
        "recent": recent,
    }
