# Roadmap

## Phase 0 — Foundations (Week 0-1)
- Initialize repo with `uv` project, linting, basic CI (format, unit tests).
- Spike Textual app shell with placeholder screens and navigation skeleton.
- Prototype connection logic using `asyncpg` against local container.

## Phase 1 — Explorer & Query Basics (Week 2-4)
- Implement connection profiles, secure storage, and session manager.
- Build schema explorer with lazy-loading sidebar and metadata panel.
- Deliver query pad with execution, result grid, and history list.
- Add smoke tests covering connection lifecycle and query execution.

## Phase 2 — Editing & Safety Nets (Week 5-7)
- Row edit forms with diff previews and transaction controls.
- Command palette, notifications, and keybinding customization.
- Error handling patterns (timeouts, retries, offline mode) without adding telemetry collectors.
- Introduce plugin discovery contract for exporters or custom panes.

## Phase 3 — Polish & Packaging (Week 8-10)
- Session monitor (locks, queries, cancel button) with live refresh.
- Theme system, accessibility improvements, onboarding flow.
- Document manual release process (`uv build`, changelog, PyPI publish); automation deferred.

## Phase 4 — Hardening & Preview Release (Week 11-12)
- Security review, dependency audits, load tests against large schemas.
- Dogfood with seed users, collect feedback, prioritize backlog.
- Ship 0.1 preview, publish docs and quickstart tutorial.

## Risks & Mitigations
- **Async complexity**: lean on `anyio` for structured concurrency and add integration tests with slow networks.
- **Terminal variability**: maintain compatibility matrix, add feature detection fallback (e.g., disable advanced mouse events if unsupported).
- **Plugin API churn**: start experimental namespace, version events, document stability promises.

## Decision Log
- Release packaging automation can wait; early releases are built/published manually until the roadmap stabilizes.
- No need to align releases with Textual/Rich cadence—track breaking changes via dependabot and upgrade when necessary.
- Commercial-only capabilities (audit logs, RBAC, SSO) stay out of scope for the OSS-focused 1.0.
