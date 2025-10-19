"""
Storage adapter interface
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from typing import Any, Optional, Dict
from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """
    Abstract base class for storage adapters.

    Implement this interface to create custom storage backends.
    Built-in implementations: Redis, PostgreSQL, MongoDB, FileSystem

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    @abstractmethod
    async def get(self, user_id: int, key: str) -> Optional[Any]:
        """
        Get value for user and key.

        Args:
            user_id: User ID
            key: Data key

        Returns:
            Stored value or None
        """
        pass

    @abstractmethod
    async def set(self, user_id: int, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value for user and key.

        Args:
            user_id: User ID
            key: Data key
            value: Value to store
            ttl: Time to live in seconds (optional)
        """
        pass

    @abstractmethod
    async def delete(self, user_id: int, key: str):
        """
        Delete value for user and key.

        Args:
            user_id: User ID
            key: Data key
        """
        pass

    @abstractmethod
    async def get_all(self, user_id: int) -> Dict[str, Any]:
        """
        Get all data for user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of all user data
        """
        pass

    @abstractmethod
    async def clear(self, user_id: int):
        """
        Clear all data for user.

        Args:
            user_id: User ID
        """
        pass
