"""Business logic for player trades, backed by `TradeRepository`.

Players submit one batch of trade requests per day. A daily job is meant
to execute those requests against the next day's prices and update the
player's portfolio accordingly - this service currently only handles the
"request" side of that flow: validating and recording what a player asked
to happen.

TODO: there's no execution step yet. Requested trades sit with
status='pending' forever - we need a daily job that reads pending
requests, matches them against `MarketDataService` prices, updates
`PortfolioService` holdings/cash (via `PortfolioService.save`), and writes
a row per executed trade via `record_executed` below (and marks the
request itself as no longer pending).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel

from app.repositories.trade_repository import (
    ExecutedTrade,
    RequestedTrade,
    Side,
    TradeRepository,
)
from app.services.market_data_service import TRADABLE_SYMBOLS

__all__ = [
    "ExecutedTrade",
    "RequestedTrade",
    "Side",
    "TradeRequest",
    "TradeService",
    "TradeValidationError",
    "TradesAlreadySubmittedError",
]


class TradeValidationError(ValueError):
    """Raised when submitted trades fail basic validation."""


class TradesAlreadySubmittedError(ValueError):
    """Raised when a player has already submitted trades for today."""


class TradeRequest(BaseModel):
    symbol: str
    side: Side
    quantity: int


class TradeService:
    def __init__(self, trade_repository: TradeRepository, logger: logging.Logger) -> None:
        self._trade_repository: TradeRepository = trade_repository
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _validate(self, trades: list[TradeRequest]) -> None:
        if not trades:
            raise TradeValidationError("Must submit at least one trade")
        for trade in trades:
            if trade.symbol not in TRADABLE_SYMBOLS:
                raise TradeValidationError(f"Unknown symbol: {trade.symbol}")
            if trade.quantity <= 0:
                raise TradeValidationError("Quantity must be positive")
        # TODO: this is intentionally minimal for now ("really simple" per
        # the initial scaffold) - it doesn't check that the player can
        # actually afford a buy, or that they hold enough shares to sell.
        # Those checks are tricky to do *at request time* anyway, since
        # trades execute against the next day's (unknown) prices - they
        # probably belong in the (not yet written) execution step instead.

    def has_submitted_today(self, user_id: str) -> bool:
        today = date.today().isoformat()
        return self._trade_repository.exists_for_date(user_id, today)

    def submit(self, user_id: str, trades: list[TradeRequest]) -> list[str]:
        """Record a player's one-per-day batch of trade requests.

        Raises `TradeValidationError` if the trades are invalid, or
        `TradesAlreadySubmittedError` if the player has already submitted
        trades today.
        """
        self._validate(trades)
        if self.has_submitted_today(user_id):
            raise TradesAlreadySubmittedError("Trades already submitted for today")

        today = date.today().isoformat()
        now = datetime.now(UTC).isoformat()
        trade_ids: list[str] = []
        for trade in trades:
            trade_id = str(uuid.uuid4())
            trade_ids.append(trade_id)
            self._trade_repository.insert_requested(
                trade_id, user_id, trade.symbol, trade.side, trade.quantity, now, today
            )
        self._logger.info("Recorded %d requested trade(s) for user %s", len(trade_ids), user_id)
        return trade_ids

    def list_requested(self, user_id: str) -> list[RequestedTrade]:
        return self._trade_repository.list_requested(user_id)

    def list_executed(self, user_id: str) -> list[ExecutedTrade]:
        return self._trade_repository.list_executed(user_id)

    def record_executed(
        self, user_id: str, symbol: str, side: Side, quantity: int, price: float
    ) -> str:
        """Record a trade that actually happened.

        TODO: not called anywhere yet - this is here for the (not yet
        written) daily execution job to use once requested trades are
        actually matched against prices.
        """
        trade_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._trade_repository.insert_executed(trade_id, user_id, symbol, side, quantity, price, now)
        self._logger.info("Recorded executed trade %s for user %s", trade_id, user_id)
        return trade_id
