"""Request/response schemas for `app/routers/market.py`."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.market import HourlyPriceData


class PricesResponse(BaseModel):
    prices: dict[str, HourlyPriceData]
    market_open: bool
