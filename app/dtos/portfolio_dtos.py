"""Request/response schemas for `app/routers/portfolio.py`."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.market import HourlyDate


class PortfolioResponse(BaseModel):
    cash: float
    holdings: dict[str, float]


class PortfolioStateResponse(BaseModel):
    cash: float
    holdings: dict[str, float]
    timestamp: HourlyDate
    total_value: float
    recorded_at: datetime
