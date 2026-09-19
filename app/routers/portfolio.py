from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import AuthContextDep, PortfolioServiceDep, UserServiceDep, get_auth_context
from app.dtos.portfolio_dtos import PortfolioResponse, PortfolioStateResponse
from app.models.market import HourlyDate

router = APIRouter(prefix="/portfolio", tags=["portfolio"], dependencies=[Depends(get_auth_context)])


@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    auth_context: AuthContextDep,
    user_service: UserServiceDep,
    portfolio_service: PortfolioServiceDep,
) -> PortfolioResponse:
    """Return the authenticated player's current portfolio, creating one if needed."""
    if not user_service.exists(auth_context.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    portfolio = portfolio_service.get_or_create(auth_context.user_id)
    return PortfolioResponse(cash=portfolio.cash, holdings=portfolio.holdings)


@router.get("/history", response_model=list[PortfolioStateResponse])
def get_portfolio_history(
    auth_context: AuthContextDep,
    user_service: UserServiceDep,
    portfolio_service: PortfolioServiceDep,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> list[PortfolioStateResponse]:
    """Return the authenticated player's recorded portfolio states, oldest first.

    States are recorded hourly. `start`/`end` are timestamps, rounded down
    to the hour, and both range ends are inclusive. `start` defaults to the
    first recorded state; `end` defaults to the latest recorded state.
    """
    if not user_service.exists(auth_context.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    states = portfolio_service.get_history(
        auth_context.user_id,
        HourlyDate.containing(start) if start is not None else None,
        HourlyDate.containing(end) if end is not None else None,
    )
    return [
        PortfolioStateResponse(
            cash=state.cash,
            holdings=state.holdings,
            timestamp=state.timestamp,
            total_value=state.total_value,
            recorded_at=state.recorded_at,
        )
        for state in states
    ]
