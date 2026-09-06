from collections.abc import Callable

from fastapi.testclient import TestClient

from app.container import container
from app.main import app
from app.repositories.portfolio_repository import STARTING_CASH

client = TestClient(app)


def test_get_portfolio_creates_a_default_portfolio_for_a_new_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    user_id = container.users.create()

    response = client.get("/portfolio", headers=auth_headers(user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["cash"] == STARTING_CASH
    assert body["holdings"] == {symbol: 0 for symbol in container.settings.tradable_symbols}


def test_get_portfolio_rejects_a_token_for_an_unknown_user(
    auth_headers: Callable[[str], dict[str, str]],
):
    # The auth layer resolves the user (for per-user auth method checks), so
    # an unknown user is rejected there with 401, before the route's 404.
    response = client.get("/portfolio", headers=auth_headers("does-not-exist"))

    assert response.status_code == 401


def test_get_portfolio_requires_authentication():
    response = client.get("/portfolio")

    assert response.status_code == 401
