"""Business logic for users, backed by `UserRepository`."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository, logger: logging.Logger) -> None:
        self._user_repository: UserRepository = user_repository
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def create(self) -> str:
        """Create a new (anonymous) user and return its ID."""
        user_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        self._user_repository.insert(user_id, created_at)
        self._logger.info("Created user %s", user_id)
        return user_id

    def exists(self, user_id: str) -> bool:
        return self._user_repository.exists(user_id)
