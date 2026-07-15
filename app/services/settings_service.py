"""Application configuration, resolved once from the environment.

Centralizing environment access here means no other module reads
`os.environ` directly - everything else takes the values it needs from a
`SettingsService` instance, handed to it by the container. This also leaves
room to swap in a different source (e.g. a JSON/YAML config file) later
without touching any call sites.
"""

from __future__ import annotations

import os
from pathlib import Path


class SettingsService:
    def __init__(self) -> None:
        self.db_path: Path = Path(os.environ.get("TRADELE_DB_PATH", "tradele.db"))
        self.keys_dir: Path = Path(os.environ.get("TRADELE_KEYS_DIR", "keys"))
        self.log_dir: Path = Path(os.environ.get("TRADELE_LOG_DIR", "logs"))
        self.log_level: str = os.environ.get("TRADELE_LOG_LEVEL", "INFO")
