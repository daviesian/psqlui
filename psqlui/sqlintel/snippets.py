"""Snippet catalog for quick template insertions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .models import AnalysisResult, Clause, Suggestion, SuggestionType


@dataclass(slots=True)
class SnippetEntry:
    """Reusable template suggestions keyed by clause."""

    label: str
    template: str
    detail: str
    clauses: Tuple[Clause, ...]
    weight: float = 0.55

    def render(self, analysis: AnalysisResult) -> Suggestion:
        table = analysis.tables[0] if analysis.tables else "table_name"
        insert_text = self.template.format(table=table)
        return Suggestion(
            label=self.label,
            detail=self.detail,
            insert_text=insert_text,
            type=SuggestionType.SNIPPET,
            score=self.weight,
        )


class SnippetCatalog:
    """Return snippet suggestions using the current analysis context."""

    def __init__(self, entries: Sequence[SnippetEntry]) -> None:
        self._entries = tuple(entries)

    @classmethod
    def default(cls) -> "SnippetCatalog":
        return cls(_DEFAULT_SNIPPETS)

    def suggestions_for(self, analysis: AnalysisResult) -> list[Suggestion]:
        clause = analysis.clause
        suggestions: list[Suggestion] = []
        for entry in self._entries:
            if Clause.ANY in entry.clauses or clause in entry.clauses:
                suggestions.append(entry.render(analysis))
        return suggestions


_DEFAULT_SNIPPETS: Tuple[SnippetEntry, ...] = (
    SnippetEntry(
        label="Limit 100 rows",
        template="SELECT * FROM {table} LIMIT 100;",
        detail="Quick peek at a table with sane row cap",
        clauses=(Clause.SELECT, Clause.FROM, Clause.ANY),
    ),
    SnippetEntry(
        label="Exists guard",
        template="WHERE EXISTS (SELECT 1 FROM {table} WHERE /* condition */)",
        detail="Filter rows when a related record exists",
        clauses=(Clause.WHERE,),
    ),
    SnippetEntry(
        label="Upsert skeleton",
        template=(
            "INSERT INTO {table} AS t (...) VALUES (...) "
            "ON CONFLICT (id) DO UPDATE SET column = EXCLUDED.column;"
        ),
        detail="Ready-to-edit INSERT ... ON CONFLICT block",
        clauses=(Clause.INSERT,),
    ),
)


__all__ = ["SnippetCatalog", "SnippetEntry"]
