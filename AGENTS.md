# AGENTS.md

This file tells future Codex sessions exactly how to work in this repository.

## Project Rules

- Build only what is needed for the Weekend Radar MVP.
- Keep the design small, reliable, and easy to maintain.
- Prefer simple module boundaries over frameworks or heavy abstractions.
- Preserve the provider abstraction so real flight APIs can be swapped in later.
- Keep all secrets in environment variables only.
- Keep non-secret operational settings in YAML.
- Never scrape airline websites.
- Never add frontend, mobile, account, booking, or payment features to the MVP.
- Tests must never call real external APIs.
- Update documentation when product behavior or developer workflow changes.

## MVP Scope

The MVP is a backend-only Python 3.12+ app that:

- reads YAML config,
- uses mock flight data first,
- evaluates weekend flight deals from `RIX`,
- stores state in SQLite,
- sends Telegram notifications.

Out of scope for MVP:

- real flight APIs,
- scraping,
- web UI,
- mobile app,
- multi-user features,
- payments or booking,
- cloud-first infrastructure complexity.

## Required Tooling

- Python 3.12+
- `uv`
- `pytest`
- `ruff`
- `pydantic`
- `httpx`
- SQLite
- YAML parser appropriate for Python

## Commands

Run these commands after implementation files exist:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

## Coding Style

- Use Python 3.12+ features where they improve clarity.
- Prefer explicit, readable code over clever code.
- Use type hints consistently.
- Use pydantic models for validated boundaries.
- Keep functions small and focused.
- Keep async boundaries where HTTP or provider interfaces need them.
- Write tests alongside each meaningful behavior change.
- Use clear names based on the domain: route, flight option, deal, threshold, notification record.
- Keep comments sparse and useful.

## Implementation Constraints

- Secrets must come from environment variables only.
- YAML must hold non-secret configuration such as routes, thresholds, and scheduling preferences.
- Tests must use mocks, fixtures, temp files, or temp databases instead of live services.
- Use `httpx` for HTTP integrations.
- Use SQLite for persistence in MVP.
- Keep provider-specific logic inside provider modules.
- Keep Telegram-specific logic inside notifier modules.
- Avoid introducing background workers, queues, or extra services for MVP.
- Avoid speculative abstractions beyond `FlightProvider`, `Notifier`, config models, and storage interface.

## Working Style for Future Codex Sessions

- Start by reading `README.md`, `PLAN.md`, `ARCHITECTURE.md`, `TASKS.md`, and this file.
- Pick the next incomplete milestone from `TASKS.md`.
- Keep each session focused on one milestone or a very small connected slice.
- Before editing, inspect the current repo state and existing conventions.
- After code changes, run the relevant validation commands.
- If behavior changes, update docs in the same session.
- When a task is complete, create a branch if needed, commit cleanly, push, and open a draft pull request.

## Definition of Done for Every Task

A task is done only when all of the following are true:

- the requested scope is implemented and stays within MVP constraints,
- code, tests, and docs are updated where relevant,
- `uv run ruff check .` passes,
- `uv run ruff format --check .` passes,
- `uv run pytest` passes,
- tests do not call real external APIs,
- secrets remain in environment variables only,
- the branch is pushed and a pull request is opened with a clear summary and validation notes.

## Special Definition of Done for This Initial Docs-Only Task

This initial task is done only when:

- `README.md`, `PLAN.md`, `ARCHITECTURE.md`, `TASKS.md`, `AGENTS.md`, and `.env.example` exist,
- planning docs are clear enough for a non-developer project owner,
- `TASKS.md` breaks the MVP into small milestones,
- `AGENTS.md` tells future Codex sessions exactly how to work,
- the repository contains no application code yet,
- the branch is pushed and a pull request is opened.

## Pull Request Expectations

Each PR should state:

- what changed,
- why it changed,
- impact on the MVP,
- how the work was validated,
- what is intentionally deferred.
