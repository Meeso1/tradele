from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import container
from app.routers import auth, health, users


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    container.database.run_migrations()
    yield


app = FastAPI(
    title="Tradele API",
    description="Backend API for Tradele, a daily stock-trading guessing game.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(users.router)
app.include_router(auth.router)
