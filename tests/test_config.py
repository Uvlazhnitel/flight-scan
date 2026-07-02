from pathlib import Path

from weekend_radar.config import (
    DEFAULT_DATA_PATH,
    AppSettings,
    ConfigLoadError,
    load_app_config,
    validate_settings,
)

ALLOWED_TAGS = {
    "hiking",
    "mountains",
    "lake",
    "sea",
    "citybreak",
    "culture",
    "food",
    "cheap",
    "nature",
    "island",
}


def test_app_settings_read_telegram_credentials_without_prefix(monkeypatch: object) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "plain-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "plain-chat")
    monkeypatch.setenv("WEEKEND_RADAR_TELEGRAM_DRY_RUN", "false")

    settings = AppSettings()

    assert settings.telegram_bot_token == "plain-token"
    assert settings.telegram_chat_id == "plain-chat"
    assert settings.telegram_dry_run is False


def test_validate_settings_rejects_placeholder_paths() -> None:
    settings = AppSettings(
        config_path="replace-me",
        db_path="replace-me",
    )

    try:
        validate_settings(settings)
    except ConfigLoadError as exc:
        assert "WEEKEND_RADAR_CONFIG_PATH" in str(exc)
    else:
        raise AssertionError("Expected ConfigLoadError for placeholder config path")


def test_shipped_destinations_yaml_validates_as_app_config() -> None:
    app_config = load_app_config(Path(DEFAULT_DATA_PATH))

    assert 25 <= len(app_config.destinations) <= 40


def test_enabled_destinations_in_shipped_yaml_have_required_fields() -> None:
    app_config = load_app_config(Path(DEFAULT_DATA_PATH))

    enabled_destinations = [
        destination for destination in app_config.destinations if destination.enabled
    ]

    assert enabled_destinations
    for destination in enabled_destinations:
        assert destination.code
        assert destination.city
        assert destination.country
        assert destination.lat is not None
        assert destination.lon is not None
        assert destination.tags
        assert 0 <= destination.nature_score <= 10


def test_shipped_destination_tags_use_only_allowed_vocabulary() -> None:
    app_config = load_app_config(Path(DEFAULT_DATA_PATH))

    for destination in app_config.destinations:
        assert set(destination.tags).issubset(ALLOWED_TAGS)
