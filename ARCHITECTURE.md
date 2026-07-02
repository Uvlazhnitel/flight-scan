# Weekend Radar Architecture

## Summary

Weekend Radar is planned as a small backend workflow that turns configured travel rules into Telegram alerts. The architecture should stay simple, testable, and easy to replace piece by piece.

## Main Modules

### `config`

Responsibilities:

- load YAML configuration from disk,
- load secrets and runtime paths from environment variables,
- validate both through pydantic models,
- expose one clean application settings object to the rest of the system.

Expected contents:

- config file schema,
- environment settings schema,
- config loader and validation helpers.

### `models`

Responsibilities:

- define shared domain models for flights, routes, weekend windows, deals, notification records, and persisted state.

Expected design:

- pydantic models for external and internal data,
- explicit field names for airport codes, dates, price, currency, provider source, and timestamps,
- an `AppConfig` YAML model that holds destinations, weekend-search rules, and pricing thresholds,
- a generated `WeekendWindow` model that represents concrete search windows.

### `providers`

Responsibilities:

- fetch flight options from a source behind a stable interface,
- isolate source-specific parsing and transport logic,
- allow the mock provider to be replaced later by a real API provider.

Required interface:

```python
class FlightProvider(Protocol):
    async def search_weekend_flights(...) -> list[FlightOffer]:
        ...
```

MVP provider set:

- `MockFlightProvider` only.

Future extension:

- additional providers can implement the same contract without changing deal selection or notification code.

### `deals`

Responsibilities:

- generate concrete Riga weekend windows before provider searches,
- filter provider results to weekend-friendly trips,
- reject offers that are too expensive, indirect when direct-only is enabled, badly timed, too short or too long, or tied to disabled destinations,
- score surviving offers with explainable reasons and warnings,
- rank scored candidates globally and keep the top deals for notification,
- convert surviving `FlightOffer` objects into `DealCandidate` records with explainable `DealScore`,
- decide whether a deal is new enough to notify after storage lookup.

Core rule:

- a deal qualifies when `price <= destination_threshold` or `price <= global_threshold` when no destination-specific override exists.

### `storage`

Responsibilities:

- persist seen flights, deal history, and notification history in SQLite,
- expose repository-style read and write methods,
- support duplicate suppression and simple auditability.

Expected interface shape:

- initialize database schema automatically,
- insert every checked offer into SQLite,
- create scan-run history rows,
- query the latest notification for a stable deal key,
- record successful notification events.

### `notifications`

Responsibilities:

- format outbound Telegram messages,
- support dry-run output for safe local testing,
- send them through `httpx`,
- isolate HTTP transport and Telegram-specific payload details,
- log Telegram failures without aborting the whole scan.

Required interface:

```python
class Notifier(Protocol):
    def send_deal(...) -> bool:
        ...
```

MVP notifier set:

- `TelegramNotifier` only.

### `scheduler` or `runner`

Responsibilities:

- coordinate one full app run,
- accept one-run CLI overrides layered on top of YAML/env settings,
- call config loading, provider fetch, deal evaluation, storage, and notification steps in order,
- serve as the entrypoint for cron or systemd scheduling.

MVP runtime model:

- one process,
- one local SQLite file,
- one CLI command: `weekend-radar scan`,
- scheduled on a local host or small server.

## End-to-End Flow

1. Load environment variables for secrets and file paths.
2. Load and validate YAML config for routes, weekend-search rules, and thresholds.
3. Instantiate the configured `FlightProvider` implementation.
4. Generate concrete `WeekendWindow` search windows in `Europe/Riga`.
5. Fetch mock `FlightOffer` options from `RIX`.
6. Filter and evaluate weekend deals.
7. Persist every checked offer in SQLite with a stable deal key.
8. Rank all scored candidates and keep only the top N for this run.
9. Check SQLite to avoid duplicate notifications for the same origin, destination, dates, and provider.
10. Re-notify only when the price improved by at least `15 EUR` or the previous alert is older than `14 days`.
11. Send Telegram alerts for new qualifying deals or print them in dry-run mode.
12. Persist notification history only after a successful send or intentional dry-run delivery.

## Data and Configuration Boundaries

- Secrets belong in environment variables only.
- Non-secret operational settings belong in YAML.
- Route lists, thresholds, preferred destinations, and weekend-search settings must not be moved into `.env`.
- Tests must inject configuration explicitly and must not depend on a developer machine environment.

## Testing Boundaries

- Provider tests use fixtures and deterministic mock responses.
- Notifier tests mock `httpx` and never send real Telegram requests.
- Storage tests use temporary SQLite databases.
- Runner integration tests use temp files and mocked boundaries with no real network access.
- The test suite must not call live flight APIs or scrape websites.

## Public Interfaces to Preserve

These interfaces should remain stable once introduced because they separate replaceable subsystems:

- `FlightProvider`
- `Notifier`
- validated config/settings models
- repository-style storage interface for deduplication and history

## Future Extension Points

- swap `MockFlightProvider` for a live provider,
- add multiple providers behind the same interface,
- add richer deal ranking without changing transport code,
- add extra notification channels later if desired.
