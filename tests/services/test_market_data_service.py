import pytest

from app.container import container
from app.services.market_data_service import TRADABLE_SYMBOLS


def test_get_price_returns_a_positive_price_for_a_known_symbol():
    price = container.market_data.get_price(TRADABLE_SYMBOLS[0])

    assert price > 0


def test_get_price_raises_for_an_unknown_symbol():
    with pytest.raises(ValueError):
        container.market_data.get_price("NOT-A-SYMBOL")


def test_get_prices_returns_a_price_for_every_tradable_symbol():
    prices = container.market_data.get_prices()

    assert set(prices.keys()) == set(TRADABLE_SYMBOLS)
    assert all(price > 0 for price in prices.values())
