"""Pure synthetic optimistic-concurrency decision evaluator."""
from __future__ import annotations
FIELDS={"expected_version","observed_version","compare_and_swap_match_count","idempotency_receipt_exists","same_command_fingerprint","commit_status","deadlock_or_timeout_before_commit","command_identity_preserved","business_invariant_version_current","candidate_sequence","last_accepted_sequence","lease_required","lease_valid_and_owned","candidate_fencing_token","last_accepted_fencing_token","bulk_atomic_or_quarantined"}
BOOL={"idempotency_receipt_exists","same_command_fingerprint","deadlock_or_timeout_before_commit","command_identity_preserved","business_invariant_version_current","lease_required","lease_valid_and_owned","bulk_atomic_or_quarantined"}
INT={"expected_version","observed_version","compare_and_swap_match_count","candidate_sequence","last_accepted_sequence","candidate_fencing_token","last_accepted_fencing_token"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or any(type(e[x]) is not int or e[x]<0 for x in INT):return "SCHEMA_INVALID"
 if e["commit_status"] not in {"NOT_STARTED","UNKNOWN","COMMITTED"}:return "SCHEMA_INVALID"
 if e["idempotency_receipt_exists"]:return "IDEMPOTENT_REPLAY_EXISTING_RECEIPT" if e["same_command_fingerprint"] else "CONFLICT_FINGERPRINT_OR_IDEMPOTENCY_KEY"
 if e["commit_status"]=="UNKNOWN":return "RECONCILIATION_REQUIRED_UNKNOWN_COMMIT"
 if e["deadlock_or_timeout_before_commit"]:
  return "RETRY_ALLOWED_SAME_COMMAND_IDENTITY" if e["command_identity_preserved"] else "RETRY_REJECTED_COMMAND_IDENTITY_CHANGED"
 if e["expected_version"]!=e["observed_version"]:return "CONFLICT_EXPECTED_VERSION_MISMATCH"
 if e["compare_and_swap_match_count"]!=1:return "CONFLICT_COMPARE_AND_SWAP_CARDINALITY"
 if not e["business_invariant_version_current"]:return "CONFLICT_BUSINESS_INVARIANT_VERSION_SET"
 if e["candidate_sequence"]<=e["last_accepted_sequence"]:return "CONFLICT_SEQUENCE_NOT_MONOTONIC"
 if e["lease_required"] and not e["lease_valid_and_owned"]:return "CONFLICT_LEASE_INVALID_OR_WRONG_OWNER"
 if e["lease_required"] and e["candidate_fencing_token"]<=e["last_accepted_fencing_token"]:return "CONFLICT_FENCING_TOKEN_STALE"
 if not e["bulk_atomic_or_quarantined"]:return "BULK_REJECTED_MIXED_VERSION_PARTIAL_POLICY"
 return "COMMIT_ACCEPTED_EXPECTED_VERSION_MATCHED"
def baseline():
 return {"expected_version":7,"observed_version":7,"compare_and_swap_match_count":1,"idempotency_receipt_exists":False,"same_command_fingerprint":True,"commit_status":"NOT_STARTED","deadlock_or_timeout_before_commit":False,"command_identity_preserved":True,"business_invariant_version_current":True,"candidate_sequence":11,"last_accepted_sequence":10,"lease_required":True,"lease_valid_and_owned":True,"candidate_fencing_token":21,"last_accepted_fencing_token":20,"bulk_atomic_or_quarantined":True}
