# Weekend Radar Tasks

## Summary

This file breaks the MVP into small milestones that future Codex sessions can implement without needing to re-plan the project.

## Milestone 1: Repository Bootstrap

Goal:
Create the basic Python project layout and tooling.

Deliverables:

- `pyproject.toml`
- package directory
- test directory
- `uv` workflow
- `ruff` and `pytest` configuration

Acceptance checks:

- dependencies install with `uv`
- lint and tests run locally

Depends on:

- none

## Milestone 2: Config Schema and Settings

Goal:
Define how YAML config and environment variables are loaded and validated.

Deliverables:

- pydantic settings models
- YAML schema models
- config loading helpers
- error messages for invalid config

Acceptance checks:

- invalid env and YAML inputs fail clearly
- route thresholds and global fallback threshold validate correctly

Depends on:

- Milestone 1

## Milestone 3: Core Domain Models

Goal:
Establish shared types for flights, deals, and notification records.

Deliverables:

- flight models
- route and weekend window models
- deal candidate models
- persistence-facing record models where needed

Acceptance checks:

- models serialize and validate predictably
- field names are consistent across provider, storage, and notifier boundaries

Depends on:

- Milestone 2

## Milestone 4: Provider Abstraction

Goal:
Create the stable interface used by all flight data sources.

Deliverables:

- `FlightProvider` protocol or abstract base
- provider factory or selection mechanism kept simple

Acceptance checks:

- runner code can depend on the abstraction instead of a concrete provider

Depends on:

- Milestone 3

## Milestone 5: Mock Flight Provider

Goal:
Provide deterministic mock flight data for development and tests.

Deliverables:

- mock provider implementation
- fixture-like sample data

Acceptance checks:

- provider returns repeatable weekend and non-weekend examples
- no external API calls are made

Depends on:

- Milestone 4

## Milestone 6: Deal Evaluation Logic

Goal:
Identify which mock flights should trigger a notification.

Deliverables:

- weekend filtering
- threshold comparison logic
- deduplication input shape for storage lookup

Acceptance checks:

- qualifying deals match route threshold rules
- global threshold fallback works
- non-qualifying and duplicate candidates are excluded

Depends on:

- Milestone 5

## Milestone 7: SQLite Storage

Goal:
Persist seen deals and sent notifications.

Deliverables:

- schema initialization
- repository methods
- duplicate notification checks
- notification history writes

Acceptance checks:

- state survives multiple runs
- duplicate alerts are suppressed

Depends on:

- Milestone 6

## Milestone 8: Telegram Notifier

Goal:
Send deal alerts to Telegram without leaking transport details into business logic.

Deliverables:

- `Notifier` abstraction
- Telegram notifier implementation
- message formatting

Acceptance checks:

- notifier sends the expected payload shape
- failures are surfaced clearly
- tests use mocked HTTP only

Depends on:

- Milestone 3

## Milestone 9: Orchestration Command

Goal:
Run one full check from config load to notification send.

Deliverables:

- app runner or CLI command
- dependency wiring
- clear logging or console output

Acceptance checks:

- one command performs the full happy path
- storage and notifier interactions happen in the right order

Depends on:

- Milestone 7
- Milestone 8

## Milestone 10: Tests, Docs, and Polish

Goal:
Stabilize the MVP and document usage.

Deliverables:

- expanded unit and integration tests
- updated README and config guidance
- cleanup of naming and error handling

Acceptance checks:

- `pytest` passes
- `ruff check .` passes
- `ruff format --check .` passes
- docs match actual behavior

Depends on:

- Milestone 9

## Milestone 11: Pull Request

Goal:
Ship the completed slice cleanly.

Deliverables:

- focused commit history
- pushed branch
- draft pull request with validation notes

Acceptance checks:

- PR clearly explains what changed, why, and how it was validated

Depends on:

- the milestone being delivered

## Notes for Future Sessions

- Keep milestones small; complete one or two at a time.
- Do not skip tests when adding a new subsystem.
- Do not introduce a real flight API before the mock-provider workflow is stable.
