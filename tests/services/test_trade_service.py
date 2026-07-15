import pytest

from app.container import container
from app.services.trade_service import (
    TradeRequest,
    TradesAlreadySubmittedError,
    TradeValidationError,
)


def test_submit_records_a_pending_requested_trade():
    user_id = container.users.create()

    trade_ids = container.trades.submit(user_id, [TradeRequest(symbol="AAPL", side="buy", quantity=1)])

    assert len(trade_ids) == 1
    requested = container.trades.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].id == trade_ids[0]
    assert requested[0].symbol == "AAPL"
    assert requested[0].side == "buy"
    assert requested[0].quantity == 1
    assert requested[0].status == "pending"


def test_submit_rejects_a_second_batch_on_the_same_day():
    user_id = container.users.create()
    container.trades.submit(user_id, [TradeRequest(symbol="AAPL", side="buy", quantity=1)])

    with pytest.raises(TradesAlreadySubmittedError):
        container.trades.submit(user_id, [TradeRequest(symbol="MSFT", side="buy", quantity=1)])


def test_submit_rejects_an_unknown_symbol():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(user_id, [TradeRequest(symbol="NOT-A-SYMBOL", side="buy", quantity=1)])


def test_submit_rejects_an_empty_batch():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(user_id, [])


def test_record_executed_is_listed_under_executed_trades():
    user_id = container.users.create()

    trade_id = container.trades.record_executed(
        user_id, symbol="AAPL", side="buy", quantity=2, price=190.0
    )

    executed = container.trades.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].id == trade_id
    assert executed[0].price == 190.0
