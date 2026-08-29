from __future__ import annotations

import asyncio
import contextlib
import logging

from app.jobs.scheduled_job import ScheduledJob


class JobScheduler:
    """Runs a set of registered `ScheduledJob`s in the background for the lifetime of the app.

    Each job gets its own `asyncio` task that repeatedly runs the job (via
    `asyncio.to_thread`) and sleeps for its `interval_seconds` in between.
    `start`/`stop` are meant to be called once each, from the FastAPI
    `lifespan` handler.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger: logging.Logger = logger
        self._jobs: list[ScheduledJob] = []
        self._tasks: list[asyncio.Task[None]] = []

    def register(self, job: ScheduledJob) -> None:
        self._jobs.append(job)

    def start(self) -> None:
        self._tasks = [asyncio.create_task(self._run_job(job)) for job in self._jobs]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []

    async def _run_job(self, job: ScheduledJob) -> None:
        loop = asyncio.get_running_loop()
        while True:
            started_at = loop.time()
            try:
                await asyncio.to_thread(job.run)
            except Exception:
                self._logger.exception("Job %s failed", type(job).__name__)

            # TODO: This won't work correctly if we're too behind on iterations - shouldn't matter right now though
            elapsed = loop.time() - started_at
            await asyncio.sleep(max(0.0, job.interval_seconds - elapsed))
