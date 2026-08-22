from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import AuthContextDep, PortfolioServiceDep, UserServiceDep, get_auth_context
from app.dtos.portfolio_dtos import PortfolioResponse

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
