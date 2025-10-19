"""
PostgreSQL storage adapter
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import json
from typing import Any, Optional, Dict
from .adapter import StorageAdapter


class PostgresStore(StorageAdapter):
    """
    PostgreSQL storage adapter for production deployments.

    Requires: asyncpg
    Install: pip install asyncpg

    Usage:
        import asyncpg
        pool = await asyncpg.create_pool("postgresql://user:pass@localhost/dbname")
        storage = PostgresStore(connection=pool)

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, connection, table_name: str = "swiftbot_user_data"):
        """Initialize PostgreSQL storage"""
        self.pool = connection
        self.table_name = table_name
        self._initialized = False

    async def _ensure_table(self):
        """Create table if it doesn't exist"""
        if self._initialized:
            return

        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    user_id BIGINT NOT NULL,
                    key VARCHAR(255) NOT NULL,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, key)
                )
            """)

            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id 
                ON {self.table_name} (user_id)
            """)

        self._initialized = True

    async def get(self, user_id: int, key: str) -> Optional[Any]:
        """Get value for user and key"""
        await self._ensure_table()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f'SELECT value FROM {self.table_name} WHERE user_id = $1 AND key = $2',
                user_id, key
            )

            if row:
                value = row['value']
                return json.loads(value) if isinstance(value, str) else value
            return None

    async def set(self, user_id: int, key: str, value: Any, ttl: Optional[int] = None):
        """Set value for user and key"""
        await self._ensure_table()

        serialized = json.dumps(value)

        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.table_name} (user_id, key, value, updated_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, key) 
                DO UPDATE SET value = $3, updated_at = CURRENT_TIMESTAMP
            """, user_id, key, serialized)

    async def delete(self, user_id: int, key: str):
        """Delete value for user and key"""
        await self._ensure_table()

        async with self.pool.acquire() as conn:
            await conn.execute(
                f'DELETE FROM {self.table_name} WHERE user_id = $1 AND key = $2',
                user_id, key
            )

    async def get_all(self, user_id: int) -> Dict[str, Any]:
        """Get all data for user"""
        await self._ensure_table()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f'SELECT key, value FROM {self.table_name} WHERE user_id = $1',
                user_id
            )

            result = {}
            for row in rows:
                value = json.loads(row['value']) if isinstance(row['value'], str) else row['value']
                result[row['key']] = value

            return result

    async def clear(self, user_id: int):
        """Clear all data for user"""
        await self._ensure_table()

        async with self.pool.acquire() as conn:
            await conn.execute(
                f'DELETE FROM {self.table_name} WHERE user_id = $1',
                user_id
            )

    async def get_all_users(self) -> list:
        """Get list of all user IDs"""
        await self._ensure_table()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f'SELECT DISTINCT user_id FROM {self.table_name}'
            )
            return [row['user_id'] for row in rows]
