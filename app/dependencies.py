"""FastAPI dependency functions that hand out services from the container.

Routes should depend on these via the `...Dep` annotations below (rather
than importing `container` directly), so tests can override them with
`app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth_context import AuthContext
from app.container import container
from app.repositories.trade_repository import TradeRepository
from app.services.auth_service import AuthService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.trade_submission_service import TradeSubmissionService
from app.services.user_service import UserService

_bearer_scheme = HTTPBearer()


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> AuthContext:
    """Verify the caller's access token and expose its claims to routes.

    Routes that need to know who's calling should depend on
    `AuthContextDep` instead of accepting a `user_id` from the client
    (query param/body), so identity comes from a verified token instead of
    being self-reported.
    """
    try:
        payload = container.auth.decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token"
        ) from error
    return AuthContext.from_token_payload(payload)


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

AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
MarketDataServiceDep = Annotated[MarketDataService, Depends(get_market_data_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
TradeServiceDep = Annotated[TradeSubmissionService, Depends(get_trade_service)]
