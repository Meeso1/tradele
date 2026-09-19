from app.jobs.trades_and_portfolio_update_job import TradesAndPortfolioUpdateJob
from app.models.market import HourlyDate


def test_run_fastforwards_trades_before_recording_portfolio_states():
    calls: list[str] = []

    class FakeTradeExecutionService:
        def fastforward_all_users(self) -> None:
            calls.append("fastforward")

    class FakePortfolioService:
        def save_state_for_all_users(self, hour: HourlyDate) -> None:
            calls.append("save_states")

    TradesAndPortfolioUpdateJob(FakeTradeExecutionService(), FakePortfolioService()).run()  # type: ignore[arg-type]

    assert calls == ["fastforward", "save_states"]
