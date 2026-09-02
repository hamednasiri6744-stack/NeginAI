import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_integration_message_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_inbound_and_matching_replay():assert M.evaluate(M.baseline())=="INBOUND_ACCEPTED_AUTHENTIC_SCOPED_AND_FRESH";assert M.evaluate(dict(M.baseline(),inbox_dedup_status="REPLAY_MATCH"))=="INBOUND_IDEMPOTENT_REPLAY_EXISTING_RESULT"
def test_signature_scope_and_replay_fail_closed():assert M.evaluate(dict(M.baseline(),signature_valid=False))=="MESSAGE_REJECTED_SIGNATURE_OR_KEY";assert M.evaluate(dict(M.baseline(),scope_current=False))=="MESSAGE_REJECTED_TENANT_ENVIRONMENT_OR_AUDIENCE_SCOPE";assert M.evaluate(dict(M.baseline(),nonce_unique=False))=="MESSAGE_REJECTED_TIMESTAMP_NONCE_OR_REPLAY"
def test_unknown_delivery_requires_reconciliation():assert M.evaluate(dict(M.baseline(),delivery_state="OUTBOUND_UNKNOWN"))=="OUTBOUND_UNKNOWN_RECONCILIATION_REQUIRED"
def test_retry_requires_idempotency_and_budget():assert M.evaluate(dict(M.baseline(),delivery_state="OUTBOUND_RETRY",idempotent_retry_current=False))=="RETRY_REJECTED_IDEMPOTENCY_OR_BUDGET";assert M.evaluate(dict(M.baseline(),delivery_state="OUTBOUND_RETRY",retry_budget_current=False))=="RETRY_REJECTED_IDEMPOTENCY_OR_BUDGET"
def test_poison_and_redrive_fail_closed():assert M.evaluate(dict(M.baseline(),delivery_state="POISON",quarantined=False))=="POISON_MESSAGE_REJECTED_NOT_QUARANTINED";assert M.evaluate(dict(M.baseline(),delivery_state="REDRIVE",loop_guard_current=False))=="REDRIVE_REJECTED_AUTHORIZATION_SCOPE_OR_LOOP"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
