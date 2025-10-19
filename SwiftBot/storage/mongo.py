"""
MongoDB storage adapter
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import json
from typing import Any, Optional, Dict
from .adapter import StorageAdapter


class MongoStore(StorageAdapter):
    """
    MongoDB storage adapter for production deployments.

    Requires: motor
    Install: pip install motor

    Usage:
        import motor.motor_asyncio
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
        storage = MongoStore(connection=client, database="swiftbot")

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, connection, database: str = "swiftbot", collection: str = "user_data"):
        """
        Initialize MongoDB storage.

        Args:
            connection: Motor AsyncIOMotorClient
            database: Database name
            collection: Collection name
        """
        self.client = connection
        self.db = self.client[database]
        self.collection = self.db[collection]
        self._initialized = False

    async def _ensure_indexes(self):
        """Create indexes for better performance"""
        if self._initialized:
            return

        # Create compound index on user_id and key
        await self.collection.create_index([("user_id", 1), ("key", 1)], unique=True)

        # Create index on user_id for faster queries
        await self.collection.create_index("user_id")

        self._initialized = True

    async def get(self, user_id: int, key: str) -> Optional[Any]:
        """
        Get value for user and key.

        Args:
            user_id: User ID
            key: Data key

        Returns:
            Stored value or None
        """
        await self._ensure_indexes()

        doc = await self.collection.find_one({
            "user_id": user_id,
            "key": key
        })

        if doc:
            return doc.get("value")
        return None

    async def set(self, user_id: int, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value for user and key.

        Args:
            user_id: User ID
            key: Data key
            value: Value to store
            ttl: Time to live in seconds (requires TTL index)
        """
        await self._ensure_indexes()

        import datetime

        doc = {
            "user_id": user_id,
            "key": key,
            "value": value,
            "updated_at": datetime.datetime.utcnow()
        }

        if ttl:
            doc["expire_at"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)

        await self.collection.update_one(
            {"user_id": user_id, "key": key},
            {"$set": doc},
            upsert=True
        )

    async def delete(self, user_id: int, key: str):
        """
        Delete value for user and key.

        Args:
            user_id: User ID
            key: Data key
        """
        await self._ensure_indexes()

        await self.collection.delete_one({
            "user_id": user_id,
            "key": key
        })

    async def get_all(self, user_id: int) -> Dict[str, Any]:
        """
        Get all data for user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of all user data
        """
        await self._ensure_indexes()

        cursor = self.collection.find({"user_id": user_id})

        result = {}
        async for doc in cursor:
            result[doc["key"]] = doc["value"]

        return result

    async def clear(self, user_id: int):
        """
        Clear all data for user.

        Args:
            user_id: User ID
        """
        await self._ensure_indexes()

        await self.collection.delete_many({"user_id": user_id})

    async def get_all_users(self) -> list:
        """
        Get list of all user IDs in storage.

        Returns:
            List of user IDs
        """
        await self._ensure_indexes()

        # Get distinct user_ids
        user_ids = await self.collection.distinct("user_id")
        return user_ids

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
