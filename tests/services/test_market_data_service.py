from datetime import date, datetime

from app.container import container
from app.models.market import HourlyDate
from app.services.market_data_service import TRADABLE_SYMBOLS


def test_get_prices_returns_a_price_for_every_tradable_symbol():
    market_state = container.market_data.get_prices(HourlyDate(day=date(2024, 1, 1), hour=10))

    assert set(market_state.prices.keys()) == set(TRADABLE_SYMBOLS)
    assert all(price_data.close > 0 for price_data in market_state.prices.values())


def test_hourly_date_containing_extracts_day_and_hour():
    hourly_date = HourlyDate.containing(datetime(2024, 1, 1, 10, 30))

    assert hourly_date.day == date(2024, 1, 1)
    assert hourly_date.hour == 10
