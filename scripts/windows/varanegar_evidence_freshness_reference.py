"""Pure reference evaluator for synthetic evidence-freshness vectors."""
from __future__ import annotations

from datetime import datetime


OUTCOMES = [
    "MISSING_TEMPORAL_EVIDENCE",
    "NOT_YET_VALID",
    "CURRENT",
    "EXPIRED",
    "REVOKED",
    "SUPERSEDED",
    "CLOCK_OR_INTERVAL_INVALID",
    "POLICY_VERSION_MISMATCH",
]


def parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed


def evaluate(envelope: dict) -> str:
    required = ("evaluated_at", "valid_from", "expires_at", "policy_version_matches", "clock_trusted", "revoked", "superseded")
    if any(field not in envelope or envelope[field] is None for field in required):
        return "MISSING_TEMPORAL_EVIDENCE"
    try:
        evaluated_at = parse_aware(envelope["evaluated_at"])
        valid_from = parse_aware(envelope["valid_from"])
        expires_at = parse_aware(envelope["expires_at"])
    except (TypeError, ValueError):
        return "CLOCK_OR_INTERVAL_INVALID"
    if not envelope["clock_trusted"] or valid_from >= expires_at:
        return "CLOCK_OR_INTERVAL_INVALID"
    if not envelope["policy_version_matches"]:
        return "POLICY_VERSION_MISMATCH"
    if envelope["revoked"]:
        return "REVOKED"
    if envelope["superseded"]:
        return "SUPERSEDED"
    if evaluated_at < valid_from:
        return "NOT_YET_VALID"
    if evaluated_at >= expires_at:
        return "EXPIRED"
    return "CURRENT"

