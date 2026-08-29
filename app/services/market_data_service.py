"""Real market data, backed by the Alpaca Market Data API.

The tradable symbol universe lives in `SettingsService.tradable_symbols`.

TODO: Cache fetched hourly bars in the database instead of re-fetching them
on every call, so repeated calls for the same (already-closed) hour don't
re-hit Alpaca.
"""

from __future__ import annotations

import logging

from app.models.market import HourlyDate, MarketState
from app.services.alpaca_market_data_client import AlpacaMarketDataClient
from app.services.settings_service import SettingsService


class MarketDataService:
    """
    Provides current prices for the configured set of tradable symbols
    (`SettingsService.tradable_symbols`).
    The most important information is hourly high/low/open/close data -
    this is used to simulate trades (a trade is executed against the
    hourly data starting from the next hour after it is posted).

    A symbol is omitted from a `MarketState`'s `prices` if Alpaca has no
    bar for it in the requested hour (e.g. the market was closed, or the
    symbol no longer trades) - callers treat a missing entry as "price
    data unavailable" (see `TradeExecutionService`).
    """

    def __init__(
        self,
        alpaca_client: AlpacaMarketDataClient,
        settings: SettingsService,
        logger: logging.Logger,
    ) -> None:
        self._alpaca_client: AlpacaMarketDataClient = alpaca_client
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def get_prices(self, time: HourlyDate) -> MarketState:
        """Return real prices for all tradable symbols for (time, time + 1 hour) window."""
        symbols = self._settings.tradable_symbols
        bars = self._alpaca_client.get_hourly_bars(symbols, start=time, end=HourlyDate.next(time))
        prices = {symbol: symbol_bars[0] for symbol, symbol_bars in bars.items() if symbol_bars}
        return MarketState(hour=time, prices=prices)
