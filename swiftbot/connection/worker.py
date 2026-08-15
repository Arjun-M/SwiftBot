"""
Worker pool for concurrent update processing
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import logging
from typing import Callable, Optional, Any
from collections import deque

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Async worker pool for processing updates concurrently.

    Features:
    - Configurable worker count
    - Bounded queue with real backpressure (``submit`` blocks / deadline)
    - Dead letter queue for failed updates (exceptions preserved, not lost)
    - Graceful shutdown that drains the queue

    NOTE: This pool dispatches **coroutines** onto a fixed number of asyncio
    tasks. It provides bounded concurrency and backpressure — it is not a
    priority queue, a thread pool, or a "1000+ updates/second" benchmark.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        num_workers: int = 50,
        max_queue_size: int = 1000,
        enable_dead_letter: bool = True,
        backpressure_timeout: float = 5.0,
    ):
        """
        Initialize worker pool.

        Args:
            num_workers: Number of concurrent worker coroutines
            max_queue_size: Maximum queue size before ``submit`` applies
                backpressure
            enable_dead_letter: Keep failed tasks in a dead letter queue
        """
        if num_workers < 1:
            raise ValueError("num_workers must be at least 1")
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")

        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.enable_dead_letter = enable_dead_letter
        self.backpressure_timeout = backpressure_timeout

        # Reserve ``num_workers`` slots for tasks already being executed so
        # the advertised ``max_queue_size`` counts queued (not in-flight)
        # work — otherwise half the capacity is silently lost.
        self.queue: asyncio.Queue = asyncio.Queue(
            maxsize=max_queue_size + num_workers
        )
        self.workers: list = []
        self.running = False

        # Dead letter queue for failed updates (exceptions preserved so they
        # can actually be inspected and retried — previously errors were lost)
        self.dead_letter_queue: deque = deque(maxlen=100)

        # Statistics
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Start all workers"""
        if self.running:
            return

        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]

    async def stop(self, timeout: float = 10.0):
        """
        Stop all workers gracefully.

        Drains the queue up to ``timeout`` seconds, then cancels workers.
        Any tasks left in the queue are recorded in the dead letter queue.

        Args:
            timeout: Maximum time to wait for the queue to drain
        """
        # Drain the queue first. The workers keep running until the queue is
        # empty, so the ``running`` flag is cleared AFTER draining — clearing
        # it first would make workers bail before processing pending updates.
        try:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        # Now stop accepting new work and cancel the worker coroutines
        self.running = False

        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)

        # Anything still enqueued after the deadline is a dead letter
        if self.enable_dead_letter and not self.queue.empty():
            while not self.queue.empty():
                try:
                    handler, args, kwargs = self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                self._dead_letter(handler, args, kwargs, "pool shutdown (task never started)")
                self.queue.task_done()

        self.workers.clear()

    def _dead_letter(self, handler, args, kwargs, error):
        if self.enable_dead_letter:
            self.dead_letter_queue.append({
                "handler": handler,
                "args": args,
                "kwargs": kwargs,
                "error": str(error),
                "worker_id": None,
            })

    async def submit(self, handler: Callable, *args, **kwargs):
        """
        Submit a task to the worker pool.

        Applies backpressure: blocks until there is room in the queue.
        Use ``submit_nowait`` if blocking the caller is not acceptable.

        Args:
            handler: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        # Backpressure: wait for room in the queue, but cap the wait so a
        # permanently blocked pool surfaces an error instead of hanging.
        try:
            await asyncio.wait_for(
                self.queue.put((handler, args, kwargs)),
                timeout=self.backpressure_timeout,
            )
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                "Worker pool queue is full — backpressure applied; "
                "the pool cannot accept more updates right now"
            )

    def submit_nowait(self, handler: Callable, *args, **kwargs):
        """Submit without blocking; raises ``asyncio.QueueFull`` if full."""
        self.queue.put_nowait((handler, args, kwargs))

    async def _worker(self, worker_id: int):
        """
        Worker coroutine that processes tasks from queue.

        Args:
            worker_id: Unique worker identifier
        """
        while self.running:
            try:
                # Get task with timeout to allow checking the running flag
                try:
                    handler, args, kwargs = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Execute handler
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)

                    self.processed_count += 1

                except Exception as e:
                    self.failed_count += 1
                    self._dead_letter(handler, args, kwargs, e)
                    logger.error(
                        "Worker %d: task %s failed: %s", worker_id,
                        getattr(handler, "__name__", "?"), e
                    )

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Unexpected error in the worker loop — log and continue
                logger.error("Worker %d: unexpected error: %s", worker_id, e)
                continue

    def get_stats(self) -> dict:
        """
        Get worker pool statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "num_workers": self.num_workers,
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "processed": self.processed_count,
            "failed": self.failed_count,
            "dead_letter_size": len(self.dead_letter_queue),
            "running": self.running
        }

    def get_dead_letters(self) -> list:
        """Get failed updates from dead letter queue (includes exceptions)."""
        return list(self.dead_letter_queue)

    async def retry_dead_letters(self):
        """Retry all failed updates from dead letter queue"""
        while self.dead_letter_queue:
            item = self.dead_letter_queue.popleft()
            await self.submit(
                item["handler"],
                *item["args"],
                **item["kwargs"]
            )
