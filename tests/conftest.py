from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_runtime_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the database, JWT signing keys, and logs at a per-test temp dir.

    This keeps tests from touching (or depending on) real dev runtime data,
    and ensures each test starts from a clean schema.
    """
    monkeypatch.setenv("TRADELE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("TRADELE_KEYS_DIR", str(tmp_path / "keys"))
    monkeypatch.setenv("TRADELE_LOG_DIR", str(tmp_path / "logs"))

    from app.container import container

    container.reset()
    container.database.run_migrations()
