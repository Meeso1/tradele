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
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 201
    assert len(response.json()["submitted_ids"]) == 1
    assert response.json()["cancelled_ids"] == []
    assert len(container.trade_repository.list_requested(user_id)) == 1


def test_submit_trades_accepts_a_value_based_order(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [{"symbol": "AAPL", "kind": "market_buy", "value": 1000.0}],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 201
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].quantity is None
    assert requested[0].value == 1000.0


def test_submit_trades_rejects_a_trade_with_both_quantity_and_value(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "market_buy", "quantity": 1, "value": 1000.0}
            ],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 400


def test_submit_trades_cancels_requested_trades(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    # A pending trade from "yesterday" that today's batch can cancel.
    container.trade_repository.insert_requested(
        _active_trade(user_id, "t1", datetime(2024, 1, 1, 8))
    )

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": ["t1"],
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["cancelled_ids"] == ["t1"]
    assert [trade.id for trade in container.trade_repository.list_requested(user_id)] != ["t1"]
    assert len(container.trade_repository.list_requested(user_id)) == 1
    (closed,) = container.trade_repository.list_executed(user_id)
    assert closed.id == "t1"
    assert closed.status == "cancelled"


def test_submit_trades_accepts_a_cancel_only_batch(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    container.trade_repository.insert_requested(
        _active_trade(user_id, "t1", datetime(2023, 12, 31, 23))
    )

    response = client.post(
        "/api/trades",
        json={"new_trades": [], "trades_to_cancel": ["t1"]},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json() == {"submitted_ids": [], "cancelled_ids": ["t1"]}
    assert container.trade_repository.list_requested(user_id) == []
    (closed,) = container.trade_repository.list_executed(user_id)
    assert closed.id == "t1"
    assert closed.status == "cancelled"
    # A cancel-only batch still consumes the once-per-day submission slot.
    assert (
        client.get("/api/trades/has-submitted-today", headers=headers).json()
        == {"has_submitted_today": True}
    )


def test_submit_trades_does_not_cancel_another_users_trade(
    auth_headers: Callable[[str], dict[str, str]],
):
    owner_id = container.users.create()
    container.trade_repository.insert_requested(
        _active_trade(owner_id, "t1", datetime(2024, 1, 1, 8))
    )
    caller_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": ["t1"],
        },
        headers=auth_headers(caller_id),
    )

    assert response.status_code == 201
    assert response.json()["cancelled_ids"] == []
    assert len(container.trade_repository.list_requested(owner_id)) == 1


def test_submit_trades_rejects_a_token_for_an_unknown_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    # The auth layer resolves the user (for per-user auth method checks), so
    # an unknown user is rejected there with 401, before the route's 404.
    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": [],
        },
        headers=auth_headers("does-not-exist"),
    )

    assert response.status_code == 401


def test_submit_trades_returns_400_for_an_unknown_symbol(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {
                    "symbol": "NOT-A-SYMBOL",
                    "kind": "limit_buy",
                    "quantity": 1,
                    "requested_price": 1.0,
                }
            ],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 400


def test_submit_trades_accepts_a_market_order_without_a_requested_price(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [{"symbol": "AAPL", "kind": "market_buy", "quantity": 1}],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 201
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].requested_price is None


def test_submit_trades_returns_400_for_a_limit_order_without_a_requested_price(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.post(
        "/api/trades",
        json={
            "new_trades": [{"symbol": "AAPL", "kind": "limit_buy", "quantity": 1}],
            "trades_to_cancel": [],
        },
        headers=auth_headers(user_id),
    )

    assert response.status_code == 400


def test_submit_trades_returns_409_when_already_submitted_today(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    body = {
        "new_trades": [
            {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
        ],
        "trades_to_cancel": [],
    }
    client.post("/api/trades", json=body, headers=headers)

    body["new_trades"] = [
        {"symbol": "MSFT", "kind": "limit_buy", "quantity": 1, "requested_price": 420.0}
    ]
    response = client.post("/api/trades", json=body, headers=headers)

    assert response.status_code == 409


def test_submit_trades_requires_authentication():
    response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": [],
        },
    )

    assert response.status_code == 401


def test_get_trades_returns_requested_and_closed_trades(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    submit_response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0},
                {"symbol": "MSFT", "kind": "limit_buy", "quantity": 1, "requested_price": 420.0},
            ],
            "trades_to_cancel": [],
        },
        headers=headers,
    )
    trade_id_to_close = submit_response.json()["submitted_ids"][0]
    container.trade_repository.move_to_executed(
        trade_id_to_close,
        190.0,
        datetime.now(UTC),
        HourlyDate.current(),
        "executed",
    )

    response = client.get("/api/trades", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["requested"]) == 1
    assert len(body["closed"]) == 1


def test_get_trades_rejects_a_token_for_an_unknown_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    # The auth layer resolves the user (for per-user auth method checks), so
    # an unknown user is rejected there with 401, before the route's 404.
    response = client.get("/api/trades", headers=auth_headers("does-not-exist"))

    assert response.status_code == 401


def test_get_trades_requires_authentication():
    response = client.get("/api/trades")

    assert response.status_code == 401


def test_has_submitted_today_reflects_a_submission(auth_headers: Callable[[str], dict[str, str]]):
    user_id = container.users.create()
    headers = auth_headers(user_id)

    before = client.get("/api/trades/has-submitted-today", headers=headers)
    client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": [],
        },
        headers=headers,
    )
    after = client.get("/api/trades/has-submitted-today", headers=headers)

    assert before.status_code == 200
    assert before.json() == {"has_submitted_today": False}
    assert after.status_code == 200
    assert after.json() == {"has_submitted_today": True}


def test_changed_since_last_submission_returns_trades_closed_after_the_last_submission(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)
    submit_response = client.post(
        "/api/trades",
        json={
            "new_trades": [
                {"symbol": "AAPL", "kind": "limit_buy", "quantity": 1, "requested_price": 190.0}
            ],
            "trades_to_cancel": [],
        },
        headers=headers,
    )
    trade_id = submit_response.json()["submitted_ids"][0]
    container.trade_repository.move_to_executed(
        trade_id,
        190.0,
        datetime.now(UTC),
        HourlyDate.current(),
        "executed",
    )

    response = client.get("/api/trades/changed-since-last-submission", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == trade_id
    assert body[0]["status"] == "executed"


def test_changed_since_last_submission_is_empty_without_changes(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()
    headers = auth_headers(user_id)

    response = client.get("/api/trades/changed-since-last-submission", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_new_trade_endpoints_require_authentication():
    assert client.get("/api/trades/has-submitted-today").status_code == 401
    assert client.get("/api/trades/changed-since-last-submission").status_code == 401


def _active_trade(user_id: str, trade_id: str, requested_at: datetime):
    from app.models.trade import ActiveTrade

    # Requested right before midnight "yesterday" - still active, but old
    # enough that it doesn't count as a submission for today.
    return ActiveTrade(
        id=trade_id,
        user_id=user_id,
        symbol="AAPL",
        kind="limit_buy",
        requested_price=190.0,
        quantity=1,
        value=None,
        requested_at=requested_at,
        active_from=HourlyDate(day=HourlyDate.current().day, hour=0),
    )
