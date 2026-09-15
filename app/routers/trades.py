
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    AuthContextDep,
    TradeRepositoryDep,
    TradeServiceDep,
    UserServiceDep,
    get_auth_context,
)
from app.dtos.trade_dtos import (
    ActiveTradeResponse,
    HistoricalTradeResponse,
    SubmitTradesRequest,
    SubmitTradesResponse,
    TradesResponse,
)
from app.models.market import HourlyDate
from app.services.trade_submission_service import (
    TradeRequest,
    TradesAlreadySubmittedError,
    TradeValidationError,
)

router = APIRouter(prefix="/trades", tags=["trades"], dependencies=[Depends(get_auth_context)])


# TODO: also allow cancelling trades through this endpoint - also in a single, daily batch, together with submitting trades
@router.post("", response_model=SubmitTradesResponse, status_code=201)
def submit_trades(
    request: SubmitTradesRequest,
    auth_context: AuthContextDep,
    user_service: UserServiceDep,
    trade_service: TradeServiceDep,
) -> SubmitTradesResponse:
    """Submit the authenticated player's one-per-day batch of trade requests."""
    if not user_service.exists(auth_context.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    trade_requests = [
        TradeRequest(
            symbol=trade.symbol,
            kind=trade.kind,
            quantity=trade.quantity,
            requested_price=trade.requested_price,
        )
        for trade in request.trades
    ]
    date = HourlyDate.current()

    try:
        trade_ids = trade_service.submit(auth_context.user_id, trade_requests, date)
    except TradesAlreadySubmittedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except TradeValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return SubmitTradesResponse(trade_ids=trade_ids)


@router.get("", response_model=TradesResponse)
def get_trades(
    auth_context: AuthContextDep,
    user_service: UserServiceDep,
    trade_repo: TradeRepositoryDep,
) -> TradesResponse:
    """Return the authenticated player's requested and closed trade history."""
    if not user_service.exists(auth_context.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return TradesResponse(
        requested=[
            ActiveTradeResponse.from_model(trade)
            for trade in trade_repo.list_requested(auth_context.user_id)
        ],
        closed=[
            HistoricalTradeResponse.from_model(trade)
            for trade in trade_repo.list_executed(auth_context.user_id)
        ],
    )

# TODO: add endpoint returning 'changes since last submission' - should be db-side-computable now
# TODO: add endpoint for checking if submission was made today.
