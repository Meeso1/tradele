# Tradele

Backend API for **Tradele**, a daily "-dle"-style guessing game built around stock trading.

## Getting started

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) installed
- Python 3.13 (uv will install/manage this for you if needed)

### Install dependencies

```bash
uv sync
```

### Run the dev server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000, with interactive docs at
http://127.0.0.1:8000/docs (Swagger UI) and http://127.0.0.1:8000/redoc (ReDoc).

### Run tests

```bash
uv run pytest
```

### Lint

```bash
uv run ruff check .
```

## Project layout

```
app/            # FastAPI application package
  main.py       # FastAPI app instance and route registration
tests/          # pytest test suite, mirrors the app/ structure
```

## Contributing

See [AGENTS.md](./AGENTS.md) for project conventions.
