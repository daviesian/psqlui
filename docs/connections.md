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
- The status bar displays the connection status plus round-trip latency for each refresh.

If a connection attempt fails (bad credentials, network issues, etc.), the app falls back to the built-in demo dataset so the UI stays usable. You’ll still see a notification in a future milestone; in the meantime check the terminal logs for details.

## Troubleshooting

- **Permission denied / auth errors**: Verify the DSN string or supply a `.pgpass` entry that matches the host/database pair.
- **No schemas listed**: Ensure the configured database user can read `information_schema`. Even with zero tables, you should now see `public` in the sidebar.
- **Long refresh times**: Watch the status bar latency; anything over a few hundred ms likely indicates a slow network or database throttling.

Let the team know if you need SSL/TLS flags or external secret-store support—these are planned, but we’re prioritizing the visibility/health wiring next.
