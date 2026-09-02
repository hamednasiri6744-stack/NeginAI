"""Build the order-to-sale policy-flag and partial-conversion checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/order_sale_policy_flag_sql_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/order_sale_policy_flag_runtime_20260829.json",
    "gate_boundary": "artifacts/varanegar_analysis/domains/order_sale_policy_gate_runtime_20260829.json",
    "config_snapshot": "artifacts/varanegar_analysis/domains/order_sale_policy_config_snapshot_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_idempotency_guard_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_order_sale_policy_flag_sql.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_order_sale_policy_flag_runtime.py",
    "gate_extractor": "scripts/sql/extract_varanegar_order_sale_policy_gate_runtime.py",
    "config_extractor": "scripts/sql/extract_varanegar_order_sale_policy_config_snapshot.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_order_sale_policy_flag_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_order_sale_policy_flag_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_POLICY_OVERRIDE_AND_PARTIAL_CONVERSION_BOUNDARY_20260829_FA.md",
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
    gate = _load("gate_boundary")
    config = _load("config_snapshot")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    sql_raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    runtime_raw = (ROOT / SOURCES["runtime_boundary"]).read_text(encoding="utf-8")
    gate_raw = (ROOT / SOURCES["gate_boundary"]).read_text(encoding="utf-8")
    config_raw = (ROOT / SOURCES["config_snapshot"]).read_text(encoding="utf-8")
    semantics = {row["policy"]: row for row in sql["semantic_contracts"]}
    checks = {
        "sql_read_only_redacted": (
            sql["validation"] == "PASS"
            and sql["safety"]["connection_readonly"]
            and sql["safety"]["operational_stored_procedure_executions"] == 0
            and sql["safety"]["raw_definition_lines_or_string_literals_persisted"] == 0
            and sql["safety"]["source_or_target_state_changed"] == 0
        ),
        "runtime_static_hash_pinned": (
            runtime["validation"] == "PASS"
            and runtime["summary"]["assembly_count"] == 3
            and runtime["summary"]["source_hash_mismatch_count"] == 0
            and runtime["safety"]["assembly_loads_or_executions"] == 0
            and runtime["safety"]["application_form_or_command_executions"] == 0
        ),
        "partial_stock_contract": (
            semantics["STOCK_SHORTAGE"]["caller_override_value"] == 1
            and semantics["STOCK_SHORTAGE"]["effect"]
            == "REMOVE_SHORT_ITEMS_FROM_TEMP_CONVERSION_SET_AND_CONTINUE_IF_ANY_ITEM_REMAINS"
            and semantics["STOCK_SHORTAGE"]["not_equivalent_to"]
            == "UNCONDITIONAL_STOCK_VALIDATION_BYPASS"
            and sql["semantic_assertions"]["stock_checker_rejects_when_no_conversion_item_remains"]
        ),
        "price_credit_limit_contract": (
            semantics["CUSTOMER_CREDIT"]["caller_override_value"] == [1, 1]
            and semantics["DEALER_CREDIT"]["caller_override_value"] == [1, 1]
            and semantics["USER_PRICE"]["independent_check_remaining"]
            == "ORDER_ITEM_PRICE_CHECK_BEFORE_FLAG_BRANCH"
            and semantics["CUSTOMER_MAXIMUM_LIMIT"]["caller_override_value"] == 1
            and all(sql["semantic_assertions"].values())
        ),
        "declared_only_and_rollback_caveat": (
            sql["summary"]["wrapper_declared_but_not_used_after_declaration_count"] == 1
            and semantics["EXPIRY_VALIDATION"]["effect"]
            == "DECLARED_ONLY_NO_RUNTIME_SQL_EFFECT_PROVEN_IN_CURRENT_WRAPPER"
            and semantics["ROLLBACK_MODE"]["not_equivalent_to"] == "DISABLE_ALL_ROLLBACK_BRANCHES"
        ),
        "caller_source_contract": (
            runtime["summary"]["matched_method_count"] == 9
            and runtime["summary"]["flag_with_runtime_member_reference_count"] == 8
            and runtime["summary"]["flag_without_runtime_member_reference_count"] == 2
            and runtime["assertions"]["form_sale_save_sets_stock_cprice_and_price_flags"]
            and runtime["assertions"]["runtime_route_markers_are_observed"]
        ),
        "three_state_gate_contract": (
            gate["validation"] == "PASS"
            and gate["summary"]["policy_control_count"] == 6
            and gate["assertions"]["five_credit_or_limit_controls_have_0_bypass_1_user_choice_2_enforced_mapping"]
            and gate["assertions"]["stock_control_has_0_user_choice_1_forced_partial_2_enforced_mapping"]
            and gate["assertions"]["six_policy_config_getters_return_nonnullable_cli_int32"]
        ),
        "selected_permission_method_is_not_policy_authorization": (
            gate["selected_permission_method_contract"]["named_permission_decision_calls"] == []
            and gate["selected_permission_method_contract"]["observed_inputs"]
            == ["SERVER_CONFIG_SITE_TYPE", "USER_SESSION_DCREF"]
            and gate["selected_permission_method_contract"]["observed_target"]
            == "MENU_BUTTON_SELECT_ENABLED"
            and not gate["selected_permission_method_contract"]["form_or_menu_open_authorization_outside_selected_method_proven"]
        ),
        "current_anonymous_config_and_null_boundary": (
            config["validation"] == "PASS"
            and config["summary"]["config_row_count"] == 2
            and config["summary"]["dc_count"] == 2
            and config["summary"]["distinct_policy_profile_count"] == 2
            and config["summary"]["profile_row_with_null_policy_count"] == 1
            and config["summary"]["null_policy_cell_count"] == 5
            and config["null_semantic_boundary"]["ui_materializer_null_to_int32_behavior"]
            == "NOT_PROVEN"
        ),
        "r079_integrated_without_count_inflation": (
            risk["severity"] == "CRITICAL"
            and (ROOT / SOURCES["sql_boundary"]).as_posix() in risk["evidence_refs"]
            and (ROOT / SOURCES["runtime_boundary"]).as_posix() in risk["evidence_refs"]
            and (ROOT / SOURCES["gate_boundary"]).as_posix() in risk["evidence_refs"]
            and (ROOT / SOURCES["config_snapshot"]).as_posix() in risk["evidence_refs"]
            and any("chkNot*" in item for item in risk["controls"])
            and any("partial conversion" in item for item in risk["controls"])
            and risks["summary"]["risk_count"] == 84
            and risks["summary"]["critical_count"] == 50
        ),
        "register_trace_and_previous_chain": (
            previous["validation"] == "PASS"
            and previous["summary"]["risk_count"] == 84
            and risks["source_checkpoint"]["order_sale_policy_selected_sql_command_count"] == 3
            and risks["source_checkpoint"]["order_sale_policy_declared_only_wrapper_flag_count"] == 1
            and risks["source_checkpoint"]["order_sale_policy_gate_configured_control_count"] == 6
            and risks["source_checkpoint"]["order_sale_policy_current_null_cell_count"] == 5
            and trace["summary"]["unique_risk_count"] == 84
            and trace["summary"]["mapped_risk_assignment_count"] == 343
            and trace["summary"]["command_ready_module_count"] == 0
        ),
        "no_uuid_secret": (
            re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", sql_raw + runtime_raw + gate_raw + config_raw) is None
            and re.search(r"(?i)(password|pwd)\s*[=:]", sql_raw + runtime_raw + gate_raw + config_raw) is None
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
        "artifact": "varanegar_order_sale_policy_flag_checkpoint_20260829",
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
            "selected_sql_command_count": sql["summary"]["selected_command_count"],
            "selected_policy_contract_count": len(sql["semantic_contracts"]),
            "runtime_matched_method_count": runtime["summary"]["matched_method_count"],
            "runtime_referenced_flag_count": runtime["summary"]["flag_with_runtime_member_reference_count"],
            "configured_policy_control_count": gate["summary"]["policy_control_count"],
            "current_null_policy_cell_count": config["summary"]["null_policy_cell_count"],
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
