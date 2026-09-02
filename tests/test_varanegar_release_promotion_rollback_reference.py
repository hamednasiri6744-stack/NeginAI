import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_release_promotion_rollback_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_uat_does_not_require_production_approval():assert M.evaluate(M.baseline("PROMOTE_SANDBOX_TO_UAT"))=="UAT_PROMOTION_ACCEPTED"
def test_production_requires_separate_approval():
 e=M.baseline("PROMOTE_UAT_TO_PRODUCTION");e["production_approved"]=False;assert M.evaluate(e)=="PRODUCTION_APPROVAL_MISSING"
def test_same_artifact_digest_required():
 e=M.baseline("PROMOTE_UAT_TO_PRODUCTION");e["target_artifact_sha256"]="b"*64;assert M.evaluate(e)=="ARTIFACT_DIGEST_MISMATCH"
def test_process_health_does_not_replace_business_invariant():
 e=M.baseline("PROMOTE_UAT_TO_PRODUCTION");e["business_invariant_pass"]=False;assert M.evaluate(e)=="HEALTH_SLO_OR_BUSINESS_INVARIANT_FAILED"
def test_unsafe_rollback_routes_to_forward_fix():
 e=M.baseline("ROLLBACK_PRODUCTION");e["rollback_safe"]=False;assert M.evaluate(e)=="FORWARD_FIX_REQUIRED_ROLLBACK_UNSAFE"
def test_schema_is_exact_and_deterministic():
 e=M.baseline("PROMOTE_UAT_TO_PRODUCTION");assert M.evaluate(copy.deepcopy(e))==M.evaluate(copy.deepcopy(e))=="PRODUCTION_PROMOTION_ACCEPTED";e["payload"]="forbidden";assert M.evaluate(e)=="SCHEMA_INVALID";e=M.baseline("PROMOTE_UAT_TO_PRODUCTION");e["target_artifact_sha256"]=None;assert M.evaluate(e)=="ARTIFACT_DIGEST_INVALID"
