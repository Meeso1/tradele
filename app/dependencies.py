"""FastAPI dependency functions that hand out services from the container.

Routes should depend on these via the `...Dep` annotations below (rather
than importing `container` directly), so tests can override them with
`app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.container import container
from app.services.auth_service import AuthService
from app.services.user_service import UserService


def get_user_service() -> UserService:
    return container.users


def get_auth_service() -> AuthService:
    return container.auth


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
