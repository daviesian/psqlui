# Connection Profiles & Real Databases

How to point psqlui at your own PostgreSQL instances.

## Config File Location

Profiles live in `~/.config/psqlui/config.toml`. The app auto-creates this file after the first launch, and you can add multiple profiles by appending additional `[[profiles]]` tables.

## Quick Start Examples

### DSN With Embedded Password

```toml
[[profiles]]
name = "Production"
dsn = "postgresql://app_user:s3cret@db.internal:5432/app_db"
metadata_key = "prod"
```

When `dsn` is present it wins over the other connection fields, so you can keep `host`, `user`, etc. as inline documentation or omit them entirely. This is the simplest way to provide a password until we add a dedicated secret store.

### Field-by-Field Connection

```toml
[[profiles]]
name = "Analytics"
host = "analytics.internal"
port = 5432
database = "analytics"
user = "read_only"

# Optional: seed the sidebar/table list while the real metadata loads
[profiles.metadata]
"public.events" = ["id", "payload"]
```

If you use this style, `psqlui` will prompt `asyncpg` to read the password from a DSN or the default libpq sources (e.g., `.pgpass`). Password entry fields are on the roadmap (see the implementation plan).

## Schema & Metadata Refresh

- Press `Ctrl+R` or run `Refresh active profile metadata` from the command palette to pull the latest schema snapshot.
- The left sidebar now lists every schema we discover (even empty ones, such as `public` on a brand-new database). Schemas with no tables show a `No tables yet` placeholder.
- The status bar displays the connection status plus round-trip latency for each refresh. It also highlights whether you are talking to the primary backend or the built-in demo fallback and shows the most recent error message when something goes wrong.

If a connection attempt fails (bad credentials, network issues, etc.), the app falls back to the built-in demo dataset so the UI stays usable. A warning toast and the sidebar summary both call out that fallback mode is active and show the most recent error so you know what to fix before retrying the profile.

## Running Queries

- Type SQL in the query pad and press `Ctrl+Enter` (or click **Run query**) to execute it against the active profile.
- Successful statements stream the first couple hundred rows into the inline results grid and display elapsed time plus row count alongside the button.
- When the app is operating in demo fallback mode, the runner returns synthetic rows that match your seeded metadata so you can still validate layouts without a live database.

## Local Sample Database via Docker

- Run `uv run python scripts/setup_sample_db.py` to start a local PostgreSQL container (`postgres:16-alpine`) on port `5543` with sample `accounts` and `orders` tables.
- The script adds a `Docker Sample` profile to `~/.config/psqlui/config.toml`, pointing at `postgresql://psqlui:psqlui@localhost:5543/psqlui_demo`.
- Re-run the script if you need to recreate the data; it will reuse the container if it already exists.

## Troubleshooting

- **Permission denied / auth errors**: Verify the DSN string or supply a `.pgpass` entry that matches the host/database pair.
- **No schemas listed**: Ensure the configured database user can read `information_schema`. Even with zero tables, you should now see `public` in the sidebar.
- **Long refresh times**: Watch the status bar latency; anything over a few hundred ms likely indicates a slow network or database throttling.

Let the team know if you need SSL/TLS flags or external secret-store support—these are planned, but we’re prioritizing the visibility/health wiring next.
