from pathlib import Path

import pytest

from app.services.logger_service import LoggerService
from app.services.settings_service import SettingsService


def test_get_logger_writes_to_console_and_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "logs"))
    settings = SettingsService()

    logger_service = LoggerService(settings)
    logger = logger_service.get_logger("SomeService")
    logger.info("hello from a test")

    log_file = settings.log_dir / "tradele.log"
    contents = log_file.read_text()
    assert "hello from a test" in contents
    assert "SomeService" in contents


def test_configure_switches_log_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "logs-a"))
    settings = SettingsService()
    logger_service = LoggerService(settings)

    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "logs-b"))
    new_settings = SettingsService()
    logger_service.configure(new_settings)

    logger_service.get_logger("SomeService").info("goes to logs-b")

    log_file_a = tmp_path / "logs-a" / "tradele.log"
    log_file_b = tmp_path / "logs-b" / "tradele.log"
    assert not log_file_a.exists() or log_file_a.read_text() == ""
    assert "goes to logs-b" in log_file_b.read_text()
