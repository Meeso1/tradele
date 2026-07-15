"""Business logic for player portfolios, backed by `PortfolioRepository`.

TODO: this only tracks current holdings - there's no historical snapshot of
portfolio value over time, which we'll probably want for showing players
how they did day over day.
"""

from __future__ import annotations

import logging

from app.repositories.portfolio_repository import Portfolio, PortfolioRepository
from app.services.market_data_service import TRADABLE_SYMBOLS

# TODO: revisit the starting amount once game balance/design is settled.
STARTING_CASH: float = 100_000.0


class PortfolioService:
    def __init__(self, portfolio_repository: PortfolioRepository, logger: logging.Logger) -> None:
        self._portfolio_repository: PortfolioRepository = portfolio_repository
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _default_portfolio(self) -> Portfolio:
        return Portfolio(cash=STARTING_CASH, holdings={symbol: 0 for symbol in TRADABLE_SYMBOLS})

    def get_or_create(self, user_id: str) -> Portfolio:
        """Return the player's portfolio, creating a fresh one if needed."""
        portfolio = self._portfolio_repository.get(user_id)
        if portfolio is not None:
            return portfolio

        portfolio = self._default_portfolio()
        self._portfolio_repository.insert(user_id, portfolio)
        self._logger.info("Created portfolio for user %s", user_id)
        return portfolio

    def save(self, user_id: str, portfolio: Portfolio) -> None:
        """Persist an updated portfolio (e.g. after trades execute).

        TODO: not called anywhere yet - wire this up once trade execution
        actually updates holdings/cash. See `TradeService`.
        """
        self._portfolio_repository.update(user_id, portfolio)
        self._logger.info("Saved portfolio for user %s", user_id)
