"""SQLite placeholder structure for the skeleton milestone."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DatabaseConfig:
    """Minimal database configuration placeholder."""

    path: Path


class StateDatabase:
    """A placeholder database boundary without persistence logic yet."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    def describe(self) -> str:
        """Return a human-readable description for logs and tests."""

        return f"SQLite placeholder at {self.config.path}"
