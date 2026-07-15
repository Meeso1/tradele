"""Application-wide logging, writing to both the console and a log file."""

from __future__ import annotations

import logging
import sys

from app.services.settings_service import SettingsService

LOGGER_NAME = "tradele"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class LoggerService:
    def __init__(self, settings: SettingsService) -> None:
        self._logger: logging.Logger = logging.getLogger(LOGGER_NAME)
        self.configure(settings)

    def configure(self, settings: SettingsService) -> None:
        """(Re)configure handlers/level from `settings`.

        Safe to call more than once - existing handlers are removed first,
        so this can be used both for initial setup and to pick up new
        settings later (e.g. when tests reset the container).
        """
        self._logger.setLevel(settings.log_level)
        self._logger.propagate = False

        for handler in list(self._logger.handlers):
            self._logger.removeHandler(handler)
            handler.close()

        formatter = logging.Formatter(LOG_FORMAT)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        settings.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(settings.log_dir / "tradele.log")
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Return a named child logger, e.g. `get_logger("UserService")`."""
        return self._logger.getChild(name)
