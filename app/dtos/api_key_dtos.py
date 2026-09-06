"""Request/response schemas for `app/routers/api_keys.py`.

The key value is only ever present in `CreateApiKeyResponse` (`secret`,
plus the ready-to-use `authorization` header value) - it can't be retrieved
again afterwards.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CreateApiKeyResponse(BaseModel):
    id: str
    name: str
    secret: str
    authorization: str
    created_at: datetime
    created_by_key: str | None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    created_by_key: str | None
    created_at: datetime
    deactivated_at: datetime | None
