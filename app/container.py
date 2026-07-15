"""Manual dependency wiring for the app's services.

A single `Container` instance is constructed here and reused for the life
of the process. Services take their dependencies as constructor arguments,
so this is the one place that knows how everything is wired together.
"""

from __future__ import annotations

from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService


class Container:
    def __init__(self) -> None:
        self.settings: SettingsService = SettingsService()
        self.logger: LoggerService = LoggerService(self.settings)

        self.database: DatabaseService = DatabaseService(
            self.settings, self.logger.get_logger("DatabaseService")
        )
        self.users: UserService = UserService(self.database, self.logger.get_logger("UserService"))
        self.auth: AuthService = AuthService(self.settings, self.logger.get_logger("AuthService"))

    def reset(self) -> None:
        """Re-resolve settings/logging from the environment and propagate them.

        Existing service instances are kept in place (and any state that
        must persist across resets, like registered migrations, is left
        untouched) - only their settings/logger references are refreshed.
        Used by tests to pick up environment variables set via `monkeypatch`
        after the module-level `container` singleton was already constructed.
        """
        self.settings = SettingsService()
        self.logger.configure(self.settings)

        self.database.configure(self.settings, self.logger.get_logger("DatabaseService"))
        self.users.configure(self.logger.get_logger("UserService"))
        self.auth.configure(self.settings, self.logger.get_logger("AuthService"))


container = Container()
