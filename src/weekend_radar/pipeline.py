"""Minimal pipeline orchestration for the project skeleton."""

from __future__ import annotations

from pathlib import Path

from weekend_radar.config import AppSettings, load_destination_catalog, load_settings
from weekend_radar.filters import enabled_destinations
from weekend_radar.models import PipelineResult


def run_pipeline(settings: AppSettings | None = None) -> PipelineResult:
    """Load example config and return a small milestone-one status object."""

    app_settings = settings or load_settings()
    catalog = load_destination_catalog(Path(app_settings.config_path))
    active_destinations = enabled_destinations(catalog.destinations)

    return PipelineResult(
        status="ok",
        destination_count=len(active_destinations),
        source=str(app_settings.config_path),
        message="Weekend Radar skeleton is installed and ready for milestone two.",
    )
