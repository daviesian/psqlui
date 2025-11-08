# Ops & Quality

## Tooling Decisions
- Use `uv` for project scaffolding, dependency resolution, and isolated virtual envs (`uv run`, `uvx`).
- Adopt `ruff` (lint/format) and `pytest` as default test harness; run via `uv run` for reproducible envs.
- Publish canonical `uv run` commands for format, lint, test, and dev tasks so contributors don't need extra task runners.

## Testing Strategy
- **Unit tests**: cover connection/session manager, SQL generation, config parsing.
- **Integration tests**: run against ephemeral PostgreSQL containers (e.g., `testcontainers`) to validate queries/transactions.
- **End-to-end smoke**: scripted Textual session using `textual-devtools` or snapshot testing harness to ensure key flows survive refactors.
- **Performance checks**: benchmark pagination + schema loads to guard against regressions without building bespoke streaming infra.

## Logging & Supportability
- Structured logs via `structlog` with log levels bound to verbosity flag; no telemetry or remote collectors.
- Crash reporting hook that redacts sensitive info before writing support bundles.
- Opt-in diagnostics command bundles logs + config snapshots for issue reports.

## Release Process
1. Run lint/test suites locally via `uv run ruff format .`, `uv run ruff check .`, and `uv run pytest`.
2. Manually tag and build release artifacts with `uv build`; automation can wait until the product stabilizes.
3. Publish wheels/sdists to PyPI, attach changelog + checksum, update docs site.
4. Provide upgrade playbook (config migrations, compatibility notes).

## Operations Concerns
- Config migrations handled via semantic versioned schema; auto-upgrade with backup file.
- Secrets never stored in logs; encourage OS keychains for long-term storage.
- Provide support bundle command that collects sanitized logs + environment info.
- No background updater; users opt into upgrades via `uv tool upgrade psqlui`.

## Decision Log
- Manual upgrades via `uv tool upgrade psqlui` are sufficient; no background updater.
- Telemetry is out of scope—only local structured logs ship in v1.
- Windows terminal support is best-effort; we test primarily on Linux/macOS until community demand warrants more.
