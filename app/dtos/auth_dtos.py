"""Request/response schemas for `app/routers/auth.py`."""

from __future__ import annotations

from pydantic import BaseModel


class IssueTokenRequest(BaseModel):
    user_id: str


class IssueTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
