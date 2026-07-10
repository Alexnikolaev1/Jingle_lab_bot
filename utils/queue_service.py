"""
utils/queue_service.py — Менеджер очереди генерации с graceful shutdown.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from config import settings

logger = logging.getLogger("jinglelab.queue")


@dataclass(order=True)
class _Task:
    priority: int
    coro_factory: Callable[[], Awaitable[None]] = field(compare=False)
    user_id: int = field(compare=False, default=0)


class GenerationQueue:
    def __init__(self, workers: int | None = None) -> None:
        self._queue: asyncio.Queue[_Task | None] = asyncio.Queue()
        self._workers_count = workers or settings.HF_MAX_CONCURRENT_REQUESTS
        self._workers_started = False
        self._worker_tasks: list[asyncio.Task] = []
        self._pending_user_ids: list[int] = []
        self._active_users: set[int] = set()

    def start(self) -> None:
        if self._workers_started:
            return
        for i in range(self._workers_count):
            self._worker_tasks.append(
                asyncio.create_task(self._worker_loop(worker_id=i))
            )
        self._workers_started = True
        logger.info("Запущено %s воркеров очереди генерации", self._workers_count)

    async def stop(self) -> None:
        for _ in range(self._workers_count):
            await self._queue.put(None)
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        self._workers_started = False
        logger.info("Очередь генерации остановлена")

    async def _worker_loop(self, worker_id: int) -> None:
        while True:
            task = await self._queue.get()
            if task is None:
                self._queue.task_done()
                break
            try:
                if task.user_id in self._pending_user_ids:
                    self._pending_user_ids.remove(task.user_id)
                self._active_users.add(task.user_id)
                await task.coro_factory()
            except Exception:
                logger.exception("Воркер %s: ошибка при выполнении задачи", worker_id)
            finally:
                self._active_users.discard(task.user_id)
                self._queue.task_done()

    @property
    def size(self) -> int:
        return self._queue.qsize()

    def position_for_new_task(self) -> int:
        return self._queue.qsize() + 1

    def is_user_busy(self, user_id: int) -> bool:
        return user_id in self._active_users or user_id in self._pending_user_ids

    async def enqueue(
        self, user_id: int, coro_factory: Callable[[], Awaitable[None]]
    ) -> int:
        position = self.position_for_new_task()
        self._pending_user_ids.append(user_id)
        await self._queue.put(
            _Task(priority=0, coro_factory=coro_factory, user_id=user_id)
        )
        return position


generation_queue = GenerationQueue()
