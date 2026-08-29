"""Request/response schemas for `app/routers/market.py`."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.market_data_service import HourlyPriceData


class PricesResponse(BaseModel):
    prices: dict[str, HourlyPriceData]
