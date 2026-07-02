# Weekend Radar Plan

## Summary

Weekend Radar will be built as a small, reliable backend service that starts with mock flight data and later gains a real flight API provider without changing the core deal logic.

The project is intentionally narrow:

- one personal owner,
- one local SQLite database,
- one scheduled process on a single machine or small server,
- one notification channel: Telegram.

## Delivery Phases

### Phase 1: Repository Bootstrap

Why:
Create a clean foundation before any feature work starts.

Outcome:

- project metadata and Python tooling are set up,
- linting and tests can run,
- basic directory structure exists,
- docs and workflow are aligned.

Deferred:

- any actual flight or notification logic.

### Phase 2: Config and Domain Models

Why:
The app needs a stable shared language for routes, weekend trips, thresholds, and persisted state.

Outcome:

- YAML config schema is defined,
- environment-based secrets are validated,
- pydantic models describe the core entities used across the app.

Deferred:

- real providers,
- scheduler polish,
- deployment extras.

### Phase 3: Provider Abstraction and Mock Provider

Why:
We need to exercise the app flow without waiting for a real flight data integration.

Outcome:

- a provider interface exists,
- the mock provider returns deterministic sample flight data,
- business logic can be built against the abstraction.

Deferred:

- live API credentials,
- rate limiting,
- provider-specific mapping complexity.

### Phase 4: Deal Selection Logic

Why:
The core value of the app is deciding which flight ideas are worth notifying about.

Outcome:

- weekend filtering is implemented,
- per-route and global threshold rules are applied,
- the app can identify candidate deals from provider results.

Deferred:

- advanced scoring,
- historical trend analysis,
- dynamic price-drop heuristics.

### Phase 5: Persistence with SQLite

Why:
The app must remember what it has already seen and what it has already notified.

Outcome:

- SQLite stores flight snapshots or normalized deal records,
- duplicate notifications can be prevented,
- local state survives restarts.

Deferred:

- multi-user storage,
- remote databases,
- analytics dashboards.

### Phase 6: Telegram Notifications

Why:
The MVP must produce a useful output channel for the owner.

Outcome:

- Telegram messages are formatted and sent through a notifier abstraction,
- notification failures are handled clearly,
- tests cover outbound requests without real network access.

Deferred:

- multiple channels,
- rich interactive bot flows,
- user preference management.

### Phase 7: Runner and Scheduling

Why:
The app becomes useful only when it can run repeatedly without manual intervention.

Outcome:

- a single command or runner entrypoint executes the full workflow,
- documentation explains cron or systemd-style scheduling on one host.

Deferred:

- Docker orchestration,
- GitHub Actions scheduling,
- distributed workers.

### Phase 8: Real Provider Integration Later

Why:
Live API work should happen only after the app shape is proven with mock data.

Outcome:

- the provider abstraction is reused,
- mock-driven tests remain intact,
- live integration is added as a separate milestone after MVP.

Deferred:

- choosing the long-term flight API vendor,
- pricing optimization across multiple external providers.

## Success Criteria for MVP

- Finds weekend flight ideas from `RIX` using mock provider data
- Applies YAML-configured thresholds correctly
- Persists state in SQLite
- Sends Telegram alerts for new qualifying deals
- Uses secrets from environment variables only
- Keeps tests fully offline

## Explicit Product Decisions

- Mock flight data comes first.
- Real provider integration happens after MVP.
- A good deal means `price <= configured threshold`.
- The app targets a single local host or small server, not a cloud platform-first design.
