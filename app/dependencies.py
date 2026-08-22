"""FastAPI dependency functions that hand out services from the container.

Routes should depend on these via the `...Dep` annotations below (rather
than importing `container` directly), so tests can override them with
`app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.container import container
from app.repositories.trade_repository import TradeRepository
from app.services.auth_service import AuthService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.trade_submission_service import TradeSubmissionService
from app.services.user_service import UserService


def get_trade_repository() -> TradeRepository:
    return container.trade_repository


def get_user_service() -> UserService:
    return container.users


def get_auth_service() -> AuthService:
    return container.auth


def get_market_data_service() -> MarketDataService:
    return container.market_data


def get_portfolio_service() -> PortfolioService:
    return container.portfolios


def get_trade_service() -> TradeSubmissionService:
    return container.trades


TradeRepositoryDep = Annotated[TradeRepository, Depends(get_trade_repository)]

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
MarketDataServiceDep = Annotated[MarketDataService, Depends(get_market_data_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
TradeServiceDep = Annotated[TradeSubmissionService, Depends(get_trade_service)]
