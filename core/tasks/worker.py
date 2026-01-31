"""
后台Worker

持续从任务队列中获取任务并执行，支持并发控制和优雅关闭。
"""

import asyncio
from typing import Optional

from config.logger import logger
from core.tasks.task_manager import TaskQueueManager, get_task_manager
from core.tasks.task_executor import TaskExecutor


class TaskWorker:
    """
    后台任务Worker

    从队列获取任务并执行，支持并发控制。
    """

    def __init__(
        self,
        task_manager: TaskQueueManager,
        max_concurrent_tasks: int = 5
    ):
        """
        初始化Worker

        Args:
            task_manager: 任务队列管理器
            max_concurrent_tasks: 最大并发任务数
        """
        self.task_manager = task_manager
        self.max_concurrent_tasks = max_concurrent_tasks
        self.executor = TaskExecutor(task_manager)

        # Worker控制
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # 当前正在执行的任务
        self._active_tasks: set = set()

    async def start(self):
        """启动Worker"""
        if self._running:
            logger.warning("Worker已经在运行")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("任务队列Worker已启动")

    async def stop(self):
        """停止Worker"""
        if not self._running:
            return

        logger.info("正在停止任务队列Worker...")
        self._running = False

        # 等待当前任务完成
        if self._active_tasks:
            logger.info(f"等待 {len(self._active_tasks)} 个活跃任务完成...")
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # 取消Worker任务
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("任务队列Worker已停止")

    async def _worker_loop(self):
        """Worker主循环"""
        logger.info("Worker循环开始运行")

        while self._running:
            try:
                # 检查是否可以接受新任务
                if len(self._active_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.5)
                    continue

                # 从队列获取任务
                task = self.task_manager.get_next_task()
                if task is None:
                    # 队列为空，等待一会儿
                    await asyncio.sleep(1)
                    continue

                # 创建任务并添加到活跃任务集合
                task_coroutine = self._execute_task(task)
                async_task = asyncio.create_task(task_coroutine)
                self._active_tasks.add(async_task)

                # 任务完成后从活跃集合中移除
                async_task.add_done_callback(
                    self._active_tasks.discard
                )

            except asyncio.CancelledError:
                logger.info("Worker循环被取消")
                break
            except Exception as e:
                logger.error(f"Worker循环出错: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("Worker循环已退出")

    async def _execute_task(self, task: dict):
        """
        执行单个任务

        Args:
            task: 任务对象
        """
        task_id = task.get("task_id")
        task_type = task.get("task_type")
        task_data = task.get("data", {})

        logger.info(
            f"开始执行任务: {task_id}, "
            f"类型: {task_type}, "
            f"活跃任务数: {len(self._active_tasks)}"
        )

        try:
            # 使用信号量控制并发
            async with self._semaphore:
                # 执行任务
                result = await self.executor.execute_task(
                    task_type, task_id, task_data
                )

                # 标记任务完成
                self.task_manager.set_task_completed(task_id, result)

                logger.info(f"任务执行成功: {task_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"任务执行失败: {task_id}, 错误: {error_msg}")

            # 标记任务失败
            self.task_manager.set_task_failed(task_id, error_msg)


# 全局Worker实例
_worker: Optional[TaskWorker] = None


async def start_worker():
    """启动全局Worker"""
    global _worker

    if _worker is not None:
        logger.warning("Worker已经启动")
        return

    task_manager = get_task_manager()
    _worker = TaskWorker(
        task_manager=task_manager,
        max_concurrent_tasks=task_manager.max_concurrent_tasks
    )

    await _worker.start()
    logger.info("全局任务队列Worker已启动")


async def stop_worker():
    """停止全局Worker"""
    global _worker

    if _worker is None:
        logger.warning("Worker未启动")
        return

    await _worker.stop()
    _worker = None
    logger.info("全局任务队列Worker已停止")


def get_worker_status() -> dict:
    """获取Worker状态"""
    if _worker is None:
        return {
            "running": False,
            "active_tasks": 0,
            "max_concurrent": 0
        }

    return {
        "running": _worker._running,
        "active_tasks": len(_worker._active_tasks),
        "max_concurrent": _worker.max_concurrent_tasks,
        "queue_size": _worker.task_manager.get_queue_size()
    }
