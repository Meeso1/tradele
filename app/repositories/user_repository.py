from __future__ import annotations

import logging
from typing import Any

from app.services.database_service import DatabaseService

DEFAULT_ALLOWED_AUTH_METHODS_JSON = '["token","api_key"]'


class UserRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def insert(
        self,
        user_id: str,
        created_at: str,
        *,
        allowed_auth_methods_json: str = DEFAULT_ALLOWED_AUTH_METHODS_JSON,
    ) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "INSERT INTO users (id, created_at, is_service_account, allowed_auth_methods) VALUES (?, ?, 0, ?)",
                (user_id, created_at, allowed_auth_methods_json),
            )

    def insert_service_account_if_not_exists(
        self, user_id: str, created_at: str, allowed_auth_methods_json: str
    ) -> bool:
        """Atomically insert the service account row if it doesn't exist yet.

        Returns whether the row was inserted by this call.
        """
        with self._database.connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO users (id, created_at, is_service_account, allowed_auth_methods) VALUES (?, ?, 1, ?)",
                (user_id, created_at, allowed_auth_methods_json),
            )
        return cursor.rowcount > 0

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._database.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row is not None else None

    def exists(self, user_id: str) -> bool:
        with self._database.connect() as conn:
            row = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
        return row is not None

    def list_all_user_ids(self) -> list[str]:
        with self._database.connect() as conn:
            rows = conn.execute("SELECT id FROM users").fetchall()
        return [row["id"] for row in rows]
