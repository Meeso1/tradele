from __future__ import annotations

import logging
from datetime import datetime

from app.models.api_key import ApiKey
from app.services.database_service import DatabaseService


class ApiKeyRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def insert(self, api_key: ApiKey) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "INSERT INTO api_keys (id, user_id, name, key_hash, created_by_key, created_at, deactivated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    api_key.id,
                    api_key.user_id,
                    api_key.name,
                    api_key.key_hash,
                    api_key.created_by_key,
                    api_key.created_at.isoformat(),
                    api_key.deactivated_at.isoformat() if api_key.deactivated_at else None,
                ),
            )

    def get_by_id(self, key_id: str) -> ApiKey | None:
        with self._database.connect() as conn:
            row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
        return ApiKey.from_row(dict(row)) if row is not None else None

    def list_for_user(self, user_id: str) -> list[ApiKey]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at", (user_id,)
            ).fetchall()
        return [ApiKey.from_row(dict(row)) for row in rows]

    def deactivate(self, key_id: str, deactivated_at: datetime) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "UPDATE api_keys SET deactivated_at = ? WHERE id = ?",
                (deactivated_at.isoformat(), key_id),
            )
