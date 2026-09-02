"""Pure synthetic reference validator for comparison-adapter contract vectors.

This module performs no I/O. It is not the target ERP adapter and must never be
used to claim runtime parity, receipt authenticity, or operational readiness.
"""
from __future__ import annotations

from copy import deepcopy


ERROR_RULES = [
    ("manifest_missing", "MANIFEST_MISSING", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("manifest_hash_mismatch", "MANIFEST_HASH_MISMATCH", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("schema_version_unsupported", "SCHEMA_VERSION_UNSUPPORTED", "UNSUPPORTED_PROFILE_OR_SCHEMA"),
    ("adapter_profile_version_mismatch", "ADAPTER_PROFILE_VERSION_MISMATCH", "UNSUPPORTED_PROFILE_OR_SCHEMA"),
    ("fixture_or_case_set_mismatch", "FIXTURE_OR_CASE_SET_MISMATCH", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("capture_side_missing_or_duplicated", "CAPTURE_SIDE_MISSING_OR_DUPLICATED", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("dimension_set_mismatch", "DIMENSION_SET_MISMATCH", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("scope_policy_version_mismatch", "SCOPE_POLICY_VERSION_MISMATCH", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("locale_timezone_calendar_ambiguous", "LOCALE_TIMEZONE_CALENDAR_AMBIGUOUS", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("decimal_rounding_currency_policy_ambiguous", "DECIMAL_ROUNDING_CURRENCY_POLICY_AMBIGUOUS", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("stable_key_missing_or_duplicated", "STABLE_KEY_MISSING_OR_DUPLICATED", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("grain_or_cardinality_mismatch", "GRAIN_OR_CARDINALITY_MISMATCH", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("canonical_serialization_failure", "CANONICAL_SERIALIZATION_FAILURE", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
    ("partial_or_unknown_outcome", "PARTIAL_OR_UNKNOWN_OUTCOME", "PARTIAL_OR_UNKNOWN_BLOCK"),
    ("idempotency_conflict", "IDEMPOTENCY_CONFLICT", "CONFLICT_OR_SUPERSESSION_BLOCK"),
    ("raw_payload_persistence_attempt", "RAW_PAYLOAD_PERSISTENCE_ATTEMPT", "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"),
]


def baseline_envelope(adapter_profile_id: str) -> dict:
    return {
        "adapter_profile_id": adapter_profile_id,
        "manifest_present": True,
        "manifest_hash_matches": True,
        "schema_version_supported": True,
        "adapter_profile_version_matches": True,
        "fixture_and_case_set_match": True,
        "capture_side_count": 2,
        "dimension_set_matches": True,
        "scope_policy_version_matches": True,
        "temporal_policy_unambiguous": True,
        "decimal_policy_unambiguous": True,
        "stable_key_count": 1,
        "grain_and_cardinality_match": True,
        "canonical_serialization_succeeds": True,
        "outcome": "COMPLETE",
        "idempotency_conflict": False,
        "raw_payload_persistence_requested": False,
        "contains_business_value": False,
        "synthetic_only": True,
    }


def mutated_envelope(adapter_profile_id: str, trigger_class: str) -> dict:
    envelope = deepcopy(baseline_envelope(adapter_profile_id))
    mutations = {
        "manifest_missing": ("manifest_present", False),
        "manifest_hash_mismatch": ("manifest_hash_matches", False),
        "schema_version_unsupported": ("schema_version_supported", False),
        "adapter_profile_version_mismatch": ("adapter_profile_version_matches", False),
        "fixture_or_case_set_mismatch": ("fixture_and_case_set_match", False),
        "capture_side_missing_or_duplicated": ("capture_side_count", 1),
        "dimension_set_mismatch": ("dimension_set_matches", False),
        "scope_policy_version_mismatch": ("scope_policy_version_matches", False),
        "locale_timezone_calendar_ambiguous": ("temporal_policy_unambiguous", False),
        "decimal_rounding_currency_policy_ambiguous": ("decimal_policy_unambiguous", False),
        "stable_key_missing_or_duplicated": ("stable_key_count", 0),
        "grain_or_cardinality_mismatch": ("grain_and_cardinality_match", False),
        "canonical_serialization_failure": ("canonical_serialization_succeeds", False),
        "partial_or_unknown_outcome": ("outcome", "UNKNOWN"),
        "idempotency_conflict": ("idempotency_conflict", True),
        "raw_payload_persistence_attempt": ("raw_payload_persistence_requested", True),
    }
    if trigger_class not in mutations:
        raise ValueError("unknown synthetic trigger class")
    field, value = mutations[trigger_class]
    envelope[field] = value
    return envelope


def validate(envelope: dict) -> dict:
    predicates = [
        not envelope["manifest_present"],
        not envelope["manifest_hash_matches"],
        not envelope["schema_version_supported"],
        not envelope["adapter_profile_version_matches"],
        not envelope["fixture_and_case_set_match"],
        envelope["capture_side_count"] != 2,
        not envelope["dimension_set_matches"],
        not envelope["scope_policy_version_matches"],
        not envelope["temporal_policy_unambiguous"],
        not envelope["decimal_policy_unambiguous"],
        envelope["stable_key_count"] != 1,
        not envelope["grain_and_cardinality_match"],
        not envelope["canonical_serialization_succeeds"],
        envelope["outcome"] != "COMPLETE",
        envelope["idempotency_conflict"],
        envelope["raw_payload_persistence_requested"],
    ]
    for matched, (trigger, error_code, typed_status) in zip(predicates, ERROR_RULES, strict=True):
        if matched:
            return {
                "accepted": False,
                "trigger_class": trigger,
                "error_code": error_code,
                "typed_status": typed_status,
            }
    return {
        "accepted": True,
        "trigger_class": None,
        "error_code": None,
        "typed_status": "SYNTHETIC_REFERENCE_READY_FOR_HASH_CONFORMANCE",
    }

