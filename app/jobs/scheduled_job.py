from __future__ import annotations

import abc


class ScheduledJob(abc.ABC):
    """A unit of work that `JobScheduler` runs repeatedly for the lifetime of the app."""

    @property
    @abc.abstractmethod
    def interval_seconds(self) -> float:
        """How long to wait between the end of one run and the start of the next."""
        ...

    @abc.abstractmethod
    def run(self) -> None:
        """Run one iteration of the job.

        Called from a worker thread (via `asyncio.to_thread`), so this can
        make normal blocking/synchronous calls (e.g. into repositories).
        """
        ...
