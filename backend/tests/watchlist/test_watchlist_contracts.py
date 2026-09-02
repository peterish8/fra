from app.domain.watchlist.funnel import Candidate, run_funnel
from app.domain.watchlist.publication import PublicationStore

def test_funnel_rejects_unresolved_and_keeps_fewer_than_25() -> None:
    result = run_funnel([Candidate("ok", entity_resolved=True, evidence_coverage=.8), Candidate("bad")])
    assert len(result.finalists) == 1
    assert result.excluded[0]["reason"] == "IDENTITY_UNRESOLVED"

def test_publication_is_idempotent_and_ranked() -> None:
    store = PublicationStore()
    store.stage("2026-W01", [{"company_id": "a", "score": 50}, {"company_id": "a", "score": 60}])
    published = store.publish("2026-W01")
    assert published["status"] == "PUBLISHED"
    assert published["entries"][0]["rank"] == 1
