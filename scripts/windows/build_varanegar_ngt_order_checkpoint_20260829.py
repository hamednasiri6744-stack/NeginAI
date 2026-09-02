"""Build an offline hash-pinned checkpoint for NGT order persistence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_order_runtime_boundary_20260829.json",
    "authorization_endpoints": "artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json",
    "authorization_manual_guards": "artifacts/varanegar_analysis/domains/ngt_authorization_manual_guard_boundary_20260829.json",
    "prior_order_lifecycle": "artifacts/varanegar_analysis/domains/order_sale_lifecycle_20260826.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_order_persistence_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_order_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_order_checkpoint_20260829.py",
    "order_tests": "tests/test_varanegar_ngt_order_boundary.py",
    "order_doc": "docs/varanegar_reconstruction/NGT_ORDER_PERSISTENCE_REPLICATION_AND_CROSSWALK_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "reconstruction_readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    missing = [value for value in SOURCES.values() if not (ROOT / value).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    endpoints = _load("authorization_endpoints")
    guards = _load("authorization_manual_guards")
    risks = _load("risk_register")
    trace = _load("traceability")

    sql_summary = sql["summary"]
    runtime_summary = runtime["summary"]
    header = sql["header_state_contract"]
    header_aggregate = header["aggregate"]
    duplicates = header["duplicate_crosswalk_groups"]
    line = sql["line_persistence_contract"]
    line_aggregate = line["aggregate"]
    parent_groups = line["parent_mapping_groups"]
    matrix = {
        (row["has_numeric_header_order_id"], row["active_line_mapping_state"]): row
        for row in line["header_line_mapping_matrix"]
    }
    strategies = {
        row["mapping_strategy"]: row
        for row in sql["crosswalk_mapping_strategy_timeline"]["all_time"]
    }
    window = sql["crosswalk_mapping_strategy_timeline"]["window_month_buckets"]
    procedure = sql["replication_procedure_contract"]
    procedure_profile = next(
        row
        for row in sql["target_sql_module_profiles"]
        if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    orchestration = runtime["key_orchestration_contract"]
    order_endpoint = next(
        row
        for row in endpoints["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.OrderController"
        and row["method"] == "RequestSaveTourData"
    )
    order_guard = next(
        row
        for row in guards["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.OrderController"
        and row["method"] == "RequestSaveTourData"
    )
    risk = next((row for row in risks["risks"] if row["id"] == "R-033"), None)

    months_have_both_shapes = all(
        {row["mapping_strategy"] for row in window if row["month_bucket"] == month}
        >= {"ALL_ACTIVE_LINES_ONLY", "HEADER_NUMERIC_ONLY"}
        for month in ("2026-06", "2026-07", "2026-08")
    )

    checks = {
        "sql_artifact_valid_and_read_only": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["denies_data_writes"] == 1,
        "sql_executed_no_procedure_or_command": sql["safety"][
            "stored_procedure_or_application_command_executions"
        ]
        == 0,
        "sql_persisted_no_business_rows_or_definitions": sql["safety"][
            "business_rows_customer_user_configuration_values_or_identifiers_persisted"
        ]
        == 0
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "seven_tables_and_313_columns": sql_summary["target_table_count"] == 7
        and sql_summary["catalog_column_count"] == 313,
        "228284_headers_and_1239998_lines": sql_summary["order_header_count"]
        == 228284
        and sql_summary["order_line_count"] == 1239998,
        "status_table_currently_empty": sql_summary["order_status_event_count"] == 0,
        "six_id_only_unique_or_primary_indexes": sql_summary[
            "unique_or_primary_index_count"
        ]
        == 6
        and all(row["key_columns"] == ["Id"] for row in sql["target_unique_index_contracts"]),
        "status_and_crosswalk_have_no_unique_key": not any(
            row["qualified_table"] == "NGT.CustomerCallOrderStatus"
            for row in sql["target_unique_index_contracts"]
        ),
        "61_enabled_but_untrusted_related_foreign_keys": sql_summary[
            "related_foreign_key_edge_count"
        ]
        == 61
        and sql_summary["untrusted_related_foreign_key_edge_count"] == 61
        and all(not row["is_disabled"] and row["is_not_trusted"] for row in sql["related_foreign_key_contracts"]),
        "current_header_state_218489_sent_and_9795_numeric": header_aggregate[
            "sent_to_console_count"
        ]
        == 218489
        and header_aggregate["backoffice_order_id_count"] == 9795,
        "header_order_uuid_is_absent": header_aggregate[
            "backoffice_order_uuid_count"
        ]
        == 0,
        "header_invoice_uuid_is_partial": header_aggregate[
            "backoffice_invoice_id_count"
        ]
        == 9795
        and header_aggregate["backoffice_invoice_uuid_count"] == 3593,
        "header_numeric_crosswalk_is_not_unique": duplicates[
            "duplicate_numeric_backoffice_order_id_group_count"
        ]
        == 1125
        and duplicates["headers_in_duplicate_numeric_order_id_groups"] == 3385
        and duplicates["maximum_headers_per_numeric_backoffice_order_id"] == 13,
        "line_crosswalk_is_complete_when_numeric": line_aggregate[
            "numeric_backoffice_order_ref_count"
        ]
        == 1118244
        and line_aggregate["backoffice_order_uuid_count"] == 1118244
        and line_aggregate["numeric_ref_without_uuid_count"] == 0,
        "current_order_parent_integrity_has_zero_orphans_or_scope_mismatches": line_aggregate[
            "orphan_line_count"
        ]
        == 0
        and line_aggregate["active_line_under_removed_header_count"] == 0
        and line_aggregate["parent_scope_mismatch_count"] == 0,
        "212231_line_only_and_9795_header_only_orders": matrix[(0, "ALL_MAPPED")][
            "order_count"
        ]
        == 212231
        and matrix[(1, "NONE_MAPPED")]["order_count"] == 9795,
        "partial_and_split_crosswalk_exist": parent_groups[
            "partially_mapped_order_count"
        ]
        == 1
        and parent_groups["split_backoffice_order_count"] == 7
        and parent_groups["maximum_backoffice_orders_per_ngt_order"] == 2,
        "four_mapping_strategies_are_counted": set(strategies)
        == {
            "ALL_ACTIVE_LINES_ONLY",
            "HEADER_NUMERIC_ONLY",
            "NO_NUMERIC_CROSSWALK",
            "PARTIAL_ACTIVE_LINES_ONLY",
        },
        "header_and_line_strategies_coexist_in_three_month_window": months_have_both_shapes,
        "quantity_children_have_current_parent_and_scope_integrity": all(
            row["orphan_line_count"] == 0
            and row["active_detail_under_removed_line_count"] == 0
            and row["parent_scope_mismatch_count"] == 0
            for row in sql["quantity_detail_contracts"]
        ),
        "replication_procedure_has_five_fingerprinted_parameters": [
            row["parameter_name"] for row in procedure["parameters"]
        ]
        == ["@TourId", "@DataOwnerCenterId", "@AppUserUniqueId", "@PreviewOrderMode", "@OrderGuid"],
        "replication_procedure_not_executed_and_result_contract_is_unresolved": procedure[
            "result_set_contract"
        ][0]["error_number"]
        == 229
        and sql["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "replication_procedure_transaction_tokens_are_caveated": procedure_profile[
            "definition_length"
        ]
        == 61020
        and procedure_profile["begin_transaction_token_count"] == 1
        and procedure_profile["commit_token_count"] == 0
        and procedure_profile["rollback_token_count"] == 1,
        "runtime_artifact_valid_and_static": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY",
        "runtime_did_not_execute_or_read_configuration_or_business_rows": runtime[
            "safety"
        ]["assemblies_loaded_or_executed"]
        == 0
        and runtime["safety"]["application_endpoints_or_commands_called"] == 0
        and runtime["safety"]["configuration_files_or_values_read"] == 0
        and runtime["safety"]["business_rows_or_identifiers_read"] == 0,
        "runtime_scanned_four_assemblies_and_27788_methods": runtime_summary[
            "assembly_count"
        ]
        == 4
        and runtime_summary["method_body_count"] == 27788,
        "save_tour_data_owns_outer_transaction_and_calls_replication_four_times": orchestration[
            "save_tour_data"
        ]["begin_transaction_call_count"]
        == 1
        and orchestration["save_tour_data"]["commit_call_count"] == 1
        and orchestration["save_tour_data"]["rollback_call_count"] == 2
        and orchestration["save_tour_data"]["replicate_tour_call_count"] == 4,
        "replicate_tour_has_backoffice_and_new_replication_stages": orchestration[
            "replicate_tour"
        ]["new_replicate_tour_call_count"]
        == 1
        and orchestration["replicate_tour"]["replicate_to_backoffice_call_count"] == 2,
        "new_replicate_tour_references_expected_sql_procedure": orchestration[
            "new_replicate_tour"
        ]["safe_sql_object_references"]
        == ["dbo.NGT_DoReplicateTour"],
        "update_path_has_five_save_stages_without_local_begin": orchestration[
            "update_order_from_ngt"
        ]["save_changes_call_count"]
        == 5
        and orchestration["update_order_from_ngt"]["begin_transaction_call_count"] == 0,
        "status_writer_is_transactional_but_current_table_is_empty": orchestration[
            "order_status_writer"
        ]["direct_static_caller_count"]
        == 1
        and orchestration["order_status_writer"]["begin_transaction_call_count"] == 1
        and orchestration["order_status_writer"]["commit_call_count"] == 1
        and sql_summary["order_status_event_count"] == 0,
        "order_save_post_has_no_endpoint_authorization_declaration": order_endpoint[
            "http_verbs"
        ]
        == ["POST"]
        and order_endpoint["ngt_authorize_attribute_count"] == 0
        and not order_endpoint["standard_authorize_declared_or_inherited"]
        and not order_endpoint["claims_authorize_declared_or_inherited"]
        and not order_endpoint["allow_anonymous_declared_or_inherited"],
        "order_save_body_has_identity_context_not_manual_authorization_decision": not order_guard[
            "manual_authorization_decision_candidate"
        ]
        and order_guard["identity_context_only_candidate"],
        "risk_register_valid_65": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50,
        "risk_033_absorbs_order_evidence_and_keeps_incident_caveat": risk is not None
        and risk["severity"] == "CRITICAL"
        and "212,231 NGT orders are fully mapped only through active lines" in risk["failure_mode"]
        and "a current partial-write incident is not asserted" in risk["failure_mode"],
        "traceability_valid_256": trace["validation"] == "PASS"
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["unique_risk_count"] == 84,
        "zero_command_ready_modules": trace["summary"]["command_ready_module_count"] == 0,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    manifest = [
        {
            "name": name,
            "path": relative,
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_ngt_order_checkpoint_20260829",
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
            "configuration_values_business_rows_or_identifiers_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "order_header_count": sql_summary["order_header_count"],
            "order_line_count": sql_summary["order_line_count"],
            "line_only_mapped_order_count": matrix[(0, "ALL_MAPPED")]["order_count"],
            "header_only_mapped_order_count": matrix[(1, "NONE_MAPPED")]["order_count"],
            "partially_mapped_order_count": parent_groups["partially_mapped_order_count"],
            "split_backoffice_order_count": parent_groups["split_backoffice_order_count"],
            "runtime_mutation_method_count": runtime_summary["mutation_method_count"],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
