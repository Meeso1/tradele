from fastapi import FastAPI

app = FastAPI(
    title="Tradele API",
    description="Backend API for Tradele, a daily stock-trading guessing game.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple liveness check used for monitoring and local sanity checks."""
    return {"status": "ok"}
