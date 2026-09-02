import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_concurrency_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_commit_accepts_exact_version_cas_and_fence():assert M.evaluate(M.baseline())=="COMMIT_ACCEPTED_EXPECTED_VERSION_MATCHED"
def test_replay_precedes_version_evaluation():
 e=M.baseline();e["idempotency_receipt_exists"]=True;e["observed_version"]=99;assert M.evaluate(e)=="IDEMPOTENT_REPLAY_EXISTING_RECEIPT"
def test_unknown_commit_precedes_retry():
 e=M.baseline();e["commit_status"]="UNKNOWN";e["deadlock_or_timeout_before_commit"]=True;assert M.evaluate(e)=="RECONCILIATION_REQUIRED_UNKNOWN_COMMIT"
def test_version_and_cas_conflicts_are_distinct():
 e=M.baseline();e["observed_version"]=8;assert M.evaluate(e)=="CONFLICT_EXPECTED_VERSION_MISMATCH";e=M.baseline();e["compare_and_swap_match_count"]=0;assert M.evaluate(e)=="CONFLICT_COMPARE_AND_SWAP_CARDINALITY"
def test_sequence_lease_and_fence_fail_closed():
 e=M.baseline();e["candidate_sequence"]=10;assert M.evaluate(e)=="CONFLICT_SEQUENCE_NOT_MONOTONIC";e=M.baseline();e["lease_valid_and_owned"]=False;assert M.evaluate(e)=="CONFLICT_LEASE_INVALID_OR_WRONG_OWNER";e=M.baseline();e["candidate_fencing_token"]=20;assert M.evaluate(e)=="CONFLICT_FENCING_TOKEN_STALE"
def test_schema_exact():
 e=copy.deepcopy(M.baseline());e["extra"]=1;assert M.evaluate(e)=="SCHEMA_INVALID"
