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
import itertools
import logging
import pkgutil
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType

from app.services.settings_service import SettingsService

MIGRATIONS_PACKAGE = "app.migrations"


class DbTransaction:
    """Groups several repository calls into one atomic SQL transaction.

    Obtained via `DatabaseService.transaction()` and used as a context
    manager. While active, `DatabaseService.connect()` - including calls
    made indirectly by repositories - transparently returns this
    transaction's connection instead of opening a new one, so repository
    calls made anywhere inside the `with` block join the same transaction
    without a connection having to be passed to them explicitly.

    Relies on `DatabaseService` being used as a singleton (one instance per
    process, via `container.database`) - the active connection is tracked
    as a plain attribute on it rather than anything concurrency-aware.
    """

    def __init__(self, database: DatabaseService, conn: sqlite3.Connection) -> None:
        self._database: DatabaseService = database
        self._conn: sqlite3.Connection = conn

    def __enter__(self) -> DbTransaction:
        self._database._active_connection = self._conn  # pyright: ignore[reportPrivateUsage]
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._database._active_connection = None  # pyright: ignore[reportPrivateUsage]
            self._conn.close()


class DatabaseService:
    def __init__(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger
        self._migrations: dict[int, str] = {}
        self._active_connection: sqlite3.Connection | None = None

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

    def transaction(self) -> DbTransaction:
        """Start a transaction spanning multiple repository calls.

        Use as a context manager: `with database.transaction(): ...`.
        Everything run inside the block - including via repositories -
        shares one connection and commits or rolls back atomically.
        """
        return DbTransaction(self, self._new_connection())

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection]:
        """Open a connection, commit on success, and roll back on error.

        If a `transaction()` is currently active, returns its connection
        instead of opening a new one, leaving committing/rolling
        back/closing it to that transaction.
        """
        if self._active_connection is not None:
            yield self._active_connection
            return

        conn = self._new_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._settings.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

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
        for previous, current in itertools.pairwise(versions):
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
