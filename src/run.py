#!/usr/bin/env python3
"""
AI 测试用例生成器 v3.4 - 启动脚本
"""
import socket
import uvicorn
from .config import settings


def find_available_port(preferred: int, fallback: int = 8088) -> int:
    """检查首选端口是否可用，不可用则尝试备选端口"""
    def is_port_free(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return True
            except OSError:
                return False

    if is_port_free(preferred):
        return preferred

    # 尝试常用的备选端口
    for port in [fallback, 8089, 8090, 9000]:
        if port != preferred and is_port_free(port):
            return port

    return preferred  # 让 uvicorn 自己报错


if __name__ == "__main__":
    port = find_available_port(settings.port)

    print(f"""
╔══════════════════════════════════════════╗
║   🧪 AI 测试用例生成器 v4.0             ║
║   启动地址: http://localhost:{port:<5}       ║
║   API 文档: http://localhost:{port}/docs   ║
║   快捷键: Ctrl+K 命令面板                 ║
╚══════════════════════════════════════════╝
    """)

    if port != settings.port:
        print(f"  ⚠️  端口 {settings.port} 被占用，已切换到 {port}\n")

    # 使用直接导入方式避免 uvicorn 字符串加载的 lifespan 递归问题
    from .main import app
    uvicorn.run(app, host=settings.host, port=port)
