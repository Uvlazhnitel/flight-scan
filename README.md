# Weekend Radar

Weekend Radar is a small personal app that watches for cheap weekend flight ideas from Riga Airport (`RIX`) and sends a Telegram alert when a good deal appears.

This repository is currently in the planning stage. It contains project guidance and delivery documents only. No application code has been implemented yet.

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
2. Ask a flight provider for mock flight options from `RIX`.
3. Keep only weekend-friendly options.
4. Compare each price to the configured threshold rules.
5. Skip deals that were already notified recently.
6. Save state in SQLite.
7. Send Telegram notifications for new good deals.

## Repository Status

Current contents:

- `README.md`
- `PLAN.md`
- `ARCHITECTURE.md`
- `TASKS.md`
- `AGENTS.md`
- `.env.example`

Current omissions:

- no Python package yet,
- no `pyproject.toml` yet,
- no YAML sample config yet,
- no tests yet,
- no CI yet.

## Setup Guidance

This step is documentation-only for now. The actual commands will become valid once implementation begins.

1. Install Python 3.12 or newer.
2. Install `uv`.
3. Copy `.env.example` to `.env` and fill in real secret values.
4. Create the YAML config file once the config schema is implemented.
5. Run lint and tests after the project files exist.

Planned future commands:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Next Reading

- See `PLAN.md` for delivery phases.
- See `ARCHITECTURE.md` for the intended system design.
- See `TASKS.md` for milestone breakdown.
- See `AGENTS.md` for implementation rules for future Codex sessions.
