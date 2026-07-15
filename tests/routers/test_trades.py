from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_submit_trades_records_requested_trades():
    user_id = container.users.create()

    response = client.post(
        "/trades",
        json={"user_id": user_id, "trades": [{"symbol": "AAPL", "side": "buy", "quantity": 1}]},
    )

    assert response.status_code == 201
    trade_ids = response.json()["trade_ids"]
    assert len(trade_ids) == 1
    assert len(container.trades.list_requested(user_id)) == 1


def test_submit_trades_returns_404_for_an_unknown_user():
    response = client.post(
        "/trades",
        json={
            "user_id": "does-not-exist",
            "trades": [{"symbol": "AAPL", "side": "buy", "quantity": 1}],
        },
    )

    assert response.status_code == 404


def test_submit_trades_returns_400_for_an_unknown_symbol():
    user_id = container.users.create()

    response = client.post(
        "/trades",
        json={
            "user_id": user_id,
            "trades": [{"symbol": "NOT-A-SYMBOL", "side": "buy", "quantity": 1}],
        },
    )

    assert response.status_code == 400


def test_submit_trades_returns_409_when_already_submitted_today():
    user_id = container.users.create()
    client.post(
        "/trades",
        json={"user_id": user_id, "trades": [{"symbol": "AAPL", "side": "buy", "quantity": 1}]},
    )

    response = client.post(
        "/trades",
        json={"user_id": user_id, "trades": [{"symbol": "MSFT", "side": "buy", "quantity": 1}]},
    )

    assert response.status_code == 409


def test_get_trades_returns_requested_and_executed_trades():
    user_id = container.users.create()
    client.post(
        "/trades",
        json={"user_id": user_id, "trades": [{"symbol": "AAPL", "side": "buy", "quantity": 1}]},
    )
    container.trades.record_executed(user_id, symbol="AAPL", side="buy", quantity=1, price=190.0)

    response = client.get("/trades", params={"user_id": user_id})

    assert response.status_code == 200
    body = response.json()
    assert len(body["requested"]) == 1
    assert len(body["executed"]) == 1


def test_get_trades_returns_404_for_an_unknown_user():
    response = client.get("/trades", params={"user_id": "does-not-exist"})

    assert response.status_code == 404
