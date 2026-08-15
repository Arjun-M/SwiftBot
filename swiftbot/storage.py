"""
Pluggable storage backends for FSM state and per-user/per-chat data.

Provides:
- ``MemoryStorage``: in-memory storage (default, state lost on restart)
- ``JSONFileStorage``: JSON-file persistence (survives restarts)

Example:
    from swiftbot.storage import JSONFileStorage

    client = SwiftBot(token="...", storage=JSONFileStorage("states.json"))
    # ctx.set_state / ctx.get_state now persist across restarts

Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when a storage backend operation fails."""


class BaseStorage:
    """
    Abstract interface for storage backends.

    All keys are ``(namespace, key)`` pairs — ``namespace`` is typically
    ``"user"`` or ``"chat"``, and ``key`` is typically ``f"{id}:{field}"``
    (e.g. ``"user:123456789:state"``).
    """

    async def set(self, namespace: str, key: str, value: Any) -> None:
        raise NotImplementedError

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def delete(self, namespace: str, key: str) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        """Release resources (flush buffers, close files)."""


class MemoryStorage(BaseStorage):
    """
    In-memory storage. Fast but all data is lost when the process exits.
    """

    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}

    async def set(self, namespace: str, key: str, value: Any) -> None:
        self.data.setdefault(namespace, {})[key] = value

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        return self.data.get(namespace, {}).get(key)

    async def delete(self, namespace: str, key: str) -> None:
        self.data.get(namespace, {}).pop(key, None)

    async def close(self) -> None:
        pass


class JSONFileStorage(BaseStorage):
    """
    JSON-file persistent storage. Data survives restarts.

    Writes are debounced so that bursts of updates (e.g. an FSM conversation)
    do not flood the disk with one ``fsync`` per state change.

    Args:
        path: File path to persist data to. The parent directory is created
            automatically if it does not exist.
        flush_interval: Seconds to wait after the last write before flushing
            buffered changes to disk (default 1.0).
    """

    def __init__(self, path: str, flush_interval: float = 1.0):
        if not path:
            raise StorageError("storage path cannot be empty")
        self.path = path
        self.flush_interval = flush_interval

        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._data: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self._flush_task: Optional[asyncio.Task] = None
        self._flush_lock = asyncio.Lock()
        self._load()

    # ---------- persistence ----------

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if raw:
                self._data = json.loads(raw)
                if not isinstance(self._data, dict):
                    logger.warning("Corrupted storage file %s, starting fresh", self.path)
                    self._data = {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load storage file %s: %s — starting fresh", self.path, e)
            self._data = {}

    def _flush_now(self):
        """Write buffered changes to disk immediately."""
        try:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
            self._dirty = False
        except OSError as e:
            logger.error("Failed to flush storage %s: %s", self.path, e)
            raise StorageError(f"Failed to flush storage: {e}")

    def _schedule_flush(self):
        if not self._dirty:
            return
        if self._flush_task is not None and not self._flush_task.done():
            return  # A flush is already scheduled
        self._flush_task = asyncio.create_task(self._flush_soon())

    async def _flush_soon(self):
        """Wait for the debounce interval, then flush buffered changes."""
        await asyncio.sleep(self.flush_interval)
        async with self._flush_lock:
            self._flush_now()

    # ---------- public API ----------

    async def set(self, namespace: str, key: str, value: Any) -> None:
        self._data.setdefault(namespace, {})[key] = value
        self._dirty = True
        self._schedule_flush()

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        return self._data.get(namespace, {}).get(key)

    async def delete(self, namespace: str, key: str) -> None:
        self._data.get(namespace, {}).pop(key, None)
        self._dirty = True
        self._schedule_flush()

    async def close(self) -> None:
        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except (asyncio.CancelledError, Exception):
                pass
        # A final flush guarantees the buffer is on disk before close()
        async with self._flush_lock:
            self._flush_now()
            self._dirty = False


class StateManager:
    """
    High-level FSM state manager backed by a storage backend.

    Handles per-user state keyed by ``(user_id, field)`` with optional TTL.
    """

    STATE_FIELD = "state"

    def __init__(self, storage: BaseStorage, ttl: Optional[float] = None):
        self.storage = storage
        self.ttl = ttl

    def _key(self, user_id: int, field: str = "state") -> str:
        return f"{user_id}:{field}"

    async def set_state(self, user_id: int, state: Any) -> None:
        await self.storage.set("user", self._key(user_id), {
            "state": state,
            "updated_at": __import__("time").time(),
        })

    async def get_state(self, user_id: int) -> Optional[Any]:
        record = await self.storage.get("user", self._key(user_id))
        if record is None:
            return None
        if isinstance(record, dict):
            if self.ttl:
                age = __import__("time").time() - record.get("updated_at", 0)
                if age > self.ttl:
                    await self.clear_state(user_id)
                    return None
            return record.get("state")
        return record

    async def clear_state(self, user_id: int) -> None:
        await self.storage.delete("user", self._key(user_id))
