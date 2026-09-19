"""Manual dependency wiring for the app's repositories and services.

A single `Container` instance is constructed here and reused for the life
of the process. Repositories/services take their dependencies as
constructor arguments, so this is the one place that knows how everything
is wired together.
"""

from __future__ import annotations

from app.jobs.job_scheduler import JobScheduler
from app.jobs.trades_and_portfolio_update_job import TradesAndPortfolioUpdateJob
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.user_repository import UserRepository
from app.services.alpaca_market_data_client import AlpacaMarketDataClient
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.authentication_service import AuthenticationService
from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.service_account_creator import ServiceAccountCreator
from app.services.settings_service import SettingsService
from app.services.trade_execution_service import TradeExecutionService
from app.services.trade_submission_service import TradeSubmissionService
from app.services.user_service import UserService


class Container:
    def __init__(self) -> None:
        self.settings: SettingsService = SettingsService()
        self.logger: LoggerService = LoggerService(self.settings)

        self.database: DatabaseService = DatabaseService(
            self.settings, self.logger.get_logger("DatabaseService")
        )

        self.user_repository: UserRepository = UserRepository(
            self.database, self.logger.get_logger("UserRepository")
        )
        self.portfolio_repository: PortfolioRepository = PortfolioRepository(
            self.database, self.settings, self.logger.get_logger("PortfolioRepository")
        )
        self.trade_repository: TradeRepository = TradeRepository(
            self.database, self.logger.get_logger("TradeRepository")
        )
        self.api_key_repository: ApiKeyRepository = ApiKeyRepository(
            self.database, self.logger.get_logger("ApiKeyRepository")
        )
        self.market_data_repository: MarketDataRepository = MarketDataRepository(
            self.database, self.logger.get_logger("MarketDataRepository")
        )

        self.users: UserService = UserService(
            self.user_repository, self.logger.get_logger("UserService")
        )
        self.auth: AuthService = AuthService(self.settings, self.logger.get_logger("AuthService"))
        self.api_keys: ApiKeyService = ApiKeyService(
            self.api_key_repository,
            self.users,
            self.settings,
            self.logger.get_logger("ApiKeyService"),
        )
        self.authentication: AuthenticationService = AuthenticationService(
            self.auth,
            self.api_keys,
            self.users,
            self.logger.get_logger("AuthenticationService"),
        )
        self.service_account_creator: ServiceAccountCreator = ServiceAccountCreator(
            self.users,
            self.api_keys,
            self.settings,
            self.logger.get_logger("ServiceAccountCreator"),
        )
        self.alpaca_client: AlpacaMarketDataClient = AlpacaMarketDataClient(
            self.settings, self.logger.get_logger("AlpacaMarketDataClient")
        )
        self.market_data: MarketDataService = MarketDataService(
            self.alpaca_client,
            self.market_data_repository,
            self.settings,
            self.logger.get_logger("MarketDataService"),
        )
        self.portfolios: PortfolioService = PortfolioService(
            self.portfolio_repository,
            self.users,
            self.market_data,
            self.logger.get_logger("PortfolioService"),
        )
        self.trades: TradeSubmissionService = TradeSubmissionService(
            self.trade_repository, self.settings, self.logger.get_logger("TradeService")
        )
        self.trade_execution: TradeExecutionService = TradeExecutionService(
            self.logger.get_logger("TradeExecutionService"),
            self.trade_repository,
            self.market_data,
            self.portfolio_repository,
            self.users,
            self.database,
        )

        self.job_scheduler: JobScheduler = JobScheduler(self.settings, self.logger.get_logger("JobScheduler"))
        self.job_scheduler.register(TradesAndPortfolioUpdateJob(self.trade_execution, self.portfolios))

    def reset(self) -> None:
        """Re-resolve settings/logging from the environment and propagate them.

        Existing repository/service instances are kept in place (and any
        state that must persist across resets, like registered
        migrations, is left untouched) - only their settings/logger
        references are refreshed. Used by tests to pick up environment
        variables set via `monkeypatch` after the module-level `container`
        singleton was already constructed.
        """
        self.settings = SettingsService()
        self.logger.configure(self.settings)

        self.database.configure(self.settings, self.logger.get_logger("DatabaseService"))

        self.user_repository.configure(self.logger.get_logger("UserRepository"))
        self.portfolio_repository.configure(
            self.settings, self.logger.get_logger("PortfolioRepository")
        )
        self.trade_repository.configure(self.logger.get_logger("TradeRepository"))
        self.api_key_repository.configure(self.logger.get_logger("ApiKeyRepository"))
        self.market_data_repository.configure(self.logger.get_logger("MarketDataRepository"))

        self.users.configure(self.logger.get_logger("UserService"))
        self.auth.configure(self.settings, self.logger.get_logger("AuthService"))
        self.api_keys.configure(self.settings, self.logger.get_logger("ApiKeyService"))
        self.authentication.configure(self.logger.get_logger("AuthenticationService"))
        self.service_account_creator.configure(
            self.settings, self.logger.get_logger("ServiceAccountCreator")
        )
        self.alpaca_client.configure(
            self.settings, self.logger.get_logger("AlpacaMarketDataClient")
        )
        self.market_data.configure(self.settings, self.logger.get_logger("MarketDataService"))
        self.portfolios.configure(self.logger.get_logger("PortfolioService"))
        self.trades.configure(self.settings, self.logger.get_logger("TradeService"))
        self.trade_execution.configure(self.logger.get_logger("TradeExecutionService"))

        self.job_scheduler.configure(self.settings, self.logger.get_logger("JobScheduler"))


container = Container()
