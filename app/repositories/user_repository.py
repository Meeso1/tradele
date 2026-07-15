"""Data access for the `users` table.

This repository only wraps raw SQL and row/model mapping - it has no
business logic (e.g. generating IDs/timestamps), which belongs in
`UserService` instead.
"""

from __future__ import annotations

import logging

from app.services.database_service import DatabaseService


class UserRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def insert(self, user_id: str, created_at: str) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "INSERT INTO users (id, created_at) VALUES (?, ?)",
                (user_id, created_at),
            )

    def exists(self, user_id: str) -> bool:
        with self._database.connect() as conn:
            row = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
        return row is not None
