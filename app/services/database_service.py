"""Database connections and a small custom migration runner.

`DatabaseService` is intentionally independent of any table's contents. Code
that deals with a specific table (or group of tables backing one "thing")
belongs in its own service instead (e.g. `UserService`).

Migrations live in `app/migrations/` as separate modules, each calling
`container.database.add_migration()` at import time to register a version
number and the SQL that upgrades the schema to it. `run_migrations()` imports
every module in that package (so all migrations are registered) and then
applies any that are newer than the database's current version, in order.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from app.services.settings_service import SettingsService

MIGRATIONS_PACKAGE = "app.migrations"


class DatabaseService:
    def __init__(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger
        self._migrations: dict[int, str] = {}

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        """Point this service at (possibly new) settings/logger.

        Registered migrations are intentionally left untouched - they're
        registered once via module imports (see `_load_migrations`) and
        don't depend on settings.
        """
        self._settings = settings
        self._logger = logger

    def add_migration(self, version: int, sql: str) -> None:
        """Register the SQL that upgrades the schema to `version`.

        Called by modules under `app/migrations/` at import time. Versions
        must be unique; duplicates almost certainly indicate a copy-paste
        mistake.
        """
        if version in self._migrations:
            raise ValueError(f"Duplicate migration version: {version}")
        self._migrations[version] = sql

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection]:
        """Open a connection, commit on success, and roll back on error."""
        conn = sqlite3.connect(self._settings.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _load_migrations(self) -> None:
        """Import every module under `app/migrations` so they self-register."""
        package = importlib.import_module(MIGRATIONS_PACKAGE)
        for module_info in pkgutil.iter_modules(package.__path__):
            importlib.import_module(f"{MIGRATIONS_PACKAGE}.{module_info.name}")

    def _validate_versions(self, versions: list[int]) -> None:
        if not versions:
            return
        if versions[0] != 1:
            raise RuntimeError("Migrations must start at version 1")
        for previous, current in zip(versions, versions[1:]):
            if current != previous + 1:
                message = f"Non-contiguous migration versions: jump from {previous} to {current}"
                raise RuntimeError(message)

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (0)")
            return 0
        return row["version"]

    def run_migrations(self) -> None:
        """Bring the database schema up to date with every registered migration."""
        self._load_migrations()

        versions = sorted(self._migrations)
        self._validate_versions(versions)

        with self.connect() as conn:
            current_version = self._get_schema_version(conn)
            for version in versions:
                if version <= current_version:
                    continue
                self._logger.info("Applying migration %s", version)
                conn.executescript(self._migrations[version])
                conn.execute("UPDATE schema_version SET version = ?", (version,))
                current_version = version

        self._logger.info("Database schema is at version %s", current_version)
