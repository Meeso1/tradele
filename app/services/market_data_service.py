"""Mock market data for the fixed set of tradable symbols.

TODO: Replace this with a real price data source (e.g. a market data API).
For now, prices are randomly generated on each call so the rest of the
gameplay loop (portfolios, trades) can be built and tested independently of
a real feed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import logging
import random
from typing import override

from pydantic.dataclasses import dataclass
from collections.abc import Iterable

# The set of tokens players can trade, plus cash (handled separately by
# `PortfolioService`). This list is intentionally fixed for now.
# TODO: support a configurable/changing universe of symbols instead of a
# hardcoded list.
TRADABLE_SYMBOLS: list[str] = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

# Rough "anchor" prices so mock quotes stay in a plausible range across calls.
_BASE_PRICES: dict[str, float] = {
    "AAPL": 190.0,
    "GOOGL": 165.0,
    "MSFT": 420.0,
    "AMZN": 180.0,
    "TSLA": 250.0,
}


# TODO: Move to separate file (in `models`)
@dataclass(order=True)
class HourlyDate:
    day: date
    hour: int

    def timestamp(self) -> datetime:
        return datetime(self.day.year, self.day.month, self.day.day, self.hour, tzinfo=UTC)

    @staticmethod
    def containing(timestamp: datetime) -> HourlyDate:
        return HourlyDate(day=timestamp.date(), hour=timestamp.hour)

    @staticmethod
    def current() -> HourlyDate:
        return HourlyDate.containing(datetime.now(UTC))

    @staticmethod
    def last_passed_hour() -> HourlyDate:
        """
        Returns the HourlyDate for the last passed hour.
        Use this to determine the last hour for which market data is available and trades can be executed.
        """
        return HourlyDate.containing(datetime.now(UTC) - timedelta(hours=1))

    @staticmethod
    def next(hour: HourlyDate) -> HourlyDate:
        return HourlyDate.containing(hour.timestamp() + timedelta(hours=1))

    @staticmethod
    def enumerate_range(start: HourlyDate, end: HourlyDate) -> Iterable[HourlyDate]:
        """Yields each HourlyDate in the range [start, end), starting from `start` and incrementing by hour."""
        current = start
        while current < end:
            yield current
            current = HourlyDate.next(current)

    @override
    def __str__(self) -> str:
        return f"{self.hour:02}:00 {self.day.isoformat()}"


@dataclass
class HourlyPriceData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    starting_hour: HourlyDate


@dataclass
class MarketState:
    hour: HourlyDate
    prices: dict[str, HourlyPriceData]


class MarketDataService:
    """
    Provides current prices for the fixed set of tradable symbols.
    The most important information is hourly high/low/open/close data - 
    this will be used to simulate trades (trade is executed against the 
    hourly data starting from the next hour after it is posted).

    TODO: Return real market data instead of mock prices.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def get_prices(self, time: HourlyDate) -> MarketState:
        """Return mock prices for all symbols for (time, time + 1 hour) window."""
        prices = {
            symbol: round(random.uniform(base * 0.95, base * 1.05), 2)
            for symbol, base in _BASE_PRICES.items()
        }
        return MarketState(
            hour=time,
            prices={
                symbol: HourlyPriceData(
                    symbol=symbol,
                    open=prices[symbol],
                    high=prices[symbol] * 1.05,
                    low=prices[symbol] * 0.95,
                    close=prices[symbol],
                    starting_hour=time,
                )
                for symbol in _BASE_PRICES
            }
        )
