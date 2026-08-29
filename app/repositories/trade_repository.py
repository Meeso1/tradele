from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta

from app.models.market import HourlyDate
from app.models.trade import ActiveTrade, HistoricalTrade, InactiveTradeStatus
from app.services.database_service import DatabaseService


class TradeRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def exists_for_date(self, user_id: str, request_date: HourlyDate) -> bool:
        """Check whether the user already has an active trade requested on the same day as `request_date`.

        Compares the day of `active_from` minus one hour (i.e. the day a
        trade was actually requested on) against `request_date`'s day,
        rather than `active_from`'s day directly, so a trade requested
        right before midnight (whose `active_from` rolls over to the next
        day) is still correctly attributed to the day it was requested on.
        """
        next_day = request_date.day + timedelta(days=1)
        with self._database.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM active_trades
                WHERE user_id = ?
                    AND (
                        (active_from_day = ? AND active_from_hour >= 1)
                        OR (active_from_day = ? AND active_from_hour = 0)
                    )
                """,
                (user_id, request_date.day.isoformat(), next_day.isoformat()),
            ).fetchone()
        return row is not None

    def insert_requested(self, trade: ActiveTrade) -> None:
        with self._database.connect() as conn:
            conn.execute(
                """
                INSERT INTO active_trades
                    (id, user_id, symbol, kind, requested_price, quantity, requested_at,
                     active_from_day, active_from_hour)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.id,
                    trade.user_id,
                    trade.symbol,
                    trade.kind,
                    trade.requested_price,
                    trade.quantity,
                    trade.requested_at.isoformat(),
                    trade.active_from.day.isoformat(),
                    trade.active_from.hour,
                ),
            )

    def list_requested(self, user_id: str) -> list[ActiveTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM active_trades WHERE user_id = ? ORDER BY requested_at",
                (user_id,),
            ).fetchall()
        return [self._active_trade_from_row(row) for row in rows]

    def list_active_in_order(self, user_id: str, hour: HourlyDate) -> list[ActiveTrade]:
        """Return all trades from active_trades that are active in the given hour, ordered by active_from, then requested_at, then ID."""
        with self._database.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM active_trades
                WHERE user_id = ?
                    AND (active_from_day < ? OR (active_from_day = ? AND active_from_hour <= ?))
                ORDER BY active_from_day, active_from_hour, requested_at, id
                """,
                (user_id, hour.day.isoformat(), hour.day.isoformat(), hour.hour),
            ).fetchall()
        return [self._active_trade_from_row(row) for row in rows]

    def list_executed(self, user_id: str) -> list[HistoricalTrade]:
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM historical_trades WHERE user_id = ? ORDER BY closed_at",
                (user_id,),
            ).fetchall()
        return [self._historical_trade_from_row(row) for row in rows]

    def move_to_executed(
        self,
        trade_id: str,
        fill_price: float | None,
        closed_at: datetime,
        closed_at_hour: HourlyDate,
        status: InactiveTradeStatus,
    ) -> None:
        """Move a trade from `active_trades` to `historical_trades`, filling in the closing fields."""
        with self._database.connect() as conn:
            row = conn.execute("SELECT * FROM active_trades WHERE id = ?", (trade_id,)).fetchone()
            if row is None:
                raise ValueError(f"No active trade with id {trade_id}")

            conn.execute(
                """
                INSERT INTO historical_trades
                    (id, user_id, symbol, kind, requested_price, quantity, requested_at,
                     active_from_day, active_from_hour, fill_price, closed_at,
                     closed_at_hour_day, closed_at_hour_hour, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["user_id"],
                    row["symbol"],
                    row["kind"],
                    row["requested_price"],
                    row["quantity"],
                    row["requested_at"],
                    row["active_from_day"],
                    row["active_from_hour"],
                    fill_price,
                    closed_at.isoformat(),
                    closed_at_hour.day.isoformat(),
                    closed_at_hour.hour,
                    status,
                ),
            )
            conn.execute("DELETE FROM active_trades WHERE id = ?", (trade_id,))

    @staticmethod
    def _active_trade_from_row(row: sqlite3.Row) -> ActiveTrade:
        return ActiveTrade(
            id=row["id"],
            user_id=row["user_id"],
            symbol=row["symbol"],
            kind=row["kind"],
            requested_price=row["requested_price"],
            quantity=row["quantity"],
            requested_at=row["requested_at"],
            active_from=HourlyDate(
                day=date.fromisoformat(row["active_from_day"]), hour=row["active_from_hour"]
            ),
        )

    @staticmethod
    def _historical_trade_from_row(row: sqlite3.Row) -> HistoricalTrade:
        return HistoricalTrade(
            id=row["id"],
            user_id=row["user_id"],
            symbol=row["symbol"],
            kind=row["kind"],
            requested_price=row["requested_price"],
            quantity=row["quantity"],
            requested_at=row["requested_at"],
            active_from=HourlyDate(
                day=date.fromisoformat(row["active_from_day"]), hour=row["active_from_hour"]
            ),
            fill_price=row["fill_price"],
            closed_at=row["closed_at"],
            closed_at_hour=HourlyDate(
                day=date.fromisoformat(row["closed_at_hour_day"]),
                hour=row["closed_at_hour_hour"],
            ),
            status=row["status"],
        )
