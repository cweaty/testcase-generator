"""系统信息 API 路由"""
import os
import time
import logging
from datetime import datetime
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..database import list_documents, get_testcases, backup_database, get_database_stats, rebuild_fts_index
from ..parsers import PDF_AVAILABLE
from ._shared import _stats_cache, CACHE_TTL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])

APP_VERSION = "3.4.0"


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": APP_VERSION, "timestamp": datetime.now().isoformat()}


@router.get("/system/info")
async def system_info():
    """获取系统信息"""
    supported_formats = [".md", ".docx", ".json", ".txt"]
    if PDF_AVAILABLE:
        supported_formats.append(".pdf")

    return {
        "version": APP_VERSION,
        "supported_formats": supported_formats,
        "pdf_support": PDF_AVAILABLE,
        "export_formats": ["xlsx", "csv", "json", "markdown", "pdf"],
        "features": [
            "ai_generate", "sse_stream", "search", "pagination",
            "batch_delete", "batch_priority", "multi_export", "rate_limit",
            "doc_preview", "theme_toggle", "card_view", "quick_stats",
            "upload_progress", "ai_params_config", "shortcuts", "trash",
            "copy_testcase", "import_testcases", "custom_prompt",
            "gzip_compression", "stats_cache", "prompt_templates",
            "sorting", "operation_logs", "batch_copy", "search_highlight",
            "version_history", "multi_upload", "task_queue", "config_test",
            "toast_notifications", "inline_edit", "command_palette",
            "fts_search", "pdf_export", "db_backup", "input_sanitization"
        ]
    }


@router.get("/stats")
async def get_stats():
    """获取全局统计数据（带缓存）"""
    now = time.time()
    if _stats_cache["data"] and now - _stats_cache["ts"] < CACHE_TTL:
        return _stats_cache["data"]

    result = await get_testcases(page_size=100000)
    docs = await list_documents(page_size=100000)

    tc = result["testcases"]
    stats = result.get("stats", {})

    modules = defaultdict(int)
    types = defaultdict(int)
    for t in tc:
        if t.get("module"):
            modules[t["module"]] += 1
        types[t.get("case_type", "未分类")] += 1

    data = {
        "documents": {"total": docs["total"]},
        "testcases": {
            "total": len(tc),
            "by_priority": {
                "P0": stats.get("p0_count", 0),
                "P1": stats.get("p1_count", 0),
                "P2": stats.get("p2_count", 0),
                "P3": stats.get("p3_count", 0),
            },
            "by_type": dict(types),
            "by_module": dict(sorted(modules.items(), key=lambda x: -x[1])[:20]),
        }
    }

    _stats_cache["data"] = data
    _stats_cache["ts"] = now
    return data


@router.get("/database/stats")
async def database_stats():
    """获取数据库统计信息"""
    try:
        stats = await get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据库统计失败: {str(e)}")


@router.post("/database/backup")
async def database_backup():
    """创建数据库备份"""
    try:
        from ..config import settings
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(os.path.dirname(settings.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"data_backup_{ts}.db")
        await backup_database(backup_path)
        return {"message": "备份成功", "backup_path": backup_path}
    except Exception as e:
        logger.error(f"数据库备份失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"数据库备份失败: {str(e)}")


@router.post("/database/rebuild-fts")
async def rebuild_fts():
    """重建 FTS5 全文搜索索引"""
    try:
        await rebuild_fts_index()
        return {"message": "FTS 索引重建成功"}
    except Exception as e:
        logger.error(f"FTS 索引重建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"FTS 索引重建失败: {str(e)}")
