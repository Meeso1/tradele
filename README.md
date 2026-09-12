# Tradele

**Tradele** is a daily "-dle"-style game built around stock trading. This repo
contains both the FastAPI backend and the React frontend; in production a single FastAPI
app serves both.

## Getting started

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) installed
- Python 3.13 (uv will install/manage this for you if needed)
- Node.js 22+ and npm (for the frontend)

### Install dependencies

```bash
uv sync
cd frontend && npm install
```

### Run in development

Start the backend:

```bash
uv run uvicorn app.main:app --reload
```

The API is available at http://127.0.0.1:8000, with interactive docs at
http://127.0.0.1:8000/docs (Swagger UI) and http://127.0.0.1:8000/redoc (ReDoc).
All API routes are mounted under `/api`.

Start the frontend dev server (hot module replacement):

```bash
cd frontend && npm run dev
```

and open http://localhost:5173. The Vite dev server proxies `/api` requests to the
backend on port 8000, so the frontend uses same-origin relative URLs everywhere
(no CORS needed).

### Serve the UI from FastAPI

Building the frontend produces static files that FastAPI serves at `/`:

```bash
cd frontend && npm run build
uv run uvicorn app.main:app
```

http://127.0.0.1:8000/ now serves the UI, while http://127.0.0.1:8000/api/... serves
the API. If `frontend/dist/` doesn't exist, the app behaves as a pure API.

#### Configuration

Settings are read from environment variables (see `app/services/settings_service.py`),
including `TRADELE_FRONTEND_DIST` (default `frontend/dist`) for the built frontend's
location. A `.env` file with placeholder values is included for local development -
fill in real Alpaca API credentials (used by `MarketDataService` to fetch real hourly
stock prices) and load it with `uv run`'s built-in `--env-file` support:

```bash
uv run --env-file .env uvicorn app.main:app --reload
```

### Run tests

```bash
uv run pytest
```

### Lint

```bash
uv run ruff check .
```

## Docker

The multi-stage `Dockerfile` builds the frontend, installs Python dependencies with uv,
and produces a slim runtime image serving both the API and the UI:

```bash
docker build -t tradele .
docker run -p 8000:8000 tradele
```

Runtime state (the SQLite database, JWT signing keys, logs) defaults to paths relative
to the working directory inside the container, and is ephemeral - for persistent
deployments, point `TRADELE_DB_PATH`, `TRADELE_KEYS_DIR`, and `TRADELE_LOG_DIR` at a
mounted volume.

## Project layout

```
app/            # FastAPI application package
  main.py       # FastAPI app instance, route registration, SPA serving
frontend/       # React (Vite + TypeScript) UI
tests/          # pytest test suite, mirrors the app/ structure
Dockerfile      # multi-stage image build (frontend + backend)
```

## Contributing

See [AGENTS.md](./AGENTS.md) for project conventions.
