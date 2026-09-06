import hashlib

import pytest

from app.container import container
from app.services.service_account_creator import SERVICE_ACCOUNT_KEY_NAME
from app.services.user_service import UserService


def test_ensure_creates_account_and_key(decode_basic_authorization):
    authorization = container.service_account_creator.ensure_exists()

    assert authorization is not None
    assert container.users.exists(UserService.SERVICE_ACCOUNT_ID)

    key_id, secret = decode_basic_authorization(authorization)
    authenticated = container.api_keys.authenticate(key_id, secret)
    assert authenticated is not None
    assert authenticated.user_id == UserService.SERVICE_ACCOUNT_ID
    # The bootstrapped key wasn't created via the API, so it has no creator.
    assert authenticated.created_by_key is None
    # The key name is the predefined one plus a creation timestamp.
    assert authenticated.name.startswith(SERVICE_ACCOUNT_KEY_NAME)

    # A second call must not create (or reprint) another key.
    assert container.service_account_creator.ensure_exists() is None


def test_ensure_uses_configured_hash(monkeypatch: pytest.MonkeyPatch):
    secret = "operator-chosen-secret"
    monkeypatch.setenv(
        "TRADELE_SERVICE_API_KEY_HASH", hashlib.sha256(secret.encode()).hexdigest()
    )
    container.reset()

    authorization = container.service_account_creator.ensure_exists()

    assert authorization is None
    keys = container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID)
    assert len(keys) == 1
    authenticated = container.api_keys.authenticate(keys[0].id, secret)
    assert authenticated is not None
    assert authenticated.user_id == UserService.SERVICE_ACCOUNT_ID


def test_ensure_does_not_modify_an_existing_key(monkeypatch: pytest.MonkeyPatch):
    container.service_account_creator.ensure_exists()
    original = container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID)[0]

    monkeypatch.setenv("TRADELE_SERVICE_API_KEY_HASH", hashlib.sha256(b"never-used").hexdigest())
    container.reset()
    assert container.service_account_creator.ensure_exists() is None

    assert container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID) == [original]


def test_ensure_creates_a_new_key_when_none_is_active(decode_basic_authorization):
    authorization = container.service_account_creator.ensure_exists()
    assert authorization is not None
    key_id, _ = decode_basic_authorization(authorization)
    container.api_keys.deactivate_key(
        UserService.SERVICE_ACCOUNT_ID, key_id, authenticating_key_id=None
    )

    second = container.service_account_creator.ensure_exists()

    assert second is not None
    keys = container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID)
    assert len(keys) == 2
    # Names share the predefined prefix but are distinguishable.
    assert keys[0].name != keys[1].name
    assert all(key.name.startswith(SERVICE_ACCOUNT_KEY_NAME) for key in keys)
