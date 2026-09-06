import asyncio
import logging
from typing import override

from app.jobs.job_scheduler import JobScheduler
from app.jobs.scheduled_job import ScheduledJob


class RecordingJob(ScheduledJob):
    def __init__(self, name: str, interval_seconds: float = 1.0) -> None:
        self._name: str = name
        self._interval_seconds: float = interval_seconds
        self.run_count: int = 0

    @property
    @override
    def name(self) -> str:
        return self._name

    @property
    @override
    def interval_seconds(self) -> float:
        return self._interval_seconds

    @override
    def run(self) -> None:
        self.run_count += 1


def _make_scheduler(**settings_overrides: object) -> JobScheduler:
    from app.container import container

    settings = container.settings
    for key, value in settings_overrides.items():
        setattr(settings, key, value)
    return JobScheduler(settings, logging.getLogger("test"))


def test_register_rejects_duplicate_names():
    scheduler = _make_scheduler()
    job = RecordingJob("some_job")
    scheduler.register(job)

    try:
        scheduler.register(RecordingJob("some_job"))
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for duplicate job name")

    assert scheduler._jobs["some_job"] is job


def test_trigger_job_returns_false_for_unknown_job():
    scheduler = _make_scheduler()

    assert scheduler.trigger_job("nonexistent") is False


def test_trigger_job_runs_once_and_cleans_up_task():
    scheduler = _make_scheduler()
    job = RecordingJob("some_job")
    scheduler.register(job)

    async def wait_for_run() -> None:
        assert scheduler.trigger_job("some_job") is True
        while job.run_count == 0:
            await asyncio.sleep(0.01)
        # Let the done callback fire so the task entry is cleaned up.
        await asyncio.sleep(0.01)

    asyncio.run(wait_for_run())

    assert job.run_count == 1
    assert scheduler._tasks == {}


def test_start_does_nothing_when_jobs_disabled():

    scheduler = _make_scheduler(run_scheduled_jobs=False)
    scheduler.register(RecordingJob("some_job"))

    scheduler.start()

    assert scheduler._tasks == {}
