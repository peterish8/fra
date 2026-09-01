"""Red contracts for the forward Truth Ledger migration."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
MIGRATION_PATH = REPO_ROOT / "supabase" / "migrations" / "0001_truth_ledger.sql"


def _contract() -> dict:
    with (FIXTURE_ROOT / "truth_ledger_schema_contract.json").open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _migration_text() -> str:
    assert MIGRATION_PATH.is_file(), (
        "forward migration is missing: expected supabase/migrations/0001_truth_ledger.sql"
    )
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _table_block(sql: str, table: str) -> str:
    match = re.search(
        rf"create\s+table\s+(?:if\s+not\s+exists\s+)?{re.escape(table)}\s*\((.*?)(?=\);)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"required table {table!r} is missing from the forward migration"
    return match.group(1)


def test_forward_migration_contains_every_truth_ledger_table_and_enum() -> None:
    sql = _migration_text()
    contract = _contract()

    for table in contract["tables"]:
        _table_block(sql, table)
    declared_enums = set(re.findall(r"create\s+type\s+(\w+)\s+as\s+enum", sql, re.IGNORECASE))
    assert set(contract["enums"]).issubset(declared_enums)


def test_forward_migration_preserves_required_index_families() -> None:
    sql = _migration_text().lower()
    contract = _contract()

    for family in contract["index_families"]:
        table, *columns = family
        assert re.search(rf"create\s+(?:unique\s+)?index\b[^;]*\bon\s+{table}\b", sql), (
            f"no index declaration targets required table {table!r}"
        )
        for column in columns:
            assert re.search(
                rf"create\s+(?:unique\s+)?index\b[^;]*\bon\s+{table}\b[^;]*\b{column}\b",
                sql,
            ), f"index family {family!r} does not cover {column!r}"


def test_schema_uses_uuid_timestamptz_and_decimal_patterns() -> None:
    sql = _migration_text()
    assert re.search(r"\bid\s+uuid\b", sql, re.IGNORECASE)
    assert re.search(
        r"\b(?:created_at|updated_at|retrieved_at)\s+timestamptz\b", sql, re.IGNORECASE
    )
    assert re.search(r"\bnumeric\(\d+\s*,\s*\d+\)", sql, re.IGNORECASE), (
        "decimal financial precision must use an explicit numeric(p,s) declaration"
    )
    assert re.search(r"\bnumeric\(38\s*,\s*12\)", _table_block(sql, "facts"), re.IGNORECASE)
    assert re.search(
        r"\bmax_cost_usd\s+numeric\(12\s*,\s*4\)", _table_block(sql, "research_runs"), re.IGNORECASE
    )


def test_unknown_financial_values_are_nullable_not_zero_filled() -> None:
    sql = _migration_text()
    facts = _table_block(sql, "facts")
    contract = _contract()

    for column in contract["nullable_financial_columns"]:
        declaration = re.search(rf"\b{re.escape(column)}\b\s+[^,\n]+", facts, re.IGNORECASE)
        assert declaration, f"facts.{column} is missing"
        assert "not null" not in declaration.group(0).lower(), (
            f"facts.{column} must remain nullable when the source does not disclose a value"
        )
    assert not re.search(r"\bnumeric_value\b[^,\n]*default\s+0\b", facts, re.IGNORECASE)


def test_historical_records_are_append_oriented_and_corrections_supersede() -> None:
    sql = _migration_text()
    contract = _contract()

    for table in contract["immutable_tables"]:
        assert re.search(
            rf"create\s+trigger\b[^;]*\bbefore\s+(?:update\s+or\s+delete|delete\s+or\s+update)\b[^;]*\bon\s+{re.escape(table)}\b",
            sql,
            re.IGNORECASE | re.DOTALL,
        ), f"{table} lacks a mutation guard for immutable historical records"
    assert re.search(
        r"supersedes_claim_version_id\s+uuid\s+references\s+claim_versions\s*\(\s*id\s*\)",
        _table_block(sql, "claim_versions"),
        re.IGNORECASE,
    )
    assert re.search(r"raise\s+exception", sql, re.IGNORECASE), (
        "immutable mutation guards must fail closed rather than silently changing history"
    )
    assert re.search(r"unique\s*\(\s*report_id\s*,\s*version_number\s*\)", sql, re.IGNORECASE)


def test_forward_migration_has_no_destructive_reset_statements() -> None:
    sql = _migration_text()
    destructive = re.findall(
        r"\b(?:drop\s+(?:table|type|schema)|truncate(?:\s+table)?|delete\s+from)\b",
        sql,
        re.IGNORECASE,
    )
    assert not destructive, f"forward migration contains destructive statements: {destructive}"


@pytest.mark.parametrize("required_table", _contract()["tables"])
def test_each_required_table_has_a_primary_or_composite_identity(required_table: str) -> None:
    sql = _migration_text()
    block = _table_block(sql, required_table)
    assert re.search(r"\bprimary\s+key\b", block, re.IGNORECASE) or required_table in {
        "report_companies",
        "conflict_members",
        "run_sources",
        "report_version_claims",
    }, f"{required_table} needs a stable primary/composite identity"
