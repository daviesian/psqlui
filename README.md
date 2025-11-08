# psqlui

Cross-platform terminal UI for PostgreSQL built with Textual. See the `design/` folder for product, architecture, and roadmap docs.

## Getting Started

```bash
uv sync
uv run textual run psqlui.app:main
```

## Common Commands
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Test: `uv run pytest`
- Dev shell: `uv run textual run psqlui.app:main`
