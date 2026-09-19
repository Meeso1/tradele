"""Caches hourly OHLC bars fetched from `AlpacaMarketDataClient`.

An hour's bars never change once that hour has fully elapsed, so caching is
indefinite - there's no eviction/TTL logic here. The repository's methods
are shaped around `MarketDataService`'s exact usage pattern: look up
whatever's cached for one (hour, batch-of-symbols) request, then persist the
results of one Alpaca request in a single call.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from app.models.market import HourlyDate, HourlyPriceData
from app.services.database_service import DatabaseService


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
        with self._database.connect() as conn:
            conn.executemany(
                """
                INSERT INTO market_data_cache (symbol, day, hour, open, high, low, close, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, day, hour) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    fetched_at = excluded.fetched_at
                """,
                [
                    (
                        symbol,
                        hour.day.isoformat(),
                        hour.hour,
                        price_data.open if price_data is not None else None,
                        price_data.high if price_data is not None else None,
                        price_data.low if price_data is not None else None,
                        price_data.close if price_data is not None else None,
                        fetched_at,
                    )
                    for symbol, price_data in prices.items()
                ],
            )

    def cache_all(self, prices: dict[HourlyDate, dict[str, HourlyPriceData | None]]) -> None:
        # TODO(cleanup): persist multiple hours. Probably could be done in a single SQL call? IDK if that's the best idea, though. There could be a lot of data here.
        ...

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
