"""Request/response schemas for `app/routers/portfolio.py`."""

from __future__ import annotations

from pydantic import BaseModel


class PortfolioResponse(BaseModel):
    cash: float
    holdings: dict[str, int]
