"""Core dataclasses shared by the SQL intelligence services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from sqlglot import exp


class Clause(str, Enum):
    """Represents the current SQL clause under the cursor."""

    ANY = "any"
    SELECT = "select"
    FROM = "from"
    WHERE = "where"
    GROUP = "group"
    HAVING = "having"
    ORDER = "order"
    LIMIT = "limit"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class SuggestionType(str, Enum):
    """Types of suggestions surfaced to the editor."""

    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    SNIPPET = "snippet"
    FUNCTION = "function"


class DiagnosticSeverity(str, Enum):
    """Severity levels for lint feedback."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LintMode(str, Enum):
    """Lint modes to toggle more expensive rules."""

    INTERACTIVE = "interactive"
    EXECUTION = "execution"


@dataclass(slots=True)
class Suggestion:
    """Single autocomplete entry."""

    label: str
    type: SuggestionType
    detail: str | None = None
    insert_text: str | None = None
    score: float = 0.0


@dataclass(slots=True)
class Diagnostic:
    """Represents an issue discovered while linting."""

    message: str
    severity: DiagnosticSeverity
    start: int | None = None
    end: int | None = None


@dataclass(slots=True)
class AnalysisResult:
    """Details derived from the last parse invocation."""

    buffer: str
    cursor: int
    clause: Clause
    tables: Tuple[str, ...]
    columns: Tuple[str, ...]
    ast: exp.Expression | None
    errors: Tuple[str, ...]


__all__ = [
    "AnalysisResult",
    "Clause",
    "Diagnostic",
    "DiagnosticSeverity",
    "LintMode",
    "Suggestion",
    "SuggestionType",
]
