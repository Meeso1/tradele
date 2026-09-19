"""Request/response schemas for `app/routers/market.py`."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.models.market import HourlyDate, HourlyPriceData


class PriceHistoryRange(str, Enum):
    """Convenience ranges for the prices endpoint (exclusive with start/end)."""

    CURRENT_HOUR = "current_hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class MarketStateResponse(BaseModel):
    hour: HourlyDate
    prices: dict[str, HourlyPriceData]
    market_open: bool
