#!/usr/bin/env python3
"""
Railway 入口文件 - 直接启动 FastAPI 应用
"""
import os
import sys
import socket

# 将 src 目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import uvicorn
from src.config import settings


def find_available_port(preferred: int, fallback: int = 8088) -> int:
    def is_port_free(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return True
            except OSError:
                return False

    if is_port_free(preferred):
        return preferred
    for port in [fallback, 8089, 8090, 9000]:
        if port != preferred and is_port_free(port):
            return port
    return preferred


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    port = int(env_port) if env_port else find_available_port(settings.port)

    print(f"🧪 AI 测试用例生成器 v4.1 (auth enabled)")
    print(f"   启动地址: http://0.0.0.0:{port}")
    print(f"   API 文档: http://0.0.0.0:{port}/docs")

    from src.main import app
    uvicorn.run(app, host="0.0.0.0", port=port)
