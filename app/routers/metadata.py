from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.dependencies import (
    AuthContextDep,
    SettingsServiceDep,
    TutorialRepositoryDep,
    get_auth_context,
)
from app.dtos.metadata_dtos import MetadataResponse

# TODO(nitpick): rename - to what?
router = APIRouter(prefix="/metadata", tags=["metadata"], dependencies=[Depends(get_auth_context)])


@router.get("")
def get_metadata(
    auth_context: AuthContextDep,
    settings: SettingsServiceDep,
    tutorial_repo: TutorialRepositoryDep,
) -> MetadataResponse:
    now = datetime.now(tz=UTC)
    next_day_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return MetadataResponse(
        day_number=(now - settings.first_day_of_game).days,
        seconds_until_day_end=int((next_day_start - now).total_seconds()),
        has_completed_tutorial=tutorial_repo.has_completed_tutorial(user_id=auth_context.user_id),
    )


@router.post("/complete-tutorial")
def complete_tutorial(
    auth_context: AuthContextDep,
    tutorial_repo: TutorialRepositoryDep,
) -> None:
    tutorial_repo.mark_tutorial_completed(user_id=auth_context.user_id)
