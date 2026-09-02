"""Pure synthetic timeout/retry/backpressure/degradation decision evaluator."""
from __future__ import annotations
FIELDS={"parent_budget_ms","elapsed_ms","local_timeout_ms","downstream_timeout_ms","retries_used","retry_limit","idempotent","commit_status","backoff_and_jitter_valid","inflight","inflight_limit","queue_depth","queue_capacity","dependency_healthy","circuit_open","degraded_mode_requested","degraded_invariants_preserved","overload_recovery_requested","drain_complete","reconciliation_complete","blocking_unknown_count"}
INT={"parent_budget_ms","elapsed_ms","local_timeout_ms","downstream_timeout_ms","retries_used","retry_limit","inflight","inflight_limit","queue_depth","queue_capacity","blocking_unknown_count"}
BOOL={"idempotent","backoff_and_jitter_valid","dependency_healthy","circuit_open","degraded_mode_requested","degraded_invariants_preserved","overload_recovery_requested","drain_complete","reconciliation_complete"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not int or e[x]<0 for x in INT) or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if e["commit_status"] not in {"NOT_STARTED","UNKNOWN","COMMITTED"}:return "SCHEMA_INVALID"
 if not all(e[x]>0 for x in ("parent_budget_ms","local_timeout_ms","inflight_limit","queue_capacity")) or e["retry_limit"]<1:return "SCHEMA_INVALID"
 if e["blocking_unknown_count"]:return "BLOCKING_UNKNOWN_PRESENT"
 if e["commit_status"]=="UNKNOWN":return "RECONCILIATION_REQUIRED_UNKNOWN_COMMIT"
 if e["elapsed_ms"]+e["local_timeout_ms"]>e["parent_budget_ms"] or e["downstream_timeout_ms"]>e["local_timeout_ms"]:return "TIMEOUT_BUDGET_INVALID"
 if e["inflight"]>=e["inflight_limit"]:return "REQUEST_REJECTED_CONCURRENCY_LIMIT"
 if e["queue_depth"]>=e["queue_capacity"]:return "QUEUE_BACKPRESSURE_APPLIED"
 if e["retries_used"]:
  if not e["idempotent"] or not e["backoff_and_jitter_valid"]:return "RETRY_BLOCKED_UNSAFE_OR_UNBOUNDED"
  if e["retries_used"]>=e["retry_limit"]:return "RETRY_BUDGET_EXHAUSTED"
 if not e["dependency_healthy"]:return "CIRCUIT_OPEN_DEPENDENCY_SHED" if e["circuit_open"] else "DEPENDENCY_FAILURE_CIRCUIT_NOT_OPEN"
 if e["degraded_mode_requested"]:return "DEGRADED_MODE_ACCEPTED_INVARIANTS_PRESERVED" if e["degraded_invariants_preserved"] else "DEGRADED_MODE_REJECTED_INVARIANT"
 if e["overload_recovery_requested"]:
  return "RECOVERY_ACCEPTED_DRAIN_AND_RECONCILIATION_COMPLETE" if e["drain_complete"] and e["reconciliation_complete"] else "RECOVERY_PENDING_DRAIN_OR_RECONCILIATION"
 return "CAPACITY_ACCEPTED_WITHIN_ENVELOPE" if not e["retries_used"] else "RETRY_ALLOWED_WITHIN_BUDGET_AND_IDEMPOTENCY"
def baseline():
 return {"parent_budget_ms":1000,"elapsed_ms":100,"local_timeout_ms":600,"downstream_timeout_ms":400,"retries_used":0,"retry_limit":3,"idempotent":True,"commit_status":"NOT_STARTED","backoff_and_jitter_valid":True,"inflight":3,"inflight_limit":10,"queue_depth":2,"queue_capacity":20,"dependency_healthy":True,"circuit_open":False,"degraded_mode_requested":False,"degraded_invariants_preserved":True,"overload_recovery_requested":False,"drain_complete":True,"reconciliation_complete":True,"blocking_unknown_count":0}
