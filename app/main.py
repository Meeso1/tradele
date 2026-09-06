from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import container
from app.routers import api_keys, auth, health, market, portfolio, scheduled_jobs, trades, users


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
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(market.router)
app.include_router(portfolio.router)
app.include_router(trades.router)
app.include_router(scheduled_jobs.router)
