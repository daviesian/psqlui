"""Placeholder query pad widget that wires in the SQL intelligence service."""

from __future__ import annotations

from typing import Callable, Mapping, Sequence

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Static

from psqlui.query import QueryExecutionError, QueryResult
from psqlui.sqlintel import AnalysisResult, SqlIntelService, Suggestion
from psqlui.sqlintel.debounce import Debouncer
from psqlui.session import SessionManager, SessionState


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

    #metadata-status {
        color: $text-muted;
    }

    QueryPad:focus-within {
        border: round $primary;
        background: $surface-lighten-1;
    }

    QueryPad .query-actions {
        margin-top: 1;
        align-horizontal: left;
    }

    QueryPad .query-actions > * {
        margin-right: 1;
    }

    QueryPad #query-results {
        height: 10;
        margin-top: 1;
        border-top: solid $surface-darken-2;
    }
    """

    BINDINGS = Container.BINDINGS + [
        Binding("ctrl+enter", "run_query", "Run query", show=False, priority=True),
    ]

    def __init__(
        self,
        sql_service: SqlIntelService,
        *,
        initial_metadata: Mapping[str, Sequence[str]] | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        super().__init__(id="query-pad")
        self._sql_service = sql_service
        self._debouncer = Debouncer()
        self._suggestions: Static | None = None
        self._analysis_panel: Static | None = None
        self._metadata_panel: Static | None = None
        self._status_panel: Static | None = None
        self._input: Input | None = None
        self._result_table: DataTable | None = None
        self._metadata_snapshot: Mapping[str, Sequence[str]] = dict(initial_metadata or {})
        self._session_manager = session_manager
        self._unsubscribe: Callable[[], None] | None = None
        self._result_limit = 200

    def compose(self) -> ComposeResult:
        """Compose the input + suggestion panes."""

        yield Static("Query Pad", classes="panel-title")
        yield _QueryInput(
            placeholder="Type SQL, e.g. SELECT * FROM accounts WHERE id = 1;",
            id="query-input",
            on_query=self._request_query_run,
        )
        yield Static("Suggestions appear here.", id="query-suggestions")
        yield Static("", id="query-analysis")
        yield Static("", id="metadata-status")
        actions = Horizontal(
            Button("Run query", id="run-query", variant="primary"),
            Static("", id="query-status"),
            classes="query-actions",
        )
        yield actions
        yield DataTable(id="query-results", zebra_stripes=True)

    async def on_mount(self) -> None:
        self._input = self.query_one("#query-input", _QueryInput)
        self._suggestions = self.query_one("#query-suggestions", Static)
        self._analysis_panel = self.query_one("#query-analysis", Static)
        self._metadata_panel = self.query_one("#metadata-status", Static)
        self._status_panel = self.query_one("#query-status", Static)
        self._result_table = self.query_one("#query-results", DataTable)
        self._configure_table()
        self._render_metadata_status()
        if self._session_manager:
            self._unsubscribe = self._session_manager.subscribe(self._handle_session_update)

    def on_unmount(self) -> None:
        self._debouncer.cancel()
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    async def on_input_changed(self, event: Input.Changed) -> None:
        buffer = event.value
        cursor = len(buffer)
        self._debouncer.submit(lambda b=buffer, c=cursor: self._refresh_analysis(b, c))

    async def action_run_query(self) -> None:
        await self._execute_current_query()

    async def on_query_run_requested(self, event: "QueryRunRequested") -> None:
        await self._execute_current_query()
        event.stop()

    def _request_query_run(self) -> None:
        self.post_message(QueryRunRequested())

    async def _execute_current_query(self) -> None:
        if not self._session_manager or not self._input:
            return
        sql = self._input.value.strip()
        if not sql:
            self._set_status("Enter SQL to run.", severity="warning")
            return
        self._set_status("Executing…", severity="information")
        try:
            result = await self._session_manager.run_query(sql)
        except QueryExecutionError as exc:
            self._set_status(f"Error: {exc}", severity="error")
            self._render_query_result(None)
            return
        self._render_query_result(result)
        badge = f"{result.status} · {result.elapsed_ms} ms"
        self._set_status(badge, severity="success")

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

    def _render_metadata_status(self) -> None:
        if not self._metadata_panel:
            return
        tables = ", ".join(sorted(self._metadata_snapshot)) or "No tables loaded"
        self._metadata_panel.update(f"Metadata tables: {tables}")

    def _handle_session_update(self, state: SessionState) -> None:
        self._metadata_snapshot = state.metadata
        self._render_metadata_status()

    def _configure_table(self) -> None:
        if not self._result_table:
            return
        self._result_table.clear(columns=True)
        self._result_table.cursor_type = "row"

    def _render_query_result(self, result: QueryResult | None) -> None:
        if not self._result_table:
            return
        self._result_table.clear(columns=True)
        if not result or not result.columns:
            return
        col_count = min(len(result.columns), self._result_limit)
        columns = result.columns[:col_count]
        if not columns:
            return
        self._result_table.add_columns(*columns)
        for row in result.rows[: self._result_limit]:
            values = list(row[:col_count])
            if len(values) < col_count:
                values.extend([""] * (col_count - len(values)))
            display = [self._format_cell(value) for value in values]
            self._result_table.add_row(*display)

    def _set_status(self, message: str, *, severity: str) -> None:
        if not self._status_panel:
            return
        prefix = {
            "information": "ℹ",
            "warning": "⚠",
            "error": "✖",
            "success": "✔",
        }.get(severity, "•")
        self._status_panel.update(f"{prefix} {message}")

    @staticmethod
    def _format_cell(value: object) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        return str(value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-query":
            await self._execute_current_query()

    async def action_run_query(self) -> None:
        await self._execute_current_query()


class QueryRunRequested(Message):
    """Message fired when the input requests a query run."""

    pass


class _QueryInput(Input):
    """Input wrapper that detects Ctrl+Enter/newline chords."""

    _TRIGGER_KEYS = {"ctrl+enter", "ctrl+j", "newline"}

    def __init__(
        self,
        *args: object,
        on_query: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._on_query = on_query

    def _on_key(self, event: events.Key) -> None:
        key = event.key or ""
        ctrl_enter = key == "enter" and bool(getattr(event, "control", False))
        if (key in self._TRIGGER_KEYS or ctrl_enter) and self._on_query:
            self._on_query()
            event.stop()
            return
        super()._on_key(event)


__all__ = ["QueryPad"]
