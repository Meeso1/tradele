from fastapi import APIRouter, HTTPException, status

from app.dependencies import PortfolioServiceDep, UserServiceDep
from app.dtos.portfolio_dtos import PortfolioResponse

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    user_id: str,
    user_service: UserServiceDep,
    portfolio_service: PortfolioServiceDep,
) -> PortfolioResponse:
    """Return the player's current portfolio, creating one if needed.

    TODO: `user_id` should come from an authenticated session instead of a
    query parameter, once there's a dependency that extracts it from the
    access token issued by `/auth/token`.
    """
    if not user_service.exists(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    portfolio = portfolio_service.get_or_create(user_id)
    return PortfolioResponse(cash=portfolio.cash, holdings=portfolio.holdings)
