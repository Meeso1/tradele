"""Real market data, backed by the Alpaca Market Data API and cached in the DB.

The tradable symbol universe lives in `SettingsService.tradable_symbols`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import logging

from pydantic.dataclasses import dataclass

from app.models.market import HourlyDate, HourlyPriceData, MarketState
from app.repositories.market_data_repository import MarketDataRepository
from app.services.alpaca_market_data_client import AlpacaMarketDataClient
from app.services.settings_service import SettingsService


@dataclass
class CacheSearchResult:
    data: dict[HourlyDate, dict[str, HourlyPriceData | None]]
    missing_symbols: set[str]
    earliest_time_with_missing_symbols: HourlyDate | None
    latest_time_with_missing_symbols: HourlyDate | None


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

    def get_prices_for_hour(self, time: HourlyDate) -> MarketState:
        """Return prices for all tradable symbols for (time, time + 1 hour) window."""
        prices_for_range = self.get_prices_for_range(time, HourlyDate.next(time))
        assert len(prices_for_range) == 1, "Expected exactly one result for a single-hour window"
        return prices_for_range[0]

    def get_latest_open_market_prices(self, hour: HourlyDate) -> MarketState:
        """Return the latest open market prices for all tradable symbols."""
        day_shift = 0
        while day_shift < 366: # Safety not to iterate forever. We should never have more than a few days of closed market.
            end = HourlyDate.next(hour) - timedelta(days=day_shift)
            day = self.get_prices_for_range(end - timedelta(days=1), end)
            if (latest_open := self._latest_open_market(day)) is not None:
                return latest_open
            day_shift += 1

        raise RuntimeError("No open market data found within 365 days")

    # TODO(cleanup): Create an endpoint returning that. Maybe we can also have an option to specify i.e. 'past month' instead of start and end? 
    def get_prices_for_range(self, start: HourlyDate, end: HourlyDate) -> list[MarketState]:
        """Return prices for all tradable symbols for each hour in the range [start, end)."""
        symbols = self._settings.tradable_symbols

        self._logger.debug(f"Fetching prices for all symbols for range: {start} to {end}")

        cache_result = self._get_from_cache(symbols, start, end)
        if cache_result.missing_symbols:
            self._logger.debug(f"{len(cache_result.missing_symbols)} missing symbols found between: {cache_result.earliest_time_with_missing_symbols} to {cache_result.latest_time_with_missing_symbols}")
        else:
            self._logger.debug("All data was found in cache - no need to fetch")

        fetched: dict[HourlyDate, dict[str, HourlyPriceData | None]] = defaultdict(dict)
        if cache_result.missing_symbols \
            and cache_result.earliest_time_with_missing_symbols is not None \
            and cache_result.latest_time_with_missing_symbols is not None:
            fetched = self._fetch_data(
                cache_result.missing_symbols,
                cache_result.earliest_time_with_missing_symbols,
                cache_result.latest_time_with_missing_symbols,
            )

        return self._combine_results(cache_result.data, fetched, start, end)

    def _get_from_cache(
        self, symbols: list[str], start: HourlyDate, end: HourlyDate
    ) -> CacheSearchResult:
        cached_results: dict[HourlyDate, dict[str, HourlyPriceData | None]] = {}
        missing_symbols: set[str] = set()
        earliest_time_with_missing_symbols: HourlyDate | None = None
        latest_time_with_missing_symbols: HourlyDate | None = None
        for time in HourlyDate.enumerate_range(start, end):
            # TODO(cleanup): We could make a method that fetches cached data for multiple hours, and have less SQL calls. I'm not 100% sure that's a good idea, though, since there could be a lot of data.
            cached = self._market_data_repository.get_cached(symbols, time)
            cached_results[time] = cached
            missing_for_this_hour = [symbol for symbol in symbols if symbol not in cached]
            missing_symbols.update(missing_for_this_hour)

            if missing_for_this_hour:
                earliest_time_with_missing_symbols = min(earliest_time_with_missing_symbols, time) \
                    if earliest_time_with_missing_symbols is not None else time
                latest_time_with_missing_symbols = max(latest_time_with_missing_symbols, time) \
                    if latest_time_with_missing_symbols is not None else time

        return CacheSearchResult(
            data=cached_results,
            missing_symbols=missing_symbols,
            earliest_time_with_missing_symbols=earliest_time_with_missing_symbols,
            latest_time_with_missing_symbols=latest_time_with_missing_symbols,
        )

    def _fetch_data(
        self, symbols: set[str], start: HourlyDate, end: HourlyDate
    ) -> dict[HourlyDate, dict[str, HourlyPriceData | None]]:
        fetched: dict[HourlyDate, dict[str, HourlyPriceData | None]] = defaultdict(dict)
        bars = self._alpaca_client.get_hourly_bars(
            symbols,
            start=start,
            end=HourlyDate.next(end) # end is exclusive
        )

        for symbol, symbol_bars in bars.items():
            for bar in symbol_bars:
                fetched[bar.starting_hour][symbol] = bar

        self._market_data_repository.cache_all(fetched)
        return fetched

    def _combine_results(
        self,
        cached: dict[HourlyDate, dict[str, HourlyPriceData | None]],
        fetched: dict[HourlyDate, dict[str, HourlyPriceData | None]],
        start: HourlyDate,
        end: HourlyDate,
    ) -> list[MarketState]:
        all_results = {
            hour: {**cached.get(hour, {}), **fetched.get(hour, {})}
            for hour in HourlyDate.enumerate_range(start, end)}
        prices = {
            hour: {
                symbol: price_data for symbol, price_data in hour_results.items() if price_data is not None
            } for hour, hour_results in all_results.items()
        }
        return sorted(
            [
                MarketState(hour=hour, prices=hour_prices, market_open=any(hour_prices))
                for hour, hour_prices in prices.items()
            ],
            key=lambda state: state.hour.timestamp()
        )

    @staticmethod
    def _latest_open_market(prices: list[MarketState]) -> MarketState | None:
        for state in reversed(prices):
            if state.market_open:
                return state
        return None
