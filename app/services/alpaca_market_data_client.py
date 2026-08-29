"""Thin HTTP wrapper around Alpaca's historical stock bars API.

This module only deals with transport, authentication, and translating
Alpaca's HTTP error responses into typed exceptions. Interpreting the
returned bars (e.g. deciding what a missing symbol means for gameplay)
is left to `MarketDataService`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from app.models.market import HourlyDate, HourlyPriceData
from app.services.settings_service import SettingsService

BARS_PATH = "/v2/stocks/bars"


class AlpacaApiError(Exception):
    """Base class for errors returned by the Alpaca Market Data API."""


class AlpacaAuthenticationError(AlpacaApiError):
    """Raised when Alpaca rejects the configured API credentials (401/403)."""


class AlpacaValidationError(AlpacaApiError):
    """Raised when Alpaca rejects the request parameters (400/422)."""


class AlpacaRateLimitError(AlpacaApiError):
    """Raised when Alpaca's rate limit has been exceeded (429)."""

    def __init__(self, message: str, retry_after_seconds: float | None) -> None:
        super().__init__(message)
        self.retry_after_seconds: float | None = retry_after_seconds


class AlpacaMarketDataClient:
    """Fetches historical OHLC bars from Alpaca's Market Data API."""

    def __init__(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def get_hourly_bars(
        self, symbols: Iterable[str], start: HourlyDate, end: HourlyDate
    ) -> dict[str, list[HourlyPriceData]]:
        """Fetch 1-hour OHLC bars for `symbols` in the interval [start, end).

        The returned dict always has an entry for every requested symbol,
        even if Alpaca returned no bars for it (e.g. the market was closed
        that hour, or the symbol no longer trades) - in that case its value
        is an empty list.
        """
        symbol_list = list(symbols)
        if not symbol_list:
            return {}

        bars: dict[str, list[HourlyPriceData]] = {symbol: [] for symbol in symbol_list}
        page_token: str | None = None

        with httpx.Client(base_url=self._settings.alpaca_base_url) as client:
            while True:
                params: dict[str, Any] = {
                    "symbols": ",".join(symbol_list),
                    "timeframe": "1Hour",
                    "start": start.timestamp().isoformat(),
                    "end": end.timestamp().isoformat(),
                    "limit": 10000,
                }
                if page_token is not None:
                    params["page_token"] = page_token

                response = self._request(client, params)
                payload = response.json()
                for symbol, symbol_bars in payload.get("bars", {}).items():
                    bars.setdefault(symbol, [])
                    bars[symbol].extend(self._parse_bar(symbol, bar) for bar in symbol_bars)

                page_token = payload.get("next_page_token")
                if not page_token:
                    break

        return bars

    def _request(self, client: httpx.Client, params: dict[str, Any]) -> httpx.Response:
        try:
            response = client.get(
                BARS_PATH,
                params=params,
                headers={
                    "APCA-API-KEY-ID": self._settings.alpaca_api_key_id,
                    "APCA-API-SECRET-KEY": self._settings.alpaca_api_secret_key,
                },
            )
        except httpx.RequestError as error:
            self._logger.exception("Network error calling Alpaca")
            raise AlpacaApiError(f"Network error calling Alpaca: {error}") from error

        if response.status_code in (401, 403):
            self._logger.error("Alpaca rejected credentials: %s", response.text)
            raise AlpacaAuthenticationError("Alpaca rejected the configured API credentials")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            self._logger.warning("Alpaca rate limit hit, retry after %s", retry_after)
            raise AlpacaRateLimitError(
                "Alpaca rate limit exceeded",
                retry_after_seconds=float(retry_after) if retry_after else None,
            )

        if response.status_code in (400, 422):
            self._logger.error("Alpaca rejected request parameters: %s", response.text)
            raise AlpacaValidationError(f"Alpaca rejected request parameters: {response.text}")

        if response.is_error:
            self._logger.error(
                "Alpaca request failed with status %s: %s", response.status_code, response.text
            )
            raise AlpacaApiError(
                f"Alpaca request failed with status {response.status_code}: {response.text}"
            )

        return response

    @staticmethod
    def _parse_bar(symbol: str, bar: dict[str, Any]) -> HourlyPriceData:
        timestamp = datetime.fromisoformat(str(bar["t"]))
        return HourlyPriceData(
            symbol=symbol,
            open=float(bar["o"]),
            high=float(bar["h"]),
            low=float(bar["l"]),
            close=float(bar["c"]),
            starting_hour=HourlyDate.containing(timestamp),
        )
