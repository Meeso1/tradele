from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_create_user_returns_a_persisted_id():
    response = client.post("/users")

    assert response.status_code == 201
    user_id = response.json()["id"]
    assert user_id
    assert container.users.exists(user_id)
