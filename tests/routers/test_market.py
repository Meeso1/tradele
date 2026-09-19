from collections.abc import Callable
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.models.market import HourlyDate, HourlyPriceData

client = TestClient(app)

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)


def _mock_bars_for_requested_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Alpaca to return one bar per symbol, stamped at the requested start."""

    def _get_hourly_bars(symbols, start, end):
        return {
            symbol: [
                HourlyPriceData(
                    symbol=symbol, open=1.0, high=2.0, low=0.5, close=1.5, starting_hour=start
                )
            ]
            for symbol in symbols
        }

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)


def test_get_symbols_returns_the_tradable_symbols(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.get("/api/market/symbols", headers=auth_headers(user_id))

    assert response.status_code == 200
    assert response.json() == container.settings.tradable_symbols


def test_get_prices_defaults_to_the_current_hour(
    auth_headers: Callable[[str], dict[str, str]], monkeypatch: pytest.MonkeyPatch
):
    user_id = container.users.create()
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    _mock_bars_for_requested_start(monkeypatch)

    response = client.get("/api/market/prices", headers=auth_headers(user_id))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["hour"]["day"] == HourlyDate.last_passed_hour().day.isoformat()
    assert body[0]["hour"]["hour"] == HourlyDate.last_passed_hour().hour
    assert set(body[0]["prices"].keys()) == {"AAPL"}
    assert body[0]["market_open"] is True


def test_get_prices_returns_one_state_per_hour_in_the_timestamp_range(
    auth_headers: Callable[[str], dict[str, str]], monkeypatch: pytest.MonkeyPatch
):
    user_id = container.users.create()
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    _mock_bars_for_requested_start(monkeypatch)

    response = client.get(
        "/api/market/prices",
        params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-01T23:00:00Z"},
        headers=auth_headers(user_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 24
    hour_with_prices = next(state for state in body if state["hour"]["hour"] == 0)
    assert hour_with_prices["hour"] == {"day": "2024-01-01", "hour": 0}
    assert set(hour_with_prices["prices"].keys()) == {"AAPL"}


def test_get_prices_rounds_timestamps_down_to_the_hour(
    auth_headers: Callable[[str], dict[str, str]], monkeypatch: pytest.MonkeyPatch
):
    user_id = container.users.create()
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    _mock_bars_for_requested_start(monkeypatch)

    response = client.get(
        "/api/market/prices",
        params={"start": "2024-01-01T10:30:00Z", "end": "2024-01-01T10:59:59Z"},
        headers=auth_headers(user_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["hour"] == {"day": "2024-01-01", "hour": 10}


@pytest.mark.parametrize(
    ("range_value", "expected_hours"),
    [
        ("current_hour", 1),
        ("day", 24),
        ("week", 24 * 7),
        ("month", 24 * 30),
        ("year", 24 * 365),
    ],
)
def test_get_prices_range_shortcuts_have_a_fixed_length(
    auth_headers: Callable[[str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    range_value: str,
    expected_hours: int,
):
    user_id = container.users.create()
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    _mock_bars_for_requested_start(monkeypatch)

    response = client.get(
        "/api/market/prices", params={"range": range_value}, headers=auth_headers(user_id)
    )

    assert response.status_code == 200
    body = response.json()
    last_passed = HourlyDate.last_passed_hour()
    assert len(body) == expected_hours
    assert body[-1]["hour"] == {"day": last_passed.day.isoformat(), "hour": last_passed.hour}
    assert body[0]["hour"] == {
        "day": (last_passed - timedelta(hours=expected_hours - 1)).day.isoformat(),
        "hour": (last_passed - timedelta(hours=expected_hours - 1)).hour,
    }


def test_get_prices_rejects_range_combined_with_start_or_end(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.get(
        "/api/market/prices",
        params={"range": "day", "start": "2024-01-01T00:00:00Z"},
        headers=auth_headers(user_id),
    )

    assert response.status_code == 400


def test_get_symbols_requires_authentication():
    response = client.get("/api/market/symbols")

    assert response.status_code == 401


def test_get_prices_requires_authentication():
    response = client.get("/api/market/prices")

    assert response.status_code == 401
