"""Mock market data for the fixed set of tradable symbols.

TODO: Replace this with a real price data source (e.g. a market data API).
For now, prices are randomly generated on each call so the rest of the
gameplay loop (portfolios, trades) can be built and tested independently of
a real feed.
"""

from __future__ import annotations

import logging
import random

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


class MarketDataService:
    """Provides current prices for the fixed set of tradable symbols.

    TODO: prices should probably be snapshotted once per day (rather than
    randomized on every call) so "today's price" is stable while players
    are deciding on trades, and "tomorrow's price" is what their requested
    trades actually execute against.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def get_price(self, symbol: str) -> float:
        """Return a mock current price for `symbol`.

        Raises `ValueError` if `symbol` isn't tradable.
        """
        if symbol not in _BASE_PRICES:
            raise ValueError(f"Unknown symbol: {symbol}")
        base = _BASE_PRICES[symbol]
        # +/- 5% random walk around the anchor price, just to have
        # *something* that varies from call to call.
        return round(random.uniform(base * 0.95, base * 1.05), 2)

    def get_prices(self) -> dict[str, float]:
        """Return mock current prices for every tradable symbol."""
        return {symbol: self.get_price(symbol) for symbol in TRADABLE_SYMBOLS}
