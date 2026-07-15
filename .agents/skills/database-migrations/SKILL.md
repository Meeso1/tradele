---
name: database-migrations
description: Explains Tradele's custom sqlite migration system - how to add a new migration, how DatabaseService and the schema_version table work, and the rules migration versions must follow. Use this whenever changing the database schema (adding/altering tables) in the tradele backend.
---

# Database migrations in Tradele

Tradele uses a small hand-rolled migration system instead of a migration
framework (e.g. Alembic). This is intentional - the schema is simple and this
keeps things dependency-free. Follow this convention exactly; the runner
depends on it.

## How it works

- `app/services/database_service.py` defines `DatabaseService`, which owns:
  - `add_migration(version, sql)` - registers the SQL that upgrades the schema
    to `version`.
  - `run_migrations()` - imports every module under `app/migrations/` (which
    register migrations as a side effect of being imported), then applies any
    migration whose version is greater than the database's current version,
    in ascending order, inside a single transaction per call.
  - A `schema_version` table (created automatically) stores the current
    version as a single row.
- `app/container.py` constructs one `DatabaseService` instance
  (`container.database`) that is reused for the life of the process. Always
  register/run migrations through this instance, not a new `DatabaseService()`.
- `app/main.py` calls `container.database.run_migrations()` during the
  FastAPI `lifespan` startup, so migrations run automatically whenever the
  app starts.

## Adding a new migration

1. Create a new file under `app/migrations/`, named `m{version:04d}_{short_description}.py`
   (e.g. `m0002_add_guesses_table.py`). Every file in this directory is
   auto-imported by `run_migrations()` via `pkgutil`, so the file **must**
   live directly in `app/migrations/` - there's no separate registration
   list to update.
2. In that file, import the shared container and register the migration:

   ```python
   from app.container import container

   container.database.add_migration(
       version=2,
       sql="""
       CREATE TABLE guesses (
           id TEXT PRIMARY KEY,
           user_id TEXT NOT NULL REFERENCES users(id),
           created_at TEXT NOT NULL
       );
       """,
   )
   ```

3. Version numbers must:
   - Start at `1`.
   - Be contiguous across all migrations (no gaps). `run_migrations()`
     validates this and raises `RuntimeError` if a jump is detected - this
     is meant to catch a migration file being deleted or renamed with the
     wrong version after the fact.
   - Be unique. `add_migration()` raises `ValueError` on a duplicate version.
4. `sql` can contain multiple statements (it's run via `executescript`), so a
   single migration can create/alter several tables if they belong together.
5. Never edit the SQL of a migration that has already shipped/been applied
   anywhere (including in your own local dev db) - add a new migration with
   the next version number instead. Editing a past migration's SQL has no
   effect on databases that already recorded that version as applied.

## Testing migrations

- Tests should go through `container.database` (imported from
  `app.container`), not construct a bare `DatabaseService()`, except when
  specifically testing `DatabaseService`'s validation logic in isolation
  (e.g. `_validate_versions`), where a fresh instance (with its own
  `SettingsService` and a throwaway `logging.Logger`) is appropriate.
- The `tests/conftest.py` `isolated_runtime_data` fixture points
  `TRADELE_DB_PATH` at a per-test temp file, calls `container.reset()` (so
  `DatabaseService` picks up the new path - see the `SettingsService`
  section of `AGENTS.md`), and then calls `container.database.run_migrations()`
  before every test, so each test starts from a fresh, fully-migrated
  schema. You don't need to call `run_migrations()` yourself in individual
  tests.
- `container.reset()` does not clear `DatabaseService`'s registered
  migrations (only its settings/logger) - migrations are registered once,
  the first time `app.migrations` modules are imported, and Python's module
  cache means re-importing them on a later `run_migrations()` call would be
  a no-op anyway.
