import jwt
import pytest

from app.container import container


def test_create_access_token_round_trips_user_id():
    token = container.auth.create_access_token("some-user-id")

    payload = container.auth.decode_access_token(token)

    assert payload["sub"] == "some-user-id"
    assert payload["iss"] == "tradele"


def test_decode_access_token_rejects_tampered_token():
    token = container.auth.create_access_token("some-user-id")

    with pytest.raises(jwt.InvalidTokenError):
        container.auth.decode_access_token(token + "tampered")
