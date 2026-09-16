from datetime import UTC, date, datetime

import pytest

from app.container import container
from app.models.market import HourlyDate
from app.models.trade import ActiveTrade
from app.services.trade_submission_service import (
    TradeRequest,
    TradesAlreadySubmittedError,
    TradeValidationError,
)

TODAY = HourlyDate(day=date(2024, 1, 1), hour=10)


def test_submit_records_a_pending_requested_trade():
    user_id = container.users.create()

    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        [],
        TODAY,
    )

    assert len(result.submitted_ids) == 1
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].id == result.submitted_ids[0]
    assert requested[0].symbol == "AAPL"
    assert requested[0].kind == "limit_buy"
    assert requested[0].quantity == 1
    assert requested[0].value is None
    assert requested[0].requested_price == 190.0
    assert requested[0].active_from == HourlyDate.next(TODAY)


def test_submit_records_a_value_based_trade():
    user_id = container.users.create()

    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="market_buy", value=1000.0)],
        [],
        TODAY,
    )

    assert len(result.submitted_ids) == 1
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].quantity is None
    assert requested[0].value == 1000.0


def test_submit_rejects_a_trade_with_both_quantity_and_value():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="AAPL", kind="market_buy", quantity=1, value=1000.0)],
            [],
            TODAY,
        )


def test_submit_rejects_a_trade_with_neither_quantity_nor_value():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="AAPL", kind="market_buy")],
            [],
            TODAY,
        )


def test_submit_rejects_a_second_batch_on_the_same_day():
    user_id = container.users.create()
    container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        [],
        TODAY,
    )

    with pytest.raises(TradesAlreadySubmittedError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="MSFT", kind="limit_buy", quantity=1, requested_price=420.0)],
            [],
            TODAY,
        )


def test_submit_rejects_an_unknown_symbol():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [
                TradeRequest(
                    symbol="NOT-A-SYMBOL", kind="limit_buy", quantity=1, requested_price=1.0
                )
            ],
            [],
            TODAY,
        )


def test_submit_records_a_market_order_without_a_requested_price():
    user_id = container.users.create()

    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="market_buy", quantity=1)],
        [],
        TODAY,
    )

    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].id == result.submitted_ids[0]
    assert requested[0].requested_price is None


def test_submit_rejects_a_market_order_with_a_requested_price():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="AAPL", kind="market_buy", quantity=1, requested_price=190.0)],
            [],
            TODAY,
        )


def test_submit_rejects_a_limit_order_without_a_requested_price():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1)],
            [],
            TODAY,
        )


def test_submit_rejects_a_stop_order_without_a_requested_price():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="AAPL", kind="stop_sell", quantity=1)],
            [],
            TODAY,
        )


def test_submit_allows_a_cancel_only_batch():
    user_id = container.users.create()
    # A trade requested right before midnight "yesterday" - still active, but
    # old enough that today's submission isn't blocked by it.
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id=user_id,
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2023, 12, 31, 23),
            active_from=HourlyDate(day=TODAY.day, hour=0),
        )
    )

    result = container.trades.submit(user_id, [], ["t1"], TODAY)

    assert result.submitted_ids == []
    assert result.cancelled_ids == ["t1"]
    assert container.trade_repository.list_requested(user_id) == []
    (closed,) = container.trade_repository.list_executed(user_id)
    assert closed.id == "t1"
    assert closed.status == "cancelled"


def test_submit_cancels_the_users_own_active_trades():
    user_id = container.users.create()
    # A trade requested right before midnight "yesterday" - still active, but
    # old enough that today's submission isn't blocked by it.
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id=user_id,
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2023, 12, 31, 23),
            active_from=HourlyDate(day=TODAY.day, hour=0),
        )
    )

    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        ["t1"],
        TODAY,
    )

    assert result.cancelled_ids == ["t1"]
    assert [trade.id for trade in container.trade_repository.list_requested(user_id)] != ["t1"]
    assert len(container.trade_repository.list_requested(user_id)) == 1
    (closed,) = container.trade_repository.list_executed(user_id)
    assert closed.id == "t1"
    assert closed.status == "cancelled"


def test_submit_does_not_cancel_another_users_trade():
    owner_id = container.users.create()
    caller_id = container.users.create()
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id=owner_id,
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2023, 12, 31, 23),
            active_from=HourlyDate(day=TODAY.day, hour=0),
        )
    )

    result = container.trades.submit(
        caller_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        ["t1"],
        TODAY,
    )

    assert result.cancelled_ids == []
    # The other user's trade is untouched.
    assert len(container.trade_repository.list_requested(owner_id)) == 1


def test_submit_ignores_unknown_trade_ids_to_cancel():
    user_id = container.users.create()

    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        ["missing"],
        TODAY,
    )

    assert result.cancelled_ids == []


def test_has_submitted_today_is_false_before_any_submission():
    user_id = container.users.create()

    assert container.trades.has_submitted_today(user_id, TODAY) is False


def test_has_submitted_today_is_true_after_a_submission():
    user_id = container.users.create()
    container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        [],
        TODAY,
    )

    assert container.trades.has_submitted_today(user_id, TODAY) is True


def test_recorded_executed_trade_is_listed_under_historical_trades():
    user_id = container.users.create()
    result = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=2, requested_price=190.0)],
        [],
        TODAY,
    )

    container.trade_repository.move_to_executed(
        result.submitted_ids[0],
        190.0,
        datetime.now(UTC),
        HourlyDate.next(TODAY),
        "executed",
    )

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].id == result.submitted_ids[0]
    assert executed[0].fill_price == 190.0
