"""Application configuration, resolved once from the environment.

Centralizing environment access here means no other module reads
`os.environ` directly - everything else takes the values it needs from a
`SettingsService` instance, handed to it by the container. This also leaves
room to swap in a different source (e.g. a JSON/YAML config file) later
without touching any call sites.
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path


class SettingsService:
    def __init__(self) -> None:
        self.db_path: Path = Path(os.environ.get("TRADELE_DB_PATH", "tradele.db"))
        self.keys_dir: Path = Path(os.environ.get("TRADELE_KEYS_DIR", "keys"))
        self.log_dir: Path = Path(os.environ.get("TRADELE_LOG_DIR", "logs"))
        self.log_level: str = os.environ.get("TRADELE_LOG_LEVEL", "INFO")

        self.frontend_dist_dir: Path = Path(
            os.environ.get("TRADELE_FRONTEND_DIST", "frontend/dist")
        )

        self.tradable_symbols: list[str] = [
            symbol.strip().upper()
            for symbol in os.environ.get(
                "TRADELE_TRADABLE_SYMBOLS", "AAPL,GOOGL,MSFT,AMZN,TSLA"
            ).split(",")
            if symbol.strip()
        ]
        self.first_day_of_game: datetime = datetime.strptime(
            os.environ.get("TRADELE_FIRST_DAY_OF_GAME", "2026-09-01"), "%Y-%m-%d"
        ).replace(tzinfo=UTC)

        self.alpaca_api_key_id: str = os.environ.get("ALPACA_API_KEY_ID", "")
        self.alpaca_api_secret_key: str = os.environ.get("ALPACA_API_SECRET_KEY", "")
        self.alpaca_base_url: str = os.environ.get(
            "ALPACA_DATA_BASE_URL", "https://data.alpaca.markets"
        )

        # SHA-256 hex digest of the secret part of the service account's API
        # key, used to create the key on first startup
        self.service_api_key_hash: str = os.environ.get("TRADELE_SERVICE_API_KEY_HASH", "")

        # If false, scheduled jobs are not run on a background schedule;
        # the service is expected to trigger them via the scheduled-jobs API.
        self.run_scheduled_jobs: bool = os.environ.get("TRADELE_RUN_SCHEDULED_JOBS", "true").lower() == "true"
