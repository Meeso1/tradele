from app.container import container
from app.repositories.portfolio_repository import Portfolio


def test_get_returns_none_for_a_user_with_no_portfolio():
    container.user_repository.insert("u1", "now")

    assert container.portfolio_repository.get("u1") is None


def test_insert_then_get_returns_the_stored_portfolio():
    container.user_repository.insert("u1", "now")
    portfolio = Portfolio(cash=1000.0, holdings={"AAPL": 2})

    container.portfolio_repository.insert("u1", portfolio)

    assert container.portfolio_repository.get("u1") == portfolio


def test_update_overwrites_the_stored_portfolio():
    container.user_repository.insert("u1", "now")
    container.portfolio_repository.insert("u1", Portfolio(cash=1000.0, holdings={"AAPL": 2}))

    updated = Portfolio(cash=500.0, holdings={"AAPL": 4})
    container.portfolio_repository.update("u1", updated)

    assert container.portfolio_repository.get("u1") == updated
