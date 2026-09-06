"""Creation, verification and lifecycle management of API keys.

API keys are presented by clients via HTTP Basic auth, in the form
`Authorization: Basic base64(base64(key_id) + ":" + base64(secret))` - the
Basic username is `base64(key_id)` and the password is `base64(secret)`, so
any characters can appear in either part. The key ID is looked up in the
database and the secret is verified by SHA-256 hash equality (key values
themselves are never stored). Key IDs and secrets are treated as arbitrary
strings - the `key_`/`secret_` prefixes used when generating them are purely
cosmetic.

Keys are never deleted, only deactivated, and a key can never be used to
deactivate itself (so the authenticating key always remains active). The
service account's key is created at startup by `ServiceAccountCreator`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime

from app.models.api_key import ApiKey
from app.repositories.api_key_repository import ApiKeyRepository
from app.services.settings_service import SettingsService
from app.services.user_service import UserService


class AuthenticatingKeyDeactivationError(Exception):
    """A key cannot be deactivated by a request authenticated with itself."""


class ApiKeyService:
    def __init__(
        self,
        api_key_repository: ApiKeyRepository,
        user_service: UserService,
        settings: SettingsService,
        logger: logging.Logger,
    ) -> None:
        self._repository: ApiKeyRepository = api_key_repository
        self._user_service: UserService = user_service
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    @staticmethod
    def generate_key_id() -> str:
        """Generate a new key ID. The `key_` prefix is cosmetic only."""
        return f"key_{uuid.uuid4()}"

    @staticmethod
    def generate_secret() -> str:
        """Generate a new key secret. The `secret_` prefix is cosmetic only."""
        return f"secret_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    @staticmethod
    def format_authorization_header(key_id: str, secret: str) -> str:
        """Build the `Authorization` header value that presents this key."""
        username = base64.b64encode(key_id.encode()).decode()
        password = base64.b64encode(secret.encode()).decode()
        blob = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {blob}"

    def create_key(
        self,
        user_id: str,
        name: str,
        *,
        key_hash: str | None = None,
        created_by_key: str | None = None,
    ) -> tuple[ApiKey, str | None]:
        """Create an active API key and return it alongside its secret.

        `key_hash` can be overridden when bootstrapping the service
        account's key from an operator-configured hash. When given, no
        secret is generated and None is returned instead - the value is
        only known to whoever configured the hash. Otherwise, the secret
        is not recoverable after this call - callers must return it to the
        user immediately.
        """
        if key_hash is None:
            secret = self.generate_secret()
            key_hash = self._hash_secret(secret)
        else:
            secret = None

        api_key = ApiKey(
            id=self.generate_key_id(),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            created_by_key=created_by_key,
            created_at=datetime.now(UTC),
            deactivated_at=None,
        )
        self._repository.insert(api_key)
        self._logger.info("Created API key %s for user %s", api_key.id, user_id)
        return api_key, secret

    def get_key(self, key_id: str) -> ApiKey | None:
        """Return a key by ID, regardless of its status."""
        return self._repository.get_by_id(key_id)

    def authenticate(self, key_id: str, secret: str) -> ApiKey | None:
        """Verify an API key, returning its record if valid."""
        api_key = self._repository.get_by_id(key_id)
        if api_key is None:
            self._logger.warning("API key authentication failed: unknown key ID %s", key_id)
            return None
        if api_key.deactivated_at is not None:
            self._logger.warning("API key authentication failed: key %s is deactivated", key_id)
            return None
        if not hmac.compare_digest(api_key.key_hash, self._hash_secret(secret)):
            self._logger.warning("API key authentication failed: wrong secret for key %s", key_id)
            return None
        return api_key

    def list_keys(self, user_id: str) -> list[ApiKey]:
        """List all of the user's API keys, active and deactivated."""
        return self._repository.list_for_user(user_id)

    def deactivate_key(
        self, user_id: str, key_id: str, *, authenticating_key_id: str | None
    ) -> ApiKey | None:
        """Deactivate one of the user's API keys and return the updated record.

        Returns None if the key doesn't exist or belongs to another user.
        Deactivating an already-deactivated key is a no-op. A key can never
        be deactivated by a request authenticated with itself, so the
        authenticating key always remains active.
        """
        api_key = self._repository.get_by_id(key_id)
        if api_key is None or api_key.user_id != user_id:
            return None
        if api_key.deactivated_at is not None:
            return api_key
        if key_id == authenticating_key_id:
            raise AuthenticatingKeyDeactivationError(
                f"API key {key_id} was used to authenticate this request"
            )

        self._repository.deactivate(key_id, datetime.now(UTC))
        self._logger.info("Deactivated API key %s for user %s", key_id, user_id)
        updated = self._repository.get_by_id(key_id)
        assert updated is not None
        return updated
