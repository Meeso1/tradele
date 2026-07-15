from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.services.market_data_service import TRADABLE_SYMBOLS
from app.services.portfolio_service import STARTING_CASH

client = TestClient(app)


def test_get_portfolio_creates_a_default_portfolio_for_a_new_user():
    user_id = container.users.create()

    response = client.get("/portfolio", params={"user_id": user_id})

    assert response.status_code == 200
    body = response.json()
    assert body["cash"] == STARTING_CASH
    assert body["holdings"] == {symbol: 0 for symbol in TRADABLE_SYMBOLS}


def test_get_portfolio_returns_404_for_an_unknown_user():
    response = client.get("/portfolio", params={"user_id": "does-not-exist"})

    assert response.status_code == 404
