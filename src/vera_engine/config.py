"""Environment-driven configuration. Zero surprises."""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Single source of truth for runtime configuration."""

    def __init__(self) -> None:
        self.data_dir = Path(os.getenv("VERA_DATA_DIR", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "vera_ledger.db"
        self.private_key_path = self.data_dir / "ed25519_private.pem"
        self.public_key_path = self.data_dir / "ed25519_public.pem"

        # SaaS metering defaults
        self.default_tenant = os.getenv("VERA_DEFAULT_TENANT", "demo")
        self.metering_enabled = os.getenv("VERA_METERING", "1") == "1"

        # Strict mode: reject unsigned or malformed payloads
        self.strict = os.getenv("VERA_STRICT", "1") == "1"


settings = Settings()
