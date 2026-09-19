from datetime import date

from app.container import container
from app.models.market import HourlyDate, HourlyPriceData, MarketState
from app.models.portfolio import Portfolio
from app.repositories.portfolio_repository import STARTING_CASH

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)
MARKET_STATE = MarketState(
    hour=HOUR,
    market_open=True,
    prices={
        "AAPL": HourlyPriceData(
            symbol="AAPL", open=10.0, high=12.0, low=9.0, close=11.0, starting_hour=HOUR
        )
    },
)


def test_get_or_create_creates_a_default_portfolio_for_a_new_user():
    user_id = container.users.create()

    portfolio = container.portfolios.get_or_create(user_id)

    assert portfolio.cash == STARTING_CASH
    assert portfolio.holdings == {symbol: 0 for symbol in container.settings.tradable_symbols}


def test_get_or_create_returns_the_same_portfolio_on_repeated_calls():
    user_id = container.users.create()

    first = container.portfolios.get_or_create(user_id)
    second = container.portfolios.get_or_create(user_id)

    assert first == second


def test_save_persists_changes_to_the_portfolio():
    user_id = container.users.create()
    portfolio = container.portfolios.get_or_create(user_id)

    updated = Portfolio(
        cash=portfolio.cash - 1000,
        holdings={**portfolio.holdings, "AAPL": 5},
        last_hourly_update=portfolio.last_hourly_update,
    )
    container.portfolios.save(user_id, updated)

    assert container.portfolios.get_or_create(user_id) == updated


def test_save_hourly_state_records_the_portfolios_value_at_the_hour(monkeypatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])
    user_id = container.users.create()
    container.portfolios.get_or_create(user_id)
    container.portfolios.save(
        user_id, Portfolio(cash=1000.0, holdings={"AAPL": 2}, last_hourly_update=HOUR)
    )

    container.portfolios.save_hourly_state(user_id, HOUR, MARKET_STATE)

    states = container.portfolios.get_history(user_id)
    assert len(states) == 1
    assert states[0].timestamp == HOUR
    assert states[0].total_value == 1000.0 + 2 * 11.0
    assert states[0].cash == 1000.0
    assert states[0].holdings == {"AAPL": 2}


def test_save_hourly_state_skips_an_already_recorded_hour():
    user_id = container.users.create()
    container.portfolios.get_or_create(user_id)
    container.portfolios.save(
        user_id, Portfolio(cash=1000.0, holdings={"AAPL": 2}, last_hourly_update=HOUR)
    )

    container.portfolios.save_hourly_state(user_id, HOUR, MARKET_STATE)
    container.portfolios.save_hourly_state(user_id, HOUR, MARKET_STATE)

    assert len(container.portfolios.get_history(user_id)) == 1


def test_save_hourly_state_skips_hours_whose_trades_havent_been_executed():
    user_id = container.users.create()
    container.portfolios.get_or_create(user_id)
    container.portfolios.save(
        user_id, Portfolio(cash=1000.0, holdings={"AAPL": 2}, last_hourly_update=HOUR)
    )

    container.portfolios.save_hourly_state(user_id, HourlyDate.next(HOUR), MARKET_STATE)

    assert container.portfolios.get_history(user_id) == []


def test_save_state_for_all_users_records_every_user(monkeypatch):
    monkeypatch.setattr(container.settings, "tradable_symbols", ["AAPL"])

    def _get_hourly_bars(symbols, start, end):
        return {
            symbol: [
                HourlyPriceData(
                    symbol=symbol, open=10.0, high=12.0, low=9.0, close=11.0, starting_hour=start
                )
            ]
            for symbol in symbols
        }

    monkeypatch.setattr(container.alpaca_client, "get_hourly_bars", _get_hourly_bars)
    users = [container.users.create(), container.users.create()]
    for user_id in users:
        container.portfolios.get_or_create(user_id)
        container.portfolios.save(
            user_id, Portfolio(cash=1000.0, holdings={"AAPL": 1}, last_hourly_update=HOUR)
        )

    container.portfolios.save_state_for_all_users(HOUR)

    for user_id in users:
        states = container.portfolios.get_history(user_id)
        assert len(states) == 1
        assert states[0].total_value == 1000.0 + 11.0
