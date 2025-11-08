# SQL Intelligence

Design for the client-side parsing, linting, and autocomplete services that underpin the query experience.

## Goals
- Provide low-latency autocomplete and lint feedback without hitting the database on each keystroke.
- Understand SQL structure (clauses, tables, aliases, parameters) well enough to offer contextual hints and guardrails.
- Enrich the editor, command palette, and future plugins via a single source of truth for SQL analysis.

## Non-Goals
- Full ANSI SQL validation or execution planning (leave that to PostgreSQL).
- Server-side telemetry collection or behavioral tracking.
- Embedding heavyweight ML/AI assistants; the focus is deterministic, explainable completions.

## Key Capabilities
1. **Parsing & AST access**
   - Use [`sqlglot`](https://github.com/tobymao/sqlglot) for dialect-aware parsing/formatting.
   - Normalize statements to surface clause boundaries, selected columns, and table/CTE definitions.
2. **Autocomplete**
   - **Keyword & snippet suggestions**: ordered by context (e.g., `WHERE` after `FROM`).
   - **Identifier suggestions**: cross-reference metadata cache for schemas/tables/columns/indexes.
   - **Function helpers**: provide signatures for common Postgres functions.
3. **Linting & safety hints**
   - Detect obvious mistakes: missing `WHERE` on `UPDATE/DELETE`, unqualified ambiguous columns, unused CTEs.
   - Warn about potentially destructive commands when autocommit is off.
4. **Formatting & snippets**
   - Offer on-demand formatting via sqlglot's formatter.
   - Support reusable snippet blocks (e.g., `SELECT * FROM {table} LIMIT 100`).

## Architecture
```
┌──────────────────┐
│ Textual UI        │
│  - Query Pad      │
│  - Command Pal.   │
└────────┬─────────┘
         │ events
┌────────▼─────────┐
│ SQL Intel Orchestrator │
│  - Parser worker       │
│  - Suggestion broker   │
│  - Lint engine         │
└────────┬─────────┘
         │ metadata fetch
┌────────▼─────────┐
│ Metadata Cache   │
│  (schemas, cols) │
└────────┬─────────┘
         │ async pool
┌────────▼─────────┐
│ PostgreSQL DB    │
└──────────────────┘
```
- All services live in-process. Heavy parsing runs inside an `anyio` task group to avoid blocking the UI thread.
- Metadata cache already exists in the domain layer; the SQL intelligence orchestrator subscribes to its invalidation events.

## Data Flows
1. **Initialization**: load parser rules + keyword catalog; hydrate metadata cache (schemas, tables, columns) after connection.
2. **Typing loop**:
   - Editor emits `TextChanged` events → orchestrator debounces (e.g., 120 ms) → parse current statement.
   - AST + cursor position feed suggestion broker → UI renders dropdown.
3. **Linting**:
   - Run lightweight rules on every parse.
   - Trigger deeper checks (e.g., destructive DML) only when the statement is about to execute.
4. **Metadata refresh**:
   - Cache invalidation (e.g., after DDL) notifies orchestrator so identifier suggestions stay fresh.

## Storage & Caching
- **Keyword catalog**: static JSON bundled with the app.
- **Function signatures**: generated at build time from Postgres catalogs, cached locally.
- **Metadata cache**: TTL-based store keyed by connection profile + schema version.
- **Autocomplete history**: track recently used suggestions to bias ranking (local-only, no telemetry upload).

## API Surface (internal)
```python
class SqlIntelService:
    async def prime(connection_capabilities: ConnectionCaps) -> None: ...
    async def analyze(buffer: str, cursor: int) -> AnalysisResult: ...
    async def suggest(buffer: str, cursor: int) -> list[Suggestion]: ...
    async def lint(statement: str, mode: LintMode) -> list[Diagnostic]: ...
```
- `AnalysisResult` contains AST handles, clause context, referenced tables/columns, and derived aliases.
- Suggestions carry type (`keyword`, `identifier`, `snippet`, `function`), label, detail, and optional post-insert edits.
- Diagnostics keep range offsets so the editor can underline issues.

## Integration Points
- **Query Pad**: inline autocomplete, linting squiggles, format-on-demand.
- **Command Palette**: share snippets/keywords for quick insertion.
- **Plugins**: expose a read-only API for plugins that want parse trees or clause context (e.g., explain visualizer plugin can reuse AST to build explain commands).

## Performance Considerations
- Debounce parsing and cancel stale tasks when newer input arrives.
- Keep metadata lookups async and chunked to avoid blocking the UI when thousands of tables exist.
- Limit suggestion payloads (<50 entries) and support pagination when users keep typing.

## Testing Strategy
- Unit tests for parser wrappers (verify clause detection on representative statements).
- Golden tests for autocomplete ranking given sample buffers + cursor positions.
- Lint rule tests including destructive DML scenarios.
- Integration tests tying sqlglot parsing to metadata cache updates (use synthetic catalogs).

## Decision Log
- `sqlglot` is the primary parser/formatter; no bespoke grammar for v1.
- Autocomplete is client-driven; server introspection supplies metadata but not live suggestions.
- No background workers—everything runs inside the foreground Textual process.
