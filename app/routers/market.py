from fastapi import APIRouter, Depends

from app.dependencies import MarketDataServiceDep, SettingsServiceDep, get_auth_context
from app.dtos.market_dtos import PricesResponse
from app.models.market import HourlyDate

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_auth_context)])


# TODO: Maybe return some more metadata about symbols here?
@router.get("/symbols", response_model=list[str])
def get_symbols(settings: SettingsServiceDep) -> list[str]:
    """Return the configured set of symbols players can trade."""
    return settings.tradable_symbols


@router.get("/prices", response_model=PricesResponse)
def get_prices(market_data_service: MarketDataServiceDep) -> PricesResponse:
    """Return current (hourly) prices for every tradable symbol."""
    market_state = market_data_service.get_prices_for_hour(HourlyDate.last_passed_hour())
    return PricesResponse(prices=market_state.prices, market_open=market_state.market_open)

# TODO: Some historical prices endpoint for plots etc.
