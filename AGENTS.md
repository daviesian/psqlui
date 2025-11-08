# Agent Runbook

Reference playbook so any LLM agent can resume work on `psqlui` without re-reading the entire repo history.

## Before You Start
- Read `design/progress_log.md` for the latest commit hash, outstanding tasks, and repo cleanliness. Update it at the end of **every** coding session/commit. The `design/` folder is for internal planning/engineering artifacts; user-facing references belong under `docs/`.
- Skim `design/implementation_plan.md` to confirm which milestone you’re advancing. Maintain the plan when scope changes.
- Run `git status -sb` to confirm the working tree matches the progress log assumptions.

## Project Context
- Python 3.12 project managed with `uv`; run all tooling via `uv run …`. Use the provided lockfile.
- Current focus: Milestone 3 (plugin loader) unless the progress log specifies otherwise; Milestone 2 (SQL intel) is complete.
- Core app is a Textual TUI. **Do not launch interactive commands** like `uv run python -m psqlui` inside the harness because you cannot send Ctrl+C; rely on unit tests or describe expected behaviour instead.
- **Never override `UV_CACHE_DIR`.** Commands should use the default cache; if you must write outside the workspace (e.g., installer wants `/var`), rerun with `with_escalated_permissions` instead of redirecting caches.

## Common Commands
- Tests: `uv run pytest`
- Lint/format (if needed): `uv run ruff check .` / `uv run ruff format .`
- Dev shell for quick scripts: `uv run python - <<'PY' … PY`

## Coding Workflow
1. Create/update files using ASCII, keep comments minimal and meaningful.
2. For multi-step tasks, optionally outline a plan (see system instructions) and update it as steps finish.
3. Prefer `rg` for searches, `apply_patch` for targeted edits.
4. Never reset or revert user changes you didn’t make.
5. When touching SQL intel or other core services, add/extend unit tests and run pytest.

## Documentation Rituals
- After implementing changes, update `design/progress_log.md` (latest commit, summary, TODOs, repo state) before committing.
- Note this ritual in any new planning docs so future agents remember.

## Testing Philosophy
- Default to running the relevant subset of `pytest`. If tests cannot run, explain why in the final response and list manual verification steps taken.
- Avoid interactive UI testing in this environment; describe expected UI impact instead.

## Commit & Hand-off
- Keep commits scoped; include docs/tests when relevant.
- Before handing back, ensure `git status -sb` is clean (or describe remaining changes if intentionally uncommitted).
- In the final message, summarize changes, reference key files with `path:line`, mention tests run, and suggest logical next steps.
- Always tell the user what new things (if any) they should see or try in the app when summarizing your changes.
