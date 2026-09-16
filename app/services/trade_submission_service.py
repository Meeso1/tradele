from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from dataclasses import dataclass

from app.models.market import HourlyDate
from app.models.trade import ActiveTrade, Kind
from app.repositories.trade_repository import TradeRepository
from app.services.settings_service import SettingsService


class TradeValidationError(ValueError):
    """Raised when submitted trades fail basic validation."""


class TradesAlreadySubmittedError(ValueError):
    """Raised when a player has already submitted trades for today."""


@dataclass
class TradeRequest:
    symbol: str
    kind: Kind
    quantity: float | None = None
    value: float | None = None
    requested_price: float | None = None


@dataclass
class TradeSubmissionResult:
    submitted_ids: list[str]
    cancelled_ids: list[str]


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
        for trade in trades:
            if trade.symbol not in self._settings.tradable_symbols:
                raise TradeValidationError(f"Unknown symbol: {trade.symbol}")

            if trade.quantity is not None and trade.quantity <= 0:
                raise TradeValidationError("Quantity must be positive")
            if trade.value is not None and trade.value <= 0:
                raise TradeValidationError("Value must be positive")
            if trade.quantity is None and trade.value is None:
                raise TradeValidationError("Either quantity or value must be provided")
            if trade.quantity is not None and trade.value is not None:
                raise TradeValidationError("Only one of quantity or value must be provided")

            requires_requested_price = {"limit_buy", "limit_sell", "stop_buy", "stop_sell"}
            if trade.kind in requires_requested_price and trade.requested_price is None:
                raise TradeValidationError(f"requested_price is required for {trade.kind} orders")

    # TODO: Track submission hour separately
    def has_submitted_today(self, user_id: str, date: HourlyDate) -> bool:
        return self._trade_repository.exists_for_date(user_id, date)

    def submit(self, user_id: str, trades: list[TradeRequest], trades_to_cancel: list[str], date: HourlyDate) -> TradeSubmissionResult:
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
                    value=trade.value,
                    requested_at=now,
                    active_from=active_from,
                )
            )

        cancelled: list[str] = []
        for trade_id in trades_to_cancel:
            if self._trade_repository.cancel_if_active(user_id, trade_id, now, date):
                cancelled.append(trade_id)

        self._logger.info("Recorded %d requested trade(s) for user %s, active from %s. Cancelled %d trade(s) (%s requested)", 
            len(trade_ids), user_id, active_from, len(cancelled), len(trades_to_cancel))

        return TradeSubmissionResult(submitted_ids=trade_ids, cancelled_ids=cancelled)
