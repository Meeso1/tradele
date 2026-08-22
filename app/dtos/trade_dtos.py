"""Request/response schemas for `app/routers/trades.py`."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.repositories.trade_repository import ActiveTrade, HistoricalTrade, Side


class TradeInput(BaseModel):
    symbol: str
    side: Side
    quantity: int = Field(gt=0)


class SubmitTradesRequest(BaseModel):
    trades: list[TradeInput]


class SubmitTradesResponse(BaseModel):
    trade_ids: list[str]


class TradesResponse(BaseModel):
    requested: list[ActiveTrade]
    closed: list[HistoricalTrade]
