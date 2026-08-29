from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.models.market import HourlyDate

client = TestClient(app)


def test_submit_trades_records_requested_trades(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ]
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 201
    trade_ids = response.json()["trade_ids"]
    assert len(trade_ids) == 1
    assert len(container.trade_repository.list_requested(user_id)) == 1


def test_submit_trades_returns_404_for_an_unknown_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    response = client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ]
        },
        headers=auth_headers("does-not-exist"),
    )

    assert response.status_code == 404


def test_submit_trades_returns_400_for_an_unknown_symbol(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/trades",
        json={
            "trades": [
                {
                    "symbol": "NOT-A-SYMBOL",
                    "kind": "limit_buy",
                    "quantity": 1,
                    "requested_price": 1.0,
                }
            ]
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 400


def test_submit_trades_returns_409_when_already_submitted_today(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ]
        },
        headers=headers,
    )

    response = client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "MSFT", "kind": "limit_buy", "quantity": 1, "requested_price": 420.0}
            ]
        },
        headers=headers,
    )

    assert response.status_code == 409


def test_submit_trades_requires_authentication():
    response = client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ]
        },
    )

    assert response.status_code == 401


def test_get_trades_returns_requested_and_closed_trades(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    submit_response = client.post(
        "/trades",
        json={
            "trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0},
                {"symbol": "MSFT", "kind": "limit_buy", "quantity": 1, "requested_price": 420.0},
            ]
        },
        headers=headers,
    )
    trade_id_to_close = submit_response.json()["trade_ids"][0]
    container.trade_repository.move_to_executed(
        trade_id_to_close,
        190.0,
        datetime.now(UTC),
        HourlyDate.current(),
        "executed",
    )

    response = client.get("/trades", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["requested"]) == 1
    assert len(body["closed"]) == 1


def test_get_trades_returns_404_for_an_unknown_user(auth_headers: Callable[[str], dict[str, str]]):
    response = client.get("/trades", headers=auth_headers("does-not-exist"))

    assert response.status_code == 404


def test_get_trades_requires_authentication():
    response = client.get("/trades")

    assert response.status_code == 401
