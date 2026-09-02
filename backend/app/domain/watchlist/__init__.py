"""Weekly watchlist funnel, scoring, and publication contracts."""

from .funnel import Candidate, FunnelResult, run_funnel
from .publication import PublicationStore
from .scoring import score_candidate

__all__ = ["Candidate", "FunnelResult", "PublicationStore", "run_funnel", "score_candidate"]
