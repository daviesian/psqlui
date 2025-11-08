set shell := ["bash", "-eo", "pipefail", "-c"]

# Run formatters and linters
fmt:
	uv run ruff format .

lint:
	uv run ruff check .

check:
	just fmt
	just lint

# Run pytest suite
test:
	uv run pytest

# Launch Textual dev shell
dev:
	uv run textual run psqlui.app:main
