from collections.abc import Callable
from pathlib import Path

import base64

import pytest


@pytest.fixture(autouse=True)
def isolated_runtime_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the database, JWT signing keys, and logs at a per-test temp dir.

    This keeps tests from touching (or depending on) real dev runtime data,
    and ensures each test starts from a clean schema.
    """
    monkeypatch.setenv("TRADELE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("TRADELE_KEYS_DIR", str(tmp_path / "keys"))
    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("TRADELE_FRONTEND_DIST", str(tmp_path / "frontend-dist"))

    from app.container import container

    container.reset()
    container.database.run_migrations()


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    """Return a factory for `Authorization` headers carrying a valid access
    token for the given user ID, for use against endpoints protected by
    `AuthContextDep`.
    """

    def _auth_headers(user_id: str) -> dict[str, str]:
        from app.container import container

        token = container.auth.create_access_token(user_id)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def service_auth_headers() -> dict[str, str]:
    """Ensure the service account and its auto-created API key exist, then
    return `Authorization` headers authenticating with that key.
    """
    from app.container import container

    authorization = container.service_account_creator.ensure_exists()
    assert authorization is not None, "Service account key should have been generated"
    return {"Authorization": authorization}


@pytest.fixture
def decode_basic_authorization() -> Callable[[str], tuple[str, str]]:
    """Return a function decoding a Basic `Authorization` header value into
    its `(key_id, secret)` parts (the inverse of
    `ApiKeyService.format_authorization_header`).
    """

    def _decode(authorization: str) -> tuple[str, str]:
        assert authorization.startswith("Basic ")
        username, _, password = base64.b64decode(authorization[len("Basic ") :]).decode().partition(
            ":"
        )
        return base64.b64decode(username).decode(), base64.b64decode(password).decode()

    return _decode
