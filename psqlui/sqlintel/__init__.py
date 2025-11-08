"""SQL intelligence services and helpers."""

from __future__ import annotations

from .catalog import KeywordCatalog
from .metadata import MetadataProvider, StaticMetadataProvider
from .models import (
    AnalysisResult,
    Clause,
    Diagnostic,
    DiagnosticSeverity,
    LintMode,
    Suggestion,
    SuggestionType,
)
from .service import SqlIntelService

__all__ = [
    "AnalysisResult",
    "Clause",
    "Diagnostic",
    "DiagnosticSeverity",
    "KeywordCatalog",
    "LintMode",
    "MetadataProvider",
    "SqlIntelService",
    "StaticMetadataProvider",
    "Suggestion",
    "SuggestionType",
]
