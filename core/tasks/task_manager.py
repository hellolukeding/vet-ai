"""
任务队列管理器

提供基于Redis的任务队列功能，支持任务提交、状态查询、并发控制等。
"""

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from redis import Redis
from redis.lock import Lock

from config.logger import logger


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待执行
    PROCESSING = "processing" # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class TaskQueueManager:
    """
    任务队列管理器

    功能：
    1. 任务提交和排队
    2. 任务状态跟踪
    3. 并发控制
    4. 任务结果缓存
    """

    # Redis键前缀
    TASK_QUEUE_KEY = "task_queue:pet_care"       # 任务队列
    TASK_DATA_KEY = "task_data:"                 # 任务数据
    TASK_STATUS_KEY = "task_status:"             # 任务状态
    TASK_RESULT_KEY = "task_result:"             # 任务结果
    TASK_PROGRESS_KEY = "task_progress:"         # 任务进度
    CONCURRENCY_LOCK_KEY = "concurrency_lock"    # 并发控制锁

    def __init__(
        self,
        redis_client: Redis,
        max_concurrent_tasks: int = 5,
        task_timeout: int = 600,         # 任务超时时间（秒）
        result_expire_time: int = 3600   # 结果过期时间（秒）
    ):
        """
        初始化任务队列管理器

        Args:
            redis_client: Redis客户端
            max_concurrent_tasks: 最大并发任务数
            task_timeout: 任务超时时间（秒）
            result_expire_time: 结果缓存时间（秒）
        """
        self.redis = redis_client
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.result_expire_time = result_expire_time

        # 后台worker引用
        self._worker_task: Optional[asyncio.Task] = None

    def submit_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        提交任务到队列

        Args:
            task_type: 任务类型（如 "pet_care_plan"）
            task_data: 任务数据
            priority: 优先级（数字越大优先级越高）

        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())

        # 创建任务对象
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "data": task_data,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING
        }

        try:
            # 保存任务数据
            self.redis.setex(
                f"{self.TASK_DATA_KEY}{task_id}",
                self.task_timeout + 60,  # 数据保存时间比超时时间长一些
                json.dumps(task)
            )

            # 初始化任务状态
            self.redis.setex(
                f"{self.TASK_STATUS_KEY}{task_id}",
                self.task_timeout + 60,
                TaskStatus.PENDING
            )

            # 添加到队列（使用有序集合实现优先级队列）
            # score = priority + timestamp，确保相同优先级按时间排序
            score = priority + datetime.now().timestamp() / 10000000
            self.redis.zadd(
                self.TASK_QUEUE_KEY,
                {task_id: score}
            )

            logger.info(
                f"任务已提交: task_id={task_id}, "
                f"task_type={task_type}, priority={priority}"
            )

            return task_id

        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            raise

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            Dict: 任务状态信息，如果任务不存在返回None
        """
        try:
            # 获取状态
            status_data = self.redis.get(f"{self.TASK_STATUS_KEY}{task_id}")
            if not status_data:
                return None

            status = status_data.decode('utf-8')

            # 获取进度信息
            progress_data = self.redis.get(f"{self.TASK_PROGRESS_KEY}{task_id}")
            progress = json.loads(progress_data) if progress_data else None

            return {
                "task_id": task_id,
                "status": status,
                "progress": progress
            }

        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            Dict: 任务结果，如果任务未完成或不存在返回None
        """
        try:
            result_data = self.redis.get(f"{self.TASK_RESULT_KEY}{task_id}")
            if not result_data:
                return None

            return json.loads(result_data)

        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        try:
            # 检查任务状态
            status_data = self.redis.get(f"{self.TASK_STATUS_KEY}{task_id}")
            if not status_data:
                return False

            status = status_data.decode('utf-8')
            if status != TaskStatus.PENDING:
                logger.warning(f"任务不在可取消状态: {status}")
                return False

            # 从队列中移除
            self.redis.zrem(self.TASK_QUEUE_KEY, task_id)

            # 更新状态
            self.redis.setex(
                f"{self.TASK_STATUS_KEY}{task_id}",
                self.task_timeout + 60,
                TaskStatus.CANCELLED
            )

            logger.info(f"任务已取消: {task_id}")
            return True

        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False

    def update_task_progress(
        self,
        task_id: str,
        stage: str,
        progress: int,
        message: str = ""
    ):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            stage: 当前阶段（如 "提取宠物信息", "生成营养计划"）
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        try:
            progress_data = {
                "stage": stage,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now().isoformat()
            }

            self.redis.setex(
                f"{self.TASK_PROGRESS_KEY}{task_id}",
                self.task_timeout + 60,
                json.dumps(progress_data)
            )

            logger.debug(
                f"任务进度更新: {task_id}, {stage}, {progress}%"
            )

        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")

    def set_task_processing(self, task_id: str):
        """设置任务为处理中状态"""
        try:
            self.redis.setex(
                f"{self.TASK_STATUS_KEY}{task_id}",
                self.task_timeout + 60,
                TaskStatus.PROCESSING
            )
            logger.info(f"任务开始处理: {task_id}")
        except Exception as e:
            logger.error(f"设置任务状态失败: {e}")

    def set_task_completed(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成并保存结果"""
        try:
            # 保存结果
            self.redis.setex(
                f"{self.TASK_RESULT_KEY}{task_id}",
                self.result_expire_time,
                json.dumps(result)
            )

            # 更新状态
            self.redis.setex(
                f"{self.TASK_STATUS_KEY}{task_id}",
                self.result_expire_time,
                TaskStatus.COMPLETED
            )

            # 更新进度为100%
            self.update_task_progress(task_id, "completed", 100, "任务已完成")

            logger.info(f"任务完成: {task_id}")

        except Exception as e:
            logger.error(f"设置任务完成状态失败: {e}")

    def set_task_failed(self, task_id: str, error: str):
        """标记任务失败"""
        try:
            # 保存错误信息
            error_result = {"error": error}
            self.redis.setex(
                f"{self.TASK_RESULT_KEY}{task_id}",
                self.result_expire_time,
                json.dumps(error_result)
            )

            # 更新状态
            self.redis.setex(
                f"{self.TASK_STATUS_KEY}{task_id}",
                self.result_expire_time,
                TaskStatus.FAILED
            )

            logger.error(f"任务失败: {task_id}, error={error}")

        except Exception as e:
            logger.error(f"设置任务失败状态失败: {e}")

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        从队列获取下一个待处理任务（原子操作）

        Returns:
            Dict: 任务数据，如果没有任务返回None
        """
        try:
            # 使用原子操作从有序集合获取并移除最高优先级的任务
            # ZRANGEBYSCORE ... LIMIT 0 1 获取最高分（优先级）的任务
            tasks = self.redis.zrange(
                self.TASK_QUEUE_KEY,
                0,
                0,
                desc=True  # 降序，最高优先级在前
            )

            if not tasks:
                return None

            task_id = tasks[0].decode('utf-8')

            # 从队列中移除
            self.redis.zrem(self.TASK_QUEUE_KEY, task_id)

            # 获取任务数据
            task_data = self.redis.get(f"{self.TASK_DATA_KEY}{task_id}")
            if not task_data:
                logger.warning(f"任务数据不存在: {task_id}")
                return None

            task = json.loads(task_data)
            logger.info(f"获取任务: {task_id}")

            return task

        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None

    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        try:
            return self.redis.zcard(self.TASK_QUEUE_KEY)
        except Exception as e:
            logger.error(f"获取队列大小失败: {e}")
            return 0

    def get_active_tasks_count(self) -> int:
        """获取当前正在处理的任务数"""
        try:
            # 统计PROCESSING状态的任务数
            # 这里简化处理，实际可以使用更精确的计数器
            pattern = f"{self.TASK_STATUS_KEY}*"
            count = 0
            for key in self.redis.scan_iter(match=pattern):
                status = self.redis.get(key)
                if status and status.decode('utf-8') == TaskStatus.PROCESSING:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"获取活跃任务数失败: {e}")
            return 0


# 全局任务队列管理器实例
_task_manager: Optional[TaskQueueManager] = None


def get_task_manager() -> TaskQueueManager:
    """获取任务队列管理器单例"""
    global _task_manager
    if _task_manager is None:
        from backend.settings import settings
        redis_client = Redis.from_url(settings.REDIS_URL)
        _task_manager = TaskQueueManager(
            redis_client=redis_client,
            max_concurrent_tasks=5,  # 最多同时处理5个任务
            task_timeout=600,        # 10分钟超时
            result_expire_time=3600  # 结果保存1小时
        )
    return _task_manager
