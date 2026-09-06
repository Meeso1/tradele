import base64
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.services.user_service import UserService

client = TestClient(app)


def _active_service_key_id() -> str:
    """Return the ID of the service account's active (bootstrapped) key."""
    return next(
        key.id
        for key in container.api_keys.list_keys(UserService.SERVICE_ACCOUNT_ID)
        if key.deactivated_at is None
    )


def test_api_key_routes_require_authentication():
    assert client.post("/api-keys", json={"name": "key"}).status_code == 401
    assert client.get("/api-keys").status_code == 401
    assert client.post("/api-keys/some-id/deactivate").status_code == 401


def test_malformed_basic_credentials_return_401():
    garbage = base64.b64encode(b"not-base64-of-two-parts").decode()
    response = client.get("/api-keys", headers={"Authorization": f"Basic {garbage}"})

    assert response.status_code == 401


def test_unsupported_authorization_scheme_returns_401():
    response = client.get("/api-keys", headers={"Authorization": "Digest something"})

    assert response.status_code == 401


def test_api_key_routes_reject_regular_user_token(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.get("/api-keys", headers=auth_headers(user_id))

    assert response.status_code == 403


def test_api_key_routes_reject_service_account_token():
    container.service_account_creator.ensure_exists()
    token = container.auth.create_access_token(UserService.SERVICE_ACCOUNT_ID)

    response = client.get("/api-keys", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_create_and_use_api_key(service_auth_headers: dict[str, str]):
    response = client.post("/api-keys", json={"name": "worker key"}, headers=service_auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "worker key"
    assert body["id"].startswith("key_")
    assert body["secret"].startswith("secret_")
    assert body["authorization"].startswith("Basic ")
    assert body["created_by_key"] == _active_service_key_id()

    # The new key authenticates against a protected endpoint.
    portfolio = client.get(
        "/portfolio", headers={"Authorization": body["authorization"]}
    )
    assert portfolio.status_code == 200


def test_list_api_keys_hides_key_values(service_auth_headers: dict[str, str]):
    client.post("/api-keys", json={"name": "key"}, headers=service_auth_headers)

    response = client.get("/api-keys", headers=service_auth_headers)

    assert response.status_code == 200
    keys = response.json()
    assert len(keys) >= 1
    assert all(
        "secret" not in key and "authorization" not in key and "key_hash" not in key
        for key in keys
    )
    # The bootstrapped key has no creator; manually created ones do.
    bootstrapped = [key for key in keys if key["created_by_key"] is None]
    assert len(bootstrapped) == 1


def test_deactivate_api_key(service_auth_headers: dict[str, str]):
    created = client.post(
        "/api-keys", json={"name": "key"}, headers=service_auth_headers
    ).json()
    response = client.post(
        f"/api-keys/{created['id']}/deactivate", headers=service_auth_headers
    )

    assert response.status_code == 200
    assert response.json()["deactivated_at"] is not None

    # The deactivated key no longer authenticates.
    rejected = client.get(
        "/portfolio", headers={"Authorization": created["authorization"]}
    )
    assert rejected.status_code == 401


def test_deactivate_unknown_api_key_returns_404(service_auth_headers: dict[str, str]):
    response = client.post(
        "/api-keys/does-not-exist/deactivate", headers=service_auth_headers
    )

    assert response.status_code == 404


def test_deactivate_authenticating_key_returns_409(service_auth_headers: dict[str, str]):
    response = client.post(
        f"/api-keys/{_active_service_key_id()}/deactivate",
        headers=service_auth_headers,
    )

    assert response.status_code == 409
