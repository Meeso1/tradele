from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, date, datetime

from app.models.market import HourlyDate
from app.models.portfolio import HistoricalPortfolio, Portfolio
from app.services.database_service import DatabaseService
from app.services.settings_service import SettingsService


STARTING_CASH: float = 100_000.0


class PortfolioRepository:
    def __init__(
        self, database: DatabaseService, settings: SettingsService, logger: logging.Logger
    ) -> None:
        self._database: DatabaseService = database
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def get(self, user_id: str) -> Portfolio | None:
        with self._database.connect() as conn:
            row = conn.execute(
                "SELECT data FROM portfolios WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return Portfolio.model_validate_json(row["data"])

    def insert(self, user_id: str, portfolio: Portfolio) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "INSERT INTO portfolios (user_id, data, updated_at) VALUES (?, ?, ?)",
                (user_id, portfolio.model_dump_json(), datetime.now(UTC).isoformat()),
            )

    def update(self, user_id: str, portfolio: Portfolio) -> None:
        with self._database.connect() as conn:
            conn.execute(
                "UPDATE portfolios SET data = ?, updated_at = ? WHERE user_id = ?",
                (portfolio.model_dump_json(), datetime.now(UTC).isoformat(), user_id),
            )

    def get_or_create(self, user_id: str) -> Portfolio:
        portfolio = self.get(user_id)
        if portfolio is not None:
            return portfolio

        portfolio = self._default_portfolio()
        self.insert(user_id, portfolio)
        self._logger.info("Created portfolio for user %s", user_id)
        return portfolio

    def try_record_state(self, user_id: str, state: HistoricalPortfolio) -> bool:
        """Record a portfolio state, unless one already exists for its hour.

        Returns True if the state was recorded, False if a state for the
        same (user, hour) already existed - states are recorded at most
        once per hour, so the first writer wins.
        """
        # TODO(nitpick): we will have a bunch of no-change records when the market is closed - would be nice to skip these, and recreate on demand, on the backend, or even on the frontend.
        with self._database.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO portfolio_states (user_id, day, hour, cash, holdings, total_value, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, day, hour) DO NOTHING
                """,
                (
                    user_id,
                    state.timestamp.day.isoformat(),
                    state.timestamp.hour,
                    state.cash,
                    json.dumps(state.holdings),
                    state.total_value,
                    state.recorded_at.isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def get_states(
        self,
        user_id: str,
        start: HourlyDate | None,
        end: HourlyDate | None,
    ) -> list[HistoricalPortfolio]:
        """Return the user's recorded states in [start, end], both ends
        inclusive, oldest first.

        `start` defaults to the first recorded state; `end` defaults to
        unbounded, so the latest state is included.
        """
        query = "SELECT * FROM portfolio_states WHERE user_id = ?"
        params: list[object] = [user_id]
        if start is not None:
            query += " AND (day > ? OR (day = ? AND hour >= ?))"
            params.extend([start.day.isoformat(), start.day.isoformat(), start.hour])
        if end is not None:
            query += " AND (day < ? OR (day = ? AND hour <= ?))"
            params.extend([end.day.isoformat(), end.day.isoformat(), end.hour])
        query += " ORDER BY day, hour"

        with self._database.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._state_from_row(row) for row in rows]

    def get_last_recorded_hour(self, user_id: str) -> HourlyDate | None:
        """Return the latest hour a state was recorded for the user, if any."""
        with self._database.connect() as conn:
            row = conn.execute(
                """
                SELECT day, hour FROM portfolio_states
                WHERE user_id = ?
                ORDER BY day DESC, hour DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return HourlyDate(day=date.fromisoformat(row["day"]), hour=row["hour"])

    @staticmethod
    def _state_from_row(row: sqlite3.Row) -> HistoricalPortfolio:
        return HistoricalPortfolio(
            cash=row["cash"],
            holdings=json.loads(row["holdings"]),
            timestamp=HourlyDate(day=date.fromisoformat(row["day"]), hour=row["hour"]),
            total_value=row["total_value"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )

    def _default_portfolio(self) -> Portfolio:
        return Portfolio(
            cash=STARTING_CASH,
            holdings={symbol: 0 for symbol in self._settings.tradable_symbols},
            last_hourly_update=HourlyDate.containing(datetime.now(UTC)),
        )
