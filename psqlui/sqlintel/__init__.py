"""SQL intelligence services and helpers."""

from __future__ import annotations

from .catalog import KeywordCatalog
from .functions import FunctionCatalog
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
from .snippets import SnippetCatalog

__all__ = [
    "AnalysisResult",
    "Clause",
    "Diagnostic",
    "DiagnosticSeverity",
    "FunctionCatalog",
    "KeywordCatalog",
    "LintMode",
    "MetadataProvider",
    "SqlIntelService",
    "StaticMetadataProvider",
    "Suggestion",
    "SuggestionType",
    "SnippetCatalog",
]
