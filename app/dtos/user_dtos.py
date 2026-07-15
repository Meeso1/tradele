"""Request/response schemas for `app/routers/users.py`."""

from __future__ import annotations

from pydantic import BaseModel


class CreateUserResponse(BaseModel):
    id: str
