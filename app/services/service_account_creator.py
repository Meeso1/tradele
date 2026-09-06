"""Creation of the service account and its API key at startup."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.services.api_key_service import ApiKeyService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

SERVICE_ACCOUNT_KEY_NAME: str = "Service account key"


class ServiceAccountCreator:
    """Ensures the service account and an active API key for it exist at
    startup.

    Keys are never predefined: if the service account has no active key, a
    new one is created, either with the hash configured via
    `TRADELE_SERVICE_API_KEY_HASH` (the key value is then only known to
    whoever configured it) or with a generated value that is printed to the
    console - shown only once. Keys are named after a predefined name plus
    the creation time, so keys from multiple bootstrap runs (which
    shouldn't happen) stay distinguishable. Existing keys are never
    modified or reprinted.
    """

    def __init__(
        self,
        user_service: UserService,
        api_key_service: ApiKeyService,
        settings: SettingsService,
        logger: logging.Logger,
    ) -> None:
        self._user_service: UserService = user_service
        self._api_key_service: ApiKeyService = api_key_service
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def ensure_exists(self) -> str | None:
        """Create the service account and an active key for it if missing.

        Returns the full `Authorization` header value if a key value was
        generated - this is the only time it is available. Returns None if
        the service account already had an active key, or the new key was
        created from a configured hash.
        """
        self._user_service.ensure_service_account_exists()

        if any(
            key.deactivated_at is None
            for key in self._api_key_service.list_keys(UserService.SERVICE_ACCOUNT_ID)
        ):
            return None

        name = self._service_account_key_name()
        api_key, secret = self._api_key_service.create_key(
            UserService.SERVICE_ACCOUNT_ID,
            name,
            key_hash=self._settings.service_api_key_hash or None,
        )
        if secret is None:
            self._logger.info(
                "Created service account API key %s (%s) from TRADELE_SERVICE_API_KEY_HASH",
                api_key.id,
                name,
            )
            return None

        authorization = self._api_key_service.format_authorization_header(api_key.id, secret)
        self._logger.warning(
            "Generated service account API key %s (%s), shown once - store it securely and use it as the `Authorization` header value: %s",
            api_key.id,
            name,
            authorization,
        )
        return authorization

    @staticmethod
    def _service_account_key_name() -> str:
        """Predefined name plus creation time, so keys created by multiple
        bootstrap runs (which shouldn't happen) stay distinguishable."""
        return f"{SERVICE_ACCOUNT_KEY_NAME} ({datetime.now(UTC).isoformat()})"
