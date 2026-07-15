"""Request/response schemas for `app/routers/market.py`."""

from __future__ import annotations

from pydantic import BaseModel


class PricesResponse(BaseModel):
    prices: dict[str, float]
