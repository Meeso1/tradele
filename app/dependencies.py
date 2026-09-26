"""FastAPI dependency functions that hand out services from the container.

Routes should depend on these via the `...Dep` annotations below (rather
than importing `container` directly), so tests can override them with
`app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated
from urllib import parse

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from app.auth_context import SCOPE_SERVICE_ACCESS, AuthContext
from app.container import container
from app.jobs.job_scheduler import JobScheduler
from app.repositories.trade_repository import TradeRepository
from app.repositories.tutorial_repository import TutorialRepository
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.authentication_service import (
    AuthenticationService,
    ForbiddenError,
    UnauthorizedError,
)
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.settings_service import SettingsService
from app.services.trade_submission_service import TradeSubmissionService
from app.services.user_service import UserService

_bearer_scheme = HTTPBearer(auto_error=False)
_basic_scheme = HTTPBasic(auto_error=False)


def get_auth_context(
    bearer_credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    basic_credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic_scheme)],
) -> AuthContext:
    """Verify the caller's credentials (Bearer access token or Basic API
    key) and expose the resulting identity, auth method, scopes and key
    metadata to routes.

    API keys use HTTP Basic auth where the username is the URL-encoded key
    ID and the password is the URL-encoded secret (the pair itself is
    base64-encoded as required by the Basic scheme).

    Routes that need to know who's calling should depend on
    `AuthContextDep` instead of accepting a `user_id` from the client
    (query param/body), so identity comes from verified credentials instead
    of being self-reported.
    """
    try:
        if bearer_credentials is not None:
            return container.authentication.authenticate_token(
                bearer_credentials.credentials
            )
        if basic_credentials is not None:
            key_id, secret = _decode_api_key_parts(basic_credentials)
            return container.authentication.authenticate_api_key(key_id, secret)
        raise UnauthorizedError("Missing credentials")
    except UnauthorizedError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired credentials"
        ) from error
    except ForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication method not allowed for this account",
        ) from error


def _decode_api_key_parts(
    credentials: HTTPBasicCredentials,
) -> tuple[str, str]:
    """Decode API key Basic credentials of the form
    `base64(urlencode(key_id)):base64(urlencode(secret))`, returning the
    arbitrary-string parts."""
    key_id = parse.unquote(credentials.username)
    secret = parse.unquote(credentials.password)
    return key_id, secret


def require_service_access(auth_context: AuthContextDep) -> AuthContext:
    """Require the `service:access` scope, which only the service account
    holds (and only when authenticating with its API key).

    API key management additionally checks the identity itself, so it stays
    service-account-only even if scope assignment changes later.
    """
    if SCOPE_SERVICE_ACCESS not in auth_context.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Service access required"
        )
    if auth_context.user_id != UserService.SERVICE_ACCOUNT_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Service account required"
        )
    return auth_context


def get_trade_repository() -> TradeRepository:
    return container.trade_repository


def get_tutorial_repository() -> TutorialRepository:
    return container.tutorial_repository


def get_user_service() -> UserService:
    return container.users


def get_auth_service() -> AuthService:
    return container.auth


def get_api_key_service() -> ApiKeyService:
    return container.api_keys


def get_authentication_service() -> AuthenticationService:
    return container.authentication


def get_market_data_service() -> MarketDataService:
    return container.market_data


def get_portfolio_service() -> PortfolioService:
    return container.portfolios


def get_trade_service() -> TradeSubmissionService:
    return container.trades


def get_settings_service() -> SettingsService:
    return container.settings


def get_job_scheduler() -> JobScheduler:
    return container.job_scheduler


TradeRepositoryDep = Annotated[TradeRepository, Depends(get_trade_repository)]

TutorialRepositoryDep = Annotated[TutorialRepository, Depends(get_tutorial_repository)]

AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]
ServiceAccessDep = Annotated[AuthContext, Depends(require_service_access)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
AuthenticationServiceDep = Annotated[
    AuthenticationService, Depends(get_authentication_service)
]
MarketDataServiceDep = Annotated[MarketDataService, Depends(get_market_data_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
TradeServiceDep = Annotated[TradeSubmissionService, Depends(get_trade_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
JobSchedulerDep = Annotated[JobScheduler, Depends(get_job_scheduler)]
