from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.dependencies import SettingsServiceDep, get_auth_context
from app.dtos.metadata_dtos import MetadataResponse

# TODO(nitpick): rename - to what?
router = APIRouter(prefix="/metadata", tags=["metadata"], dependencies=[Depends(get_auth_context)])


@router.get("")
def get_metadata(settings: SettingsServiceDep) -> MetadataResponse:
    now = datetime.now(tz=UTC)
    next_day_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return MetadataResponse(
        day_number=(now - settings.first_day_of_game).days,
        seconds_until_day_end=int((next_day_start - now).total_seconds()),
    )
