"""Placeholder query pad widget that wires in the SQL intelligence service."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input, Static

from psqlui.sqlintel import AnalysisResult, SqlIntelService, Suggestion
from psqlui.sqlintel.debounce import Debouncer


class QueryPad(Container):
    """Minimal editor surface used to validate the SqlIntelService round-trip."""

    DEFAULT_CSS = """
    QueryPad {
        layout: vertical;
        border: round $primary 40%;
        padding: 1 2;
        height: 1fr;
        background: $surface;
    }

    QueryPad .panel-title {
        text-style: bold;
    }

    QueryPad Input {
        border: heavy $primary;
    }

    #query-suggestions {
        height: auto;
        min-height: 3;
        border-top: solid $surface-darken-2;
        padding-top: 1;
    }
    """

    def __init__(self, sql_service: SqlIntelService) -> None:
        super().__init__(id="query-pad")
        self._sql_service = sql_service
        self._debouncer = Debouncer()
        self._suggestions: Static | None = None
        self._analysis_panel: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose the input + suggestion panes."""

        yield Static("Query Pad", classes="panel-title")
        yield Input(
            placeholder="Type SQL, e.g. SELECT * FROM accounts WHERE id = 1;",
            id="query-input",
        )
        yield Static("Suggestions appear here.", id="query-suggestions")
        yield Static("", id="query-analysis")

    async def on_mount(self) -> None:
        self._suggestions = self.query_one("#query-suggestions", Static)
        self._analysis_panel = self.query_one("#query-analysis", Static)

    def on_unmount(self) -> None:
        self._debouncer.cancel()

    async def on_input_changed(self, event: Input.Changed) -> None:
        buffer = event.value
        cursor = len(buffer)
        self._debouncer.submit(lambda b=buffer, c=cursor: self._refresh_analysis(b, c))

    async def _refresh_analysis(self, buffer: str, cursor: int) -> None:
        analysis = await self._sql_service.analyze(buffer, cursor)
        suggestions = await self._sql_service.suggestions_from_analysis(analysis)
        self._render_analysis(analysis)
        self._render_suggestions(suggestions)

    def _render_suggestions(self, suggestions: list[Suggestion]) -> None:
        if not self._suggestions:
            return
        if not suggestions:
            self._suggestions.update("No suggestions yet.")
            return
        rows = [
            f"{entry.label} · {entry.detail or entry.type.value}"
            for entry in suggestions[:5]
        ]
        self._suggestions.update("\n".join(rows))

    def _render_analysis(self, analysis: AnalysisResult) -> None:
        if not self._analysis_panel:
            return
        lines = [
            f"Clause: {analysis.clause.value}",
            f"Tables: {', '.join(analysis.tables) if analysis.tables else '—'}",
            f"Columns: {', '.join(analysis.columns) if analysis.columns else '—'}",
        ]
        if analysis.errors:
            lines.append(f"Errors: {analysis.errors[0]}")
        self._analysis_panel.update("\n".join(lines))


__all__ = ["QueryPad"]
