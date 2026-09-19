from __future__ import annotations

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from app.models.market import HourlyDate


class Portfolio(BaseModel):
    cash: float
    holdings: dict[str, float]
    last_hourly_update: HourlyDate | None


# TODO(cleanup): Let's also store 'recorded_at' (real time)
@dataclass
class HistoricalPortfolio:
    cash: float
    holdings: dict[str, float]
    timestamp: HourlyDate
    total_value: float
