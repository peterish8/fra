"""Pure, conservative company/entity resolution."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .models import CompanyCandidate, EntityQuery, EntityResolution, MatchReason, ResolutionStatus

_RESOLUTION_THRESHOLD = 0.80
_WORD_RE = re.compile(r"[^a-z0-9]+")


def resolve_entity(
    query: EntityQuery | Mapping[str, Any] | str,
    candidates: Sequence[CompanyCandidate | Mapping[str, Any]],
) -> EntityResolution:
    """Resolve a query without ever merging on name similarity alone.

    The function intentionally has no repository/provider dependency. Candidate
    records are the evidence available at this boundary; persisted evidence
    references are preserved and missing fixture references are represented as
    input-field references rather than fabricated source snapshots.
    """

    normalized_query = _coerce_query(query)
    parsed_candidates = [
        candidate
        if isinstance(candidate, CompanyCandidate)
        else CompanyCandidate.from_input(dict(candidate))
        for candidate in candidates
    ]
    scored = [_score_candidate(normalized_query, candidate) for candidate in parsed_candidates]
    scored.sort(key=lambda item: (-item[0], item[1].company_id))
    rendered = [
        _with_explanations(candidate, score, reasons, refs)
        for score, candidate, reasons, refs in scored
    ]

    if not rendered:
        return EntityResolution(
            status=ResolutionStatus.UNCONFIRMED,
            selected_company_id=None,
            research_allowed=False,
            abstention_reason="No candidate legal entity was supplied for resolution.",
            candidates=[],
            match_reasons=[
                MatchReason(code="NO_CANDIDATES", detail="No candidate entities were available.")
            ],
        )

    identifier_winners = _identifier_winners(normalized_query, rendered)
    if len(identifier_winners) > 1:
        reason = MatchReason(
            code="IDENTITY_CONFLICT",
            detail="Supplied identity identifiers point to different candidate entities.",
        )
        return _abstain(
            ResolutionStatus.UNCONFIRMED,
            "Identity identifiers conflict; a canonical entity cannot be selected safely.",
            rendered,
            reason,
        )

    if normalized_query.domain and not _domain_winners(normalized_query, rendered):
        reason = MatchReason(
            code="DOMAIN_UNCONFIRMED",
            detail="The supplied domain does not match a candidate official domain.",
        )
        return _abstain(
            ResolutionStatus.UNCONFIRMED,
            "The supplied domain could not be confirmed as an official domain.",
            rendered,
            reason,
        )

    strong_winner = next(iter(identifier_winners), None)
    name_matches = [candidate for candidate in rendered if _has_name_match(candidate)]

    if strong_winner is not None:
        selected = next(
            candidate for candidate in rendered if candidate.company_id == strong_winner
        )
        if selected.confidence >= _RESOLUTION_THRESHOLD:
            return _resolved(selected, rendered)

    # A name is safe only when paired with an explicit jurisdiction. This is
    # deliberately stricter than fuzzy-search ranking and prevents auto-merges.
    if normalized_query.country_code:
        jurisdiction_matches = [
            candidate
            for candidate in name_matches
            if candidate.country_code == normalized_query.country_code
        ]
        if (
            len(jurisdiction_matches) == 1
            and jurisdiction_matches[0].confidence >= _RESOLUTION_THRESHOLD
        ):
            selected = jurisdiction_matches[0]
            return _resolved(selected, rendered)

    if len(name_matches) > 1:
        reason = MatchReason(
            code="JURISDICTION_REQUIRED",
            detail=(
                "Multiple legal entities share the supplied name; jurisdiction or "
                "another strong identifier is required."
            ),
        )
        return _abstain(
            ResolutionStatus.AMBIGUOUS,
            (
                "Multiple matching legal entities remain; select a jurisdiction or "
                "candidate before research."
            ),
            rendered,
            reason,
        )

    reason = MatchReason(
        code="INSUFFICIENT_IDENTITY_EVIDENCE",
        detail="The available name signal is not sufficient to identify one legal entity.",
    )
    return _abstain(
        ResolutionStatus.UNCONFIRMED,
        "Identity evidence is insufficient for safe research.",
        rendered,
        reason,
    )


def _coerce_query(value: EntityQuery | Mapping[str, Any] | str) -> EntityQuery:
    if isinstance(value, EntityQuery):
        return value
    if isinstance(value, str):
        return EntityQuery(name=value)
    payload = dict(value)
    if "name" not in payload and "query" in payload:
        payload["name"] = payload["query"]
    return EntityQuery.model_validate(payload)


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(_WORD_RE.sub(" ", normalized).split())


def _normalize_identifier(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    candidate = value.strip().casefold()
    parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _score_candidate(
    query: EntityQuery,
    candidate: CompanyCandidate,
) -> tuple[float, CompanyCandidate, list[MatchReason], list[str]]:
    reasons: list[MatchReason] = []
    evidence_refs = list(candidate.evidence_refs)
    query_name = _normalize_text(query.name)
    canonical_name = _normalize_text(candidate.canonical_name)
    name_matched = False
    score = 0.0

    if query_name and query_name == canonical_name:
        name_matched = True
        score = max(score, 0.72)
        reasons.append(
            MatchReason(
                code="CANONICAL_NAME_MATCH",
                detail="The query exactly matches the canonical company name.",
            )
        )
        evidence_refs.append("input:name")
    else:
        for alias in candidate.aliases:
            if query_name and query_name == _normalize_text(alias.value):
                name_matched = True
                score = max(score, 0.70)
                alias_code = (
                    "FORMER_NAME_ALIAS_MATCH"
                    if alias.alias_type.upper() == "FORMER_NAME"
                    else "ALIAS_MATCH"
                )
                reasons.append(
                    MatchReason(
                        code=alias_code,
                        detail=f"The query matches the candidate {alias.alias_type.lower()} alias.",
                    )
                )
                evidence_refs.append("input:name")
                break

    if query.country_code and candidate.country_code == query.country_code:
        score += 0.14 if name_matched else 0.0
        reasons.append(
            MatchReason(
                code="JURISDICTION_MATCH",
                detail="The candidate country matches the supplied jurisdiction.",
            )
        )
        evidence_refs.append("input:country_code")

    ticker_match = bool(
        query.ticker
        and _normalize_identifier(query.ticker) == _normalize_identifier(candidate.primary_ticker)
    )
    exchange_match = bool(
        query.exchange
        and _normalize_identifier(query.exchange)
        == _normalize_identifier(candidate.primary_exchange)
    )
    if ticker_match and exchange_match:
        score = max(score, 0.98)
        reasons.append(
            MatchReason(
                code="TICKER_EXCHANGE_MATCH", detail="Ticker and exchange both match the candidate."
            )
        )
        evidence_refs.append("input:ticker_exchange")
    elif ticker_match:
        score = max(score, 0.87)
        reasons.append(
            MatchReason(
                code="TICKER_MATCH", detail="The supplied ticker matches the candidate ticker."
            )
        )
        evidence_refs.append("input:ticker")

    domain_match = bool(
        query.domain
        and any(
            _normalize_domain(query.domain) == _normalize_domain(domain)
            for domain in candidate.domains
        )
    )
    if domain_match:
        score = max(score, 0.96)
        reasons.append(
            MatchReason(
                code="OFFICIAL_DOMAIN_MATCH",
                detail="The supplied domain matches a candidate official domain.",
            )
        )
        evidence_refs.append("input:domain")

    registry_match = False
    if query.registry_id:
        query_registry = _normalize_identifier(query.registry)
        query_value = _normalize_identifier(query.registry_id)
        registry_match = any(
            _normalize_identifier(item.registry) == query_registry
            and _normalize_identifier(item.value) == query_value
            for item in candidate.registry_identifiers
        )
        if registry_match:
            score = 1.0
            reasons.append(
                MatchReason(
                    code="REGISTRY_IDENTIFIER_MATCH",
                    detail="The supplied registry and registration identifier match the candidate.",
                )
            )
            evidence_refs.append("input:registry_id")

    if query.lei:
        lei_match = any(
            _normalize_identifier(item.value) == _normalize_identifier(query.lei)
            for item in candidate.registry_identifiers
        )
        if lei_match:
            registry_match = True
            score = 1.0
            reasons.append(
                MatchReason(
                    code="LEI_MATCH",
                    detail="The supplied LEI matches the candidate registry identifier.",
                )
            )
            evidence_refs.append("input:lei")

    if not reasons:
        reasons.append(
            MatchReason(
                code="NO_MATCHING_IDENTIFIER",
                detail="No supplied identity field matched the candidate.",
            )
        )
        evidence_refs.append(f"candidate:{candidate.company_id}")
    return min(score, 1.0), candidate, reasons, _unique(evidence_refs)


def _with_explanations(
    candidate: CompanyCandidate,
    score: float,
    reasons: list[MatchReason],
    evidence_refs: list[str],
) -> CompanyCandidate:
    return candidate.model_copy(
        update={
            "confidence": round(score, 4),
            "match_reasons": reasons,
            "evidence_refs": evidence_refs,
        }
    )


def _identifier_winners(query: EntityQuery, candidates: Sequence[CompanyCandidate]) -> set[str]:
    winners: set[str] = set()
    if query.registry_id:
        for candidate in candidates:
            if any(
                _normalize_identifier(identifier.registry) == _normalize_identifier(query.registry)
                and _normalize_identifier(identifier.value)
                == _normalize_identifier(query.registry_id)
                for identifier in candidate.registry_identifiers
            ):
                winners.add(candidate.company_id)
    if query.lei:
        winners.update(
            candidate.company_id
            for candidate in candidates
            if any(
                _normalize_identifier(identifier.value) == _normalize_identifier(query.lei)
                for identifier in candidate.registry_identifiers
            )
        )
    if query.ticker:
        ticker_candidates = [
            candidate
            for candidate in candidates
            if _normalize_identifier(candidate.primary_ticker)
            == _normalize_identifier(query.ticker)
        ]
        if query.exchange:
            ticker_candidates = [
                candidate
                for candidate in ticker_candidates
                if _normalize_identifier(candidate.primary_exchange)
                == _normalize_identifier(query.exchange)
            ]
        if len(ticker_candidates) == 1:
            winners.add(ticker_candidates[0].company_id)
    domain_matches = _domain_winners(query, candidates)
    if len(domain_matches) == 1:
        winners.update(domain_matches)
    return winners


def _domain_winners(query: EntityQuery, candidates: Sequence[CompanyCandidate]) -> set[str]:
    if not query.domain:
        return set()
    normalized = _normalize_domain(query.domain)
    return {
        candidate.company_id
        for candidate in candidates
        if any(normalized == _normalize_domain(domain) for domain in candidate.domains)
    }


def _has_name_match(candidate: CompanyCandidate) -> bool:
    return any(
        reason.code in {"CANONICAL_NAME_MATCH", "FORMER_NAME_ALIAS_MATCH", "ALIAS_MATCH"}
        for reason in candidate.match_reasons
    )


def _resolved(selected: CompanyCandidate, candidates: list[CompanyCandidate]) -> EntityResolution:
    return EntityResolution(
        status=ResolutionStatus.RESOLVED,
        selected_company_id=selected.company_id,
        research_allowed=True,
        abstention_reason=None,
        candidates=candidates,
        match_reasons=selected.match_reasons,
        evidence_refs=selected.evidence_refs,
    )


def _abstain(
    status: ResolutionStatus,
    abstention_reason: str,
    candidates: list[CompanyCandidate],
    reason: MatchReason,
) -> EntityResolution:
    return EntityResolution(
        status=status,
        selected_company_id=None,
        research_allowed=False,
        abstention_reason=abstention_reason,
        candidates=candidates,
        match_reasons=[reason],
        evidence_refs=_unique(ref for candidate in candidates for ref in candidate.evidence_refs),
    )


def _unique(values: Sequence[str] | Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


__all__ = ["resolve_entity"]
