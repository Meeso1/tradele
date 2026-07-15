"""Data access and row/model mapping for the `requested_trades` and
`executed_trades` tables.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel

from app.services.database_service import DatabaseService

Side = Literal["buy", "sell"]


class RequestedTrade(BaseModel):
    id: str
    user_id: str
    symbol: str
    side: Side
    quantity: int
    requested_at: str
    trade_date: str
    status: str


class ExecutedTrade(BaseModel):
    id: str
    user_id: str
    symbol: str
    side: Side
    quantity: int
    price: float
    executed_at: str


class TradeRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def exists_for_date(self, user_id: str, trade_date: str) -> bool:
        with self._database.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM requested_trades WHERE user_id = ? AND trade_date = ?",
                (user_id, trade_date),
            ).fetchone()
        return row is not None

    def insert_requested(
        self,
        trade_id: str,
        user_id: str,
        symbol: str,
        side: Side,
        quantity: int,
        requested_at: str,
        trade_date: str,
    ) -> None:
        with self._database.connect() as conn:
            conn.execute(
                """
                INSERT INTO requested_trades
                    (id, user_id, symbol, side, quantity, requested_at, trade_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (trade_id, user_id, symbol, side, quantity, requested_at, trade_date),
            )

    def list_requested(self, user_id: str) -> list[RequestedTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM requested_trades WHERE user_id = ? ORDER BY requested_at",
                (user_id,),
            ).fetchall()
        return [RequestedTrade(**dict(row)) for row in rows]

    def list_executed(self, user_id: str) -> list[ExecutedTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM executed_trades WHERE user_id = ? ORDER BY executed_at",
                (user_id,),
            ).fetchall()
        return [ExecutedTrade(**dict(row)) for row in rows]

    def insert_executed(
        self,
        trade_id: str,
        user_id: str,
        symbol: str,
        side: Side,
        quantity: int,
        price: float,
        executed_at: str,
    ) -> None:
        with self._database.connect() as conn:
            conn.execute(
                """
                INSERT INTO executed_trades
                    (id, user_id, symbol, side, quantity, price, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trade_id, user_id, symbol, side, quantity, price, executed_at),
            )
