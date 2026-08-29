"""Business logic for player portfolios, backed by `PortfolioRepository`.

TODO: this only tracks current holdings - there's no historical snapshot of
portfolio value over time, which we'll probably want for showing players
how they did day over day.
"""

from __future__ import annotations

import logging

from app.repositories.portfolio_repository import Portfolio, PortfolioRepository


class PortfolioService:
    def __init__(self, portfolio_repository: PortfolioRepository, logger: logging.Logger) -> None:
        self._portfolio_repository: PortfolioRepository = portfolio_repository
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def get_or_create(self, user_id: str) -> Portfolio:
        """Return the player's portfolio, creating a fresh one if needed."""
        return self._portfolio_repository.get_or_create(user_id)

    def save(self, user_id: str, portfolio: Portfolio) -> None:
        """Persist an updated portfolio (e.g. after trades execute)."""
        self._portfolio_repository.update(user_id, portfolio)
        self._logger.info("Saved portfolio for user %s", user_id)
