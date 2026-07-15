"""Business logic and persistence for users."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.services.database_service import DatabaseService


class UserService:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def create(self) -> str:
        """Create a new (anonymous) user and return its ID."""
        user_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._database.connect() as conn:
            conn.execute(
                "INSERT INTO users (id, created_at) VALUES (?, ?)",
                (user_id, created_at),
            )
        self._logger.info("Created user %s", user_id)
        return user_id

    def exists(self, user_id: str) -> bool:
        with self._database.connect() as conn:
            row = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
        return row is not None
