"""Issuing and verifying JWTs that assert a user's identity.

Tokens are signed with RS256 using a key pair generated (and cached to disk)
on first use. `iss` is set to identify these as tokens minted by this
backend, as opposed to tokens that might later be issued by a third-party
identity provider (e.g. Auth0), so verification can branch on it if needed.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.settings_service import SettingsService


class AuthService:
    ALGORITHM: str = "RS256"
    ISSUER: str = "tradele"
    ACCESS_TOKEN_TTL_SECONDS: int = 60 * 60 * 24  # 1 day

    def __init__(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger
        self._private_key: bytes | None = None
        self._public_key: bytes | None = None

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        """Point this service at (possibly new) settings/logger.

        Clears any cached key material so it's reloaded (or regenerated)
        from the new settings' `keys_dir` on next use.
        """
        self._settings = settings
        self._logger = logger
        self._private_key = None
        self._public_key = None

    def _generate_key_pair(self) -> tuple[bytes, bytes]:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return private_pem, public_pem

    def _keys(self) -> tuple[bytes, bytes]:
        """Return the signing key pair, loading or generating it if needed."""
        if self._private_key is not None and self._public_key is not None:
            return self._private_key, self._public_key

        keys_dir = self._settings.keys_dir
        private_key_path = keys_dir / "jwt_private_key.pem"
        public_key_path = keys_dir / "jwt_public_key.pem"

        if private_key_path.exists() and public_key_path.exists():
            self._logger.debug("Loading JWT signing key pair from %s", keys_dir)
            private_pem = private_key_path.read_bytes()
            public_pem = public_key_path.read_bytes()
        else:
            self._logger.info("Generating new JWT signing key pair in %s", keys_dir)
            private_pem, public_pem = self._generate_key_pair()
            keys_dir.mkdir(parents=True, exist_ok=True)
            private_key_path.write_bytes(private_pem)
            public_key_path.write_bytes(public_pem)

        self._private_key, self._public_key = private_pem, public_pem
        return private_pem, public_pem

    def create_access_token(self, user_id: str) -> str:
        """Issue a signed JWT asserting the given user ID as `sub`.

        This performs no authentication of its own - callers are
        responsible for deciding whether `user_id` should be trusted before
        calling this.
        """
        private_key, _ = self._keys()
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": user_id,
            "iss": self.ISSUER,
            "iat": now,
            "exp": now + self.ACCESS_TOKEN_TTL_SECONDS,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, private_key, algorithm=self.ALGORITHM)
        self._logger.info("Issued access token for user %s", user_id)
        return token

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Verify a token's signature/claims and return its payload."""
        _, public_key = self._keys()
        try:
            payload: dict[str, Any] = jwt.decode(
                token, public_key, algorithms=[self.ALGORITHM], issuer=self.ISSUER
            )
        except jwt.InvalidTokenError:
            self._logger.warning("Rejected invalid access token")
            raise
        self._logger.debug("Decoded access token for user %s", payload.get("sub"))
        return payload
