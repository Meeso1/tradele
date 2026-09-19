from __future__ import annotations

from typing import override

from app.jobs.scheduled_job import ScheduledJob
from app.models.market import HourlyDate
from app.services.portfolio_service import PortfolioService
from app.services.trade_execution_service import TradeExecutionService

_INTERVAL_SECONDS = 60 * 60


class TradesAndPortfolioUpdateJob(ScheduledJob):
    """Periodically fastforwards every user's active trades to the current
    hour, then records every user's resulting portfolio state.

    State recording runs in the same job, after fastforwarding, so a
    snapshot is never recorded before the hour's trades have executed -
    each hour's state is recorded at most once, so a separate job racing
    this one could lock in a pre-trade snapshot.
    """

    def __init__(
        self,
        trade_execution_service: TradeExecutionService,
        portfolio_service: PortfolioService,
    ) -> None:
        self._trade_execution_service: TradeExecutionService = trade_execution_service
        self._portfolio_service: PortfolioService = portfolio_service

    @property
    @override
    def name(self) -> str:
        return "trade_execution"

    @property
    @override
    def interval_seconds(self) -> float:
        return _INTERVAL_SECONDS

    @override
    def run(self) -> None:
        self._trade_execution_service.fastforward_all_users()
        self._portfolio_service.save_state_for_all_users(HourlyDate.last_passed_hour())
