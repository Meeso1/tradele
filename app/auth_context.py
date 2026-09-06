"""The authenticated identity of the caller making a request.

`AuthContext` is built by `AuthenticationService` after verifying the
caller's credentials (an access token or an API key) and is what route
handlers depend on to find out who's calling, instead of trusting a
`user_id` supplied by the client itself.

Claims (scopes) are assigned based on both the caller's identity and the
auth method used: e.g. the service access scope is only granted to the
service account, and only when it authenticates with its API key - never
via a token minted by `/auth/token`, which doesn't prove identity.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AuthMethod = Literal["token", "api_key"]
AUTH_METHOD_TOKEN: AuthMethod = "token"
AUTH_METHOD_API_KEY: AuthMethod = "api_key"

# Grants access to service/automation endpoints (job triggering, API key
# management). Deliberately narrow - this is not a general "admin" scope.
SCOPE_SERVICE_ACCESS: str = "service:access"


class AuthContext(BaseModel):
    user_id: str
    method: AuthMethod
    scopes: frozenset[str] = frozenset()
    # ID of the API key used to authenticate; only set when `method` is
    # "api_key" (e.g. so new keys can record which key created them).
    api_key_id: str | None = None
