from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.market import HourlyDate

Kind = Literal[
    "market_buy",
    "market_sell",
    "limit_buy",
    "limit_sell",
    "stop_buy",
    "stop_sell",
]
InactiveTradeStatus = Literal[
    "executed",
    "cancelled",
    "error",
    "insufficient_funds",
    "symbol_unavailable",
    "malformed_request",
]


class ActiveTrade(BaseModel):
    """
    Trade that is active and will attempt to be executed 
    against every subsequent hour window.
    """
    id: str
    user_id: str
    symbol: str
    kind: Kind
    requested_price: float | None
    quantity: float | None
    value: float | None
    requested_at: datetime # Real time at which the trade was requested
    active_from: HourlyDate # Hour when the trade is active. After being posted, the trade starts being active from the next full hour.


class HistoricalTrade(BaseModel):
    """
    Trade is no longer active - due to being executed, cancelled, etc.
    """
    id: str
    user_id: str
    symbol: str
    kind: Kind
    requested_price: float | None
    quantity: float | None
    value: float | None
    requested_at: datetime
    active_from: HourlyDate
    fill_price: float | None # Price at which the trade was executed, or None if it wasn't executed
    closed_at: str # Real time at which the trade was closed (due to execution, cancellation, etc.)
    closed_at_hour: HourlyDate # Hourly window during which the trade was closed (not real time)
    status: InactiveTradeStatus # Status of the trade after it has been closed
