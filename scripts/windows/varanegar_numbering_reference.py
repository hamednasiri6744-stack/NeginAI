"""Pure synthetic document-numbering state evaluator."""
from __future__ import annotations
FIELDS={"scope_complete","series_active","fiscal_period_open","allocation_stage","idempotency_receipt_exists","same_command_fingerprint","commit_status","expected_sequence_version","observed_sequence_version","candidate_number","last_committed_number","candidate_fencing_token","last_accepted_fencing_token","reservation_expired","void_receipt_present","offline_mode","offline_range_start","offline_range_end","offline_range_expired","offline_range_overlap","rollover_requested","open_reservation_count","gap_void_reconciled"}
BOOL={"scope_complete","series_active","fiscal_period_open","idempotency_receipt_exists","same_command_fingerprint","reservation_expired","void_receipt_present","offline_mode","offline_range_expired","offline_range_overlap","rollover_requested","gap_void_reconciled"}
INT={"expected_sequence_version","observed_sequence_version","candidate_number","last_committed_number","candidate_fencing_token","last_accepted_fencing_token","offline_range_start","offline_range_end","open_reservation_count"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or any(type(e[x]) is not int or e[x]<0 for x in INT):return "SCHEMA_INVALID"
 if e["allocation_stage"] not in {"DRAFT","RESERVED","COMMIT"} or e["commit_status"] not in {"NOT_STARTED","UNKNOWN","COMMITTED"}:return "SCHEMA_INVALID"
 if not e["scope_complete"]:return "ALLOCATION_REJECTED_SCOPE_INCOMPLETE"
 if not e["series_active"] or not e["fiscal_period_open"]:return "ALLOCATION_REJECTED_SERIES_OR_PERIOD"
 if e["idempotency_receipt_exists"]:return "IDEMPOTENT_REPLAY_EXISTING_NUMBER" if e["same_command_fingerprint"] else "CONFLICT_FINGERPRINT_OR_IDEMPOTENCY_KEY"
 if e["commit_status"]=="UNKNOWN":return "ALLOCATION_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["expected_sequence_version"]!=e["observed_sequence_version"]:return "ALLOCATION_REJECTED_SEQUENCE_VERSION"
 if e["candidate_fencing_token"]<=e["last_accepted_fencing_token"]:return "ALLOCATION_REJECTED_STALE_FENCING_TOKEN"
 if e["rollover_requested"]:
  return "ROLLOVER_ACCEPTED_CLOSED_AND_RECONCILED" if e["open_reservation_count"]==0 and e["gap_void_reconciled"] else "ROLLOVER_REJECTED_OPEN_RESERVATION_OR_GAP"
 if e["allocation_stage"]=="DRAFT":return "DRAFT_ACCEPTED_NUMBER_NOT_ALLOCATED"
 if e["reservation_expired"]:return "GAP_RECORDED_WITH_IMMUTABLE_VOID" if e["void_receipt_present"] else "VOID_RECEIPT_REQUIRED_EXPIRED_RESERVATION"
 if e["candidate_number"]<=e["last_committed_number"]:return "ALLOCATION_REJECTED_DUPLICATE_OR_NONMONOTONIC"
 if e["offline_mode"]:
  if e["offline_range_start"]>e["offline_range_end"] or e["offline_range_expired"] or e["offline_range_overlap"] or not e["offline_range_start"]<=e["candidate_number"]<=e["offline_range_end"]:return "OFFLINE_RANGE_REJECTED_BOUNDARY_EXPIRY_OR_OVERLAP"
  return "OFFLINE_RESERVATION_ACCEPTED_SCOPED_RANGE"
 return "RESERVATION_ACCEPTED_NOT_COMMITTED" if e["allocation_stage"]=="RESERVED" else "NUMBER_COMMITTED_UNIQUE_AND_MONOTONIC"
def baseline():
 return {"scope_complete":True,"series_active":True,"fiscal_period_open":True,"allocation_stage":"COMMIT","idempotency_receipt_exists":False,"same_command_fingerprint":True,"commit_status":"NOT_STARTED","expected_sequence_version":10,"observed_sequence_version":10,"candidate_number":101,"last_committed_number":100,"candidate_fencing_token":21,"last_accepted_fencing_token":20,"reservation_expired":False,"void_receipt_present":False,"offline_mode":False,"offline_range_start":100,"offline_range_end":200,"offline_range_expired":False,"offline_range_overlap":False,"rollover_requested":False,"open_reservation_count":0,"gap_void_reconciled":True}
