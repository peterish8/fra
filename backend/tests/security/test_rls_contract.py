"""Text-only RLS, ownership, service-write, and immutability contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
MIGRATION_PATH = REPO_ROOT / "supabase" / "migrations" / "0001_truth_ledger.sql"


def _fixture() -> dict:
    with (FIXTURE_ROOT / "rls_contract_cases.json").open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _migration_text() -> str:
    assert MIGRATION_PATH.is_file(), (
        "RLS contract cannot run before supabase/migrations/0001_truth_ledger.sql exists"
    )
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _policy_blocks(sql: str) -> list[str]:
    return re.findall(r"create\s+policy\b.*?;", sql, re.IGNORECASE | re.DOTALL)


def _table_enabled(sql: str, table: str) -> bool:
    return bool(
        re.search(
            rf"alter\s+table\s+{re.escape(table)}\s+enable\s+row\s+level\s+security\s*;",
            sql,
            re.IGNORECASE,
        )
    )


def test_rls_is_enabled_for_profiles_reports_and_all_report_descendants() -> None:
    sql = _migration_text()
    contract = _fixture()
    for table in contract["owner_tables"]:
        assert _table_enabled(sql, table), f"RLS is not enabled for report-owned table {table}"


@pytest.mark.parametrize(
    ("table", "operation"),
    [
        (table, operation)
        for table, details in _fixture()["owner_tables"].items()
        for operation in details["operations"]
    ],
)
def test_authenticated_owner_policies_cover_every_report_operation(
    table: str, operation: str
) -> None:
    policies = _policy_blocks(_migration_text())
    matching = [
        policy
        for policy in policies
        if re.search(rf"\bon\s+{re.escape(table)}\b", policy, re.IGNORECASE)
        and re.search(rf"\bfor\s+{operation}\b", policy, re.IGNORECASE)
        and re.search(r"\bto\s+authenticated\b", policy, re.IGNORECASE)
    ]
    assert matching, f"authenticated {operation} policy is missing for {table}"
    assert any(re.search(r"auth\.uid\(\)", policy, re.IGNORECASE) for policy in matching)

    details = _fixture()["owner_tables"][table]
    if "identity" in details:
        assert any(details["identity"].lower() in policy.lower() for policy in matching)
    else:
        assert any(
            re.search(r"\bexists\s*\(", policy, re.IGNORECASE)
            and all(
                re.search(rf"\b{re.escape(fragment)}\b", policy, re.IGNORECASE)
                for fragment in details["owner_join"]
            )
            for policy in matching
        ), f"{table} policy does not prove ownership through its report ancestor"


def test_shared_truth_tables_are_client_write_protected_and_service_role_scoped() -> None:
    sql = _migration_text()
    policies = _policy_blocks(sql)
    contract = _fixture()

    for table in contract["shared_truth_tables"]:
        assert _table_enabled(sql, table), f"shared truth table {table} must have RLS enabled"
        client_writes = [
            policy
            for policy in policies
            if re.search(rf"\bon\s+{re.escape(table)}\b", policy, re.IGNORECASE)
            and re.search(r"\bfor\s+(?:insert|update|delete|all)\b", policy, re.IGNORECASE)
            and re.search(r"\bto\s+(?:anon|authenticated)\b", policy, re.IGNORECASE)
        ]
        assert not client_writes, f"client write policy would expose shared truth table {table}"

        service_policy = [
            policy
            for policy in policies
            if re.search(rf"\bon\s+{re.escape(table)}\b", policy, re.IGNORECASE)
            and re.search(r"\bto\s+service_role\b", policy, re.IGNORECASE)
            and re.search(r"\bfor\s+(?:insert|update|delete|all)\b", policy, re.IGNORECASE)
        ]
        assert service_policy, f"service_role write policy is missing for {table}"

        revoke = re.search(
            rf"revoke\s+(?:all|(?:insert\s*,\s*)?update\s*,?\s*(?:delete\s*,?\s*)?insert?)\s+on\s+{re.escape(table)}\s+from\s+(?:anon\s*,\s*authenticated|authenticated\s*,\s*anon)",
            sql,
            re.IGNORECASE,
        )
        assert revoke, f"client table grants are not explicitly revoked for {table}"


def test_cross_user_and_role_cases_are_represented_by_contracts() -> None:
    cases = _fixture()["cross_user_role_cases"]
    assert {case["expected"] for case in cases} == {"allow", "deny"}
    assert any(case["actor"] == "other_user" and case["expected"] == "deny" for case in cases)
    assert any(case["role"] == "anon" and case["expected"] == "deny" for case in cases)
    assert any(case["role"] == "service_role" and case["expected"] == "allow" for case in cases)
    assert any(case["operation"] == "insert_superseding" for case in cases)

    sql = _migration_text()
    assert re.search(r"\bto\s+authenticated\b", sql, re.IGNORECASE)
    assert re.search(r"\bto\s+service_role\b", sql, re.IGNORECASE)
    assert not re.search(
        r"create\s+policy\b[^;]*\bon\s+reports\b[^;]*\bto\s+anon\b", sql, re.IGNORECASE | re.DOTALL
    )


def test_immutable_truth_records_reject_in_place_correction_but_support_supersession() -> None:
    sql = _migration_text()
    immutable_tables = [
        "source_snapshots",
        "verifications",
        "calculations",
        "claim_scores",
        "disclosure_score_snapshots",
        "company_score_snapshots",
        "report_versions",
        "audit_events",
    ]
    for table in immutable_tables:
        assert re.search(
            rf"create\s+trigger\b[^;]*\bon\s+{table}\b[^;]*\bbefore\s+(?:update\s+or\s+delete|delete\s+or\s+update)\b",
            sql,
            re.IGNORECASE | re.DOTALL,
        ), f"{table} needs an in-place mutation safeguard"
    assert re.search(
        r"supersedes_claim_version_id\s+uuid\s+references\s+claim_versions\s*\(\s*id\s*\)",
        sql,
        re.IGNORECASE,
    ), "claim correction must point to a new superseding claim version"
    assert not re.search(
        r"create\s+policy\b[^;]*\bon\s+(?:source_snapshots|verifications|calculations|report_versions)\b[^;]*\bfor\s+(?:update|delete|all)\b[^;]*\bto\s+authenticated\b",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
