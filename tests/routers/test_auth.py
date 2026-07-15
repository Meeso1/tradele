from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_issue_token_for_existing_user():
    user_id = container.users.create()

    response = client.post("/auth/token", json={"user_id": user_id})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    payload = container.auth.decode_access_token(body["access_token"])
    assert payload["sub"] == user_id


def test_issue_token_for_unknown_user_returns_404():
    response = client.post("/auth/token", json={"user_id": "does-not-exist"})

    assert response.status_code == 404
