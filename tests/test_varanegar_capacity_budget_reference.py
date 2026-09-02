import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_capacity_budget_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_capacity_accepts_bounded_baseline():assert M.evaluate(M.baseline())=="CAPACITY_ACCEPTED_WITHIN_ENVELOPE"
def test_timeout_budget_is_hierarchical():
 e=M.baseline();e["elapsed_ms"]=500;e["local_timeout_ms"]=600;assert M.evaluate(e)=="TIMEOUT_BUDGET_INVALID";e=M.baseline();e["downstream_timeout_ms"]=700;assert M.evaluate(e)=="TIMEOUT_BUDGET_INVALID"
def test_unknown_commit_precedes_retry():
 e=M.baseline();e["commit_status"]="UNKNOWN";e["retries_used"]=1;assert M.evaluate(e)=="RECONCILIATION_REQUIRED_UNKNOWN_COMMIT"
def test_backpressure_and_retry_are_typed():
 e=M.baseline();e["queue_depth"]=20;assert M.evaluate(e)=="QUEUE_BACKPRESSURE_APPLIED";e=M.baseline();e["retries_used"]=1;assert M.evaluate(e)=="RETRY_ALLOWED_WITHIN_BUDGET_AND_IDEMPOTENCY"
def test_degradation_and_recovery_preserve_invariants():
 e=M.baseline();e["degraded_mode_requested"]=True;e["degraded_invariants_preserved"]=False;assert M.evaluate(e)=="DEGRADED_MODE_REJECTED_INVARIANT";e=M.baseline();e["overload_recovery_requested"]=True;e["drain_complete"]=False;assert M.evaluate(e)=="RECOVERY_PENDING_DRAIN_OR_RECONCILIATION"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=1;assert M.evaluate(e)=="SCHEMA_INVALID"
