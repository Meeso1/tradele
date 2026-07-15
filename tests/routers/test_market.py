from fastapi.testclient import TestClient

from app.main import app
from app.services.market_data_service import TRADABLE_SYMBOLS

client = TestClient(app)


def test_get_symbols_returns_the_tradable_symbols():
    response = client.get("/market/symbols")

    assert response.status_code == 200
    assert response.json() == TRADABLE_SYMBOLS


def test_get_prices_returns_a_price_for_every_symbol():
    response = client.get("/market/prices")

    assert response.status_code == 200
    prices = response.json()["prices"]
    assert set(prices.keys()) == set(TRADABLE_SYMBOLS)
