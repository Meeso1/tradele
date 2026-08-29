from __future__ import annotations

from pydantic import BaseModel

from app.models.market import HourlyDate


class Portfolio(BaseModel):
    cash: float
    holdings: dict[str, float]
    last_hourly_update: HourlyDate | None
