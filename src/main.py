"""
FastAPI 应用入口 v3.4
提供文档上传、AI 测试用例生成、管理、多格式导出等 API
模块化路由版本
"""
import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .database import init_db, pool

# 导入路由模块
from .routers import (
    documents,
    testcases,
    trash,
    config as config_router,
    templates,
    export,
    tasks,
    logs,
    system,
    executor,
    suites,
)

# 导入共享工具（用于中间件）
from .routers._shared import rate_limiter

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("应用关闭，释放连接池...")
    await pool.close_all()


app = FastAPI(
    title="AI 测试用例生成器",
    description="基于 AI 根据需求文档/接口文档自动生成测试用例",
    version="4.0.0",
    lifespan=lifespan
)

# GZip 压缩中间件（减少传输大小 60-80%）
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 中间件 & 异常处理 ==========

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """全局请求限流中间件"""
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试", "retry_after": 60}
            )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """统一错误响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局未知异常处理"""
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": 500,
            "detail": "服务器内部错误",
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )


# 静态文件服务（开发模式：禁用缓存）
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    """开发模式下禁止浏览器缓存静态文件"""
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ========== 页面路由 ==========

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """提供前端页面"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>前端文件未找到</h1>")


# ========== 注册路由模块 ==========
app.include_router(documents.router)
app.include_router(testcases.router)
app.include_router(trash.router)
app.include_router(config_router.router)
app.include_router(templates.router)
app.include_router(export.router)
app.include_router(tasks.router)
app.include_router(logs.router)
app.include_router(system.router)
app.include_router(executor.router)
app.include_router(suites.router)


if __name__ == "__main__":
    import uvicorn
    from .main import app
    uvicorn.run(app, host=settings.host, port=settings.port)
