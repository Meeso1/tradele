from app.container import container
from app.services.market_data_service import TRADABLE_SYMBOLS
from app.services.portfolio_service import STARTING_CASH, Portfolio


def test_get_or_create_creates_a_default_portfolio_for_a_new_user():
    user_id = container.users.create()

    portfolio = container.portfolios.get_or_create(user_id)

    assert portfolio.cash == STARTING_CASH
    assert portfolio.holdings == {symbol: 0 for symbol in TRADABLE_SYMBOLS}


def test_get_or_create_returns_the_same_portfolio_on_repeated_calls():
    user_id = container.users.create()

    first = container.portfolios.get_or_create(user_id)
    second = container.portfolios.get_or_create(user_id)

    assert first == second


def test_save_persists_changes_to_the_portfolio():
    user_id = container.users.create()
    portfolio = container.portfolios.get_or_create(user_id)

    updated = Portfolio(cash=portfolio.cash - 1000, holdings={**portfolio.holdings, "AAPL": 5})
    container.portfolios.save(user_id, updated)

    assert container.portfolios.get_or_create(user_id) == updated
