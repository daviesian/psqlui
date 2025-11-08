"""Keyword catalog powering deterministic autocomplete suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from .models import Clause, Suggestion, SuggestionType


@dataclass(slots=True)
class KeywordEntry:
    """Keyword metadata used for ranking suggestions."""

    keyword: str
    detail: str
    clauses: Tuple[Clause, ...]
    weight: float = 1.0


class KeywordCatalog:
    """In-memory catalog that returns clause-aware keyword suggestions."""

    def __init__(self, entries: Sequence[KeywordEntry]) -> None:
        self._entries = tuple(entries)

    @classmethod
    def default(cls) -> "KeywordCatalog":
        return cls(_DEFAULT_ENTRIES)

    def suggestions_for(self, clause: Clause) -> list[Suggestion]:
        """Return catalog entries that match the provided clause."""

        matches: list[Suggestion] = []
        for entry in self._entries:
            if Clause.ANY in entry.clauses or clause in entry.clauses:
                matches.append(
                    Suggestion(
                        label=entry.keyword,
                        detail=entry.detail,
                        type=SuggestionType.KEYWORD,
                        score=entry.weight,
                    )
                )
        return matches


_DEFAULT_ENTRIES: Tuple[KeywordEntry, ...] = (
    KeywordEntry("SELECT", "Start a query", (Clause.ANY,), 1.0),
    KeywordEntry("DISTINCT", "Deduplicate rows", (Clause.SELECT,), 0.9),
    KeywordEntry("FROM", "Choose a table or view", (Clause.SELECT, Clause.ANY), 0.95),
    KeywordEntry("WHERE", "Filter rows", (Clause.FROM, Clause.WHERE), 0.92),
    KeywordEntry("GROUP BY", "Aggregate rows", (Clause.WHERE, Clause.GROUP), 0.85),
    KeywordEntry("HAVING", "Filter aggregates", (Clause.GROUP, Clause.HAVING), 0.8),
    KeywordEntry("ORDER BY", "Sort result set", (Clause.WHERE, Clause.ORDER, Clause.GROUP), 0.78),
    KeywordEntry("LIMIT", "Restrict row count", (Clause.ORDER, Clause.LIMIT, Clause.SELECT), 0.75),
    KeywordEntry("INSERT INTO", "Insert rows", (Clause.ANY, Clause.INSERT), 0.88),
    KeywordEntry("UPDATE", "Modify rows", (Clause.ANY, Clause.UPDATE), 0.82),
    KeywordEntry("DELETE FROM", "Remove rows", (Clause.ANY, Clause.DELETE), 0.82),
)


__all__ = ["KeywordCatalog", "KeywordEntry"]
