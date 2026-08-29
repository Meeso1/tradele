from datetime import date, datetime

from app.container import container
from app.repositories.trade_repository import ActiveTrade
from app.services.market_data_service import HourlyDate


def test_exists_for_date_is_false_with_no_requested_trades():
    container.user_repository.insert("u1", "now")

    assert (
        container.trade_repository.exists_for_date(
            "u1", HourlyDate(day=date(2024, 1, 1), hour=9)
        )
        is False
    )


def test_insert_requested_then_exists_for_date_returns_true():
    container.user_repository.insert("u1", "now")

    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    assert (
        container.trade_repository.exists_for_date(
            "u1", HourlyDate(day=date(2024, 1, 1), hour=9)
        )
        is True
    )


def test_exists_for_date_matches_a_trade_requested_right_before_midnight():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1, 23),
            # Requested at 23:00 on Jan 1st, so active_from rolls over to Jan 2nd.
            active_from=HourlyDate(day=date(2024, 1, 2), hour=0),
        )
    )

    # Still attributed to Jan 1st (the day it was actually requested on)...
    assert (
        container.trade_repository.exists_for_date(
            "u1", HourlyDate(day=date(2024, 1, 1), hour=23)
        )
        is True
    )
    # ...and doesn't block a genuinely new submission on Jan 2nd.
    assert (
        container.trade_repository.exists_for_date(
            "u1", HourlyDate(day=date(2024, 1, 2), hour=9)
        )
        is False
    )


def test_list_requested_returns_inserted_trades():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    requested = container.trade_repository.list_requested("u1")

    assert len(requested) == 1
    assert requested[0].id == "t1"
    assert requested[0].symbol == "AAPL"
    assert requested[0].active_from == HourlyDate(day=date(2024, 1, 1), hour=10)


def test_list_active_in_order_returns_trades_active_by_the_given_hour():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="later",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1, 9),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=12),
        )
    )
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="earlier",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1, 8),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    active = container.trade_repository.list_active_in_order(
        "u1", HourlyDate(day=date(2024, 1, 1), hour=11)
    )

    assert [trade.id for trade in active] == ["earlier"]


def test_move_to_executed_moves_a_trade_from_active_to_historical():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    container.trade_repository.move_to_executed(
        "t1",
        190.0,
        datetime(2024, 1, 1, 11),
        HourlyDate(day=date(2024, 1, 1), hour=10),
        "executed",
    )

    assert container.trade_repository.list_active_in_order(
        "u1", HourlyDate(day=date(2024, 1, 1), hour=10)
    ) == []
    executed = container.trade_repository.list_executed("u1")
    assert len(executed) == 1
    assert executed[0].id == "t1"
    assert executed[0].fill_price == 190.0
    assert executed[0].status == "executed"
