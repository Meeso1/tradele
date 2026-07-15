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
- `tests/` — pytest test suite, mirrors the `app/` structure

## Conventions

- Add new routes as FastAPI routers under `app/`, and include them in `app/main.py`. Prefer
  splitting by domain/feature once there's more than a couple of endpoints (e.g.
  `app/routers/game.py`).
- Use type hints everywhere; FastAPI relies on them for request/response validation.
- Prefer Pydantic models for request/response schemas over raw dicts.
- Keep business logic out of route handlers where practical — route handlers should stay thin.
- Add/update tests under `tests/` for any new route or non-trivial logic.

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
