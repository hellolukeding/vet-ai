"""
LLM API调用速率限制器

使用信号量(Semaphore)限制同时进行的LLM API调用数量，
防止触发API服务商的并发限制。
"""

import asyncio
from typing import Callable, TypeVar

from config.logger import logger

T = TypeVar("T")


class GlobalRateLimiter:
    """
    全局LLM API调用速率限制器

    使用单例模式，确保整个应用共享同一个限制器实例。
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, max_concurrent: int = 1):
        """
        创建或获取单例实例

        Args:
            max_concurrent: 最大并发API调用数，默认1（完全串行）
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._semaphore = asyncio.Semaphore(max_concurrent)
            cls._instance._max_concurrent = max_concurrent
            cls._instance._active_calls = 0
        return cls._instance

    @classmethod
    async def get_limiter(cls, max_concurrent: int = 1) -> "GlobalRateLimiter":
        """
        获取速率限制器实例（线程安全）

        Args:
            max_concurrent: 最大并发数

        Returns:
            GlobalRateLimiter实例
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_concurrent)
            return cls._instance

    async def __aenter__(self):
        """进入上下文，等待获取信号量"""
        await self._semaphore.acquire()
        self._active_calls += 1
        logger.debug(
            f"API调用开始 - 当前活跃调用数: {self._active_calls}/{self._max_concurrent}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，释放信号量"""
        self._active_calls -= 1
        self._semaphore.release()
        logger.debug(
            f"API调用结束 - 当前活跃调用数: {self._active_calls}/{self._max_concurrent}"
        )

    async def call_with_limit(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        在速率限制下调用函数

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        async with self:
            return await func(*args, **kwargs)


# 全局限制器实例（默认最大并发数为1）
_global_limiter: GlobalRateLimiter = None


async def get_global_rate_limiter(max_concurrent: int = 1) -> GlobalRateLimiter:
    """
    获取全局速率限制器

    Args:
        max_concurrent: 最大并发API调用数，默认1

    Returns:
        GlobalRateLimiter实例
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = await GlobalRateLimiter.get_limiter(max_concurrent)
    return _global_limiter
