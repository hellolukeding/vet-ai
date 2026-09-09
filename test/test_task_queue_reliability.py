import asyncio
import json

from core.tasks.task_manager import TaskQueueManager
from core.tasks.worker import TaskWorker


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.operations = []

    def setex(self, *args):
        self.operations.append(("setex", args))
        return self

    def expire(self, *args):
        self.operations.append(("expire", args))
        return self

    def zadd(self, *args):
        self.operations.append(("zadd", args))
        return self

    def execute(self):
        for operation, args in self.operations:
            getattr(self.redis, operation)(*args)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}
        self.queue = {}

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.expirations[key] = ttl

    def get(self, key):
        value = self.values.get(key)
        return value.encode() if isinstance(value, str) else value

    def expire(self, key, ttl):
        if key in self.values:
            self.expirations[key] = ttl

    def zadd(self, _key, values):
        self.queue.update(values)

    def zpopmax(self, _key, count=1):
        if not self.queue:
            return []
        task_id = max(self.queue, key=self.queue.get)
        score = self.queue.pop(task_id)
        return [(task_id.encode(), score)][:count]

    def pipeline(self, transaction=True):
        assert transaction is True
        return FakePipeline(self)


def test_queue_claim_is_priority_first_and_fifo():
    redis = FakeRedis()
    manager = TaskQueueManager(redis)

    first = manager.submit_task("diagnosis", {"n": 1}, priority=0)
    second = manager.submit_task("diagnosis", {"n": 2}, priority=0)
    urgent = manager.submit_task("diagnosis", {"n": 3}, priority=2)

    assert manager.get_next_task()["task_id"] == urgent
    assert manager.get_next_task()["task_id"] == first
    assert manager.get_next_task()["task_id"] == second


def test_terminal_state_is_written_with_one_transaction_and_consistent_ttl():
    redis = FakeRedis()
    manager = TaskQueueManager(redis, result_expire_time=123)
    redis.values["task_assessment:t1"] = json.dumps({"status": "completed"})

    assert manager.set_task_completed("t1", {"diagnoses": []}) is True
    assert redis.values["task_status:t1"] == "completed"
    assert json.loads(redis.values["task_progress:t1"])["progress"] == 100
    assert redis.expirations["task_progress:t1"] == 123
    assert redis.expirations["task_assessment:t1"] == 123


def test_worker_enforces_execution_timeout():
    class Manager:
        task_timeout = 0.01
        failed = None

        def set_task_failed(self, task_id, error):
            self.failed = (task_id, error)
            return True

    manager = Manager()
    worker = TaskWorker(manager)

    async def slow(*_args):
        await asyncio.sleep(1)

    worker.executor.execute_task = slow
    asyncio.run(
        worker._execute_task({"task_id": "t1", "task_type": "diagnosis", "data": {}})
    )

    assert manager.failed[0] == "t1"
    assert "超时" in manager.failed[1]
