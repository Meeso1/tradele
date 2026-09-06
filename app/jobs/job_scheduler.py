from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid

from app.jobs.scheduled_job import ScheduledJob
from app.services.settings_service import SettingsService


class JobScheduler:
    """Runs a set of registered `ScheduledJob`s in the background for the lifetime of the app.

    Each job gets its own `asyncio` task that repeatedly runs the job (via
    `asyncio.to_thread`) and sleeps for its `interval_seconds` in between.
    `start`/`stop` are meant to be called once each, from the FastAPI
    `lifespan` handler.
    """

    def __init__(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings: SettingsService = settings
        self._logger: logging.Logger = logger
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def register(self, job: ScheduledJob) -> None:
        if job.name in self._jobs:
            raise ValueError(f"Job with name {job.name} is already registered")

        self._jobs[job.name] = job

    def configure(self, settings: SettingsService, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def start(self) -> None:
        if not self._settings.run_scheduled_jobs:
            self._logger.info("Scheduled jobs are disabled - jobs should be triggered via API")
            return

        self._tasks = {
            self._create_task_key(job): asyncio.create_task(self._run_job(job))
            for job in self._jobs.values()
        }

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = {}

    def trigger_job(self, name: str) -> bool:
        if name not in self._jobs:
            return False

        job = self._jobs[name]
        key = self._create_task_key(job)
        task = asyncio.create_task(self._run_job_once(job))
        self._tasks[key] = task
        task.add_done_callback(lambda _: self._tasks.pop(key))

        return True

    async def _run_job(self, job: ScheduledJob) -> None:
        loop = asyncio.get_running_loop()
        while True:
            started_at = loop.time()
            try:
                await asyncio.to_thread(job.run)
            except Exception:
                self._logger.exception("Job %s failed", job.name)

            # TODO: This won't work correctly if we're too behind on iterations - shouldn't matter right now though
            elapsed = loop.time() - started_at
            await asyncio.sleep(max(0.0, job.interval_seconds - elapsed))

    async def _run_job_once(self, job: ScheduledJob) -> None:
        loop = asyncio.get_running_loop()
        started_at = loop.time()

        try:
            await asyncio.to_thread(job.run)
        except Exception:
            self._logger.exception("Job %s failed", job.name)

        elapsed = loop.time() - started_at
        self._logger.info("Job %s completed in %.2f seconds", job.name, elapsed)

    def _create_task_key(self, job: ScheduledJob) -> str:
        return f"{job.name}-{uuid.uuid4()}"
