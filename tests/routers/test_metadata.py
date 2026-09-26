from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


@pytest.fixture
def game_started_today(monkeypatch: pytest.MonkeyPatch):
    """Start the game "today" (UTC), so the current day number is 0."""
    monkeypatch.setenv(
        "TRADELE_FIRST_DAY_OF_GAME", datetime.now(UTC).date().isoformat()
    )
    container.reset()
    container.database.run_migrations()


def test_get_metadata_returns_day_number_and_time_until_day_end(game_started_today):
    user_id = container.users.create()

    response = client.get("/api/metadata", headers=_headers(user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["day_number"] == 0
    assert 0 <= body["seconds_until_day_end"] < 24 * 60 * 60
    assert body["has_completed_tutorial"] is False


def test_get_metadata_counts_days_since_the_first_day(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRADELE_FIRST_DAY_OF_GAME", "2024-01-01")
    container.reset()
    container.database.run_migrations()
    user_id = container.users.create()

    response = client.get("/api/metadata", headers=_headers(user_id))

    assert response.status_code == 200
    expected_days = (
        datetime.now(UTC) - container.settings.first_day_of_game
    ).days
    assert response.json()["day_number"] == expected_days


def test_get_metadata_requires_authentication():
    response = client.get("/api/metadata")

    assert response.status_code == 401


def test_complete_tutorial_marks_tutorial_completed():
    user_id = container.users.create()
    headers = _headers(user_id)

    response = client.post("/api/metadata/complete-tutorial", headers=headers)

    assert response.status_code == 200
    body = client.get("/api/metadata", headers=headers).json()
    assert body["has_completed_tutorial"] is True


def test_complete_tutorial_is_idempotent():
    user_id = container.users.create()
    headers = _headers(user_id)

    for _ in range(2):
        assert client.post("/api/metadata/complete-tutorial", headers=headers).status_code == 200

    body = client.get("/api/metadata", headers=headers).json()
    assert body["has_completed_tutorial"] is True


def test_complete_tutorial_requires_authentication():
    response = client.post("/api/metadata/complete-tutorial")

    assert response.status_code == 401


def test_tutorial_state_is_tracked_per_user():
    first = container.users.create()
    second = container.users.create()

    client.post("/api/metadata/complete-tutorial", headers=_headers(first))

    assert client.get("/api/metadata", headers=_headers(first)).json()["has_completed_tutorial"] is True
    assert client.get("/api/metadata", headers=_headers(second)).json()["has_completed_tutorial"] is False


def _headers(user_id: str) -> dict[str, str]:
    token = container.auth.create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}
