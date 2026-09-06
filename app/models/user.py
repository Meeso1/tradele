from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserInfo(BaseModel):
    user_id: str
    created_at: datetime
    is_service_account: bool
    allowed_auth_methods: tuple[str, ...]
