"""
LLM API调用重试助手

为LLM API调用提供自动重试功能，处理429（并发限制）和5xx错误。
"""

import asyncio
from typing import Callable, TypeVar

from config.logger import logger

T = TypeVar("T")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base


async def retry_on_rate_limit(
    func: Callable[..., T], config: RetryConfig = None, *args, **kwargs
) -> T:
    """
    在遇到429或5xx错误时自动重试

    Args:
        func: 要执行的异步函数
        config: 重试配置
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数执行结果

    Raises:
        Exception: 重试次数用尽后仍失败
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"重试第 {attempt} 次...")

            result = await func(*args, **kwargs)

            if attempt > 0:
                logger.info(f"重试成功（第 {attempt} 次尝试）")

            return result

        except Exception as e:
            last_exception = e

            # 检查是否是可重试的错误
            error_str = str(e)
            is_rate_limit = "429" in error_str or "1302" in error_str
            is_server_error = any(
                f"5{code}" in error_str for code in ["00", "01", "02", "03", "04"]
            )

            if not (is_rate_limit or is_server_error):
                # 不是可重试的错误，直接抛出
                logger.error(f"不可重试的错误: {e}")
                raise

            if attempt >= config.max_retries:
                # 重试次数用尽
                logger.error(f"重试次数用尽（{config.max_retries}次），最后错误: {e}")
                raise

            # 计算退避时间（指数退避）
            delay = min(
                config.initial_delay * (config.exponential_base**attempt),
                config.max_delay,
            )

            logger.warning(
                f"API调用失败（第{attempt + 1}次尝试）: {e}，{delay:.1f}秒后重试..."
            )

            await asyncio.sleep(delay)

    # 所有重试都失败
    raise last_exception
