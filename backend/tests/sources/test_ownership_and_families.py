"""Fixture-backed contracts for ownership and source-family independence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlsplit

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "source_family_cases.json"


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
        f"missing ownership/family contract: {module_name}.{name} ({error})",
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
    pytest.fail("ownership/family contract returned a non-object result", pytrace=False)


@pytest.mark.parametrize(
    "case",
    _cases()["ownership_cases"],
    ids=lambda case: case["id"],
)
def test_source_ownership_distinguishes_self_reported_independent_and_unconfirmed(
    case: dict[str, Any],
) -> None:
    classify = _symbol(
        "app.domain.claims.ownership",
        "classify_ownership",
    )
    result = classify(
        source_domain=urlsplit(case["source_url"]).hostname,
        company_domains=case["confirmed_official_domains"],
        confirmed_company_domains=case["confirmed_official_domains"],
        source_type=case.get("source_type"),
        authoritative_domain_confirmation=bool(case.get("authoritative_domains")),
    )
    result_map = _mapping(result)

    assert result_map["relation"] == case["expected_ownership"]
    assert "explanation" in result_map
    assert result_map["explanation"]
    if case["expected_ownership"] == "SELF_REPORTED":
        assert result_map["independent_eligible"] is False
    if case["expected_ownership"] == "UNCONFIRMED":
        assert result_map["decision"] == "UNCONFIRMED"


def test_self_reported_origin_is_structurally_excluded_from_independent_selection() -> None:
    classify = _symbol(
        "app.domain.claims.ownership",
        "classify_ownership",
    )

    result = classify(
        source_domain="acme.example.com",
        company_domains=["acme.example.com"],
        confirmed_company_domains=["acme.example.com"],
        source_type="COMPANY_PRESS_RELEASE",
    )
    result_map = _mapping(result)

    assert result_map["relation"] == "SELF_REPORTED"
    assert result_map["independent_eligible"] is False


def test_unconfirmed_company_domain_remains_visible_but_is_not_excluded_as_official() -> None:
    exclude = _symbol(
        "app.domain.claims.ownership",
        "exclude_company_owned_domains",
    )

    result = exclude(
        [
            "acme.example.com",
            "acme-news.example.net",
            "https://www.sec.gov/Archives/edgar/data/acme/annual.htm",
        ],
        ["acme.example.com", "acme-news.example.net"],
        confirmed_company_domains=["acme.example.com"],
    )

    assert "acme.example.com" not in result
    assert "acme-news.example.net" in result
    assert "https://www.sec.gov/Archives/edgar/data/acme/annual.htm" in result


@pytest.mark.parametrize(
    "case",
    _cases()["family_cases"],
    ids=lambda case: case["id"],
)
def test_source_families_collapse_fake_consensus_but_retain_urls(case: dict[str, Any]) -> None:
    source_type = _symbol("app.domain.sources.models", "SourceRecord")
    classifier_type = _symbol("app.domain.sources.families", "SourceFamilyClassifier")
    connected = _symbol("app.domain.sources.families", "connected_source_families")
    sources = [
        source_type(
            canonical_url=source["url"],
            publisher=source["origin"],
            source_type="NEWS",
            authority_tier="C1",
        )
        for source in case["sources"]
    ]
    metadata = {
        source.source_id: {
            "original_url": case["sources"][0]["url"]
            if index > 0 and case["id"] == "company_pr_copied_by_blogs"
            else (
                case["sources"][0]["url"]
                if index > 0 and case["id"] == "reuters_syndication_is_one_family"
                else None
            ),
            "syndicated_from": case["sources"][0]["url"]
            if index > 0 and case["id"] == "reuters_syndication_is_one_family"
            else None,
        }
        for index, source in enumerate(sources)
    }
    relationships = classifier_type().classify(sources, metadata=metadata)
    family_groups = connected([source.source_id for source in sources], relationships)

    assert len(family_groups) == case["expected_family_count"]
    source_origins = {
        source.source_id: case["sources"][index]["origin"]
        for index, source in enumerate(sources)
    }
    independent_groups = [
        group
        for group in family_groups
        if not any(source_origins[source_id] == "company" for source_id in group)
    ]
    assert len(independent_groups) == case["expected_independent_family_count"]
    assert any(
        case["expected_relationship"] in str(relationship)
        for relationship in relationships
    )
    assert len(sources) == len(case["sources"])


def test_provider_agreement_on_one_article_is_not_independent_consensus() -> None:
    case = next(
        case
        for case in _cases()["family_cases"]
        if case["id"] == "providers_citing_one_article_are_not_consensus"
    )

    source_type = _symbol("app.domain.sources.models", "SourceRecord")
    classifier_type = _symbol("app.domain.sources.families", "SourceFamilyClassifier")
    connected = _symbol("app.domain.sources.families", "connected_source_families")
    sources = [
        source_type(
            canonical_url=source["url"],
            publisher=source["origin"],
            source_type="NEWS",
            authority_tier="C1",
        )
        for source in case["sources"]
    ]
    relationships = classifier_type().classify(
        sources,
        metadata={
            sources[0].source_id: {"content_hash": "same-wire-copy"},
            sources[1].source_id: {"content_hash": "same-wire-copy"},
        },
    )
    family_groups = connected([source.source_id for source in sources], relationships)

    assert len(family_groups) == 2
    assert any(relationship.relationship_type == "DUPLICATE_OF" for relationship in relationships)
