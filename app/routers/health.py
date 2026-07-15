from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Simple liveness check used for monitoring and local sanity checks."""
    return {"status": "ok"}
