"""
Optional SQLite-backed state store for commercial deployment.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from functools import partial
from pathlib import Path
from threading import Lock
from typing import Any

from backend.core.settings import COMMERCIAL_DB_PATH


class SqliteStateStore:
    def __init__(self, db_path: str = "") -> None:
        self.db_path = Path(db_path).expanduser() if db_path else None
        self._lock = Lock()
        if self.db_path:
            self._initialize()

    @property
    def enabled(self) -> bool:
        return self.db_path is not None

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path:
            raise RuntimeError("SQLite state store is disabled")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def get_json(self, key: str, default: Any) -> Any:
        if not self.enabled:
            return default

        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()
            if not row:
                return default
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return default

    def set_json(self, key: str, value: Any, *, updated_at: str) -> None:
        if not self.enabled:
            return

        serialized = json.dumps(value, ensure_ascii=False)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO kv_store(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, serialized, updated_at),
            )
            connection.commit()

    # ------------------------------------------------------------------
    # Async wrappers — offload blocking SQLite I/O to a thread executor
    # ------------------------------------------------------------------

    async def async_get_json(self, key: str, default: Any) -> Any:
        """Async version of :meth:`get_json`."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self.get_json, key, default))

    async def async_set_json(self, key: str, value: Any, *, updated_at: str) -> None:
        """Async version of :meth:`set_json`."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(self.set_json, key, value, updated_at=updated_at))


state_store = SqliteStateStore(COMMERCIAL_DB_PATH)
