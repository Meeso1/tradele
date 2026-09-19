from datetime import UTC, date, datetime

from app.container import container
from app.models.market import HourlyDate
from app.models.portfolio import HistoricalPortfolio, Portfolio

HOUR = HourlyDate(day=date(2024, 1, 1), hour=10)
RECORDED_AT = datetime(2024, 1, 1, 11, 5, tzinfo=UTC)


def _state(hour: HourlyDate, cash: float = 100.0, total_value: float = 150.0) -> HistoricalPortfolio:
    return HistoricalPortfolio(
        cash=cash,
        holdings={"AAPL": 2},
        timestamp=hour,
        total_value=total_value,
        recorded_at=RECORDED_AT,
    )


def test_get_returns_none_for_a_user_with_no_portfolio():
    container.user_repository.insert("u1", "now")

    assert container.portfolio_repository.get("u1") is None


def test_insert_then_get_returns_the_stored_portfolio():
    container.user_repository.insert("u1", "now")
    portfolio = Portfolio(cash=1000.0, holdings={"AAPL": 2}, last_hourly_update=None)

    container.portfolio_repository.insert("u1", portfolio)

    assert container.portfolio_repository.get("u1") == portfolio


def test_update_overwrites_the_stored_portfolio():
    container.user_repository.insert("u1", "now")
    container.portfolio_repository.insert(
        "u1", Portfolio(cash=1000.0, holdings={"AAPL": 2}, last_hourly_update=None)
    )

    updated = Portfolio(cash=500.0, holdings={"AAPL": 4}, last_hourly_update=None)
    container.portfolio_repository.update("u1", updated)

    assert container.portfolio_repository.get("u1") == updated


def test_try_record_state_records_a_new_state():
    container.user_repository.insert("u1", "now")

    assert container.portfolio_repository.try_record_state("u1", _state(HOUR)) is True

    assert container.portfolio_repository.get_states("u1", None, None) == [_state(HOUR)]


def test_try_record_state_returns_false_for_an_already_recorded_hour():
    container.user_repository.insert("u1", "now")
    assert container.portfolio_repository.try_record_state("u1", _state(HOUR)) is True

    assert container.portfolio_repository.try_record_state("u1", _state(HOUR, cash=999.0)) is False

    assert container.portfolio_repository.get_states("u1", None, None) == [_state(HOUR)]


def test_try_record_state_records_multiple_hours_for_the_same_user():
    container.user_repository.insert("u1", "now")

    assert container.portfolio_repository.try_record_state("u1", _state(HOUR)) is True
    assert container.portfolio_repository.try_record_state("u1", _state(HourlyDate.next(HOUR))) is True


def test_try_record_state_does_not_leak_across_users():
    container.user_repository.insert("u1", "now")
    container.user_repository.insert("u2", "now")
    container.portfolio_repository.try_record_state("u1", _state(HOUR))

    assert container.portfolio_repository.get_states("u2", None, None) == []


def test_get_states_returns_states_ordered_oldest_first():
    container.user_repository.insert("u1", "now")
    later = HourlyDate(day=date(2024, 1, 2), hour=9)
    container.portfolio_repository.try_record_state("u1", _state(later, total_value=200.0))
    container.portfolio_repository.try_record_state("u1", _state(HOUR, total_value=150.0))

    states = container.portfolio_repository.get_states("u1", None, None)

    assert [state.total_value for state in states] == [150.0, 200.0]


def test_get_states_includes_both_range_ends():
    container.user_repository.insert("u1", "now")
    before = HourlyDate.next(HOUR)
    after = HourlyDate.next(before)
    for hour in (HOUR, before, after):
        container.portfolio_repository.try_record_state("u1", _state(hour))

    states = container.portfolio_repository.get_states("u1", before, after)

    assert [state.timestamp for state in states] == [before, after]


def test_get_states_includes_the_latest_state_when_end_is_none():
    container.user_repository.insert("u1", "now")
    latest = HourlyDate.next(HOUR)
    container.portfolio_repository.try_record_state("u1", _state(HOUR))
    container.portfolio_repository.try_record_state("u1", _state(latest))

    states = container.portfolio_repository.get_states("u1", HOUR, None)

    assert [state.timestamp for state in states] == [HOUR, latest]


def test_get_states_round_trips_holdings_and_recorded_at():
    container.user_repository.insert("u1", "now")
    container.portfolio_repository.try_record_state("u1", _state(HOUR))

    state = container.portfolio_repository.get_states("u1", None, None)[0]

    assert state.holdings == {"AAPL": 2}
    assert state.recorded_at == RECORDED_AT


def test_get_last_recorded_hour_returns_none_when_nothing_is_recorded():
    container.user_repository.insert("u1", "now")

    assert container.portfolio_repository.get_last_recorded_hour("u1") is None


def test_get_last_recorded_hour_returns_the_latest_recorded_hour():
    container.user_repository.insert("u1", "now")
    latest = HourlyDate(day=date(2024, 1, 2), hour=9)
    container.portfolio_repository.try_record_state("u1", _state(HOUR))
    container.portfolio_repository.try_record_state("u1", _state(latest))

    assert container.portfolio_repository.get_last_recorded_hour("u1") == latest
