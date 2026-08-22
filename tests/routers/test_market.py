from collections.abc import Callable

from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.services.market_data_service import TRADABLE_SYMBOLS

client = TestClient(app)


def test_get_symbols_returns_the_tradable_symbols(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.get("/market/symbols", headers=auth_headers(user_id))

    assert response.status_code == 200
    assert response.json() == TRADABLE_SYMBOLS


def test_get_prices_returns_a_price_for_every_symbol(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.get("/market/prices", headers=auth_headers(user_id))

    assert response.status_code == 200
    prices = response.json()["prices"]
    assert set(prices.keys()) == set(TRADABLE_SYMBOLS)


def test_get_symbols_requires_authentication():
    response = client.get("/market/symbols")

    assert response.status_code == 401


def test_get_prices_requires_authentication():
    response = client.get("/market/prices")

    assert response.status_code == 401
