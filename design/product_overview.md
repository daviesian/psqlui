# Product Overview

## Mission
Deliver a fast, scriptable terminal UI (TUI) for PostgreSQL power users who want richer context than `psql` but prefer staying inside the terminal over switching to GUI clients.

## Target Users
- Backend/data engineers who bounce between many databases and need a consistent workflow.
- SREs who diagnose production incidents and need read-only dashboards plus targeted updates.
- Analysts comfortable with SQL who want better discoverability than raw CLI tools.

## Value Proposition
1. **Zero-friction setup**: ship as a Python package (via [`uv`](https://github.com/astral-sh/uv)) with minimal dependencies and portable binaries later.
2. **Stateful exploration**: maintain session context (connections, filters, pinned queries) to avoid repetitive typing.
3. **Safe updates**: guided edit flows, transaction previews, and diff prompts to minimize destructive mistakes.
4. **Session awareness**: surface query history, locks, and safety nets inline so users stay informed without bolting on observability stacks.

## Core Use Cases
- Quickly connect to a known database using a stored profile or URI.
- Browse schemas, tables, and indexes with metadata (row counts, size, ownership).
- Run ad-hoc queries with results in pageable grids, export snippets, and rerun history.
- Edit rows or run migrations inside a guarded transaction with rollback-on-failure.
- Monitor active sessions and locks to debug blocking issues.

## Constraints & Principles
- **Terminal-first UX**: rely on a single binary/entrypoint, no server components.
- **Cross-platform**: Linux/macOS/Windows via `uv` for create/run and `textual`/`rich` for UI compatibility.
- **Extensible**: design plugin hooks (custom query templates, result exporters) early.
- **Secure by default**: avoid storing secrets in plain text; integrate with `pgpass`, env vars, and vaults later.
- **Lean core**: advanced helpers such as explain visualizers, SSH tunnels, or observability panes live in optional plugins so the base install stays focused on CRUD + monitoring.

## Non-goals (for now)
- Embedding observability data or telemetry streams inside the main UI.
- Shipping SSH tunneling, commercial management aids, or other enterprise niceties in the core build.
- Maintaining multiple layout profiles; we persist the last arrangement only.

## Success Metrics (initial)
- <5 min onboarding from `uv init` to first successful query.
- 80% of navigation reachable without mouse/trackpad.
- 95% query operations succeed without unexpected crashes under typical network latency.
- Power users can accomplish top 3 workflows with ≤20 key presses after onboarding.

## Decision Log
- Advanced helpers (logical replication explorers, explain visualizer) graduate into plugins instead of the core runtime.
- SSH tunneling is deferred; a future plugin can manage tunnels, but v1 assumes the OS handles connectivity.
- Observability surfaces stay out of scope until the CRUD workflow feels rock-solid.
