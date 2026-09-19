"""Caches hourly OHLC bars fetched from `AlpacaMarketDataClient`.

An hour's bars never change once that hour has fully elapsed, so caching is
indefinite - there's no eviction/TTL logic here. The repository's methods
are shaped around `MarketDataService`'s exact usage pattern: look up
whatever's cached for a batch of symbols over one hour or an hour range,
then persist the results of one Alpaca request in a single call.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, date, datetime

from app.models.market import HourlyDate, HourlyPriceData
from app.services.database_service import DatabaseService


# Shared by `cache_hour` and `cache_all`.
_UPSERT_SQL = """
    INSERT INTO market_data_cache (symbol, day, hour, open, high, low, close, fetched_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (symbol, day, hour) DO UPDATE SET
        open = excluded.open,
        high = excluded.high,
        low = excluded.low,
        close = excluded.close,
        fetched_at = excluded.fetched_at
"""


class MarketDataRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def get_cached(self, symbols: list[str], hour: HourlyDate) -> dict[str, HourlyPriceData | None]:
        """Return whatever's already cached for `symbols` at `hour`.

        A symbol present in the result with a `None` value means it was
        previously fetched and confirmed to have no data for this hour
        (e.g. market closed, or the symbol no longer trades). A symbol
        missing from the result entirely hasn't been fetched yet, and the
        caller should fetch (and then cache) it.
        """
        if not symbols:
            return {}

        placeholders = ",".join("?" for _ in symbols)
        with self._database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM market_data_cache
                WHERE day = ? AND hour = ? AND symbol IN ({placeholders})
                """,
                (hour.day.isoformat(), hour.hour, *symbols),
            ).fetchall()
        return {row["symbol"]: self._price_data_from_row(row, hour) for row in rows}

    def get_cached_range(
        self, symbols: list[str], start: HourlyDate, end: HourlyDate
    ) -> dict[HourlyDate, dict[str, HourlyPriceData | None]]:
        """Return whatever's already cached for `symbols` across [start, end],
        both ends inclusive.

        Per-symbol semantics are the same as `get_cached` (present with a
        `None` value = confirmed no data; missing = never fetched), grouped
        by hour. Hours with nothing cached at all are absent from the result.
        """
        if not symbols:
            return {}

        placeholders = ",".join("?" for _ in symbols)
        with self._database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM market_data_cache
                WHERE symbol IN ({placeholders})
                  AND (day > ? OR (day = ? AND hour >= ?))
                  AND (day < ? OR (day = ? AND hour <= ?))
                """,
                (
                    *symbols,
                    start.day.isoformat(), start.day.isoformat(), start.hour,
                    end.day.isoformat(), end.day.isoformat(), end.hour,
                ),
            ).fetchall()

        cached: dict[HourlyDate, dict[str, HourlyPriceData | None]] = {}
        for row in rows:
            hour = HourlyDate(day=date.fromisoformat(row["day"]), hour=row["hour"])
            cached.setdefault(hour, {})[row["symbol"]] = self._price_data_from_row(row, hour)
        return cached

    def cache_hour(self, hour: HourlyDate, prices: dict[str, HourlyPriceData | None]) -> None:
        """Persist the full result of one Alpaca request for `hour`.

        `prices` should map every symbol that was requested from Alpaca to
        either its `HourlyPriceData` or `None` (if Alpaca returned no bar
        for it), so future requests for this hour don't need to re-fetch
        any of them.
        """
        if not prices:
            return

        fetched_at = datetime.now(UTC).isoformat()
        rows = [
            self._row_for(hour, symbol, price_data, fetched_at)
            for symbol, price_data in prices.items()
        ]
        with self._database.connect() as conn:
            conn.executemany(_UPSERT_SQL, rows)

    def cache_all(self, prices: dict[HourlyDate, dict[str, HourlyPriceData | None]]) -> None:
        """Persist the full results of one Alpaca request covering multiple hours.

        Same contract as `cache_hour`, applied to each hour in `prices`.
        All hours are persisted in a single batched statement.
        """
        if not prices:
            return

        fetched_at = datetime.now(UTC).isoformat()
        rows = [
            self._row_for(hour, symbol, price_data, fetched_at)
            for hour, hour_prices in prices.items()
            for symbol, price_data in hour_prices.items()
        ]
        with self._database.connect() as conn:
            conn.executemany(_UPSERT_SQL, rows)

    @staticmethod
    def _row_for(
        hour: HourlyDate,
        symbol: str,
        price_data: HourlyPriceData | None,
        fetched_at: str,
    ) -> tuple[object, ...]:
        return (
            symbol,
            hour.day.isoformat(),
            hour.hour,
            price_data.open if price_data is not None else None,
            price_data.high if price_data is not None else None,
            price_data.low if price_data is not None else None,
            price_data.close if price_data is not None else None,
            fetched_at,
        )

    @staticmethod
    def _price_data_from_row(row: sqlite3.Row, hour: HourlyDate) -> HourlyPriceData | None:
        if row["open"] is None:
            return None
        return HourlyPriceData(
            symbol=row["symbol"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            starting_hour=hour,
        )
