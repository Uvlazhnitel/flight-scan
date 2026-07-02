"""Configuration helpers for environment settings and YAML data."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from weekend_radar.models import AppConfig

DEFAULT_DATA_PATH = Path("data/destinations.yaml")


class ConfigLoadError(RuntimeError):
    """A beginner-friendly configuration error."""


class AppSettings(BaseSettings):
    """Environment-backed settings used by the skeleton runner."""

    model_config = SettingsConfigDict(
        env_prefix="WEEKEND_RADAR_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    config_path: Path = DEFAULT_DATA_PATH
    db_path: Path = Path("data/weekend_radar.sqlite3")
    log_level: str = "INFO"
    telegram_dry_run: bool = True
    telegram_bot_token: str | None = Field(default=None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, validation_alias="TELEGRAM_CHAT_ID")


def load_settings() -> AppSettings:
    """Load application settings from the environment."""

    return AppSettings()


def validate_settings(settings: AppSettings) -> None:
    """Reject placeholder path values that would make first-run UX confusing."""

    if str(settings.config_path) == "replace-me":
        raise ConfigLoadError(
            "WEEKEND_RADAR_CONFIG_PATH still uses 'replace-me'. "
            "Set it to data/destinations.yaml or remove it from .env."
        )
    if str(settings.db_path) == "replace-me":
        raise ConfigLoadError(
            "WEEKEND_RADAR_DB_PATH still uses 'replace-me'. "
            "Set it to data/weekend_radar.sqlite3 or remove it from .env."
        )


def load_app_config(path: Path) -> AppConfig:
    """Read and validate non-secret app config from YAML."""

    try:
        raw_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigLoadError(
            f"Config file not found at {path}. Check WEEKEND_RADAR_CONFIG_PATH."
        ) from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(
            f"Config file at {path} is not valid YAML. Fix the YAML syntax and try again."
        ) from exc

    try:
        return AppConfig.model_validate(raw_data)
    except ValidationError as exc:
        raise ConfigLoadError(
            f"Config file at {path} is invalid: {exc.errors()[0]['msg']}"
        ) from exc
