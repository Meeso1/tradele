from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date

import httpx
import pytest

from app.models.market import HourlyDate
from app.services.alpaca_market_data_client import (
    AlpacaApiError,
    AlpacaAuthenticationError,
    AlpacaMarketDataClient,
    AlpacaRateLimitError,
    AlpacaValidationError,
)
from app.services.settings_service import SettingsService

START = HourlyDate(day=date(2024, 1, 1), hour=10)
END = HourlyDate.next(START)

# Captured before any test monkeypatches `httpx.Client`, so the fake
# constructor below always builds a real `httpx.Client` (backed by a mock
# transport) instead of recursing into itself.
_RealHttpxClient = httpx.Client


def _make_client(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> AlpacaMarketDataClient:
    settings = SettingsService()
    monkeypatch.setattr(settings, "alpaca_api_key_id", "test-key")
    monkeypatch.setattr(settings, "alpaca_api_secret_key", "test-secret")
    monkeypatch.setattr(settings, "alpaca_base_url", "https://data.alpaca.markets")

    def _fake_httpx_client(base_url: str) -> httpx.Client:
        return _RealHttpxClient(base_url=base_url, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(
        "app.services.alpaca_market_data_client.httpx.Client", _fake_httpx_client
    )
    return AlpacaMarketDataClient(settings, logging.getLogger("test"))


def test_get_hourly_bars_maps_response_to_hourly_price_data(monkeypatch: pytest.MonkeyPatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "bars": {
                    "AAPL": [
                        {"t": "2024-01-01T10:00:00Z", "o": 190.0, "h": 195.0, "l": 185.0, "c": 192.0}
                    ]
                },
                "next_page_token": None,
            },
        )

    client = _make_client(monkeypatch, handler)

    bars = client.get_hourly_bars(["AAPL"], START, END)

    assert set(bars.keys()) == {"AAPL"}
    assert len(bars["AAPL"]) == 1
    bar = bars["AAPL"][0]
    assert bar.symbol == "AAPL"
    assert bar.open == 190.0
    assert bar.high == 195.0
    assert bar.low == 185.0
    assert bar.close == 192.0
    assert bar.starting_hour == START


def test_get_hourly_bars_follows_pagination(monkeypatch: pytest.MonkeyPatch):
    calls: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page_token = request.url.params.get("page_token")
        calls.append(page_token)
        if page_token is None:
            return httpx.Response(
                200,
                json={
                    "bars": {
                        "AAPL": [
                            {
                                "t": "2024-01-01T10:00:00Z",
                                "o": 190.0,
                                "h": 195.0,
                                "l": 185.0,
                                "c": 192.0,
                            }
                        ]
                    },
                    "next_page_token": "page-2",
                },
            )
        return httpx.Response(
            200,
            json={
                "bars": {
                    "AAPL": [
                        {
                            "t": "2024-01-01T11:00:00Z",
                            "o": 192.0,
                            "h": 196.0,
                            "l": 191.0,
                            "c": 194.0,
                        }
                    ]
                },
                "next_page_token": None,
            },
        )

    client = _make_client(monkeypatch, handler)

    bars = client.get_hourly_bars(["AAPL"], START, END)

    assert calls == [None, "page-2"]
    assert len(bars["AAPL"]) == 2


def test_get_hourly_bars_returns_empty_list_for_a_symbol_with_no_bars(
    monkeypatch: pytest.MonkeyPatch,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"bars": {}, "next_page_token": None})

    client = _make_client(monkeypatch, handler)

    bars = client.get_hourly_bars(["DELISTED"], START, END)

    assert bars == {"DELISTED": []}


def test_get_hourly_bars_returns_empty_dict_for_no_symbols(monkeypatch: pytest.MonkeyPatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not make a request when no symbols are given")

    client = _make_client(monkeypatch, handler)

    assert client.get_hourly_bars([], START, END) == {}


@pytest.mark.parametrize("status_code", [401, 403])
def test_get_hourly_bars_raises_authentication_error(
    monkeypatch: pytest.MonkeyPatch, status_code: int
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": "unauthorized"})

    client = _make_client(monkeypatch, handler)

    with pytest.raises(AlpacaAuthenticationError):
        client.get_hourly_bars(["AAPL"], START, END)


@pytest.mark.parametrize("status_code", [400, 422])
def test_get_hourly_bars_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, status_code: int
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": "invalid symbol"})

    client = _make_client(monkeypatch, handler)

    with pytest.raises(AlpacaValidationError):
        client.get_hourly_bars(["AAPL"], START, END)


def test_get_hourly_bars_raises_rate_limit_error_with_retry_after(
    monkeypatch: pytest.MonkeyPatch,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"}, json={"message": "slow down"})

    client = _make_client(monkeypatch, handler)

    with pytest.raises(AlpacaRateLimitError) as exc_info:
        client.get_hourly_bars(["AAPL"], START, END)
    assert exc_info.value.retry_after_seconds == 30.0


def test_get_hourly_bars_raises_rate_limit_error_without_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "slow down"})

    client = _make_client(monkeypatch, handler)

    with pytest.raises(AlpacaRateLimitError) as exc_info:
        client.get_hourly_bars(["AAPL"], START, END)
    assert exc_info.value.retry_after_seconds is None


def test_get_hourly_bars_raises_generic_api_error_for_other_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    client = _make_client(monkeypatch, handler)

    with pytest.raises(AlpacaApiError):
        client.get_hourly_bars(["AAPL"], START, END)
