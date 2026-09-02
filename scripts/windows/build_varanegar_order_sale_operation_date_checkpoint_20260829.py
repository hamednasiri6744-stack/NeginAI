"""Build the order-to-sale operation-date and finality checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/order_sale_operation_date_sql_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/order_sale_operation_date_runtime_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_order_sale_policy_flag_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_order_sale_operation_date_sql.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_order_sale_operation_date_runtime.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_order_sale_operation_date_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_order_sale_operation_date_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_OPERATION_DATE_AND_FINALITY_BOUNDARY_20260829_FA.md",
    "policy_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_POLICY_OVERRIDE_AND_PARTIAL_CONVERSION_BOUNDARY_20260829_FA.md",
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
    contracts = {row["boundary"]: row for row in sql["semantic_contracts"]}
    checks = {
        "sql_read_only_redacted": (
            sql["validation"] == "PASS"
            and sql["summary"]["selected_sql_module_count"] == 6
            and sql["safety"]["connection_readonly"]
            and sql["safety"]["operational_stored_procedure_executions"] == 0
            and sql["safety"]["raw_sql_definitions_messages_or_string_literals_persisted"] == 0
            and sql["safety"]["source_or_target_state_changed"] == 0
        ),
        "runtime_static_hash_pinned": (
            runtime["validation"] == "PASS"
            and runtime["summary"]["assembly_count"] == 2
            and runtime["summary"]["selected_method_count"] == 6
            and runtime["summary"]["source_hash_mismatch_count"] == 0
            and runtime["safety"]["assembly_loads_or_executions"] == 0
            and runtime["safety"]["form_or_application_command_executions"] == 0
        ),
        "standard_sale_finality": (
            sql["semantic_assertions"]["wrapper_forwards_create_sale_date_to_core"]
            and sql["semantic_assertions"]["core_uses_operation_date_for_price_and_open_date_checks"]
            and sql["semantic_assertions"]["date_open_rejects_closed_or_not_after_last_date"]
            and contracts["STANDARD_ORDER_DATE_FINALITY"]["applies_when"]
            == "ORDER_TYPE_NOT_IN_1007_1008"
        ),
        "special_and_missing_boundary_explicit": (
            sql["semantic_assertions"]["date_open_is_skipped_for_order_types_1007_and_1008"]
            and sql["semantic_assertions"]["missing_boundary_row_has_no_explicit_rejection"]
            and contracts["MISSING_OPERATION_DATE_ROW"]["effective_null_branch_behavior"]
            == "FAIL_OPEN_BY_SQL_THREE_VALUED_LOGIC"
            and sql["semantic_assertions"][
                "both_date_open_exception_types_are_configured_but_have_no_current_clone_instances"
            ]
            and sql["summary"]["configured_special_order_type_count"] == 2
            and sql["summary"]["current_special_order_count"] == 0
            and sql["summary"]["current_special_sale_count"] == 0
        ),
        "fetch_reason_two_cross_layer_mapping": (
            sql["semantic_assertions"]["fetch_reason_two_returns_last_date_then_operation_date"]
            and runtime["assertions"]["fetch_reason_two_outputs_last_date_then_operation_date"]
            and runtime["contract"]["fetch_reason_two_output_order"]
            == ["LAST_DATE", "OPERATION_DATE"]
            and runtime["assertions"]["automatic_session_assignment_uses_operation_date_second_output"]
            and len(runtime["contract"]["automatic_date_flows"]) == 2
        ),
        "session_route_and_permission_separation": (
            runtime["assertions"]["both_conversion_routes_use_session_operation_date_as_create_sale_date"]
            and runtime["contract"]["set_operation_date_permission_resource"] == "VN.SDS.Sales"
            and runtime["contract"]["set_operation_date_permission_action"] == "SetOprDate"
            and not runtime["contract"]["operation_date_permission_is_conversion_permission"]
            and not runtime["contract"]["server_command_revalidates_actor_set_operation_date_permission"]
        ),
        "current_anonymous_sale_boundary": (
            sql["summary"]["sale_boundary_row_count"] == 3
            and sql["summary"]["open_sale_boundary_row_count"] == 1
            and sql["summary"]["closed_sale_boundary_row_count"] == 2
            and sql["summary"]["missing_sale_oprdate_count"] == 0
            and sql["summary"]["orphan_dc_count"] == 0
        ),
        "r079_integrated_without_count_inflation": (
            (ROOT / SOURCES["sql_boundary"]).as_posix() in risk["evidence_refs"]
            and (ROOT / SOURCES["runtime_boundary"]).as_posix() in risk["evidence_refs"]
            and any("operation date" in item for item in risk["controls"])
            and risks["summary"]["risk_count"] == 84
            and risks["summary"]["critical_count"] == 50
            and risks["source_checkpoint"]["order_sale_operation_date_sql_module_count"] == 6
            and risks["source_checkpoint"]["order_sale_operation_date_automatic_flow_count"] == 2
            and risks["source_checkpoint"]["order_sale_operation_date_configured_special_type_count"] == 2
            and risks["source_checkpoint"]["order_sale_operation_date_current_special_order_count"] == 0
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
        {
            "name": name,
            "path": path,
            "size_bytes": (ROOT / path).stat().st_size,
            "sha256": _sha(ROOT / path),
        }
        for name, path in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_order_sale_operation_date_checkpoint_20260829",
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
            "automatic_operation_date_flow_count": len(runtime["contract"]["automatic_date_flows"]),
            "current_sale_boundary_row_count": sql["summary"]["sale_boundary_row_count"],
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
