"""Business logic for player portfolios, backed by `PortfolioRepository`.

TODO: this only tracks current holdings - there's no historical snapshot of
portfolio value over time, which we'll probably want for showing players
how they did day over day.
"""

from __future__ import annotations

import logging

from app.models.market import HourlyDate, MarketState
from app.models.portfolio import HistoricalPortfolio, Portfolio
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.market_data_service import MarketDataService
from app.services.user_service import UserService


class PortfolioService:
    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        user_service: UserService,
        market_data_service: MarketDataService,
        logger: logging.Logger,
    ) -> None:
        self._portfolio_repository: PortfolioRepository = portfolio_repository
        self._user_service: UserService = user_service
        self._market_data_service: MarketDataService = market_data_service
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

    def save_hourly_state(
        self,
        user_id: str,
        hour: HourlyDate,
        last_open_market_state: MarketState
    ) -> None:
        last_recorded_hour = self._portfolio_repository.get_last_recorded_hour(user_id)
        if last_recorded_hour is not None and last_recorded_hour >= hour:
            self._logger.debug("Skipping hourly state save for user %s at %s (already recorded)", user_id, hour)
            return
        
        portfolio = self.get_or_create(user_id)
        state = self._to_historical_portfolio(portfolio, hour, last_open_market_state)
        success = self._portfolio_repository.try_record_state(user_id, state)
        if success:
            self._logger.info("Saved hourly state for user %s at %s", user_id, hour)
        else:
            self._logger.info("Failed to save hourly state for user %s at %s (parallel update)", user_id, hour)

    # TODO(cleanup): Create a scheduled job to call this every hour, with current (or last passed? check) hour.
    def save_state_for_all_users(self, hour: HourlyDate) -> None:
        self._logger.info("Saving hourly state for all users at %s", hour)
        last_open_market_state = self._market_data_service.get_latest_open_market_prices(hour)
        self._logger.info("Got latest open market state from %s", last_open_market_state.hour)
        
        for user_id in self._user_service.list_ids():
            self.save_hourly_state(user_id, hour, last_open_market_state)

    def _to_historical_portfolio(
        self,
        portfolio: Portfolio,
        hour: HourlyDate,
        market_state: MarketState,
    ) -> HistoricalPortfolio:
        return HistoricalPortfolio(
            cash=portfolio.cash,
            holdings=portfolio.holdings,
            timestamp=hour,
            total_value=self._calculate_total_value(portfolio, market_state)
        )

    def _calculate_total_value(self, portfolio: Portfolio, market_state: MarketState) -> float:
        total_value = portfolio.cash
        for symbol, quantity in portfolio.holdings.items():
            price = market_state.prices.get(symbol, None)
            if price is None:
                # TODO(nitpick): This will happen if symbol stops being trade-able. Important to consider in the future.
                self._logger.warning("No price found for symbol %s", symbol)
                continue
            total_value += quantity * price.close
        return total_value
