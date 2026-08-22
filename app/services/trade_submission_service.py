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
from datetime import UTC, datetime

from pydantic import BaseModel

from app.repositories.trade_repository import (
    ActiveTrade,
    HistoricalTrade,
    Side,
    TradeRepository,
)
from app.services.market_data_service import TRADABLE_SYMBOLS, HourlyDate

__all__ = [ # TODO: don't do that - use normal imports
    "ActiveTrade",
    "HistoricalTrade",
    "Side",
    "TradeRequest",
    "TradeSubmissionService",
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


class TradeSubmissionService:
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

    def has_submitted_today(self, user_id: str, date: HourlyDate) -> bool:
        return self._trade_repository.exists_for_date(user_id, date.day.isoformat())

    def submit(self, user_id: str, trades: list[TradeRequest], date: HourlyDate) -> list[str]:
        """
        Validate and save to db a daily batch of trade requests for a given user.

        Raises `TradeValidationError` if the trades are invalid, or
        `TradesAlreadySubmittedError` if the player has already submitted
        trades today.
        """
        self._validate(trades)
        if self.has_submitted_today(user_id, date):
            raise TradesAlreadySubmittedError(f"Trades already submitted for {date.day.isoformat()}")

        now = datetime.now(UTC)
        trade_ids: list[str] = []
        for trade in trades:
            trade_id = str(uuid.uuid4())
            trade_ids.append(trade_id)
            self._trade_repository.insert_requested(
                ActiveTrade(
                    id=trade_id,
                    user_id=user_id,
                    symbol=trade.symbol,
                    side=trade.side,
                    quantity=trade.quantity,
                    requested_at=now,
                    trade_date=date.day.isoformat(),
                    active_from_hour=date.hour,
                )
            )
        self._logger.info("Recorded %d requested trade(s) for user %s, active from %d:00 %s", len(trade_ids), user_id, date.hour, date.day.isoformat())
        return trade_ids
