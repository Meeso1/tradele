# Agent Instructions

This is the backend for **Tradele**, a daily "-dle"-style guessing game built around stock
trading.

## Stack

- **Language:** Python 3.13
- **Package/dependency manager:** [`uv`](https://docs.astral.sh/uv/)
- **Web framework:** [FastAPI](https://fastapi.tiangolo.com/) served by `uvicorn`
- **Testing:** `pytest` (+ FastAPI's `TestClient`, backed by `httpx`)
- **Linting:** `ruff`

## Project layout

- `app/` — application package
  - `app/main.py` — FastAPI app instance and route registration
  - `app/routers/` — FastAPI routers, one module per domain/feature
  - `app/services/` — service classes containing business logic and persistence
  - `app/migrations/` — database migrations (see `app/services/database_service.py`)
  - `app/container.py` — manual dependency wiring for services
  - `app/dependencies.py` — FastAPI `Depends` functions exposing container services to routes
- `tests/` — pytest test suite, mirrors the `app/` structure

## Conventions

- Add new routes as FastAPI routers under `app/routers/`, and include them in `app/main.py`.
  Prefer splitting by domain/feature once there's more than a couple of endpoints (e.g.
  `app/routers/game.py`).
- Use type hints everywhere; FastAPI relies on them for request/response validation.
- Prefer Pydantic models for request/response schemas over raw dicts.
- Keep business logic out of route handlers — route handlers should stay thin and delegate to
  services.
- Business logic and persistence live in service classes under `app/services/` (e.g.
  `UserService`, `AuthService`, `DatabaseService`). Avoid loose module-level functions for this
  kind of logic — prefer a class, even if it currently only has one method, since it gives
  dependencies (like `DatabaseService`) a clear place to be injected and makes the service easy
  to extend later.
- Configuration is centralized in `SettingsService` (`app/services/settings_service.py`), which
  resolves environment variables once when it's constructed. Don't read `os.environ` anywhere
  else — take a `SettingsService` as a constructor dependency instead. This also means the
  source of config could later change (e.g. to a JSON file) without touching call sites.
- Logging goes through `LoggerService` (`app/services/logger_service.py`), which writes to both
  the console and a log file. Services take a `logging.Logger` (via
  `logger_service.get_logger("SomeService")`) as a constructor dependency and log through it
  rather than using `print` or the root logger directly.
- Services are wired together manually in `app/container.py` (a single `Container` instance
  constructed once, with dependencies passed in via constructors — no DI framework). Add new
  services there rather than instantiating them elsewhere.
- Routes should not import `container` directly. Instead, add a `get_<thing>_service()` function
  to `app/dependencies.py`, plus a corresponding `<Thing>ServiceDep = Annotated[<Thing>Service,
  Depends(get_<thing>_service)]` alias, and depend on it by using that alias as a parameter type
  (e.g. `user_service: UserServiceDep`) rather than a `Depends(...)` default value. This keeps
  `Depends(...)` calls in one place and lets tests override the underlying function via
  `app.dependency_overrides` if needed.
- Don't use `__all__` in modules just to control/shorten what other modules can import from them
  (e.g. to make a re-export look intentional). Import the thing directly from the module that
  actually defines it instead. `__all__` is fine if there's a genuine reason unrelated to import
  ergonomics (e.g. controlling `from module import *`), but that's rare in this codebase.
- Endpoints are protected (require a valid access token) by default. A route is only allowed to
  be anonymous if it fundamentally can't require auth yet (e.g. `POST /users`, which creates the
  account, or `POST /auth/token`, which issues the token in the first place) - new routes should
  default to being protected unless there's a similarly fundamental reason not to be. To protect
  a whole router, pass `dependencies=[Depends(get_auth_context)]` to its `APIRouter(...)` (see
  `app/routers/portfolio.py` or `app/routers/trades.py`); routes that also need to know *who's*
  calling should additionally depend on `AuthContextDep` (from `app/dependencies.py`) to get the
  caller's `user_id` (and, potentially, other claims later) - FastAPI caches the underlying
  dependency per request, so this doesn't verify the token twice.
- For database access and migrations, see the `database-migrations` skill.
- Tests run against a per-test temp DB/keys/log directory (see `tests/conftest.py`), which
  requires calling `container.reset()` after changing env vars via `monkeypatch`, since
  `SettingsService` resolves the environment once at construction time. Services expose a
  `configure(...)` method for this rather than being fully reconstructed, so state that must
  persist across a reset (e.g. registered migrations) survives it.
- Add/update tests under `tests/` for any new route or non-trivial logic. Tests mirror the `app/`
  structure (e.g. `app/services/user_service.py` → `tests/services/test_user_service.py`,
  `app/routers/users.py` → `tests/routers/test_users.py`).

## Common commands

Run these from the repo root.

```bash
# Install/sync dependencies
uv sync

# Run the dev server (auto-reloads on change)
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## Notes for agents

- This repo is backend-only. A separate frontend project consumes this API.
- Don't commit `.venv/` or other local environment artifacts (already covered by `.gitignore`).
- When adding dependencies, use `uv add <package>` (or `uv add --dev <package>` for dev-only
  tools) rather than editing `pyproject.toml` by hand, so `uv.lock` stays in sync.
