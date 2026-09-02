from app.domain.claims.models import ClaimVerdict


def test_golden_outcome_vocabulary_is_closed() -> None:
    assert {item.value for item in ClaimVerdict} == {
        "VERIFIED",
        "PARTIALLY_SUPPORTED",
        "CONTRADICTED",
        "UNVERIFIED",
        "INSUFFICIENT_EVIDENCE",
        "STALE",
    }
