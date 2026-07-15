"""Data access and row/model mapping for the `portfolios` table.

A player's portfolio (cash + share holdings) is stored as a single JSON
blob per user, rather than normalized columns/rows, since it's always read
and written as a whole and there's no need to query into it from SQL yet.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from app.services.database_service import DatabaseService


class Portfolio(BaseModel):
    cash: float
    holdings: dict[str, int]


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
