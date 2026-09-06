"""Authenticates request credentials and resolves the caller's `AuthContext`.

Two credential types are accepted:

- JWT access tokens minted by `/auth/token` (via `AuthService`) - these
  assert a user ID but don't prove identity.
- API keys, presented via HTTP Basic auth and already decoded into their
  `key_id`/`secret` parts by the caller (see `app.dependencies`; the parts
  are arbitrary strings, verified via `ApiKeyService`).

Both are resolved to a user, which is then checked against its list of
allowed auth methods (e.g. the service account may never log in via
`/auth/token`). Scopes are assigned based on identity *and* method: the
service access scope is only granted to the service account authenticating
with its API key, so a token minted for it (were that ever allowed) would
carry no scopes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import jwt

from app.auth_context import (
    AUTH_METHOD_API_KEY,
    AUTH_METHOD_TOKEN,
    SCOPE_SERVICE_ACCESS,
    AuthContext,
    AuthMethod,
)
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.user_service import UserService


class UnauthorizedError(Exception):
    """The presented credentials are invalid (unknown, malformed, or expired)."""


class ForbiddenError(Exception):
    """The credentials are valid, but the request is not allowed."""


@dataclass
class CredentialMetadata:
    """Who a validated credential belongs to, and how it was presented."""

    user_id: str
    method: AuthMethod
    api_key_id: str | None = None


class AuthenticationService:
    def __init__(
        self,
        auth_service: AuthService,
        api_key_service: ApiKeyService,
        user_service: UserService,
        logger: logging.Logger,
    ) -> None:
        self._auth_service: AuthService = auth_service
        self._api_key_service: ApiKeyService = api_key_service
        self._user_service: UserService = user_service
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def authenticate_token(self, token: str) -> AuthContext:
        """Verify a JWT access token and build the caller's auth context."""
        return self._build_context(self._validate_token(token))

    def authenticate_api_key(self, key_id: str, secret: str) -> AuthContext:
        """Verify an API key and build the caller's auth context."""
        return self._build_context(self._validate_api_key(key_id, secret))

    def _validate_token(self, token: str) -> CredentialMetadata:
        try:
            payload = self._auth_service.decode_access_token(token)
        except jwt.InvalidTokenError as error:
            raise UnauthorizedError("Invalid or expired access token") from error
        return CredentialMetadata(
            user_id=self._token_subject(payload), method=AUTH_METHOD_TOKEN
        )

    def _validate_api_key(self, key_id: str, secret: str) -> CredentialMetadata:
        api_key = self._api_key_service.authenticate(key_id, secret)
        if api_key is None:
            raise UnauthorizedError("Invalid API key")
        return CredentialMetadata(
            user_id=api_key.user_id, method=AUTH_METHOD_API_KEY, api_key_id=api_key.id
        )

    def _build_context(self, metadata: CredentialMetadata) -> AuthContext:
        user_info = self._user_service.get_user_info(metadata.user_id)
        if user_info is None:
            raise UnauthorizedError(f"Unknown user: {metadata.user_id}")

        if metadata.method not in user_info.allowed_auth_methods:
            raise ForbiddenError(
                f"Auth method {metadata.method!r} is not allowed for user {metadata.user_id}"
            )

        return AuthContext(
            user_id=metadata.user_id,
            method=metadata.method,
            scopes=self._resolve_scopes(metadata.method, user_info.is_service_account),
            api_key_id=metadata.api_key_id,
        )

    def _resolve_scopes(self, method: AuthMethod, is_service_account: bool) -> frozenset[str]:
        if is_service_account and method == AUTH_METHOD_API_KEY:
            return frozenset({SCOPE_SERVICE_ACCESS})
        return frozenset()

    @staticmethod
    def _token_subject(payload: dict[str, Any]) -> str:
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise UnauthorizedError("Access token has no valid subject")
        return user_id
