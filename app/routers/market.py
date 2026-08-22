from datetime import datetime, timedelta

from fastapi import APIRouter

from app.dependencies import MarketDataServiceDep
from app.dtos.market_dtos import PricesResponse
from app.services.market_data_service import TRADABLE_SYMBOLS, HourlyDate

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    """Return the fixed set of symbols players can trade."""
    return TRADABLE_SYMBOLS


@router.get("/prices", response_model=PricesResponse)
def get_prices(market_data_service: MarketDataServiceDep) -> PricesResponse:
    """Return mock current prices for every tradable symbol."""
    # TODO: add timezone to settings and replace all `datetime.now()` calls with some mini-service that provides timezone-aware timestamps
    return PricesResponse(prices=market_data_service.get_prices(HourlyDate.containing(datetime.now() - timedelta(hours=1))))

# TODO: Some historical prices endpoint for plots etc.
