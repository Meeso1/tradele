"""Data for API key authentication, backed by the `api_keys` table.

Key values are never stored - only a SHA-256 hash of the secret part. The
plaintext credential is shown exactly once, when the key is created (or
auto-generated for the service account at startup).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic.dataclasses import dataclass


@dataclass
class ApiKey:
    id: str
    user_id: str
    name: str
    key_hash: str
    created_by_key: str | None
    created_at: datetime
    deactivated_at: datetime | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ApiKey:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            key_hash=row["key_hash"],
            created_by_key=row["created_by_key"],
            created_at=datetime.fromisoformat(row["created_at"]),
            deactivated_at=(
                datetime.fromisoformat(row["deactivated_at"])
                if row["deactivated_at"] is not None
                else None
            ),
        )
