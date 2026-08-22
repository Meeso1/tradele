from datetime import date

import pytest

from app.container import container
from app.repositories.trade_repository import HistoricalTrade
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
        user_id, [TradeRequest(symbol="AAPL", side="buy", quantity=1)], TODAY
    )

    assert len(trade_ids) == 1
    requested = container.trade_repository.list_requested(user_id)
    assert len(requested) == 1
    assert requested[0].id == trade_ids[0]
    assert requested[0].symbol == "AAPL"
    assert requested[0].side == "buy"
    assert requested[0].quantity == 1
    assert requested[0].trade_date == TODAY.day.isoformat()
    assert requested[0].active_from_hour == TODAY.hour


def test_submit_rejects_a_second_batch_on_the_same_day():
    user_id = container.users.create()
    container.trades.submit(user_id, [TradeRequest(symbol="AAPL", side="buy", quantity=1)], TODAY)

    with pytest.raises(TradesAlreadySubmittedError):
        container.trades.submit(
            user_id, [TradeRequest(symbol="MSFT", side="buy", quantity=1)], TODAY
        )


def test_submit_rejects_an_unknown_symbol():
    user_id = container.users.create()

    with pytest.raises(TradeValidationError):
        container.trades.submit(
            user_id, [TradeRequest(symbol="NOT-A-SYMBOL", side="buy", quantity=1)], TODAY
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
    container.trades.submit(user_id, [TradeRequest(symbol="AAPL", side="buy", quantity=1)], TODAY)

    assert container.trades.has_submitted_today(user_id, TODAY) is True


def test_recorded_executed_trade_is_listed_under_historical_trades():
    user_id = container.users.create()

    container.trade_repository.insert_executed(
        HistoricalTrade(
            id="e1",
            user_id=user_id,
            symbol="AAPL",
            side="buy",
            quantity=2,
            price=190.0,
            closed_at="2024-01-02T00:00:00",
            status="executed",
        )
    )

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].id == "e1"
    assert executed[0].price == 190.0
