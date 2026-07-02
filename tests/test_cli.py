import subprocess
from pathlib import Path


def test_scan_cli_runs_full_dry_run_pipeline(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    db_path = tmp_path / "weekend_radar.sqlite3"
    config_path.write_text(
        """
default_price_threshold_eur: 140
destination_thresholds_eur:
  FCO: 120
weekend_search:
  timezone: Europe/Riga
  future_windows_count: 8
  enabled_patterns:
    - friday_evening_to_sunday_evening
    - friday_evening_to_monday_morning
    - saturday_morning_to_sunday_evening
    - saturday_morning_to_monday_morning
offer_filters:
  max_price_eur: 120
  direct_only: true
destinations:
  - code: FCO
    city: Rome
    country: Italy
    nature_score: 3
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "weekend-radar",
            "scan",
            "--dry-run",
            "--limit",
            "3",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **__import__("os").environ,
            "WEEKEND_RADAR_CONFIG_PATH": str(config_path),
            "WEEKEND_RADAR_DB_PATH": str(db_path),
            "WEEKEND_RADAR_TELEGRAM_DRY_RUN": "true",
            "TELEGRAM_BOT_TOKEN": "plain-token",
            "TELEGRAM_CHAT_ID": "plain-chat",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "🔥 Weekend deal from Riga" in result.stdout
    assert "=== Scan Summary ===" in result.stdout
    assert "Selected top deals: 3" in result.stdout
    assert db_path.exists()
