"""
Storage adapters for data persistence
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .adapter import StorageAdapter
from .redis import RedisStore
from .file import FileStore
from .postgres import PostgresStore
from .mongo import MongoStore

__all__ = ["StorageAdapter", "RedisStore", "FileStore", "PostgresStore", "MongoStore"]
