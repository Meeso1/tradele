import logging

import pytest

from app.services.database_service import DatabaseService
from app.services.settings_service import SettingsService


def _new_database_service() -> DatabaseService:
    return DatabaseService(SettingsService(), logging.getLogger("test"))


def test_run_migrations_creates_users_table():
    from app.container import container

    with container.database.connect() as conn:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 1

        conn.execute("INSERT INTO users (id, created_at) VALUES ('u1', 'now')")
        result = conn.execute("SELECT id, created_at FROM users WHERE id = 'u1'").fetchone()
        assert result["id"] == "u1"


def test_run_migrations_is_idempotent():
    from app.container import container

    container.database.run_migrations()
    container.database.run_migrations()

    with container.database.connect() as conn:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 1


def test_validate_versions_rejects_non_contiguous_versions():
    database = _new_database_service()
    with pytest.raises(RuntimeError, match="contiguous"):
        database._validate_versions([1, 3])


def test_validate_versions_rejects_versions_not_starting_at_one():
    database = _new_database_service()
    with pytest.raises(RuntimeError, match="start at version 1"):
        database._validate_versions([2, 3])


def test_add_migration_rejects_duplicate_versions():
    database = _new_database_service()
    database.add_migration(1, "SELECT 1;")
    with pytest.raises(ValueError, match="Duplicate"):
        database.add_migration(1, "SELECT 1;")
