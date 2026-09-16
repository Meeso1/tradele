from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.container import container
from app.routers import api_keys, auth, health, market, portfolio, scheduled_jobs, trades, users, metadata

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    container.database.run_migrations()
    container.service_account_creator.ensure_exists()
    container.job_scheduler.start()
    try:
        yield
    finally:
        await container.job_scheduler.stop()


app = FastAPI(
    title="Tradele API",
    description="Backend API for Tradele, a daily stock-trading guessing game.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(api_keys.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(trades.router, prefix=API_PREFIX)
app.include_router(scheduled_jobs.router, prefix=API_PREFIX)
app.include_router(metadata.router, prefix=API_PREFIX)


# Catch unmatched `/api/...` routes and return 404
@app.api_route(
    f"{API_PREFIX}/{{_path:path}}",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"],
    include_in_schema=False,
)
async def api_not_found(_path: str) -> None:
    raise HTTPException(status_code=404, detail="Not Found")


# Serve frontend from `/`
@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str) -> FileResponse:
    dist_root = container.settings.frontend_dist_dir.resolve()
    index = dist_root / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Frontend not built")
    if path:
        candidate = (dist_root / path).resolve()
        # Allowlist of servable locations: 
        # - files directly in the dist root
        # - files under `dist/assets/` (build output)
        if candidate.is_file() and (
            candidate.parent == dist_root or candidate.is_relative_to(dist_root / "assets")
        ):
            return FileResponse(candidate)
    return FileResponse(index)
