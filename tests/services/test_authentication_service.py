import pytest

from app.auth_context import SCOPE_SERVICE_ACCESS
from app.container import container
from app.services.authentication_service import ForbiddenError, UnauthorizedError
from app.services.user_service import UserService


def test_authenticate_token_for_regular_user():
    user_id = container.users.create()
    token = container.auth.create_access_token(user_id)

    context = container.authentication.authenticate_token(token)

    assert context.user_id == user_id
    assert context.method == "token"
    assert context.scopes == frozenset()
    assert context.api_key_id is None


def test_authenticate_api_key_for_regular_user_has_no_service_scope():
    user_id = container.users.create()
    api_key, secret = container.api_keys.create_key(user_id, "test key")

    context = container.authentication.authenticate_api_key(api_key.id, secret)

    assert context.user_id == user_id
    assert context.method == "api_key"
    assert context.api_key_id == api_key.id
    assert SCOPE_SERVICE_ACCESS not in context.scopes


def test_authenticate_api_key_for_service_account_grants_service_scope(
    decode_basic_authorization,
):
    authorization = container.service_account_creator.ensure_exists()
    assert authorization is not None
    key_id, secret = decode_basic_authorization(authorization)

    context = container.authentication.authenticate_api_key(key_id, secret)

    assert context.user_id == UserService.SERVICE_ACCOUNT_ID
    assert context.method == "api_key"
    assert context.api_key_id == key_id
    assert SCOPE_SERVICE_ACCESS in context.scopes


def test_authenticate_token_for_service_account_is_refused():
    container.service_account_creator.ensure_exists()
    token = container.auth.create_access_token(UserService.SERVICE_ACCOUNT_ID)

    with pytest.raises(ForbiddenError):
        container.authentication.authenticate_token(token)


def test_authenticate_invalid_token_is_refused():
    with pytest.raises(UnauthorizedError):
        container.authentication.authenticate_token("not-a-jwt")


def test_authenticate_token_for_unknown_user_is_refused():
    token = container.auth.create_access_token("does-not-exist")

    with pytest.raises(UnauthorizedError):
        container.authentication.authenticate_token(token)


def test_authenticate_invalid_api_key_is_refused():
    container.service_account_creator.ensure_exists()
    key_id = next(
        key.id
        for key in container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID)
        if key.deactivated_at is None
    )

    with pytest.raises(UnauthorizedError):
        container.authentication.authenticate_api_key(key_id, "wrong-secret")


def test_authenticate_unknown_api_key_is_refused():
    with pytest.raises(UnauthorizedError):
        container.authentication.authenticate_api_key("does-not-exist", "secret")
