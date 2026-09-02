"""Chain the target command authorization, scope, and decision-trace contract."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_command_authorization_scope_decision_trace_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_COMMAND_AUTHORIZATION_SCOPE_DECISION_TRACE_20260829_FA.md",
}
def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in SOURCES.items()};c=load(paths["contract"]);prev=load(paths["previous"]);s=c["summary"]
    checks={
        "sources_pass":c["validation"]==prev["validation"]=="PASS",
        "coverage_14_49_588_686":(s["module_count"],s["target_command_count"],s["command_dimension_assignment_count"],s["command_negative_case_assignment_count"])==(14,49,588,686),
        "gates_roles_complete":s["command_gate_assignment_count"]==784 and s["command_role_assignment_count"]==245,
        "implementation_uat_runtime_readiness_zero":s["implemented_server_authorization_count"]==s["authenticated_isolated_uat_run_count"]==s["accepted_allow_trace_count"]==s["accepted_deny_trace_count"]==s["runtime_authorization_proven_command_count"]==s["command_ready_count"]==s["pilot_ready_module_count"]==0,
        "base_stable":s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_authorization_contract"]==1404,
        "safety_zero":set(c["safety"].values())=={0},
    };failed=sorted(k for k,v in checks.items() if not v)
    out={"artifact":"varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":SOURCES["previous"],"sha256":sha(paths["previous"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":SOURCES[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],"safety":{"database_connections":0,"network_reads_or_writes":0,"authentication_sessions_commands_or_authorization_uat_executed":0,"operational_forms_reports_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"credentials_tokens_identity_pii_or_raw_business_values_read_or_persisted":0}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
