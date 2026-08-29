from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from app.models.market import HourlyDate
from app.models.trade import ActiveTrade, Kind
from app.repositories.trade_repository import TradeRepository
from app.services.settings_service import SettingsService


class TradeValidationError(ValueError):
    """Raised when submitted trades fail basic validation."""


class TradesAlreadySubmittedError(ValueError):
    """Raised when a player has already submitted trades for today."""


class TradeRequest(BaseModel):
    symbol: str
    kind: Kind
    quantity: float
    requested_price: float


class TradeSubmissionService:
    def __init__(
        self, trade_repository: TradeRepository, settings: SettingsService, logger: logging.Logger
    ) -> None:
        self._trade_repository: TradeRepository = trade_repository
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def _validate(self, trades: list[TradeRequest]) -> None:
        # We intentionally  don't validate if trade can be executed - other trades executed earlier can change the portfolio state.
        if not trades:
            raise TradeValidationError("Must submit at least one trade")
        for trade in trades:
            if trade.symbol not in self._settings.tradable_symbols:
                raise TradeValidationError(f"Unknown symbol: {trade.symbol}")
            if trade.quantity <= 0:
                raise TradeValidationError("Quantity must be positive")

    def has_submitted_today(self, user_id: str, date: HourlyDate) -> bool:
        return self._trade_repository.exists_for_date(user_id, date)

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

        active_from = HourlyDate.next(date)
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
                    kind=trade.kind,
                    requested_price=trade.requested_price,
                    quantity=trade.quantity,
                    requested_at=now,
                    active_from=active_from,
                )
            )
        self._logger.info("Recorded %d requested trade(s) for user %s, active from %s", len(trade_ids), user_id, active_from)
        return trade_ids
