from datetime import date, datetime

import pytest

from app.container import container
from app.models.market import HourlyDate, HourlyPriceData

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)


def test_get_prices_returns_a_price_for_every_symbol_with_bars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL", "MSFT"])
    bars = {
        "AAPL": [
            HourlyPriceData(symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR)
        ],
        "MSFT": [
            HourlyPriceData(symbol="MSFT", open=420.0, high=425.0, low=415.0, close=422.0, starting_hour=HOUR)
        ],
    }
    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", lambda symbols, start, end: bars)

    market_state = container.market_data.get_prices_for_hour(HOUR)

    assert set(market_state.prices.keys()) == {"AAPL", "MSFT"}
    assert all(price_data.close > 0 for price_data in market_state.prices.values())


def test_get_prices_omits_symbols_with_no_bars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL", "DELISTED"])
    bars = {
        "AAPL": [
            HourlyPriceData(symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR)
        ],
        "DELISTED": [],
    }
    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", lambda symbols, start, end: bars)

    market_state = container.market_data.get_prices_for_hour(HOUR)

    assert set(market_state.prices.keys()) == {"AAPL"}


def test_get_prices_queries_the_alpaca_client_for_the_hour_window(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    captured: dict[str, object] = {}

    def _get_hourly_bars(symbols, start, end):
        captured["symbols"] = list(symbols)
        captured["start"] = start
        captured["end"] = end
        return {}

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)

    container.market_data.get_prices_for_hour(HOUR)

    assert captured["symbols"] == ["AAPL"]
    assert captured["start"] == HOUR
    assert captured["end"] == HourlyDate.next(HOUR)


def test_get_prices_uses_the_cache_instead_of_refetching_an_already_fetched_hour(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL", "DELISTED"])
    bars = {
        "AAPL": [
            HourlyPriceData(symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR)
        ],
        "DELISTED": [],
    }
    call_count = 0

    def _get_hourly_bars(symbols, start, end):
        nonlocal call_count
        call_count += 1
        return bars

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)

    first = container.market_data.get_prices_for_hour(HOUR)
    second = container.market_data.get_prices_for_hour(HOUR)

    assert call_count == 1
    assert set(first.prices.keys()) == {"AAPL"}
    assert first.prices == second.prices


def test_get_prices_only_fetches_symbols_missing_from_the_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL", "MSFT"])
    container.market_data_repository.cache_hour(
        HOUR,
        {
            "AAPL": HourlyPriceData(
                symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
            )
        },
    )
    captured: dict[str, object] = {}

    def _get_hourly_bars(symbols, start, end):
        captured["symbols"] = list(symbols)
        return {
            "MSFT": [
                HourlyPriceData(
                    symbol="MSFT", open=420.0, high=425.0, low=415.0, close=422.0, starting_hour=HOUR
                )
            ]
        }

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)

    market_state = container.market_data.get_prices_for_hour(HOUR)

    assert captured["symbols"] == ["MSFT"]
    assert set(market_state.prices.keys()) == {"AAPL", "MSFT"}


def test_hourly_date_containing_extracts_day_and_hour():
    hourly_date = HourlyDate.containing(datetime(2024, 1, 1, 10, 30))

    assert hourly_date.day == date(2024, 1, 1)
    assert hourly_date.hour == 10
