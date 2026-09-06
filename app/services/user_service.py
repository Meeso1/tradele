"""Business logic for users, backed by `UserRepository`."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from app.auth_context import AUTH_METHOD_API_KEY, AUTH_METHOD_TOKEN
from app.models.user import UserInfo
from app.repositories.user_repository import UserRepository


class UserService:
    SERVICE_ACCOUNT_ID: str = "service-account"

    DEFAULT_ALLOWED_AUTH_METHODS: tuple[str, ...] = (AUTH_METHOD_TOKEN, AUTH_METHOD_API_KEY)
    SERVICE_ACCOUNT_ALLOWED_AUTH_METHODS: tuple[str, ...] = (AUTH_METHOD_API_KEY,)

    def __init__(self, user_repository: UserRepository, logger: logging.Logger) -> None:
        self._user_repository: UserRepository = user_repository
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def create(self) -> str:
        """Create a new (anonymous) user and return its ID."""
        user_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        self._user_repository.insert(
            user_id,
            created_at,
            allowed_auth_methods_json=json.dumps(self.DEFAULT_ALLOWED_AUTH_METHODS),
        )
        self._logger.info("Created user %s", user_id)
        return user_id

    def ensure_service_account_exists(self) -> None:
        """Create the service account if it doesn't exist yet (atomically)."""
        inserted = self._user_repository.insert_service_account_if_not_exists(
            self.SERVICE_ACCOUNT_ID,
            datetime.now(UTC).isoformat(),
            json.dumps(self.SERVICE_ACCOUNT_ALLOWED_AUTH_METHODS),
        )
        if inserted:
            self._logger.info("Created service account %s", self.SERVICE_ACCOUNT_ID)

    def get_user_info(self, user_id: str) -> UserInfo | None:
        """Return the user's data, or None if they don't exist."""
        row = self._user_repository.get_by_id(user_id)
        if row is None:
            return None
        return UserInfo(
            user_id=row["id"],
            created_at=row["created_at"],
            is_service_account=bool(row["is_service_account"]),
            allowed_auth_methods=tuple(json.loads(row["allowed_auth_methods"])),
        )

    def exists(self, user_id: str) -> bool:
        return self._user_repository.exists(user_id)

    def list_ids(self) -> list[str]:
        """Return the IDs of every registered user."""
        return self._user_repository.list_all_user_ids()
