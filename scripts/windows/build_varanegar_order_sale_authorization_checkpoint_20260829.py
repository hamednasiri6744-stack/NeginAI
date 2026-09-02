"""Build the order-to-sale authorization and resource-scope checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/order_sale_authorization_sql_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/order_sale_authorization_runtime_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_order_sale_operation_date_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_order_sale_authorization_sql.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_order_sale_authorization_runtime.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_order_sale_authorization_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_order_sale_authorization_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_AUTHORIZATION_AND_RESOURCE_SCOPE_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name):
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_redacted": (
            sql["validation"] == "PASS"
            and sql["summary"]["selected_sql_module_count"] == 4
            and sql["safety"]["connection_readonly"]
            and sql["safety"]["operational_stored_procedure_executions"] == 0
            and sql["safety"]["raw_sql_definitions_messages_string_literals_or_identities_persisted"] == 0
        ),
        "runtime_static_hash_pinned": (
            runtime["validation"] == "PASS"
            and runtime["summary"]["assembly_count"] == 3
            and runtime["summary"]["selected_method_count"] == 12
            and runtime["summary"]["source_hash_mismatch_count"] == 0
            and runtime["safety"]["assembly_loads_or_executions"] == 0
        ),
        "conditional_area_scope_contract": (
            sql["semantic_assertions"]["wrapper_calls_conditional_area_access_before_core"]
            and sql["semantic_assertions"]["area_access_is_enabled_only_by_global_key_value_one"]
            and sql["semantic_assertions"]["area_access_scopes_customer_sale_area_to_user_projection"]
            and sql["semantic_assertions"]["area_access_allows_customer_without_sale_area"]
        ),
        "current_clone_area_gate_disabled": (
            sql["summary"]["global_area_access_enabled_key_count"] == 0
            and sql["summary"]["general_config_area_access_true_count"] == 0
            and sql["summary"]["sale_user_access_projection_row_count"] == 2
        ),
        "order_type_right_has_no_convert_action": (
            sql["semantic_assertions"]["order_type_permission_has_no_convert_action"]
            and sql["semantic_assertions"]["order_type_permission_supports_admin_direct_and_group_rights"]
            and not sql["contract"]["order_type_right_has_convert_action"]
        ),
        "conversion_form_and_methods_have_no_named_gate": (
            runtime["summary"]["order_to_sale_form_permission_call_count"] == 0
            and runtime["assertions"]["order_to_sale_form_has_no_permission_or_access_member_call"]
            and runtime["assertions"]["selected_conversion_methods_have_no_permission_or_access_member_call"]
        ),
        "order_type_permission_callsites_are_list_only": (
            runtime["summary"]["order_type_permission_ui_callsite_count"] == 10
            and runtime["assertions"]["order_type_permission_is_called_from_order_lists_not_conversion_form"]
            and runtime["assertions"]["adapter_order_type_permission_reads_session_actor_and_named_procedure"]
        ),
        "r079_integrated_without_count_inflation": (
            (ROOT / SOURCES["sql_boundary"]).as_posix() in risk["evidence_refs"]
            and (ROOT / SOURCES["runtime_boundary"]).as_posix() in risk["evidence_refs"]
            and any("ConvertOrderToSale" in item for item in risk["controls"])
            and risks["summary"]["risk_count"] == 84
            and risks["source_checkpoint"]["order_sale_authorization_sql_module_count"] == 4
            and risks["source_checkpoint"]["order_sale_authorization_order_type_ui_callsite_count"] == 10
        ),
        "register_trace_and_previous_chain": (
            previous["validation"] == "PASS"
            and previous["summary"]["risk_count"] == 84
            and trace["summary"]["unique_risk_count"] == 84
            and trace["summary"]["mapped_risk_assignment_count"] == 343
            and trace["summary"]["command_ready_module_count"] == 0
        ),
        "no_uuid_secret": (
            re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", raw) is None
            and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest = [
        {"name": name, "path": path, "size_bytes": (ROOT / path).stat().st_size, "sha256": _sha(ROOT / path)}
        for name, path in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_order_sale_authorization_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "selected_sql_module_count": sql["summary"]["selected_sql_module_count"],
            "selected_runtime_method_count": runtime["summary"]["selected_method_count"],
            "order_type_permission_ui_callsite_count": runtime["summary"]["order_type_permission_ui_callsite_count"],
            "current_global_area_gate_count": sql["summary"]["global_area_access_enabled_key_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
