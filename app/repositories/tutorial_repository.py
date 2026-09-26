from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.services.database_service import DatabaseService


# TODO(nitpick): Maybe it would make sense to create some separate repo for random stuff like this
class TutorialRepository:
    def __init__(self, database: DatabaseService, logger: logging.Logger) -> None:
        self._database: DatabaseService = database
        self._logger: logging.Logger = logger

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def has_completed_tutorial(self, user_id: str) -> bool:
        """Return whether the user has completed the tutorial.

        Users without a row here (including unknown user IDs) have not.
        """
        with self._database.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM tutorial_completions WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def mark_tutorial_completed(self, user_id: str) -> None:
        """Record that the user completed the tutorial. Idempotent."""
        with self._database.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tutorial_completions (user_id, completed_at) VALUES (?, ?)",
                (user_id, datetime.now(UTC).isoformat()),
            )
