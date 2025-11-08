# Architecture

## Technology Stack
- **Language/runtime**: Python 3.12 managed by `uv` for dependency resolution and packaging.
- **TUI framework**: [`textual`](https://github.com/Textualize/textual) for layout/composability, backed by `rich` for rendering.
- **Database access**: `asyncpg` for high-throughput async operations plus sync fallbacks via `psycopg` for compatibility.
- **SQL intelligence**: embed a lightweight parser/formatter (e.g., `sqlglot`) to power local linting and autocomplete without round-trips.
- **Config/state**: `pydantic` models persisted in `$XDG_CONFIG_HOME/psqlui/config.toml` (or Windows equivalent) with optional workspace overrides.
- **Plugin system**: entry points (PEP 621) discovered via `uv` install extras; simple RPC boundary for extensions.

## Layered Design
1. **Interface Layer**
   - Textual app, screen/router manager, theming, keyboard maps.
   - Widgets for sidebar navigation, table grid, query pad, log pane.
2. **Domain Layer**
   - Connection/session manager keeps pools, transaction state, capability flags.
   - Metadata cache service (schema, stats) with TTL + invalidation triggers.
   - Command bus orchestrates async tasks (query execution, exports, plugin calls) and coordinates SQL-intel services for autocomplete.
3. **Infrastructure Layer**
   - Drivers (`asyncpg`, `psycopg`) wrapped with retry/backoff and cancellation.
   - Structured logging hardened for TUI consumption; no telemetry pipeline.
   - Storage adapters for config, history, secrets.

## Key Flows
- **Connect**: load profile → resolve secrets → establish pool → emit session ready event → hydrate sidebar.
- **Query**: parse request → route to command bus → paginate results in the grid (streaming reserved for plugins) → optionally export.
- **Edit**: open form → stage changes → generate SQL with WHERE clause + optimistic locking → preview diff → execute inside transaction → refresh cache.

## Cross-Platform Considerations
- Ship pre-built wheels via `uv tool install` to avoid local compilers.
- Abstract filesystem paths and clipboard integrations.
- Focus validation on Linux/macOS terminals; Windows support is best-effort and can lean on the community.

## Security Posture
- Never log raw credentials; redact before writing to local logs.
- Support SSL/TLS config per profile with sensible defaults.
- Optional integration with password managers via plugin API.

## Runtime Model
- Single foreground Textual process; no resident daemons or background updaters.
- Plugins run in-process but remain optional to keep the footprint small.

## Decision Log
- Client-side SQL parsing/autocomplete is mandatory for responsive linting and offline hints.
- Sensible pagination is the default; streaming mega-result sets is deferred to future plugins/exporters.
- Everything runs in the foreground process; upgrades and notifications happen when the user opts in.
