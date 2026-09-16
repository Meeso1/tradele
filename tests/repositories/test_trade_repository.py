from datetime import date, datetime

from app.container import container
from app.models.market import HourlyDate
from app.models.trade import ActiveTrade


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
            value=None,
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
            value=None,
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
            value=None,
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
            value=None,
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
            value=None,
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
            value=None,
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


def test_insert_requested_round_trips_a_value_based_trade():
    container.user_repository.insert("u1", "now")

    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="market_buy",
            requested_price=None,
            quantity=None,
            value=1000.0,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    (requested,) = container.trade_repository.list_requested("u1")
    assert requested.quantity is None
    assert requested.value == 1000.0


def test_move_to_executed_preserves_quantity_and_value():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="market_buy",
            requested_price=None,
            quantity=None,
            value=1000.0,
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

    (executed,) = container.trade_repository.list_executed("u1")
    assert executed.quantity is None
    assert executed.value == 1000.0


def test_cancel_if_active_cancels_the_users_own_active_trade():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    cancelled = container.trade_repository.cancel_if_active(
        "u1", "t1", datetime(2024, 1, 1, 9, 30), HourlyDate(day=date(2024, 1, 1), hour=9)
    )

    assert cancelled is True
    assert (
        container.trade_repository.list_active_in_order(
            "u1", HourlyDate(day=date(2024, 1, 1), hour=10)
        )
        == []
    )
    (closed,) = container.trade_repository.list_executed("u1")
    assert closed.id == "t1"
    assert closed.status == "cancelled"
    assert closed.fill_price is None
    assert closed.closed_at_hour == HourlyDate(day=date(2024, 1, 1), hour=9)


def test_cancel_if_active_does_not_cancel_another_users_trade():
    container.user_repository.insert("u1", "now")
    container.user_repository.insert("u2", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2024, 1, 1),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )

    cancelled = container.trade_repository.cancel_if_active(
        "u2", "t1", datetime(2024, 1, 1, 9, 30), HourlyDate(day=date(2024, 1, 1), hour=9)
    )

    assert cancelled is False
    # The trade is untouched and still active for its owner.
    assert (
        len(
            container.trade_repository.list_active_in_order(
                "u1", HourlyDate(day=date(2024, 1, 1), hour=10)
            )
        )
        == 1
    )
    assert container.trade_repository.list_executed("u1") == []


def test_cancel_if_active_returns_false_for_an_unknown_trade():
    container.user_repository.insert("u1", "now")

    cancelled = container.trade_repository.cancel_if_active(
        "u1", "missing", datetime(2024, 1, 1, 9, 30), HourlyDate(day=date(2024, 1, 1), hour=9)
    )

    assert cancelled is False


def test_list_changed_since_last_submission_returns_trades_closed_after_the_last_submission():
    container.user_repository.insert("u1", "now")
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t1",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=190.0,
            quantity=1,
            value=None,
            requested_at=datetime(2024, 1, 1, 9),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )
    # Closed before the submission above - should not be listed.
    container.trade_repository.move_to_executed(
        "t1",
        190.0,
        datetime(2024, 1, 1, 8, 30),
        HourlyDate(day=date(2024, 1, 1), hour=8),
        "executed",
    )
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t2",
            user_id="u1",
            symbol="MSFT",
            kind="limit_buy",
            requested_price=420.0,
            quantity=1,
            value=None,
            requested_at=datetime(2024, 1, 1, 9),
            active_from=HourlyDate(day=date(2024, 1, 1), hour=10),
        )
    )
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="t3",
            user_id="u1",
            symbol="AAPL",
            kind="limit_buy",
            requested_price=191.0,
            quantity=1,
            value=None,
            requested_at=datetime(2024, 1, 2, 9),
            active_from=HourlyDate(day=date(2024, 1, 2), hour=10),
        )
    )
    # Closed after the latest submission (t3) - should be listed.
    container.trade_repository.move_to_executed(
        "t2",
        420.0,
        datetime(2024, 1, 2, 10, 30),
        HourlyDate(day=date(2024, 1, 2), hour=10),
        "executed",
    )

    changed = container.trade_repository.list_changed_since_last_submission("u1")

    assert [trade.id for trade in changed] == ["t2"]


def test_list_changed_since_last_submission_returns_nothing_without_active_trades():
    container.user_repository.insert("u1", "now")

    assert container.trade_repository.list_changed_since_last_submission("u1") == []
