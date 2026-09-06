"""Request/response schemas for `app/routers/trades.py`."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.market import HourlyDate
from app.models.trade import ActiveTrade, HistoricalTrade, InactiveTradeStatus, Kind


class TradeInput(BaseModel):
    symbol: str
    kind: Kind
    quantity: float = Field(gt=0.001)
    # Required for limit/stop orders (enforced by TradeSubmissionService); ignored for market orders.
    requested_price: float | None = Field(default=None, gt=0)


class SubmitTradesRequest(BaseModel):
    trades: list[TradeInput]


class SubmitTradesResponse(BaseModel):
    trade_ids: list[str]


class ActiveTradeResponse(BaseModel):
    id: str
    user_id: str
    symbol: str
    kind: Kind
    requested_price: float | None
    quantity: float
    requested_at: datetime
    active_from: HourlyDate

    @classmethod
    def from_model(cls, trade: ActiveTrade) -> ActiveTradeResponse:
        return cls(
            id=trade.id,
            user_id=trade.user_id,
            symbol=trade.symbol,
            kind=trade.kind,
            requested_price=trade.requested_price,
            quantity=trade.quantity,
            requested_at=trade.requested_at,
            active_from=trade.active_from,
        )


class HistoricalTradeResponse(BaseModel):
    id: str
    user_id: str
    symbol: str
    kind: Kind
    requested_price: float | None
    quantity: float
    requested_at: datetime
    active_from: HourlyDate
    fill_price: float | None
    closed_at: str
    closed_at_hour: HourlyDate
    status: InactiveTradeStatus

    @classmethod
    def from_model(cls, trade: HistoricalTrade) -> HistoricalTradeResponse:
        return cls(
            id=trade.id,
            user_id=trade.user_id,
            symbol=trade.symbol,
            kind=trade.kind,
            requested_price=trade.requested_price,
            quantity=trade.quantity,
            requested_at=trade.requested_at,
            active_from=trade.active_from,
            fill_price=trade.fill_price,
            closed_at=trade.closed_at,
            closed_at_hour=trade.closed_at_hour,
            status=trade.status,
        )


class TradesResponse(BaseModel):
    requested: list[ActiveTradeResponse]
    closed: list[HistoricalTradeResponse]
