"""Fixture-backed contracts for canonical source identity and snapshots."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "source_ledger_cases.json"


def _cases() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture:
        return json.load(fixture)


def _symbol(module_name: str, name: str) -> Any:
    try:
        module = import_module(module_name)
        return getattr(module, name)
    except (ModuleNotFoundError, AttributeError) as error:
        _missing(module_name, name, error)


def _missing(module_name: str, name: str, error: BaseException) -> NoReturn:
    pytest.fail(
        f"missing source-ledger contract: {module_name}.{name} ({error})",
        pytrace=False,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    pytest.fail("source-ledger contract returned a non-object result", pytrace=False)


def _field(value: Any, name: str) -> Any:
    result = _mapping(value)
    if name not in result:
        pytest.fail(f"source-ledger result is missing {name}", pytrace=False)
    return result[name]


@pytest.mark.parametrize(
    "case",
    _cases()["canonical_identity_cases"],
    ids=lambda case: case["id"],
)
def test_canonical_source_identity_normalizes_url_and_document_id(case: dict[str, Any]) -> None:
    canonicalize = _symbol("app.domain.sources.identity", "canonicalize_url")
    identity = _symbol("app.domain.sources.identity", "canonical_document_identity")
    canonical_url = canonicalize(case["input_url"])
    identity_key = identity(
        canonical_url=canonical_url,
        external_document_id=case.get("document_id"),
    )

    assert canonical_url == case["expected_canonical_url"]
    assert identity_key == case["expected_identity_key"]


@pytest.mark.parametrize(
    "case",
    _cases()["snapshot_cases"],
    ids=lambda case: case["id"],
)
def test_snapshot_preserves_hash_lineage_redirects_and_retention(case: dict[str, Any]) -> None:
    service_type = _symbol("app.domain.sources.ledger", "SourceLedgerService")
    input_type = _symbol("app.domain.sources.models", "SourceSnapshotInput")
    service = service_type()
    source = service.create_source(
        publisher="Fixture Publisher",
        source_type="NEWS",
        authority_tier="C1",
        canonical_url=case["source_url"],
    )
    snapshot_input = input_type(
        source_id=source.source_id,
        content=case["content"],
        retrieved_at=case["retrieved_at"],
        redirect_chain=case["redirect_chain"],
        retention_mode=case["retention_mode"],
        permitted_excerpt=case["permitted_excerpt"],
        metadata={
            "provider": case["provider"],
            "provider_request_id": case["provider_request_id"],
        },
    )
    result = service.record_snapshot(snapshot_input)

    assert _field(result, "content_hash") == case["expected"]["content_hash"]
    retrieved_at = _field(result, "retrieved_at")
    assert isinstance(retrieved_at, datetime)
    assert retrieved_at.isoformat().replace("+00:00", "Z") == case["retrieved_at"]
    assert _field(result, "metadata")["provider"] == case["provider"]
    assert _field(result, "metadata")["provider_request_id"] == case["provider_request_id"]
    assert list(_field(result, "redirect_chain")) == case["redirect_chain"]
    assert _field(result, "retention_mode") == case["expected"]["retention_mode"]
    assert _field(result, "extracted_text") == case["permitted_excerpt"]

    if case["retention_mode"] == "METADATA_ONLY":
        snapshot = _mapping(result)
        assert snapshot.get("extracted_text") in (None, "")
        assert snapshot.get("storage_ref") in (None, "")


def test_snapshot_is_immutable_after_creation() -> None:
    service_type = _symbol("app.domain.sources.ledger", "SourceLedgerService")
    input_type = _symbol("app.domain.sources.models", "SourceSnapshotInput")
    service = service_type()
    source = service.create_source(
        publisher="Fixture Publisher",
        source_type="NEWS",
        authority_tier="C1",
        canonical_url="https://news.example.test/article/immutable",
    )
    result = service.record_snapshot(input_type(
        source_id=source.source_id,
        content="Immutable evidence.",
        retrieved_at="2026-09-01T09:00:00Z",
        redirect_chain=[],
        retention_mode="EXCERPT_ONLY",
        permitted_excerpt="Immutable evidence.",
    ))

    with pytest.raises((AttributeError, TypeError, ValueError)):
        result.content_hash = "sha256:tampered"  # type: ignore[misc]


def test_source_and_snapshot_reuse_canonical_identity_without_mutating_history() -> None:
    service_type = _symbol("app.domain.sources.ledger", "SourceLedgerService")
    input_type = _symbol("app.domain.sources.models", "SourceSnapshotInput")
    service = service_type()
    first_source = service.create_source(
        publisher="Fixture Publisher",
        source_type="NEWS",
        authority_tier="C1",
        canonical_url="HTTPS://Example.com:443/report?utm_source=fixture#top",
    )
    same_source = service.create_source(
        publisher="Fixture Publisher",
        source_type="NEWS",
        authority_tier="C1",
        canonical_url="https://example.com/report",
    )
    assert first_source.source_id == same_source.source_id

    snapshot_input = input_type(
        source_id=first_source.source_id,
        content="Stable source body.",
        retrieved_at="2026-09-01T09:00:00Z",
        retention_mode="EXCERPT_ONLY",
        permitted_excerpt="Stable source body.",
    )
    first_snapshot = service.record_snapshot(snapshot_input)
    second_snapshot = service.record_snapshot(snapshot_input)

    assert first_snapshot.snapshot_id == second_snapshot.snapshot_id
    assert first_snapshot.content_hash == second_snapshot.content_hash


def test_repeated_content_has_one_canonical_hash_and_duplicate_relationship() -> None:
    cases = _cases()["repeated_content_cases"]
    hash_content = _symbol("app.domain.sources.identity", "content_hash")
    source_type = _symbol("app.domain.sources.models", "SourceRecord")
    classifier_type = _symbol("app.domain.sources.families", "SourceFamilyClassifier")
    case = cases[0]

    first_hash = hash_content(case["first"]["content"])
    second_hash = hash_content(case["second"]["content"])
    first = source_type(
        canonical_url=case["first"]["source_url"],
        publisher="News One",
        source_type="NEWS",
        authority_tier="C1",
    )
    second = source_type(
        canonical_url=case["second"]["source_url"],
        publisher="News Two",
        source_type="NEWS",
        authority_tier="C1",
    )
    relationships = classifier_type().classify(
        [first, second],
        metadata={
            first.source_id: {"content_hash": first_hash},
            second.source_id: {"content_hash": second_hash},
        },
    )

    assert first_hash == second_hash
    assert len(relationships) == 1
    assert relationships[0].relationship_type == "DUPLICATE_OF"
