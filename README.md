# Weekend Radar

Weekend Radar is a small personal app that watches for cheap weekend flight ideas from Riga Airport (`RIX`) and sends a Telegram alert when a good deal appears.

This repository now includes the MVP pipeline through local SQLite persistence and Telegram notification delivery. The app runs a full local scan flow, stores checked offers, suppresses duplicate alerts, and can either print notifications in dry-run mode or send them to Telegram.
The shipped configuration still uses deterministic mock flight data by default, and there is now an optional first real provider integration through Amadeus Self-Service.

## MVP Goal

The MVP is a backend-only Python service that:

- reads route and pricing rules from a YAML config file,
- loads secrets from environment variables,
- fetches flight data through a provider abstraction,
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
- Mock flight provider by default

## Non-Goals for MVP

- No frontend
- No mobile app
- No booking or payments
- No user accounts
- No airline website scraping
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
2. Ask the configured flight provider for weekend options from `RIX`.
3. Filter out offers that are too expensive, indirect by default, or badly timed for a short weekend trip.
4. Compare each price to the configured threshold rules.
5. Skip deals that were already notified recently.
6. Save state in SQLite.
7. Score deals, keep the best results, and send Telegram notifications for new good deals.

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

- real provider support is limited to Amadeus Self-Service,
- no deployment automation yet.

## Data Source

Weekend Radar currently supports two provider modes:

- `mock`: deterministic in-repo sample offers for safe local testing,
- `amadeus`: live Amadeus Self-Service Flight Offers Search data.

Important current provider limitations:

- the shipped config stays on `provider: mock`,
- Amadeus quotas and test-environment limits apply,
- Amadeus Self-Service does not include some carriers such as low-cost carriers, American Airlines, Delta, and British Airways,
- booking URLs are not returned by this provider in this milestone,
- only offers already priced in `EUR` are accepted in the current Amadeus integration,
- no airline websites are scraped,
- tests stay fully offline.

The app also applies practical weekend filters before later scoring:

- max price is configurable and defaults to `120 EUR`,
- direct flights are required by default,
- offers with awkward departure or arrival times are rejected,
- disabled destinations are ignored.

It now also remembers previous alerts in SQLite:

- every checked offer is stored locally,
- duplicate notifications are suppressed for the same route/date/provider,
- a deal can notify again only after a `15 EUR` price drop or after `14 days`.

The shipped destination catalog in `data/destinations.yaml` is the manual source of truth for which cities the MVP considers.

- to disable a destination, set `enabled: false` on that entry,
- to re-enable it later, change the same field back to `true`,
- manual edits to the YAML file are expected and safe for this MVP.

Telegram delivery now works in two modes:

- dry-run is the default and prints messages locally instead of sending them,
- real send mode posts to the Telegram Bot API with `httpx`,
- Telegram failures are logged and do not stop the rest of the scan.

## Local Setup

1. Install Python 3.12 or newer.
2. Install `uv`.
3. Copy `.env.example` to `.env`.
4. Sync dependencies.
5. Run the safest first scan in dry-run mode.

```bash
cp .env.example .env
uv sync
uv run weekend-radar scan --dry-run
```

Expected first-run result:

- the app prints weekend deal messages to your terminal,
- a SQLite file is created at `data/weekend_radar.sqlite3`,
- the summary says the provider is `mock` and the mode is `dry-run`.

The copied `.env.example` file is safe for this first dry-run even though it contains placeholder secret values. Dry-run mode does not try to send Telegram messages and the shipped YAML still uses `provider: mock`.

## First Real Run

Use this sequence if you want to go from a clean checkout to a real personal-use test without guessing.

### 1. First safe local run

```bash
cp .env.example .env
uv sync
uv run weekend-radar scan --dry-run
```

Success looks like this:

- deal messages are printed in your terminal,
- a SQLite file appears at `data/weekend_radar.sqlite3`,
- the summary says `Provider: mock (mock data)` and `Mode: dry-run`.

### 2. First real Telegram delivery

Keep `provider: mock` in [data/destinations.yaml](/Users/uvlazhnitel/Documents/flight-scan/data/destinations.yaml) so you can test delivery without depending on a live flight API.

Set these values in `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `WEEKEND_RADAR_TELEGRAM_DRY_RUN=false`

Then run:

```bash
uv run weekend-radar scan --limit 1
```

Success looks like this:

- your Telegram bot sends you one deal message,
- the terminal summary says `Mode: real Telegram send`,
- the SQLite database records the notification so an immediate repeat run may send nothing.

If a repeat run prints no new deal, that is often expected: duplicate protection is working.

### 3. First live-provider test

When you are ready to try live flight data:

1. Set `AMADEUS_API_KEY` in `.env`.
2. Set `AMADEUS_API_SECRET` in `.env`.
3. Change `provider: mock` to `provider: amadeus` in [data/destinations.yaml](/Users/uvlazhnitel/Documents/flight-scan/data/destinations.yaml).
4. Keep dry-run enabled for the first live test.

```bash
uv run weekend-radar scan --dry-run
```

Success looks like this:

- the run completes without a config error,
- live-provider results are printed locally instead of being sent,
- you can switch Telegram sending on later after confirming the provider path works.

## Real Provider Setup

If you want to try the first live provider instead of mock data:

1. Create an app in [Amadeus for Developers](https://developers.amadeus.com/).
2. Copy your API key into `AMADEUS_API_KEY` in `.env`.
3. Copy your API secret into `AMADEUS_API_SECRET` in `.env`.
4. Change `provider: mock` to `provider: amadeus` in [data/destinations.yaml](/Users/uvlazhnitel/Documents/flight-scan/data/destinations.yaml).
5. Keep `WEEKEND_RADAR_TELEGRAM_DRY_RUN=true` for the first live test run.
6. Run `uv run weekend-radar scan --dry-run`.

Operator notes for Amadeus:

- this integration uses the Amadeus Self-Service test environment by default,
- missing `AMADEUS_API_KEY` or `AMADEUS_API_SECRET` will fail the run early with a clear error,
- the app skips malformed API offers instead of crashing the whole scan,
- the app skips non-EUR offers for now rather than converting currencies.

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

The current app runs a full local scan from one command. It reads the sample YAML file, initializes SQLite automatically, stores checked offers, filters and scores them, keeps the top deals, and either prints notifications in dry-run mode or sends them to Telegram.

```bash
uv run weekend-radar scan --dry-run
```

Useful flags:

- `--dry-run`: force local printing instead of real Telegram sends
- `--max-price 90`: override the max accepted price for this run
- `--weeks 4`: generate only the next 4 weekend windows
- `--direct-only`: require direct flights for this run
- `--allow-stops`: allow stopover flights for this run
- `--limit 5`: keep only the top 5 scored deals before duplicate checks

Example:

```bash
uv run weekend-radar scan --dry-run --weeks 4 --max-price 90 --limit 5
```

Repeated runs may print fewer deals, or none at all, because duplicate notifications are suppressed once the same route/date/provider combination has already been notified recently.

Important operator note:

- dry-run prints whatever the current provider produced, instead of sending it to Telegram,
- with the shipped config that still means mock data,
- real Telegram mode changes delivery only; it does not change which provider is selected in YAML.

## Release Readiness

The repository now includes a GitHub Actions workflow that runs the same release-readiness checks used locally:

- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`

The workflow supports `workflow_dispatch` for a manual run and also runs on pull requests and pushes to `main`.

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
    amadeus.py
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
