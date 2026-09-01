"""Evidence-bounded semantic verification and canonical verdict rules."""

from .semantic import (
    SemanticOutcome,
    SemanticVerificationRequest,
    SemanticVerificationResult,
    SupportType,
    verify_semantic,
)
from .verdicts import VerdictDecision, VerdictInput, determine_verdict

__all__ = [
    "SemanticOutcome",
    "SemanticVerificationRequest",
    "SemanticVerificationResult",
    "SupportType",
    "VerdictDecision",
    "VerdictInput",
    "determine_verdict",
    "verify_semantic",
]
