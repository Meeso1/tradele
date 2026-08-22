"""The authenticated identity of the caller making a request.

`AuthContext` is built from a verified access token's claims (see
`AuthService.decode_access_token`) and is what route handlers depend on to
find out who's calling, instead of trusting a `user_id` supplied by the
client itself.

It's intentionally minimal today (just `user_id`, from the token's `sub`
claim), but is meant to be the one place new claims get exposed to routes
as they're needed (e.g. roles/scopes), so routes never need to know about
raw JWT payloads.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AuthContext(BaseModel):
    user_id: str

    @classmethod
    def from_token_payload(cls, payload: dict[str, Any]) -> AuthContext:
        return cls(user_id=payload["sub"])
