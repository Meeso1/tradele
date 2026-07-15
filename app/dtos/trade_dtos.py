"""Request/response schemas for `app/routers/trades.py`."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.repositories.trade_repository import ExecutedTrade, RequestedTrade, Side


class TradeInput(BaseModel):
    symbol: str
    side: Side
    quantity: int = Field(gt=0)


class SubmitTradesRequest(BaseModel):
    # TODO: `user_id` should come from an authenticated session instead of
    # the request body, once there's a dependency that extracts it from
    # the access token issued by `/auth/token` (see `app/routers/auth.py`).
    user_id: str
    trades: list[TradeInput]


class SubmitTradesResponse(BaseModel):
    trade_ids: list[str]


class TradesResponse(BaseModel):
    requested: list[RequestedTrade]
    executed: list[ExecutedTrade]
