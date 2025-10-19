"""
Connection and worker pool management
Copyright (c) 2025 Arjun-M/SwiftBot
"""

from .pool import HTTPConnectionPool
from .worker import WorkerPool

__all__ = ["HTTPConnectionPool", "WorkerPool"]
