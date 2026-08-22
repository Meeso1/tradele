from datetime import datetime

from app.container import container
from app.repositories.trade_repository import ActiveTrade, HistoricalTrade


def test_exists_for_date_is_false_with_no_requested_trades():
    container.user_repository.insert("u1", "now")

    assert container.trade_repository.exists_for_date("u1", "2024-01-01") is False


def test_insert_requested_then_exists_for_date_returns_true():
    container.user_repository.insert("u1", "now")

    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            side="buy",
            quantity=1,
            requested_at=datetime(2024, 1, 1),
            trade_date="2024-01-01",
            active_from_hour=10,
        )
    )

    assert container.trade_repository.exists_for_date("u1", "2024-01-01") is True


def test_list_requested_returns_inserted_trades():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            side="buy",
            quantity=1,
            requested_at=datetime(2024, 1, 1),
            trade_date="2024-01-01",
            active_from_hour=10,
        )
    )

    requested = container.trade_repository.list_requested("u1")

    assert len(requested) == 1
    assert requested[0].id == "t1"
    assert requested[0].symbol == "AAPL"
    assert requested[0].active_from_hour == 10


def test_insert_executed_then_list_executed_returns_it():
    container.user_repository.insert("u1", "now")

    container.trade_repository.insert_executed(
        HistoricalTrade(
            id="e1",
            user_id="u1",
            symbol="AAPL",
            side="buy",
            quantity=1,
            price=190.0,
            closed_at="2024-01-02T00:00:00",
            status="executed",
        )
    )

    executed = container.trade_repository.list_executed("u1")

    assert len(executed) == 1
    assert executed[0].id == "e1"
    assert executed[0].price == 190.0
