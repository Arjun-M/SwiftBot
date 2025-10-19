"""
File system storage adapter
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Dict
from .adapter import StorageAdapter


class FileStore(StorageAdapter):
    """
    File system storage adapter for simple persistence.

    Suitable for development and single-instance deployments.

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(self, base_path: str = "./data"):
        """
        Initialize file storage.

        Args:
            base_path: Base directory for data files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_user_file(self, user_id: int) -> Path:
        """Get file path for user"""
        return self.base_path / f"user_{user_id}.json"

    def _load_user_data(self, user_id: int) -> Dict:
        """Load user data from file"""
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_user_data(self, user_id: int, data: Dict):
        """Save user data to file"""
        file_path = self._get_user_file(user_id)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    async def get(self, user_id: int, key: str) -> Optional[Any]:
        """Get value"""
        data = self._load_user_data(user_id)
        return data.get(key)

    async def set(self, user_id: int, key: str, value: Any, ttl: Optional[int] = None):
        """Set value (TTL not supported in file storage)"""
        data = self._load_user_data(user_id)
        data[key] = value
        self._save_user_data(user_id, data)

    async def delete(self, user_id: int, key: str):
        """Delete value"""
        data = self._load_user_data(user_id)
        data.pop(key, None)
        self._save_user_data(user_id, data)

    async def get_all(self, user_id: int) -> Dict[str, Any]:
        """Get all user data"""
        return self._load_user_data(user_id)

    async def clear(self, user_id: int):
        """Clear all user data"""
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            os.remove(file_path)
