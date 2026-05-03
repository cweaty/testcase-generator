"""
共享工具：统计缓存、限流器等
供各 router 模块引用
"""
import time
from collections import defaultdict


# ========== 请求限流 ==========
class RateLimiter:
    """基于滑动窗口的简单限流器"""
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.window
        ]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True


# 全局限流器实例
rate_limiter = RateLimiter(max_requests=120, window_seconds=60)
generate_limiter = RateLimiter(max_requests=10, window_seconds=60)


# ========== 统计缓存 ==========
_stats_cache = {"data": None, "ts": 0}
CACHE_TTL = 10  # 10秒缓存


def invalidate_stats_cache():
    """使统计缓存失效"""
    _stats_cache["data"] = None
