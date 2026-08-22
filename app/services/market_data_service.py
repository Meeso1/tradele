"""Mock market data for the fixed set of tradable symbols.

TODO: Replace this with a real price data source (e.g. a market data API).
For now, prices are randomly generated on each call so the rest of the
gameplay loop (portfolios, trades) can be built and tested independently of
a real feed.
"""

from __future__ import annotations

from datetime import date, datetime
import logging
import random

from pydantic.dataclasses import dataclass

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


@dataclass
class HourlyDate:
    day: date
    hour: int

    @staticmethod
    def containing(timestamp: datetime) -> HourlyDate:
        return HourlyDate(day=timestamp.date(), hour=timestamp.hour)


@dataclass
class HourlyPriceData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    starting_hour: HourlyDate


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

    def get_prices(self, time: HourlyDate) -> dict[str, float]:
        """Return mock prices for all symbols for (time, time + 1 hour) window."""
        return {
            symbol: round(random.uniform(base * 0.95, base * 1.05), 2)
            for symbol, base in _BASE_PRICES.items()
        }
