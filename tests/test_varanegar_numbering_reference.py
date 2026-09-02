import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_numbering_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_commit_and_draft_are_distinct():assert M.evaluate(M.baseline())=="NUMBER_COMMITTED_UNIQUE_AND_MONOTONIC" and M.evaluate(dict(M.baseline(),allocation_stage="DRAFT"))=="DRAFT_ACCEPTED_NUMBER_NOT_ALLOCATED"
def test_replay_precedes_sequence():e=dict(M.baseline(),idempotency_receipt_exists=True,observed_sequence_version=99);assert M.evaluate(e)=="IDEMPOTENT_REPLAY_EXISTING_NUMBER"
def test_unknown_commit_precedes_allocation():e=dict(M.baseline(),commit_status="UNKNOWN");assert M.evaluate(e)=="ALLOCATION_UNKNOWN_RECONCILIATION_REQUIRED"
def test_expired_reservation_requires_void():e=dict(M.baseline(),allocation_stage="RESERVED",reservation_expired=True);assert M.evaluate(e)=="VOID_RECEIPT_REQUIRED_EXPIRED_RESERVATION";e["void_receipt_present"]=True;assert M.evaluate(e)=="GAP_RECORDED_WITH_IMMUTABLE_VOID"
def test_offline_range_and_rollover_fail_closed():e=dict(M.baseline(),allocation_stage="RESERVED",offline_mode=True,candidate_number=201);assert M.evaluate(e)=="OFFLINE_RANGE_REJECTED_BOUNDARY_EXPIRY_OR_OVERLAP";e=dict(M.baseline(),rollover_requested=True,open_reservation_count=1);assert M.evaluate(e)=="ROLLOVER_REJECTED_OPEN_RESERVATION_OR_GAP"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=1;assert M.evaluate(e)=="SCHEMA_INVALID"
