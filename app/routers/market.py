from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.dependencies import MarketDataServiceDep, get_auth_context
from app.dtos.market_dtos import PricesResponse
from app.services.market_data_service import TRADABLE_SYMBOLS, HourlyDate

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_auth_context)])


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    """Return the fixed set of symbols players can trade."""
    return TRADABLE_SYMBOLS


@router.get("/prices", response_model=PricesResponse)
def get_prices(market_data_service: MarketDataServiceDep) -> PricesResponse:
    """Return mock current prices for every tradable symbol."""
    now = datetime.now(UTC)
    market_state = market_data_service.get_prices(HourlyDate.containing(now - timedelta(hours=1)))
    return PricesResponse(prices=market_state.prices)

# TODO: Some historical prices endpoint for plots etc.
