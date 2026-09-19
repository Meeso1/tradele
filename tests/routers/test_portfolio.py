from collections.abc import Callable
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.models.market import HourlyDate
from app.models.portfolio import HistoricalPortfolio
from app.repositories.portfolio_repository import STARTING_CASH

client = TestClient(app)


def _record_state(user_id: str, hour: HourlyDate, total_value: float) -> None:
    container.portfolio_repository.try_record_state(
        user_id,
        HistoricalPortfolio(
            cash=100.0,
            holdings={"AAPL": 1.0},
            timestamp=hour,
            total_value=total_value,
            recorded_at=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        ),
    )


def test_get_portfolio_creates_a_default_portfolio_for_a_new_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.get("/api/portfolio", headers=auth_headers(user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["cash"] == STARTING_CASH
    assert body["holdings"] == {symbol: 0 for symbol in container.settings.tradable_symbols}


def test_get_portfolio_rejects_a_token_for_an_unknown_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    # The auth layer resolves the user (for per-user auth method checks), so
    # an unknown user is rejected there with 401, before the route's 404.
    response = client.get("/api/portfolio", headers=auth_headers("does-not-exist"))

    assert response.status_code == 401


def test_get_portfolio_requires_authentication():
    response = client.get("/api/portfolio")

    assert response.status_code == 401


def test_get_portfolio_history_returns_recorded_states(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    hour = HourlyDate(day=date(2024, 1, 1), hour=10)
    _record_state(user_id, hour, total_value=110.0)

    response = client.get("/api/portfolio/history", headers=auth_headers(user_id))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["cash"] == 100.0
    assert body[0]["holdings"] == {"AAPL": 1.0}
    assert body[0]["timestamp"] == {"day": "2024-01-01", "hour": 10}
    assert body[0]["total_value"] == 110.0
    assert body[0]["recorded_at"].startswith("2024-01-01T11:00")


def test_get_portfolio_history_filters_by_timestamp_range(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    first_day = HourlyDate(day=date(2024, 1, 1), hour=10)
    second_day = HourlyDate(day=date(2024, 1, 2), hour=10)
    _record_state(user_id, first_day, total_value=110.0)
    _record_state(user_id, second_day, total_value=120.0)

    response = client.get(
        "/api/portfolio/history",
        params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-01T23:59:59Z"},
        headers=auth_headers(user_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert [state["total_value"] for state in body] == [110.0]


def test_get_portfolio_history_rounds_timestamps_down_to_the_hour(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    hour = HourlyDate(day=date(2024, 1, 1), hour=10)
    _record_state(user_id, hour, total_value=110.0)

    response = client.get(
        "/api/portfolio/history",
        params={"start": "2024-01-01T10:30:00Z", "end": "2024-01-01T10:59:59Z"},
        headers=auth_headers(user_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert [state["timestamp"] for state in body] == [{"day": "2024-01-01", "hour": 10}]


def test_get_portfolio_history_returns_empty_list_when_nothing_is_recorded(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.get("/api/portfolio/history", headers=auth_headers(user_id))

    assert response.status_code == 200
    assert response.json() == []


def test_get_portfolio_history_requires_authentication():
    response = client.get("/api/portfolio/history")

    assert response.status_code == 401
