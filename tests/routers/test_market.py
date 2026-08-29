from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.models.market import HourlyDate, HourlyPriceData

client = TestClient(app)


def test_get_symbols_returns_the_tradable_symbols(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.get("/market/symbols", headers=auth_headers(user_id))

    assert response.status_code == 200
    assert response.json() == container.settings.tradable_symbols


def test_get_prices_returns_a_price_for_every_symbol(
    auth_headers: Callable[[str], dict[str, str]], monkeypatch: pytest.MonkeyPatch
):
    user_id = container.users.create()
    hour = HourlyDate(day=date(2024, 1, 1), hour=10)

    def _get_hourly_bars(symbols, start, end):
        return {
            symbol: [
                HourlyPriceData(
                    symbol=symbol, open=1.0, high=2.0, low=0.5, close=1.5, starting_hour=hour
                )
            ]
            for symbol in symbols
        }

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)

    response = client.get("/market/prices", headers=auth_headers(user_id))

    assert response.status_code == 200
    prices = response.json()["prices"]
    assert set(prices.keys()) == set(container.settings.tradable_symbols)


def test_get_symbols_requires_authentication():
    response = client.get("/market/symbols")

    assert response.status_code == 401


def test_get_prices_requires_authentication():
    response = client.get("/market/prices")

    assert response.status_code == 401
