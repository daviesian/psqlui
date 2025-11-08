"""Main SQL intelligence service coordinating parsing, suggestions, and linting."""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from .catalog import KeywordCatalog
from .metadata import MetadataProvider, StaticMetadataProvider
from .models import (
    AnalysisResult,
    Clause,
    Diagnostic,
    DiagnosticSeverity,
    LintMode,
    Suggestion,
)

MAX_SUGGESTIONS = 50


class SqlIntelService:
    """Facade that wraps sqlglot parsing and feeds the editor with hints."""

    def __init__(
        self,
        metadata_provider: MetadataProvider | None = None,
        keyword_catalog: KeywordCatalog | None = None,
        *,
        dialect: str = "postgres",
    ) -> None:
        self._metadata = metadata_provider or StaticMetadataProvider()
        self._keywords = keyword_catalog or KeywordCatalog.default()
        self._dialect = dialect

    async def prime(self) -> None:
        """Placeholder for future warm-up hooks."""

        return None

    async def analyze(self, buffer: str, cursor: int) -> AnalysisResult:
        """Parse the buffer and derive structural context."""

        clause = _detect_clause(buffer, cursor)
        stripped = buffer.strip()
        ast: exp.Expression | None = None
        errors: list[str] = []
        tables: tuple[str, ...] = ()
        columns: tuple[str, ...] = ()
        if stripped:
            try:
                ast = parse_one(stripped, read=self._dialect)
            except ParseError as exc:
                errors.append(str(exc).strip())
            else:
                tables = tuple(_collect_tables(ast))
                columns = tuple(_collect_columns(ast))

        return AnalysisResult(
            buffer=buffer,
            cursor=cursor,
            clause=clause,
            tables=tables,
            columns=columns,
            ast=ast,
            errors=tuple(errors),
        )

    async def suggest(self, buffer: str, cursor: int) -> list[Suggestion]:
        """Return ordered suggestions for the current cursor location."""

        analysis = await self.analyze(buffer, cursor)
        return await self.suggestions_from_analysis(analysis)

    async def suggestions_from_analysis(self, analysis: AnalysisResult) -> list[Suggestion]:
        """Return suggestions using a precomputed analysis result."""

        suggestions = self._keywords.suggestions_for(analysis.clause)
        suggestions.extend(await self._metadata.suggestions_for(analysis))
        suggestions.sort(key=lambda item: (-item.score, item.label))
        return suggestions[:MAX_SUGGESTIONS]

    async def lint(self, statement: str, mode: LintMode = LintMode.INTERACTIVE) -> list[Diagnostic]:
        """Run lightweight lint rules on the provided statement."""

        analysis = await self.analyze(statement, len(statement))
        diagnostics: list[Diagnostic] = []
        for error in analysis.errors:
            diagnostics.append(Diagnostic(message=error, severity=DiagnosticSeverity.ERROR))

        if not analysis.ast:
            return diagnostics

        expr = analysis.ast
        if isinstance(expr, exp.Delete) and not expr.args.get("where"):
            diagnostics.append(
                Diagnostic(
                    message="DELETE statement is missing a WHERE clause.",
                    severity=DiagnosticSeverity.WARNING,
                )
            )
        if isinstance(expr, exp.Update) and not expr.args.get("where"):
            diagnostics.append(
                Diagnostic(
                    message="UPDATE statement is missing a WHERE clause.",
                    severity=DiagnosticSeverity.WARNING,
                )
            )
        if mode is LintMode.EXECUTION and isinstance(expr, exp.Insert):
            diagnostics.append(
                Diagnostic(
                    message="Confirm INSERT target before executing.",
                    severity=DiagnosticSeverity.INFO,
                )
            )
        return diagnostics


_CLAUSE_TOKENS: dict[Clause, tuple[str, ...]] = {
    Clause.DELETE: ("DELETE FROM", "DELETE"),
    Clause.UPDATE: ("UPDATE",),
    Clause.INSERT: ("INSERT INTO", "INSERT"),
    Clause.SELECT: ("SELECT",),
    Clause.FROM: ("FROM",),
    Clause.WHERE: ("WHERE",),
    Clause.GROUP: ("GROUP BY",),
    Clause.HAVING: ("HAVING",),
    Clause.ORDER: ("ORDER BY",),
    Clause.LIMIT: ("LIMIT",),
}


def _detect_clause(buffer: str, cursor: int) -> Clause:
    search = buffer[:cursor].upper()
    if not search.strip():
        return Clause.ANY
    last_clause = Clause.ANY
    last_pos = -1
    for clause, tokens in _CLAUSE_TOKENS.items():
        for token in tokens:
            pos = _rfind_token(search, token)
            if pos > last_pos:
                last_pos = pos
                last_clause = clause
    return last_clause if last_pos >= 0 else Clause.ANY


def _rfind_token(haystack: str, needle: str) -> int:
    pattern = re.compile(rf"\b{re.escape(needle)}\b")
    match_pos = -1
    for match in pattern.finditer(haystack):
        match_pos = match.start()
    return match_pos


def _collect_tables(expression: exp.Expression) -> Iterable[str]:
    tables: list[str] = []
    seen: set[str] = set()
    for table in expression.find_all(exp.Table):
        schema = table.db
        name = table.name or ""
        label = f"{schema}.{name}" if schema else name
        norm = label.lower()
        if norm and norm not in seen:
            tables.append(label)
            seen.add(norm)
    return tables


def _collect_columns(expression: exp.Expression) -> Iterable[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for column in expression.find_all(exp.Column):
        qualifier = column.table
        label = f"{qualifier}.{column.name}" if qualifier else column.name
        norm = label.lower()
        if norm and norm not in seen:
            columns.append(label)
            seen.add(norm)
    return columns


__all__ = ["SqlIntelService", "MAX_SUGGESTIONS"]
