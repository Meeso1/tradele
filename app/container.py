"""Manual dependency wiring for the app's repositories and services.

A single `Container` instance is constructed here and reused for the life
of the process. Repositories/services take their dependencies as
constructor arguments, so this is the one place that knows how everything
is wired together.
"""

from __future__ import annotations

from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.settings_service import SettingsService
from app.services.trade_service import TradeService
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
            self.database, self.logger.get_logger("PortfolioRepository")
        )
        self.trade_repository: TradeRepository = TradeRepository(
            self.database, self.logger.get_logger("TradeRepository")
        )

        self.users: UserService = UserService(
            self.user_repository, self.logger.get_logger("UserService")
        )
        self.auth: AuthService = AuthService(self.settings, self.logger.get_logger("AuthService"))
        self.market_data: MarketDataService = MarketDataService(
            self.logger.get_logger("MarketDataService")
        )
        self.portfolios: PortfolioService = PortfolioService(
            self.portfolio_repository, self.logger.get_logger("PortfolioService")
        )
        self.trades: TradeService = TradeService(
            self.trade_repository, self.logger.get_logger("TradeService")
        )

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
        self.portfolio_repository.configure(self.logger.get_logger("PortfolioRepository"))
        self.trade_repository.configure(self.logger.get_logger("TradeRepository"))

        self.users.configure(self.logger.get_logger("UserService"))
        self.auth.configure(self.settings, self.logger.get_logger("AuthService"))
        self.market_data.configure(self.logger.get_logger("MarketDataService"))
        self.portfolios.configure(self.logger.get_logger("PortfolioService"))
        self.trades.configure(self.logger.get_logger("TradeService"))


container = Container()
