import hashlib

import pytest

from app.container import container
from app.services.api_key_service import (
    ApiKeyService,
    AuthenticatingKeyDeactivationError,
)


def test_create_key_returns_working_secret():
    user_id = container.users.create()

    api_key, secret = container.api_keys.create_key(user_id, "test key")

    assert api_key.user_id == user_id
    assert api_key.deactivated_at is None
    assert api_key.created_by_key is None
    # Prefixes are cosmetic - the values themselves are arbitrary strings.
    assert api_key.id.startswith("key_")
    assert secret is not None
    assert secret.startswith("secret_")

    authenticated = container.api_keys.authenticate(api_key.id, secret)
    assert authenticated is not None
    assert authenticated.id == api_key.id


def test_create_key_records_creating_key():
    user_id = container.users.create()

    api_key, _ = container.api_keys.create_key(user_id, "test key", created_by_key="parent-key")

    assert api_key.created_by_key == "parent-key"


def test_create_key_with_configured_hash_generates_no_secret():
    user_id = container.users.create()
    key_hash = hashlib.sha256(b"operator-chosen-secret").hexdigest()

    api_key, secret = container.api_keys.create_key(user_id, "test key", key_hash=key_hash)

    assert secret is None
    assert api_key.key_hash == key_hash
    assert container.api_keys.authenticate(api_key.id, "operator-chosen-secret") is not None


def test_format_authorization_header_roundtrips():
    header = ApiKeyService.format_authorization_header("some key id", "some:secret")

    assert header.startswith("Basic ")
    assert container.api_keys.authenticate("some key id", "some:secret") is None  # unknown key
    # But the header decodes back to the exact arbitrary-string parts.
    import base64

    username, _, password = base64.b64decode(header[len("Basic ") :]).decode().partition(":")
    assert base64.b64decode(username).decode() == "some key id"
    assert base64.b64decode(password).decode() == "some:secret"


def test_authenticate_rejects_wrong_secret():
    user_id = container.users.create()
    api_key, _ = container.api_keys.create_key(user_id, "test key")

    assert container.api_keys.authenticate(api_key.id, "not-the-secret") is None


def test_authenticate_rejects_unknown_key_id():
    assert container.api_keys.authenticate("does-not-exist", "secret") is None


def test_authenticate_rejects_deactivated_key():
    user_id = container.users.create()
    api_key, secret = container.api_keys.create_key(user_id, "test key")
    spare, _ = container.api_keys.create_key(user_id, "spare key")

    container.api_keys.deactivate_key(
        user_id, api_key.id, authenticating_key_id=spare.id
    )

    assert container.api_keys.authenticate(api_key.id, secret) is None


def test_deactivate_key_updates_record():
    user_id = container.users.create()
    first, _ = container.api_keys.create_key(user_id, "first")
    second, _ = container.api_keys.create_key(user_id, "second")

    deactivated = container.api_keys.deactivate_key(
        user_id, first.id, authenticating_key_id=second.id
    )

    assert deactivated is not None
    assert deactivated.id == first.id
    assert deactivated.deactivated_at is not None
    assert container.api_keys.list_keys(user_id)[0].deactivated_at is not None


def test_deactivate_key_is_idempotent():
    user_id = container.users.create()
    first, _ = container.api_keys.create_key(user_id, "first")
    second, _ = container.api_keys.create_key(user_id, "second")
    container.api_keys.deactivate_key(user_id, first.id, authenticating_key_id=second.id)

    deactivated_again = container.api_keys.deactivate_key(
        user_id, first.id, authenticating_key_id=second.id
    )

    assert deactivated_again is not None
    assert deactivated_again.deactivated_at is not None


def test_deactivate_unknown_or_foreign_key_returns_none():
    user_id = container.users.create()
    other_id = container.users.create()
    foreign_key, _ = container.api_keys.create_key(other_id, "foreign")

    assert (
        container.api_keys.deactivate_key(
            user_id, "does-not-exist", authenticating_key_id=foreign_key.id
        )
        is None
    )
    assert (
        container.api_keys.deactivate_key(
            user_id, foreign_key.id, authenticating_key_id=foreign_key.id
        )
        is None
    )


def test_deactivate_authenticating_key_is_refused():
    user_id = container.users.create()
    first, _ = container.api_keys.create_key(user_id, "first")
    second, _ = container.api_keys.create_key(user_id, "second")

    with pytest.raises(AuthenticatingKeyDeactivationError):
        container.api_keys.deactivate_key(user_id, first.id, authenticating_key_id=first.id)

    # Still active after the refused deactivation...
    assert container.api_keys.get_key(first.id).deactivated_at is None
    # ...but can be deactivated when authenticated with another key.
    deactivated = container.api_keys.deactivate_key(
        user_id, first.id, authenticating_key_id=second.id
    )
    assert deactivated is not None
    assert deactivated.deactivated_at is not None
