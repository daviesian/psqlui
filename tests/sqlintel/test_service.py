"""Unit tests for the SQL intelligence service scaffold."""

from __future__ import annotations

import pytest

from psqlui.sqlintel import (
    Clause,
    DiagnosticSeverity,
    LintMode,
    SqlIntelService,
    StaticMetadataProvider,
    SuggestionType,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_analyze_extracts_clause_tables_and_columns() -> None:
    sql = "SELECT account_id FROM public.orders WHERE account_id = 1"
    service = SqlIntelService()

    analysis = await service.analyze(sql, len(sql))

    assert analysis.clause is Clause.WHERE
    assert "public.orders" in analysis.tables
    column_names = {column.split(".")[-1] for column in analysis.columns}
    assert "account_id" in column_names


@pytest.mark.anyio
async def test_from_clause_suggestions_include_tables() -> None:
    metadata = StaticMetadataProvider(
        {
            "public.accounts": ("id", "email"),
            "public.orders": ("id", "account_id"),
        }
    )
    service = SqlIntelService(metadata_provider=metadata)
    sql = "SELECT * FROM "

    analysis = await service.analyze(sql, len(sql))
    suggestions = await service.suggestions_from_analysis(analysis)

    labels = [entry.label for entry in suggestions if entry.type is SuggestionType.IDENTIFIER]
    assert "public.accounts" in labels
    assert "public.orders" in labels


@pytest.mark.anyio
async def test_lint_warns_on_dml_without_where() -> None:
    service = SqlIntelService()
    sql = "DELETE FROM accounts"

    diagnostics = await service.lint(sql, LintMode.EXECUTION)

    assert any("missing a WHERE clause" in diag.message for diag in diagnostics)
    assert any(diag.severity is DiagnosticSeverity.WARNING for diag in diagnostics)


@pytest.mark.anyio
async def test_empty_buffer_defaults_to_any_clause() -> None:
    service = SqlIntelService()

    analysis = await service.analyze("", 0)

    assert analysis.clause is Clause.ANY
