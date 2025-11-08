"""Metadata adapters that feed identifier suggestions into the SQL intel service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, Sequence

from .models import AnalysisResult, Clause, Suggestion, SuggestionType


class MetadataProvider(Protocol):
    """Protocol for services that surface identifier suggestions."""

    async def suggestions_for(self, analysis: AnalysisResult) -> Sequence[Suggestion]:
        """Return identifier suggestions tailored to the given analysis result."""


@dataclass(frozen=True, slots=True)
class _TableEntry:
    label: str
    columns: tuple[str, ...]


class StaticMetadataProvider:
    """Simple metadata provider backed by an in-memory catalog."""

    def __init__(self, tables: Mapping[str, Sequence[str]] | None = None) -> None:
        self._tables_full: dict[str, _TableEntry] = {}
        self._tables_short: dict[str, _TableEntry] = {}
        self._table_list: tuple[_TableEntry, ...] = ()
        self.update(tables or {})

    async def suggestions_for(self, analysis: AnalysisResult) -> Sequence[Suggestion]:
        clause = analysis.clause
        if not self._table_list:
            return ()

        if clause in {Clause.FROM, Clause.INSERT, Clause.UPDATE, Clause.DELETE}:
            return tuple(
                Suggestion(
                    label=entry.label,
                    detail="table",
                    type=SuggestionType.IDENTIFIER,
                    score=0.7,
                )
                for entry in self._table_list
            )

        targets = self._targets_for_analysis(analysis)
        suggestions: list[Suggestion] = []
        for entry in targets:
            for column in entry.columns:
                suggestions.append(
                    Suggestion(
                        label=column,
                        detail=f"{entry.label} column",
                        type=SuggestionType.IDENTIFIER,
                        score=0.65,
                    )
                )
        return tuple(suggestions)

    def _targets_for_analysis(self, analysis: AnalysisResult) -> tuple[_TableEntry, ...]:
        tables: list[_TableEntry] = []
        seen: set[_TableEntry] = set()
        for table in analysis.tables:
            entry = self._tables_full.get(_normalize(table))
            if not entry:
                entry = self._tables_short.get(_normalize(table.split(".")[-1]))
            if entry and entry not in seen:
                tables.append(entry)
                seen.add(entry)
        if not tables:
            return self._table_list
        return tuple(tables)

    def update(self, tables: Mapping[str, Sequence[str]]) -> None:
        """Replace the in-memory catalog used for identifier suggestions."""

        self._tables_full.clear()
        self._tables_short.clear()
        for table_name, columns in tables.items():
            entry = _TableEntry(label=table_name, columns=tuple(columns))
            self._tables_full[_normalize(table_name)] = entry
            short = table_name.split(".")[-1]
            short_key = _normalize(short)
            self._tables_short.setdefault(short_key, entry)
        self._table_list = tuple(self._tables_full.values()) or tuple(self._tables_short.values())


def _normalize(value: str) -> str:
    return value.replace('"', "").lower()


__all__ = ["MetadataProvider", "StaticMetadataProvider"]
