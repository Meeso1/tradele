"""Real market data, backed by the Alpaca Market Data API and cached in the DB.

The tradable symbol universe lives in `SettingsService.tradable_symbols`.
"""

from __future__ import annotations

import logging

from app.models.market import HourlyDate, HourlyPriceData, MarketState
from app.repositories.market_data_repository import MarketDataRepository
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

    Since an hour's bars never change once that hour has elapsed, results
    are cached indefinitely in `MarketDataRepository` - repeated calls for
    an already-fetched hour don't re-hit Alpaca.
    """

    def __init__(
        self,
        alpaca_client: AlpacaMarketDataClient,
        market_data_repository: MarketDataRepository,
        settings: SettingsService,
        logger: logging.Logger,
    ) -> None:
        self._alpaca_client: AlpacaMarketDataClient = alpaca_client
        self._market_data_repository: MarketDataRepository = market_data_repository
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    # TODO: Alpaca has a 15-minute delay - so trades should be executed after that time.
    def get_prices(self, time: HourlyDate) -> MarketState:
        """Return prices for all tradable symbols for (time, time + 1 hour) window."""
        symbols = self._settings.tradable_symbols

        cached = self._market_data_repository.get_cached(symbols, time)
        missing_symbols = [symbol for symbol in symbols if symbol not in cached]

        fetched: dict[str, HourlyPriceData | None] = {}
        if missing_symbols:
            bars = self._alpaca_client.get_hourly_bars(
                missing_symbols, start=time, end=HourlyDate.next(time)
            )
            fetched = {
                symbol: symbol_bars[0] if symbol_bars else None
                for symbol, symbol_bars in bars.items()
            }
            self._market_data_repository.cache_all(time, fetched)

        all_results = {**cached, **fetched}
        prices = {
            symbol: price_data for symbol, price_data in all_results.items() if price_data is not None
        }
        return MarketState(hour=time, prices=prices)
