from weekend_radar.config import AppSettings


def test_app_settings_read_telegram_credentials_without_prefix(monkeypatch: object) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "plain-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "plain-chat")
    monkeypatch.setenv("WEEKEND_RADAR_TELEGRAM_DRY_RUN", "false")

    settings = AppSettings()

    assert settings.telegram_bot_token == "plain-token"
    assert settings.telegram_chat_id == "plain-chat"
    assert settings.telegram_dry_run is False
