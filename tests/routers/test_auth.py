from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_issue_token_for_existing_user():
    user_id = container.users.create()

    response = client.post("/api/auth/token", json={"user_id": user_id})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    payload = container.auth.decode_access_token(body["access_token"])
    assert payload["sub"] == user_id


def test_issue_token_for_unknown_user_returns_404():
    response = client.post("/api/auth/token", json={"user_id": "does-not-exist"})

    assert response.status_code == 404


def test_issue_token_for_service_account_returns_403():
    from app.services.user_service import UserService

    container.users.ensure_service_account_exists()

    response = client.post("/api/auth/token", json={"user_id": UserService.SERVICE_ACCOUNT_ID})

    assert response.status_code == 403
