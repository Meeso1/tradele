"""Data access and row/model mapping for the `active_trades` and
`historical_trades` tables.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.services.database_service import DatabaseService

Side = Literal["buy", "sell"]
InactiveTradeStatus = Literal["executed", "cancelled"]


class ActiveTrade(BaseModel):
    """
    Trade that is active and will attempt to be executed 
    against every subsequent hour window.
    """
    id: str
    user_id: str
    symbol: str
    side: Side
    quantity: float
    requested_at: datetime # Real time at which the trade was requested
    trade_date: str # Day for which the trade was requested (since users can request one set per day)
    active_from_hour: int # Hour of the day when the trade is active. After being posted, the trade starts being active from the next full hour.


class HistoricalTrade(BaseModel):
    """
    Trade is no longer active - due to being executed, cancelled, etc.
    """
    id: str
    user_id: str
    symbol: str
    side: Side
    quantity: float
    price: float | None # Price at which the trade was executed, or None if it wasn't executed
    closed_at: str # Real time at which the trade was closed (due to execution, cancellation, etc.)
    status: InactiveTradeStatus # Status of the trade after it has been closed


class TradeRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def exists_for_date(self, user_id: str, trade_date: str) -> bool:
        with self._database.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM active_trades WHERE user_id = ? AND trade_date = ?",
                (user_id, trade_date),
            ).fetchone()
        return row is not None

    def insert_requested(self, trade: ActiveTrade) -> None:
        with self._database.connect() as conn:
            conn.execute(
                """
                INSERT INTO active_trades
                    (id, user_id, symbol, side, quantity, requested_at, trade_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (trade.id, trade.user_id, trade.symbol, trade.side, trade.quantity, trade.requested_at, trade.trade_date),
            )

    def list_requested(self, user_id: str) -> list[ActiveTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM active_trades WHERE user_id = ? ORDER BY requested_at",
                (user_id,),
            ).fetchall()
        return [ActiveTrade(**dict(row)) for row in rows]

    def list_executed(self, user_id: str) -> list[HistoricalTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM historical_trades WHERE user_id = ? ORDER BY closed_at",
                (user_id,),
            ).fetchall()
        return [HistoricalTrade(**dict(row)) for row in rows]

    def insert_executed(self, trade: HistoricalTrade) -> None:
        with self._database.connect() as conn:
            conn.execute(
                """
                INSERT INTO historical_trades
                    (id, user_id, symbol, side, quantity, price, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trade.id, trade.user_id, trade.symbol, trade.side, trade.quantity, trade.price, trade.closed_at),
            )
