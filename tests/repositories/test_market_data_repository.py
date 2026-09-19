from datetime import date

from app.container import container
from app.models.market import HourlyDate, HourlyPriceData

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)


def test_get_cached_returns_empty_dict_when_nothing_is_cached():
    assert container.market_data_repository.get_cached(["AAPL", "MSFT"], HOUR) == {}


def test_get_cached_returns_empty_dict_for_no_symbols():
    assert container.market_data_repository.get_cached([], HOUR) == {}


def test_cache_all_then_get_cached_returns_a_real_bar():
    price_data = HourlyPriceData(
        symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
    )

    container.market_data_repository.cache_hour(HOUR, {"AAPL": price_data})

    cached = container.market_data_repository.get_cached(["AAPL"], HOUR)
    assert cached == {"AAPL": price_data}


def test_cache_all_then_get_cached_returns_none_for_a_symbol_with_no_data():
    container.market_data_repository.cache_hour(HOUR, {"DELISTED": None})

    cached = container.market_data_repository.get_cached(["DELISTED"], HOUR)
    assert cached == {"DELISTED": None}


def test_get_cached_only_returns_symbols_that_have_been_cached():
    container.market_data_repository.cache_hour(
        HOUR,
        {
            "AAPL": HourlyPriceData(
                symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
            )
        },
    )

    cached = container.market_data_repository.get_cached(["AAPL", "MSFT"], HOUR)

    assert set(cached.keys()) == {"AAPL"}


def test_cache_all_does_not_leak_across_different_hours():
    other_hour = HourlyDate.next(HOUR)
    container.market_data_repository.cache_hour(
        HOUR,
        {
            "AAPL": HourlyPriceData(
                symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
            )
        },
    )

    assert container.market_data_repository.get_cached(["AAPL"], other_hour) == {}


def test_cache_all_overwrites_a_previously_cached_value():
    container.market_data_repository.cache_hour(HOUR, {"AAPL": None})
    price_data = HourlyPriceData(
        symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
    )

    container.market_data_repository.cache_hour(HOUR, {"AAPL": price_data})

    assert container.market_data_repository.get_cached(["AAPL"], HOUR) == {"AAPL": price_data}


def test_cache_all_persists_multiple_hours_in_one_call():
    other_hour = HourlyDate.next(HOUR)
    hour_bar = HourlyPriceData(
        symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
    )

    container.market_data_repository.cache_all(
        {HOUR: {"AAPL": hour_bar}, other_hour: {"AAPL": None}}
    )

    assert container.market_data_repository.get_cached(["AAPL"], HOUR) == {"AAPL": hour_bar}
    assert container.market_data_repository.get_cached(["AAPL"], other_hour) == {"AAPL": None}


def test_get_cached_range_returns_cached_data_grouped_by_hour():
    other_hour = HourlyDate.next(HOUR)
    hour_bar = HourlyPriceData(
        symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
    )
    container.market_data_repository.cache_all({HOUR: {"AAPL": hour_bar}, other_hour: {"AAPL": None}})

    cached = container.market_data_repository.get_cached_range(["AAPL"], HOUR, other_hour)

    assert cached == {HOUR: {"AAPL": hour_bar}, other_hour: {"AAPL": None}}


def test_get_cached_range_includes_both_range_ends():
    other_hour = HourlyDate.next(HOUR)
    hour_bar = HourlyPriceData(
        symbol="AAPL", open=190.0, high=195.0, low=185.0, close=192.0, starting_hour=HOUR
    )
    container.market_data_repository.cache_all({HOUR: {"AAPL": hour_bar}, other_hour: {"AAPL": None}})

    cached = container.market_data_repository.get_cached_range(["AAPL"], HOUR, HOUR)

    assert cached == {HOUR: {"AAPL": hour_bar}}


def test_get_cached_range_returns_empty_dict_when_nothing_is_cached():
    assert container.market_data_repository.get_cached_range(["AAPL"], HOUR, HOUR) == {}
