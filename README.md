# Weekend Radar

Weekend Radar is a small personal app that watches for cheap weekend flight ideas from Riga Airport (`RIX`) and sends a Telegram alert when a good deal appears.

This repository now includes the MVP pipeline through local SQLite persistence and Telegram notification delivery. The app still uses mock flight data, but it now runs a full local scan flow, stores checked offers, suppresses duplicate alerts, and can either print notifications in dry-run mode or send them to Telegram.
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
3. Filter out offers that are too expensive, indirect by default, or badly timed for a short weekend trip.
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
- no CI yet.

## Data Source

For the MVP so far, flight search runs on deterministic in-repo mock data only.

- no external flight APIs are called,
- no airline websites are scraped,
- tests stay fully offline.

The app also applies practical weekend filters before later scoring:

- max price is configurable and defaults to `120 EUR`,
- direct flights are required by default,
- offers with awkward departure or arrival times are rejected,
- disabled destinations are ignored.

It now also remembers previous alerts in SQLite:

- every checked mock offer is stored locally,
- duplicate notifications are suppressed for the same route/date/provider,
- a deal can notify again only after a `15 EUR` price drop or after `14 days`.

Telegram delivery now works in two modes:

- dry-run is the default and prints messages locally instead of sending them,
- real send mode posts to the Telegram Bot API with `httpx`,
- Telegram failures are logged and do not stop the rest of the scan.

## Local Setup

1. Install Python 3.12 or newer.
2. Install `uv`.
3. Copy `.env.example` to `.env`.
4. Sync dependencies.

```bash
cp .env.example .env
uv sync
```

## Telegram Setup

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Run `/newbot` and follow the prompts to create a bot.
3. Copy the bot token into `TELEGRAM_BOT_TOKEN` in `.env`.
4. Send at least one message to your bot from the Telegram account that should receive alerts.
5. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser after messaging the bot.
6. Find your chat id in the response and place it in `TELEGRAM_CHAT_ID`.
7. Leave `WEEKEND_RADAR_TELEGRAM_DRY_RUN=true` while testing locally.
8. Change `WEEKEND_RADAR_TELEGRAM_DRY_RUN=false` only when you want real Telegram sends.

## Run Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Run the App

The current entrypoint runs a full local mock scan. It reads the sample YAML file, initializes SQLite automatically, stores checked offers, applies filtering and scoring, and either prints notifications in dry-run mode or sends them to Telegram.

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
