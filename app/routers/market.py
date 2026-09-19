from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import MarketDataServiceDep, SettingsServiceDep, get_auth_context
from app.dtos.market_dtos import MarketStateResponse, PriceHistoryRange
from app.models.market import HourlyDate

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_auth_context)])


# TODO: Maybe return some more metadata about symbols here?
@router.get("/symbols", response_model=list[str])
def get_symbols(settings: SettingsServiceDep) -> list[str]:
    """Return the configured set of symbols players can trade."""
    return settings.tradable_symbols


@router.get("/prices", response_model=list[MarketStateResponse])
def get_prices(
    market_data_service: MarketDataServiceDep,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    range: Annotated[PriceHistoryRange | None, Query()] = None,
) -> list[MarketStateResponse]:
    """Return hourly prices for every tradable symbol, one state per hour.

    Hours with no data (e.g. market closed) have empty `prices`. The range
    is inclusive on both ends, and any timestamps are rounded down to the
    hour. `end` defaults to the latest hour for which market data is
    available; `start` defaults to `end`.

    Instead of `start`/`end`, a `range` shortcut can be passed: a trailing
    window of fixed length ending at the latest available hour (so a day
    always yields 24 hourly states, a week 168, etc.). It's exclusive with
    `start`/`end`, and defaults to `current_hour` when neither is given.
    """
    if range is not None and (start is not None or end is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="range is exclusive with start/end"
        )

    if range is not None:
        range_start, range_end = _range_bounds(range)
    else:
        range_end = (
            HourlyDate.containing(end) if end is not None else HourlyDate.last_passed_hour()
        )
        range_start = HourlyDate.containing(start) if start is not None else range_end

    return [
        MarketStateResponse(hour=state.hour, prices=state.prices, market_open=state.market_open)
        for state in market_data_service.get_prices_for_range(range_start, range_end)
    ]


# Trailing window length per convenience range; the response always spans
# exactly this many hourly states, ending at the latest available hour.
_RANGE_LENGTHS: dict[PriceHistoryRange, timedelta] = {
    PriceHistoryRange.CURRENT_HOUR: timedelta(hours=1),
    PriceHistoryRange.DAY: timedelta(days=1),
    PriceHistoryRange.WEEK: timedelta(days=7),
    PriceHistoryRange.MONTH: timedelta(days=30),
    PriceHistoryRange.YEAR: timedelta(days=365),
}


def _range_bounds(range_value: PriceHistoryRange) -> tuple[HourlyDate, HourlyDate]:
    """Resolve a convenience range to the inclusive [start, end] hour bounds."""
    end = HourlyDate.last_passed_hour()
    start = end - (_RANGE_LENGTHS[range_value] - timedelta(hours=1))
    return start, end
