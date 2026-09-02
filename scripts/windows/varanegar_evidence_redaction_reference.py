"""Pure synthetic reference validator for hash-only evidence envelopes."""
from __future__ import annotations

import re
from datetime import datetime


ALLOWED_FIELDS = {
    "domain_sha256",
    "opaque_reference",
    "aggregate_count",
    "status",
    "version_sha256",
    "observed_at",
    "role_type",
    "gate_passed",
}

FORBIDDEN_FIELD_CODES = {
    "credential": "PROHIBITED_CREDENTIAL_FIELD",
    "auth_token": "PROHIBITED_TOKEN_FIELD",
    "identity_pii": "PROHIBITED_IDENTITY_PII_FIELD",
    "business_identifier": "PROHIBITED_BUSINESS_IDENTIFIER_FIELD",
    "commercial_value": "PROHIBITED_COMMERCIAL_VALUE_FIELD",
    "payment_value": "PROHIBITED_PAYMENT_FIELD",
    "payload": "PROHIBITED_PAYLOAD_FIELD",
    "sql_or_rule": "PROHIBITED_SQL_RULE_FIELD",
    "file_or_binary": "PROHIBITED_FILE_BINARY_FIELD",
    "endpoint_or_path": "PROHIBITED_ENDPOINT_PATH_FIELD",
    "crypto_material": "PROHIBITED_CRYPTO_MATERIAL_FIELD",
    "stack_or_dump": "PROHIBITED_STACK_DUMP_FIELD",
    "backup_log_message_export": "PROHIBITED_BULK_CONTENT_FIELD",
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATUS = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
ROLE = re.compile(r"^[A-Z][A-Z0-9_]*_ROLE$")


def validate_evidence(channel: str, payload: object) -> dict:
    if not isinstance(channel, str) or not STATUS.fullmatch(channel):
        return {"accepted": False, "code": "INVALID_CHANNEL"}
    if not isinstance(payload, dict):
        return {"accepted": False, "code": "UNKNOWN_OR_NESTED_PAYLOAD"}
    for field in payload:
        if field in FORBIDDEN_FIELD_CODES:
            return {"accepted": False, "code": FORBIDDEN_FIELD_CODES[field]}
        if field not in ALLOWED_FIELDS:
            return {"accepted": False, "code": "UNKNOWN_OR_NESTED_PAYLOAD"}
    if set(payload) != ALLOWED_FIELDS:
        return {"accepted": False, "code": "ALLOWED_FIELD_SET_INCOMPLETE"}
    if any(isinstance(value, (dict, list, tuple, set)) for value in payload.values()):
        return {"accepted": False, "code": "UNKNOWN_OR_NESTED_PAYLOAD"}
    if not isinstance(payload["domain_sha256"], str) or not HEX64.fullmatch(payload["domain_sha256"]):
        return {"accepted": False, "code": "INVALID_DOMAIN_HASH"}
    if not isinstance(payload["version_sha256"], str) or not HEX64.fullmatch(payload["version_sha256"]):
        return {"accepted": False, "code": "INVALID_VERSION_HASH"}
    reference = payload["opaque_reference"]
    if not isinstance(reference, str) or not reference.startswith("REF:") or not HEX64.fullmatch(reference[4:]):
        return {"accepted": False, "code": "INVALID_OPAQUE_REFERENCE"}
    count = payload["aggregate_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return {"accepted": False, "code": "INVALID_AGGREGATE_COUNT"}
    if not isinstance(payload["status"], str) or not STATUS.fullmatch(payload["status"]):
        return {"accepted": False, "code": "INVALID_STATUS"}
    try:
        observed_at = datetime.fromisoformat(str(payload["observed_at"]).replace("Z", "+00:00"))
    except ValueError:
        return {"accepted": False, "code": "INVALID_OBSERVED_AT"}
    if observed_at.tzinfo is None:
        return {"accepted": False, "code": "INVALID_OBSERVED_AT"}
    if not isinstance(payload["role_type"], str) or not ROLE.fullmatch(payload["role_type"]):
        return {"accepted": False, "code": "INVALID_ROLE_TYPE"}
    if not isinstance(payload["gate_passed"], bool):
        return {"accepted": False, "code": "INVALID_GATE_BOOLEAN"}
    return {"accepted": True, "code": "ALLOWLISTED_HASH_ONLY_EVIDENCE_ACCEPTED"}
