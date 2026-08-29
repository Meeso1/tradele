from datetime import UTC, date, datetime

import pytest

from app.container import container
from app.services.market_data_service import HourlyDate
from app.services.trade_submission_service import (
    TradeRequest,
    TradesAlreadySubmittedError,
    TradeValidationError,
)

TODAY = HourlyDate(day=date(2024, 1, 1), hour=10)


def test_submit_records_a_pending_requested_trade():
    user_id = container.users.create()

    trade_ids = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        TODAY,
    )

    assert len(trade_ids) == 1
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].id == trade_ids[0]
    assert requested[0].symbol == "AAPL"
    assert requested[0].kind == "limit_buy"
    assert requested[0].quantity == 1
    assert requested[0].requested_price == 190.0
    assert requested[0].active_from == HourlyDate.next(TODAY)


def test_submit_rejects_a_second_batch_on_the_same_day():
    user_id = container.users.create()
    container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        TODAY,
    )

    with pytest.raises(TradesAlreadySubmittedError):
        container.trades.submit(
            user_id,
            [TradeRequest(symbol="MSFT", kind="limit_buy", quantity=1, requested_price=420.0)],
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
            TODAY,
        )


def test_submit_rejects_an_empty_batch():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(user_id, [], TODAY)


def test_has_submitted_today_is_false_before_any_submission():
    user_id = container.users.create()

    assert container.trades.has_submitted_today(user_id, TODAY) is False


def test_has_submitted_today_is_true_after_a_submission():
    user_id = container.users.create()
    container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=1, requested_price=190.0)],
        TODAY,
    )

    assert container.trades.has_submitted_today(user_id, TODAY) is True


def test_recorded_executed_trade_is_listed_under_historical_trades():
    user_id = container.users.create()
    trade_ids = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="limit_buy", quantity=2, requested_price=190.0)],
        TODAY,
    )

    container.trade_repository.move_to_executed(
        trade_ids[0],
        190.0,
        datetime.now(UTC),
        HourlyDate.next(TODAY),
        "executed",
    )

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].id == trade_ids[0]
    assert executed[0].fill_price == 190.0
