from pathlib import Path

from weekend_radar.config import AppSettings
from weekend_radar.main import main
from weekend_radar.pipeline import run_pipeline


def test_run_pipeline_loads_enabled_destinations_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "destinations.yaml"
    config_path.write_text(
        """
destinations:
  - origin: RIX
    destination: FCO
    city: Rome
    country: Italy
    enabled: true
    threshold_eur: 120
  - origin: RIX
    destination: BCN
    city: Barcelona
    country: Spain
    enabled: false
    threshold_eur: 150
""".strip(),
        encoding="utf-8",
    )

    settings = AppSettings(
        config_path=config_path,
        db_path=tmp_path / "weekend_radar.sqlite3",
        log_level="INFO",
    )

    result = run_pipeline(settings)

    assert result.status == "ok"
    assert result.destination_count == 1
    assert result.source == str(config_path)


def test_main_returns_success_with_sample_data(monkeypatch: object) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main() == 0
