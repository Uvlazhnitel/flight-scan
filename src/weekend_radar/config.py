"""Configuration helpers for environment settings and YAML data."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from weekend_radar.models import AppConfig

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


def load_settings() -> AppSettings:
    """Load application settings from the environment."""

    return AppSettings()


def load_app_config(path: Path) -> AppConfig:
    """Read and validate non-secret app config from YAML."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw_data)
