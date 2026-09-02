"""Pure synthetic integration-message evaluator; it performs no network or broker I/O."""
from __future__ import annotations

FIELDS={"transport_current","signature_valid","key_current","canonical_digest_match","schema_compatible","scope_current","timestamp_fresh","nonce_unique","message_id_consistent","inbox_dedup_status","ordering_current","delivery_state","idempotent_retry_current","retry_budget_current","quarantined","deadletter_encrypted","redrive_authorized","redrive_idempotent_capped","loop_guard_current","payload_policy_current","blocking_unknown"}
BOOL=FIELDS-{"inbox_dedup_status","delivery_state"}
DEDUP={"NEW","REPLAY_MATCH","CONFLICT"}
STATES={"INBOUND","OUTBOUND_ACK","OUTBOUND_UNKNOWN","OUTBOUND_RETRY","POISON","DEADLETTER","REDRIVE"}


def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or e["inbox_dedup_status"] not in DEDUP or e["delivery_state"] not in STATES:return "SCHEMA_INVALID"
 if not e["transport_current"]:return "MESSAGE_REJECTED_TRANSPORT"
 if not e["signature_valid"] or not e["key_current"]:return "MESSAGE_REJECTED_SIGNATURE_OR_KEY"
 if not e["canonical_digest_match"]:return "MESSAGE_REJECTED_CANONICAL_DIGEST"
 if not e["schema_compatible"]:return "MESSAGE_REJECTED_SCHEMA_COMPATIBILITY"
 if not e["scope_current"]:return "MESSAGE_REJECTED_TENANT_ENVIRONMENT_OR_AUDIENCE_SCOPE"
 if not e["timestamp_fresh"] or not e["nonce_unique"]:return "MESSAGE_REJECTED_TIMESTAMP_NONCE_OR_REPLAY"
 if not e["message_id_consistent"] or e["inbox_dedup_status"]=="CONFLICT":return "MESSAGE_REJECTED_MESSAGE_ID_FINGERPRINT_CONFLICT"
 if not e["ordering_current"]:return "MESSAGE_REJECTED_ORDERING_OR_SEQUENCE"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 if not e["payload_policy_current"]:return "MESSAGE_REJECTED_PAYLOAD_POLICY"
 state=e["delivery_state"]
 if state=="INBOUND":return "INBOUND_IDEMPOTENT_REPLAY_EXISTING_RESULT" if e["inbox_dedup_status"]=="REPLAY_MATCH" else "INBOUND_ACCEPTED_AUTHENTIC_SCOPED_AND_FRESH"
 if state=="OUTBOUND_ACK":return "OUTBOUND_ACKNOWLEDGED_AND_RECONCILED"
 if state=="OUTBOUND_UNKNOWN":return "OUTBOUND_UNKNOWN_RECONCILIATION_REQUIRED"
 if state=="OUTBOUND_RETRY":
  return "RETRY_ACCEPTED_IDEMPOTENT_AND_BOUNDED" if e["idempotent_retry_current"] and e["retry_budget_current"] else "RETRY_REJECTED_IDEMPOTENCY_OR_BUDGET"
 if state=="POISON":return "MESSAGE_QUARANTINED_POISON_OR_POLICY" if e["quarantined"] else "POISON_MESSAGE_REJECTED_NOT_QUARANTINED"
 if state=="DEADLETTER":return "DEADLETTER_ACCEPTED_ENCRYPTED_AND_RETAINED" if e["quarantined"] and e["deadletter_encrypted"] else "DEADLETTER_REJECTED_QUARANTINE_OR_ENCRYPTION"
 if not e["redrive_authorized"] or not e["redrive_idempotent_capped"] or not e["loop_guard_current"]:return "REDRIVE_REJECTED_AUTHORIZATION_SCOPE_OR_LOOP"
 return "REDRIVE_ACCEPTED_SCOPED_IDEMPOTENT_AND_CAPPED"


def baseline():
 return {"transport_current":True,"signature_valid":True,"key_current":True,"canonical_digest_match":True,"schema_compatible":True,"scope_current":True,"timestamp_fresh":True,"nonce_unique":True,"message_id_consistent":True,"inbox_dedup_status":"NEW","ordering_current":True,"delivery_state":"INBOUND","idempotent_retry_current":True,"retry_budget_current":True,"quarantined":False,"deadletter_encrypted":True,"redrive_authorized":True,"redrive_idempotent_capped":True,"loop_guard_current":True,"payload_policy_current":True,"blocking_unknown":False}
