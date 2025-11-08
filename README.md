# psqlui

Cross-platform terminal UI for PostgreSQL built with Textual. See the `design/` folder for product, architecture, and roadmap docs.

Additional docs:
- `docs/plugins.md` — quickstart for building plugins.

## Getting Started

```bash
uv sync
uv run python -m psqlui
```

## Common Commands
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Test: `uv run pytest`
- Dev shell: `uv run python -m psqlui`

## Sample Plugin
- A bundled `hello-world` plugin loads automatically in dev builds. Press `Ctrl+P` in the app and run the `hello.world` command to exercise the plugin command path.
- The plugin also contributes a sidebar pane. You can toggle plugin enablement from the command palette (`Enable/Disable plugin` entries) or via `~/.config/psqlui/config.toml`:

  ```toml
  [plugins]
  hello-world = true
  ```
- Changes persist to disk immediately; restart the app to apply updated enablement flags.
- The app now reads settings (theme, telemetry, plugin toggles) from that same config file; delete the file or remove keys to fall back to defaults.
