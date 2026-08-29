from __future__ import annotations

from typing import override

from app.jobs.scheduled_job import ScheduledJob
from app.services.trade_execution_service import TradeExecutionService

_INTERVAL_SECONDS = 60 * 60


class TradeExecutionJob(ScheduledJob):
    """Periodically fastforwards every user's active trades to the current hour.

    Errors are caught and logged by `JobScheduler`, so this doesn't need
    its own try/except.
    """

    def __init__(self, trade_execution_service: TradeExecutionService) -> None:
        self._trade_execution_service: TradeExecutionService = trade_execution_service

    @property
    @override
    def interval_seconds(self) -> float:
        return _INTERVAL_SECONDS

    @override
    def run(self) -> None:
        self._trade_execution_service.fastforward_all_users()
