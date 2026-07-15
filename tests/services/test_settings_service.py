from pathlib import Path

import pytest

from app.services.settings_service import SettingsService


def test_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRADELE_DB_PATH", str(tmp_path / "custom.db"))
    monkeypatch.setenv("TRADELE_KEYS_DIR", str(tmp_path / "custom-keys"))
    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "custom-logs"))
    monkeypatch.setenv("TRADELE_LOG_LEVEL", "DEBUG")

    settings = SettingsService()

    assert settings.db_path == tmp_path / "custom.db"
    assert settings.keys_dir == tmp_path / "custom-keys"
    assert settings.log_dir == tmp_path / "custom-logs"
    assert settings.log_level == "DEBUG"


def test_settings_fall_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRADELE_DB_PATH", raising=False)
    monkeypatch.delenv("TRADELE_KEYS_DIR", raising=False)
    monkeypatch.delenv("TRADELE_LOG_DIR", raising=False)
    monkeypatch.delenv("TRADELE_LOG_LEVEL", raising=False)

    settings = SettingsService()

    assert settings.db_path == Path("tradele.db")
    assert settings.keys_dir == Path("keys")
    assert settings.log_dir == Path("logs")
    assert settings.log_level == "INFO"
