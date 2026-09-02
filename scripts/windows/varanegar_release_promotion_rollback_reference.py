"""Pure reference evaluator for synthetic release promotion/rollback envelopes."""
from __future__ import annotations
import re

BOOL_FIELDS=("signature_valid","provenance_valid","sbom_valid","tests_current_zero_exclusion","environment_token_valid","change_window_valid","migration_compatible","backup_restore_current","canary_threshold_ok","kill_switch_ready","redaction_retention_current","health_pass","slo_pass","business_invariant_pass","uat_accepted","production_approved","independent_roles_separated","rollback_safe")
FIELDS={"decision_type","source_artifact_sha256","target_artifact_sha256","blocking_unknown_count","residual_difference_count",*BOOL_FIELDS}
DECISIONS={"PROMOTE_SANDBOX_TO_UAT","PROMOTE_UAT_TO_PRODUCTION","ROLLBACK_PRODUCTION"}
HEX64=re.compile(r"^[0-9a-f]{64}$")

def evaluate(envelope:dict)->str:
 if not isinstance(envelope,dict) or set(envelope)!=FIELDS:return "SCHEMA_INVALID"
 if envelope["decision_type"] not in DECISIONS:return "SCHEMA_INVALID"
 if any(type(envelope[x]) is not bool for x in BOOL_FIELDS):return "SCHEMA_INVALID"
 if any(type(envelope[x]) is not int or envelope[x]<0 for x in ("blocking_unknown_count","residual_difference_count")):return "SCHEMA_INVALID"
 if any(not isinstance(envelope[x],str) for x in ("source_artifact_sha256","target_artifact_sha256")):return "ARTIFACT_DIGEST_INVALID"
 if not HEX64.fullmatch(envelope["source_artifact_sha256"]) or not HEX64.fullmatch(envelope["target_artifact_sha256"]):return "ARTIFACT_DIGEST_INVALID"
 if envelope["source_artifact_sha256"]!=envelope["target_artifact_sha256"]:return "ARTIFACT_DIGEST_MISMATCH"
 if not all(envelope[x] for x in ("signature_valid","provenance_valid","sbom_valid")):return "SUPPLY_CHAIN_INVALID"
 if not envelope["tests_current_zero_exclusion"]:return "TEST_EVIDENCE_INVALID"
 if not envelope["environment_token_valid"]:return "ENVIRONMENT_TOKEN_INVALID"
 if not envelope["change_window_valid"]:return "CHANGE_WINDOW_INVALID"
 if not envelope["migration_compatible"] or not envelope["backup_restore_current"]:return "MIGRATION_OR_RECOVERY_INVALID"
 if not envelope["canary_threshold_ok"] or not envelope["kill_switch_ready"]:return "CANARY_OR_KILL_SWITCH_INVALID"
 if not envelope["redaction_retention_current"]:return "REDACTION_OR_RETENTION_INVALID"
 if envelope["blocking_unknown_count"]:return "BLOCKING_UNKNOWN_PRESENT"
 if envelope["residual_difference_count"]:return "RESIDUAL_DIFFERENCE_PRESENT"
 if not envelope["health_pass"] or not envelope["slo_pass"] or not envelope["business_invariant_pass"]:return "HEALTH_SLO_OR_BUSINESS_INVARIANT_FAILED"
 decision=envelope["decision_type"]
 if decision=="PROMOTE_SANDBOX_TO_UAT":return "UAT_PROMOTION_ACCEPTED"
 if not envelope["uat_accepted"]:return "UAT_ACCEPTANCE_MISSING"
 if not envelope["production_approved"]:return "PRODUCTION_APPROVAL_MISSING"
 if not envelope["independent_roles_separated"]:return "INDEPENDENT_ROLE_SEPARATION_INVALID"
 if decision=="ROLLBACK_PRODUCTION" and not envelope["rollback_safe"]:return "FORWARD_FIX_REQUIRED_ROLLBACK_UNSAFE"
 return "PRODUCTION_PROMOTION_ACCEPTED" if decision=="PROMOTE_UAT_TO_PRODUCTION" else "PRODUCTION_ROLLBACK_ACCEPTED"

def baseline(decision_type:str)->dict:
 digest="a"*64
 value={"decision_type":decision_type,"source_artifact_sha256":digest,"target_artifact_sha256":digest,"blocking_unknown_count":0,"residual_difference_count":0}
 value.update({x:True for x in BOOL_FIELDS})
 if decision_type=="PROMOTE_SANDBOX_TO_UAT":
  value["uat_accepted"]=False;value["production_approved"]=False;value["rollback_safe"]=False
 return value
