from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.dependencies import TradeRepositoryDep, TradeServiceDep, UserServiceDep
from app.dtos.trade_dtos import SubmitTradesRequest, SubmitTradesResponse, TradesResponse
from app.services.market_data_service import HourlyDate
from app.services.trade_submission_service import (
    TradeRequest,
    TradesAlreadySubmittedError,
    TradeValidationError,
)

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("", response_model=SubmitTradesResponse, status_code=201)
def submit_trades(
    request: SubmitTradesRequest,
    user_service: UserServiceDep,
    trade_service: TradeServiceDep,
) -> SubmitTradesResponse:
    """Submit a player's one-per-day batch of trade requests."""
    if not user_service.exists(request.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    trade_requests = [
        TradeRequest(symbol=trade.symbol, side=trade.side, quantity=trade.quantity)
        for trade in request.trades
    ]
    date = HourlyDate.containing(datetime.now() + timedelta(hours=1))
    
    try:
        trade_ids = trade_service.submit(request.user_id, trade_requests, date)
    except TradesAlreadySubmittedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except TradeValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return SubmitTradesResponse(trade_ids=trade_ids)


@router.get("", response_model=TradesResponse)
def get_trades(
    user_id: str,
    user_service: UserServiceDep,
    trade_repo: TradeRepositoryDep,
) -> TradesResponse:
    """Return a player's requested and executed trade history.

    TODO: same auth caveat as `submit_trades` above - `user_id` is a query
    parameter for now instead of coming from an authenticated session.
    """
    if not user_service.exists(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return TradesResponse(
        requested=trade_repo.list_requested(user_id),
        closed=trade_repo.list_executed(user_id),
    )
