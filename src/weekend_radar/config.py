"""Configuration helpers for environment settings and YAML data."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from weekend_radar.models import Destination

DEFAULT_DATA_PATH = Path("data/destinations.yaml")


class AppSettings(BaseSettings):
    """Environment-backed settings used by the skeleton runner."""

    model_config = SettingsConfigDict(
        env_prefix="WEEKEND_RADAR_",
        env_file=".env",
        extra="ignore",
    )

    config_path: Path = DEFAULT_DATA_PATH
    db_path: Path = Path("data/weekend_radar.sqlite3")
    log_level: str = "INFO"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


class DestinationCatalog(BaseModel):
    """Validated non-secret destination config loaded from YAML."""

    destinations: list[Destination] = Field(default_factory=list)


def load_settings() -> AppSettings:
    """Load application settings from the environment."""

    return AppSettings()


def load_destination_catalog(path: Path) -> DestinationCatalog:
    """Read and validate destination examples from YAML."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return DestinationCatalog.model_validate(raw_data)
