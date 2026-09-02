"""Build an offline checkpoint for the NGT order-delete log correlation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "delete_log_boundary": "artifacts/varanegar_analysis/domains/ngt_order_delete_log_boundary_20260829.json",
    "deletion_boundary": "artifacts/varanegar_analysis/domains/ngt_order_target_deletion_boundary_20260829.json",
    "history_boundary": "artifacts/varanegar_analysis/domains/ngt_order_history_target_boundary_20260829.json",
    "deletion_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_order_deletion_checkpoint_20260829.json",
    "history_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_order_history_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "extractor": "scripts/sql/extract_varanegar_ngt_order_delete_log_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_order_delete_log_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_order_delete_log_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_ORDER_DELETE_LOG_CAUSAL_RECONCILIATION_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    missing = [value for value in SOURCES.values() if not (ROOT / value).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    boundary = _load("delete_log_boundary")
    deletion = _load("deletion_boundary")
    history = _load("history_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    summary = boundary["summary"]
    match = boundary["missing_target_delete_match_contract"]
    chronology = boundary["history_delete_chronology_contract"]
    retained = boundary["retained_delete_log_contract"]
    origin = boundary["anonymous_origin_cardinality_and_concentration"]
    pathway = boundary["delete_pathway_fingerprint"]
    order_types = boundary["missing_target_order_type_partition"]
    sequences = {
        row["object_name"]: row for row in boundary["static_delete_sequence_contracts"]
    }
    r069 = next(row for row in risks["risks"] if row["id"] == "R-069")
    r070 = next(row for row in risks["risks"] if row["id"] == "R-070")
    privacy = (ROOT / SOURCES["delete_log_boundary"]).read_text(encoding="utf-8")
    checks = {
        "read_only_zero_execution": boundary["validation"] == "PASS"
        and boundary["safety"]["database_updateability"] == "READ_ONLY"
        and boundary["safety"]["can_update"] == 0
        and boundary["safety"]["stored_procedure_trigger_or_application_command_executions"] == 0,
        "redacted": boundary["safety"]["business_rows_or_identifiers_persisted"] == 0
        and boundary["safety"]["sql_definitions_persisted"] == 0
        and boundary["safety"]["app_user_host_or_session_values_persisted"] == 0,
        "trigger_exact_key_contract": all(
            boundary["delete_trigger_contract"][key]
            for key in (
                "reads_deleted_id",
                "operation_type_delete_literal",
                "operation_table_target_literal",
                "operation_id_from_deleted_record",
                "canonical_delete_script_signal",
                "calls_insert_to_log",
            )
        ),
        "log_key_and_time_schema": all(
            boundary["log_schema_contract"][key]
            for key in (
                "has_operation_type",
                "has_operation_table",
                "has_operation_id",
                "has_transaction_date",
                "operation_table_id_index_present",
            )
        ),
        "retained_delete_shape": retained["retained_delete_log_count"] == 1907
        and retained["distinct_delete_target_count"] == 1907
        and retained["canonical_delete_script_count"] == 1907,
        "all_missing_targets_match": match["missing_target_count"] == 1024
        and match["missing_with_delete_log_count"] == 1024
        and match["missing_without_delete_log_count"] == 0
        and match["matching_delete_log_count"] == 1024,
        "all_missing_lines_covered": match["missing_history_line_count"] == 5533
        and history["order_history_contract"]["missing_target_history_count"] == 5533,
        "all_deletes_after_history": chronology["delete_at_or_after_last_history_count"] == 1024
        and chronology["delete_before_first_history_count"] == 0
        and chronology["delete_between_history_count"] == 0,
        "lag_partition": chronology["same_day_count"] == 298
        and chronology["lag_1_7_day_count"] == 534
        and chronology["lag_8_30_day_count"] == 192
        and chronology["lag_over_30_day_count"] == 0,
        "recent_matched_deletes": match["recent_missing_target_delete_count"] == 115,
        "retained_partition": boundary["retained_delete_partition"][
            "retained_delete_id_count"
        ] == 1907
        and boundary["retained_delete_partition"]["id_currently_present_count"] == 0
        and boundary["retained_delete_partition"]["missing_type1_target_count"] == 1024,
        "monthly_partition": len(boundary["monthly_matched_delete_counts"]) == 24
        and sum(
            row["matched_delete_count"] for row in boundary["monthly_matched_delete_counts"]
        ) == 1024,
        "origin_anonymized": origin["row_count"] == 1024
        and origin["distinct_app_count"] == 23
        and origin["distinct_host_count"] == 25
        and origin["distinct_session_count"] == 466,
        "logged_item_visit_header_tail": pathway["item_before_visit_before_header_count"]
        == 1024
        and pathway["visit_before_item_before_header_count"] == 0
        and pathway["immediately_preceding_visit_count"] == 1008
        and pathway["non_adjacent_preceding_visit_count"] == 16,
        "static_route_narrowing": sequences["NGT_RollBackTour"][
            "visit_before_item_before_header"
        ]
        and sequences["NGT_RollBackTour"]["tour_history_delete_follows_order_header"]
        and sequences["usp_sdsnet_Order_Delete"]["item_before_visit_before_header"]
        and "visit_order"
        not in sequences["USP_sdsnet_UndoUserExtraInfo"]["delete_target_sequence"]
        and sequences["usp_sdsnet_ConfirmFreeInvoice"]["sale_delete_precedes_order_item"]
        and pathway["preceding_sale_header_delete_signal_count"] == 0,
        "order_type_partition": order_types["target_count"] == 1024
        and order_types["parent_count"] == 1022
        and order_types["free_invoice_true_target_count"] == 524
        and order_types["free_invoice_true_parent_count"] == 522
        and order_types["free_invoice_false_target_count"] == 7
        and order_types["free_invoice_null_target_count"] == 493,
        "deletion_surface_consistent": deletion["summary"]["direct_delete_module_count"] == 4
        and deletion["summary"]["active_delete_trigger_count"] == 3,
        "r069_proves_delete_not_route": "This proves target deletion after replication"
        in r069["failure_mode"]
        and "does not identify the calling procedure" in r069["failure_mode"],
        "r070_proves_gap_not_attribution": "exactly matches all 1,024" in r070["failure_mode"]
        and "does not attribute any current missing target" in r070["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            privacy,
        ) is None,
    }
    failed = sorted(key for key, value in checks.items() if not value)
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
        "artifact": "varanegar_ngt_order_delete_log_checkpoint_20260829",
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
            "business_rows_configuration_values_or_identifiers_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "retained_delete_log_count": summary["retained_order_delete_log_count"],
            "matched_missing_target_count": summary[
                "missing_target_with_exact_delete_log_count"
            ],
            "delete_after_history_count": summary["delete_after_last_history_count"],
            "recent_matched_delete_count": summary[
                "recent_three_month_matched_delete_target_count"
            ],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "high_risk_count": risks["summary"]["high_count"],
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
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
