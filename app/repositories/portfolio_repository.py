from __future__ import annotations

import logging
from datetime import UTC, datetime

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
        # TODO(cleanup): should store a portfolio state in a new table.
        # Should insert only if the state doesn't exist for the current hour. Returns True if the state was recorded.
        # TODO(nitpick): we will have a bunch of no-change records when the market is closed - would be nice to skip these, and recreate on demand, on the backend, or even on the frontend.
        ...

    # TODO(cleanup): Create an endpoint returning that. Maybe we can also have an option to specify i.e. 'past month' instead of start and end?
    def get_states(
        self,
        user_id: str,
        start: HourlyDate | None,
        end: HourlyDate | None,
    ) -> list[HistoricalPortfolio]:
        # TODO(cleanup): should return all stored portfolio states for the given user_id from [start, end) range.
        # Start defaults to the first available state, and end defaults to the current time (latest state is also returned).
        ...

    def get_last_recorded_hour(self, user_id: str) -> HourlyDate | None:
        # TODO(cleanup): should return the last recorded hour for the given user_id.
        ...

    def _default_portfolio(self) -> Portfolio:
        return Portfolio(
            cash=STARTING_CASH,
            holdings={symbol: 0 for symbol in self._settings.tradable_symbols},
            last_hourly_update=HourlyDate.containing(datetime.now(UTC)),
        )
