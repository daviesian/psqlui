"""Function catalog powering helper suggestions for common Postgres routines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .models import Clause, Suggestion, SuggestionType


@dataclass(slots=True)
class FunctionEntry:
    """Description of a SQL function surfaced to the editor."""

    name: str
    signature: str
    detail: str
    clauses: Tuple[Clause, ...]
    weight: float = 0.6


class FunctionCatalog:
    """Returns function suggestions based on the active clause."""

    def __init__(self, entries: Sequence[FunctionEntry]) -> None:
        self._entries = tuple(entries)

    @classmethod
    def default(cls) -> "FunctionCatalog":
        return cls(_DEFAULT_FUNCTIONS)

    def suggestions_for(self, clause: Clause) -> list[Suggestion]:
        suggestions: list[Suggestion] = []
        for entry in self._entries:
            if Clause.ANY in entry.clauses or clause in entry.clauses:
                suggestions.append(
                    Suggestion(
                        label=entry.name,
                        detail=entry.signature,
                        type=SuggestionType.FUNCTION,
                        insert_text=f"{entry.name}()",
                        score=entry.weight,
                    )
                )
        return suggestions


_DEFAULT_FUNCTIONS: Tuple[FunctionEntry, ...] = (
    FunctionEntry(
        name="COUNT",
        signature="COUNT(expression)",
        detail="Aggregate: number of rows/expression values",
        clauses=(Clause.SELECT, Clause.HAVING, Clause.ORDER),
        weight=0.72,
    ),
    FunctionEntry(
        name="SUM",
        signature="SUM(numeric)",
        detail="Aggregate: total of numeric column",
        clauses=(Clause.SELECT, Clause.HAVING, Clause.ORDER),
    ),
    FunctionEntry(
        name="AVG",
        signature="AVG(numeric)",
        detail="Aggregate: average of numeric column",
        clauses=(Clause.SELECT, Clause.HAVING),
    ),
    FunctionEntry(
        name="NOW",
        signature="NOW()",
        detail="Timestamp for current transaction",
        clauses=(Clause.SELECT, Clause.WHERE, Clause.ORDER),
        weight=0.65,
    ),
    FunctionEntry(
        name="COALESCE",
        signature="COALESCE(value, ...)",
        detail="Return first non-null argument",
        clauses=(Clause.SELECT, Clause.WHERE, Clause.ORDER),
    ),
    FunctionEntry(
        name="LOWER",
        signature="LOWER(text)",
        detail="Lowercase text, handy for case-insensitive filters",
        clauses=(Clause.SELECT, Clause.WHERE, Clause.ORDER),
    ),
    FunctionEntry(
        name="DATE_TRUNC",
        signature="DATE_TRUNC('unit', timestamp)",
        detail="Bucket timestamps by unit (day/week/month)",
        clauses=(Clause.SELECT, Clause.WHERE, Clause.GROUP, Clause.ORDER),
    ),
)


__all__ = ["FunctionCatalog", "FunctionEntry"]
