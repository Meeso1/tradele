from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import JobSchedulerDep, require_service_access

router = APIRouter(prefix="/scheduled-jobs", tags=["scheduled-jobs"], dependencies=[Depends(require_service_access)])


@router.post("/trigger", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_job(
    job_scheduler: JobSchedulerDep,
    job_name: Annotated[str, Query()],
) -> None:
    found = job_scheduler.trigger_job(job_name)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job with provided name not found")
