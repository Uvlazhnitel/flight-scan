# Weekend Radar

Weekend Radar is a small personal app that watches for cheap weekend flight ideas from Riga Airport (`RIX`) and sends a Telegram alert when a good deal appears.

This repository now includes the Milestone 1 project skeleton. The app logic is still intentionally minimal, but the Python project, package layout, placeholder pipeline, tests, and tooling are in place.
The MVP currently uses deterministic mock flight data only and does not call any real flight API.

## MVP Goal

The MVP is a backend-only Python service that:

- reads route and pricing rules from a YAML config file,
- loads secrets from environment variables,
- fetches mock flight data through a provider abstraction,
- stores deal history and notification state in SQLite,
- sends Telegram notifications for good weekend flight deals.

## What Counts as a Good Deal

For the MVP, a flight is considered a good deal when:

- its price is less than or equal to a configured threshold,
- the threshold may be set per route,
- a global fallback threshold is used when a route-specific threshold is not defined.

## MVP Scope

- Backend only
- Python 3.12+
- `uv` for dependency management
- `pytest` for tests
- `ruff` for linting and formatting
- `pydantic` for models and validation
- `httpx` for HTTP integrations
- SQLite for local persistence
- Telegram for notifications
- Mock flight provider first

## Non-Goals for MVP

- No frontend
- No mobile app
- No booking or payments
- No user accounts
- No airline website scraping
- No real flight API integration yet
- No tests that call external APIs

## Planned Stack

- Language: Python 3.12+
- Dependency management: `uv`
- Data validation: `pydantic`
- HTTP client: `httpx`
- Local database: SQLite
- Config format: YAML
- Testing: `pytest`
- Linting and formatting: `ruff`

## How It Will Work

1. Load secrets from environment variables and runtime config from YAML.
2. Ask a deterministic mock flight provider for fake flight options from `RIX`.
3. Keep only weekend-friendly options.
4. Compare each price to the configured threshold rules.
5. Skip deals that were already notified recently.
6. Save state in SQLite.
7. Send Telegram notifications for new good deals.

## Repository Status

Current contents:

- `pyproject.toml`
- `src/weekend_radar/`
- `tests/`
- `data/destinations.yaml`
- `README.md`
- `PLAN.md`
- `ARCHITECTURE.md`
- `TASKS.md`
- `AGENTS.md`
- `.env.example`

Current omissions:

- no real flight API integration yet,
- no real Telegram sending yet,
- no production SQLite logic yet,
- no CI yet.

## Data Source

For the MVP so far, flight search runs on deterministic in-repo mock data only.

- no external flight APIs are called,
- no airline websites are scraped,
- tests stay fully offline.

## Local Setup

1. Install Python 3.12 or newer.
2. Install `uv`.
3. Copy `.env.example` to `.env`.
4. Sync dependencies.

```bash
cp .env.example .env
uv sync
```

## Run Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Run the Skeleton

The current entrypoint only proves that the project is wired correctly. It reads the sample YAML file, configures logging, and exits successfully.

```bash
uv run python -m weekend_radar.main
```

## Current Structure

```text
src/weekend_radar/
  __init__.py
  main.py
  config.py
  models.py
  dates.py
  filters.py
  scoring.py
  db.py
  telegram.py
  pipeline.py
  providers/
    __init__.py
    base.py
    mock.py

tests/
  test_dates.py
  test_filters.py
  test_scoring.py
  test_pipeline.py

data/
  destinations.yaml
```

## Next Reading

- See `PLAN.md` for delivery phases.
- See `ARCHITECTURE.md` for the intended system design.
- See `TASKS.md` for milestone breakdown.
- See `AGENTS.md` for implementation rules for future Codex sessions.
