# log_config.py
import os
import sys

from loguru import logger

# 日志输出目录（可定制）
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 移除默认的 stderr 输出
logger.remove()

# 配置控制台输出
logger.add(
    sys.stderr,
    level="DEBUG",  # 控制台日志等级
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>"
)

# 配置写入文件（带轮转、压缩、保留策略）
logger.add(
    f"{LOG_DIR}/runtime.log",
    level="INFO",
    rotation="10 MB",     # 每个日志文件最大10MB
    retention="7 days",    # 日志保留7天
    compression="zip",     # 过期日志 zip 压缩
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)

# 可选：配置异步日志（需 install uvloop + aiofiles）
# logger.add("logs/async.log", enqueue=True)

# 将 logger 暴露给全局使用
__all__ = ["logger"]