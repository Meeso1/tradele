from fastapi import APIRouter

from app.dependencies import MarketDataServiceDep
from app.dtos.market_dtos import PricesResponse
from app.services.market_data_service import TRADABLE_SYMBOLS

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    """Return the fixed set of symbols players can trade."""
    return TRADABLE_SYMBOLS


@router.get("/prices", response_model=PricesResponse)
def get_prices(market_data_service: MarketDataServiceDep) -> PricesResponse:
    """Return mock current prices for every tradable symbol.

    TODO: these are randomly generated (see `MarketDataService`) - swap in
    a real price feed, and likely snapshot prices once per day instead of
    regenerating them on every request.
    """
    return PricesResponse(prices=market_data_service.get_prices())
