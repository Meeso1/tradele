from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from app.services.database_service import DatabaseService
from app.services.market_data_service import TRADABLE_SYMBOLS, HourlyDate


STARTING_CASH: float = 100_000.0


class Portfolio(BaseModel):
    cash: float
    holdings: dict[str, float]
    last_hourly_update: HourlyDate | None


class PortfolioRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
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

    def _default_portfolio(self) -> Portfolio:
        return Portfolio(
            cash=STARTING_CASH,
            holdings={symbol: 0 for symbol in TRADABLE_SYMBOLS},
            last_hourly_update=HourlyDate.containing(datetime.now(UTC)),
        )
