from datetime import UTC, date, datetime

import pytest

from app.container import container
from app.models.market import HourlyDate, HourlyPriceData, MarketState
from app.models.trade import ActiveTrade, Kind
from app.services.trade_submission_service import TradeRequest

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)
HOUR_BEFORE = HourlyDate(day=date(2024, 1, 1), hour=9)


def _fake_prices(symbol: str, low: float, high: float, open: float | None = None) -> MarketState:
    return MarketState(
        hour=HOUR,
        market_open=True,
        prices={
            symbol: HourlyPriceData(
                symbol=symbol,
                open=open if open is not None else low,
                high=high,
                low=low,
                close=high,
                starting_hour=HOUR,
            )
        },
    )


def _submit(user_id: str, kind: Kind, quantity: float, requested_price: float | None = None) -> str:
    result = container.trades.submit(
        user_id,
        [
            TradeRequest(
                symbol="AAPL", kind=kind, quantity=quantity, requested_price=requested_price
            )
        ],
        [],
        HOUR_BEFORE,
    )
    return result.submitted_ids[0]


def _set_last_hourly_update(user_id: str, hour: HourlyDate | None) -> None:
    """Force the user's portfolio to a known `last_hourly_update`.

    A freshly created portfolio defaults to the real current hour, which
    would make every trade in these tests (using fixed 2024 hours) look
    already up to date - so tests need to move it back explicitly.
    """
    portfolio = container.portfolios.get_or_create(user_id)
    container.portfolio_repository.update(
        user_id, portfolio.model_copy(update={"last_hourly_update": hour})
    )


def test_execute_user_trades_at_hour_fills_a_limit_buy_when_price_is_reached(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=10, requested_price=190.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert container.trade_repository.list_active_in_order(user_id, HOUR) == []
    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "executed"
    assert executed[0].fill_price == 190.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 10
    assert portfolio.cash == pytest.approx(100_000.0 - 10 * 190.0)
    assert portfolio.last_hourly_update == HOUR


def test_execute_user_trades_at_hour_leaves_a_limit_buy_open_when_price_not_reached(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=10, requested_price=100.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert len(container.trade_repository.list_active_in_order(user_id, HOUR)) == 1
    assert container.trade_repository.list_executed(user_id) == []


def test_execute_user_trades_at_hour_marks_insufficient_funds_when_cash_is_too_low(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=100_000, requested_price=190.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "insufficient_funds"
    assert executed[0].fill_price is None


def test_execute_user_trades_at_hour_marks_symbol_unavailable_when_no_price_data_exists(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=10, requested_price=190.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    # Another symbol trades this hour (so the market is open), but AAPL has no bar.
    monkeypatch.setattr(
        container.market_data,
        "get_prices_for_hour",
        lambda hour: _fake_prices("MSFT", 185.0, 195.0),
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "symbol_unavailable"
    assert executed[0].fill_price is None


def test_execute_user_trades_at_hour_is_a_noop_when_the_portfolio_is_already_up_to_date(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=10, requested_price=190.0)
    _set_last_hourly_update(user_id, HourlyDate.next(HOUR))
    called = False

    def _get_prices_for_hour(hour: HourlyDate) -> MarketState:
        nonlocal called
        called = True
        return _fake_prices("AAPL", 185.0, 195.0)

    monkeypatch.setattr(container.market_data, "get_prices_for_hour", _get_prices_for_hour)

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert not called
    assert (
        len(container.trade_repository.list_active_in_order(user_id, HourlyDate.next(HOUR))) == 1
    )


def test_execute_user_trades_at_hour_fills_a_market_buy_at_the_open_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "market_buy", quantity=10)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "executed"
    assert executed[0].fill_price == 190.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 10
    assert portfolio.cash == pytest.approx(100_000.0 - 10 * 190.0)


def test_execute_user_trades_at_hour_fills_a_market_sell_at_the_open_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "market_buy", quantity=10)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )
    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    _submit(user_id, "market_sell", quantity=4)
    container.trade_execution.execute_user_trades_at_hour(user_id, HourlyDate.next(HOUR))

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 2
    assert executed[1].status == "executed"
    assert executed[1].fill_price == 190.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 6
    assert portfolio.cash == pytest.approx(100_000.0 - 6 * 190.0)


def test_execute_user_trades_at_hour_marks_insufficient_funds_when_holdings_are_too_low_for_a_market_sell(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "market_sell", quantity=10)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "insufficient_funds"
    assert executed[0].fill_price is None


def test_execute_user_trades_at_hour_fills_a_stop_buy_at_the_requested_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "stop_buy", quantity=10, requested_price=192.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "executed"
    assert executed[0].fill_price == 192.0


def test_execute_user_trades_at_hour_fills_a_stop_buy_at_the_open_when_it_gaps_up(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "stop_buy", quantity=10, requested_price=180.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "executed"
    assert executed[0].fill_price == 190.0


def test_execute_user_trades_at_hour_leaves_a_stop_buy_open_when_the_stop_price_is_not_reached(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "stop_buy", quantity=10, requested_price=200.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert len(container.trade_repository.list_active_in_order(user_id, HOUR)) == 1
    assert container.trade_repository.list_executed(user_id) == []


def test_execute_user_trades_at_hour_fills_a_stop_sell_at_the_requested_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "market_buy", quantity=10)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )
    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    _submit(user_id, "stop_sell", quantity=10, requested_price=188.0)
    container.trade_execution.execute_user_trades_at_hour(user_id, HourlyDate.next(HOUR))

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 2
    assert executed[1].status == "executed"
    assert executed[1].fill_price == 188.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 0


def test_execute_user_trades_at_hour_marks_malformed_request_when_a_limit_trade_has_no_price(
    monkeypatch: pytest.MonkeyPatch,
):
    # Submission validation rejects price-less limit orders, but a trade already
    # stored without one (e.g. from before the validation existed) must still be
    # closed cleanly instead of crashing the execution loop.
    user_id = container.users.create()
    container.trade_repository.insert_requested(
        ActiveTrade(
            id="trade-1",
            user_id=user_id,
            symbol="AAPL",
            kind="limit_buy",
            requested_price=None,
            quantity=10,
            value=None,
            requested_at=datetime.now(UTC),
            active_from=HOUR,
        )
    )
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].status == "malformed_request"
    assert executed[0].fill_price is None


def test_fastforward_all_users_executes_pending_trades_for_every_user(
    monkeypatch: pytest.MonkeyPatch,
):
    user_a = container.users.create()
    user_b = container.users.create()
    _submit(user_a, "limit_buy", quantity=1, requested_price=190.0)
    _submit(user_b, "limit_buy", quantity=1, requested_price=190.0)
    _set_last_hourly_update(user_a, HOUR_BEFORE)
    _set_last_hourly_update(user_b, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )
    monkeypatch.setattr(HourlyDate, "current", staticmethod(lambda: HourlyDate.next(HOUR)))

    container.trade_execution.fastforward_all_users()

    assert len(container.trade_repository.list_executed(user_a)) == 1
    assert len(container.trade_repository.list_executed(user_b)) == 1


def test_execute_user_trades_at_hour_leaves_trades_active_when_the_market_is_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "limit_buy", quantity=10, requested_price=190.0)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data,
        "get_prices_for_hour",
        lambda hour: MarketState(hour=HOUR, prices={}, market_open=False),
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert len(container.trade_repository.list_active_in_order(user_id, HOUR)) == 1
    assert container.trade_repository.list_executed(user_id) == []
    # The portfolio must not be advanced past a closed hour, so the trades
    # are retried in the next open hour.
    assert container.portfolios.get_or_create(user_id).last_hourly_update == HOUR_BEFORE


def test_execute_user_trades_at_hour_fills_a_value_based_market_buy_at_the_open_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    trade_id = container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="market_buy", value=1900.0)],
        [],
        HOUR_BEFORE,
    ).submitted_ids[0]
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 1
    assert executed[0].id == trade_id
    assert executed[0].status == "executed"
    assert executed[0].fill_price == 190.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 10
    assert portfolio.cash == pytest.approx(100_000.0 - 1900.0)


def test_execute_user_trades_at_hour_fills_a_value_based_market_sell_at_the_open_price(
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = container.users.create()
    _submit(user_id, "market_buy", quantity=10)
    _set_last_hourly_update(user_id, HOUR_BEFORE)
    monkeypatch.setattr(
        container.market_data, "get_prices_for_hour", lambda hour: _fake_prices("AAPL", 185.0, 195.0, open=190.0)
    )
    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    container.trades.submit(
        user_id,
        [TradeRequest(symbol="AAPL", kind="market_sell", value=950.0)],
        [],
        HOUR_BEFORE,
    )
    container.trade_execution.execute_user_trades_at_hour(user_id, HourlyDate.next(HOUR))

    executed = container.trade_repository.list_executed(user_id)
    assert len(executed) == 2
    assert executed[1].status == "executed"
    assert executed[1].fill_price == 190.0

    portfolio = container.portfolios.get_or_create(user_id)
    assert portfolio.holdings["AAPL"] == 5
    assert portfolio.cash == pytest.approx(100_000.0 - 5 * 190.0)
