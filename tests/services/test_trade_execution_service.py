from datetime import date

import pytest

from app.container import container
from app.models.market import HourlyDate, HourlyPriceData, MarketState
from app.models.trade import Kind
from app.services.trade_submission_service import TradeRequest

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)
HOUR_BEFORE = HourlyDate(day=date(2024, 1, 1), hour=9)


def _fake_prices(symbol: str, low: float, high: float) -> MarketState:
    return MarketState(
        hour=HOUR,
        prices={
            symbol: HourlyPriceData(
                symbol=symbol, open=low, high=high, low=low, close=high, starting_hour=HOUR
            )
        },
    )


def _submit(user_id: str, kind: Kind, quantity: float, requested_price: float) -> str:
    trade_ids = container.trades.submit(
        user_id,
        [
            TradeRequest(
                symbol="AAPL", kind=kind, quantity=quantity, requested_price=requested_price
            )
        ],
        HOUR_BEFORE,
    )
    return trade_ids[0]


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
        container.market_data, "get_prices", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
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
        container.market_data, "get_prices", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
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
        container.market_data, "get_prices", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
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
    monkeypatch.setattr(
        container.market_data, "get_prices", lambda hour: MarketState(hour=HOUR, prices={})
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

    def _get_prices(hour: HourlyDate) -> MarketState:
        nonlocal called
        called = True
        return _fake_prices("AAPL", 185.0, 195.0)

    monkeypatch.setattr(container.market_data, "get_prices", _get_prices)

    container.trade_execution.execute_user_trades_at_hour(user_id, HOUR)

    assert not called
    assert (
        len(container.trade_repository.list_active_in_order(user_id, HourlyDate.next(HOUR))) == 1
    )


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
        container.market_data, "get_prices", lambda hour: _fake_prices("AAPL", 185.0, 195.0)
    )
    monkeypatch.setattr(HourlyDate, "current", staticmethod(lambda: HourlyDate.next(HOUR)))

    container.trade_execution.fastforward_all_users()

    assert len(container.trade_repository.list_executed(user_a)) == 1
    assert len(container.trade_repository.list_executed(user_b)) == 1
