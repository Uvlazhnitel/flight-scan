import os
import subprocess
from pathlib import Path


def build_cli_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if overrides:
        env.update(overrides)
    return env


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
        env=build_cli_env(
            {
                "WEEKEND_RADAR_CONFIG_PATH": str(config_path),
                "WEEKEND_RADAR_DB_PATH": str(db_path),
                "WEEKEND_RADAR_TELEGRAM_DRY_RUN": "true",
                "TELEGRAM_BOT_TOKEN": "plain-token",
                "TELEGRAM_CHAT_ID": "plain-chat",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "🔥 Weekend deal from Riga" in result.stdout
    assert "=== Scan Summary ===" in result.stdout
    assert "Provider: mock (mock data)" in result.stdout
    assert "Mode: dry-run" in result.stdout
    assert "Selected top deals: 3" in result.stdout
    assert db_path.exists()


def test_scan_cli_fails_cleanly_for_missing_config_file(tmp_path: Path) -> None:
    missing_config_path = tmp_path / "missing-destinations.yaml"
    db_path = tmp_path / "weekend_radar.sqlite3"

    result = subprocess.run(
        [
            "uv",
            "run",
            "weekend-radar",
            "scan",
            "--dry-run",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=build_cli_env(
            {
                "WEEKEND_RADAR_CONFIG_PATH": str(missing_config_path),
                "WEEKEND_RADAR_DB_PATH": str(db_path),
                "WEEKEND_RADAR_TELEGRAM_DRY_RUN": "true",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error: Config file not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_scan_cli_fails_cleanly_for_invalid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    db_path = tmp_path / "weekend_radar.sqlite3"
    config_path.write_text("destinations: [broken", encoding="utf-8")

    result = subprocess.run(
        [
            "uv",
            "run",
            "weekend-radar",
            "scan",
            "--dry-run",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=build_cli_env(
            {
                "WEEKEND_RADAR_CONFIG_PATH": str(config_path),
                "WEEKEND_RADAR_DB_PATH": str(db_path),
                "WEEKEND_RADAR_TELEGRAM_DRY_RUN": "true",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error: Config file at" in result.stderr
    assert "not valid YAML" in result.stderr
    assert "Traceback" not in result.stderr


def test_copied_env_example_is_runnable_for_first_dry_run(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env_path = tmp_path / ".env"
    env_path.write_text((repo_root / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    env_values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_values[key] = value

    result = subprocess.run(
        [
            "uv",
            "run",
            "weekend-radar",
            "scan",
            "--dry-run",
            "--limit",
            "1",
        ],
        cwd=repo_root,
        env=build_cli_env(env_values),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Mode: dry-run" in result.stdout
    assert "Provider: mock (mock data)" in result.stdout


def test_scan_cli_fails_cleanly_when_real_send_lacks_credentials(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    db_path = tmp_path / "weekend_radar.sqlite3"
    config_path.write_text(
        """
provider: mock
default_price_threshold_eur: 140
destination_thresholds_eur:
  FCO: 120
weekend_search:
  timezone: Europe/Riga
  future_windows_count: 8
  enabled_patterns:
    - friday_evening_to_sunday_evening
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
            "--limit",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=build_cli_env(
            {
                "WEEKEND_RADAR_CONFIG_PATH": str(config_path),
                "WEEKEND_RADAR_DB_PATH": str(db_path),
                "WEEKEND_RADAR_TELEGRAM_DRY_RUN": "false",
                "TELEGRAM_BOT_TOKEN": "",
                "TELEGRAM_CHAT_ID": "",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID" in result.stderr
    assert "Traceback" not in result.stderr
