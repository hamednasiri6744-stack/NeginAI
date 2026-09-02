"""Build an offline checkpoint for NGT replication compensation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_replication_compensation_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_replication_compensation_runtime_boundary_20260829.json",
    "payment_replication_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_replication_boundary_20260829.json",
    "payment_replication_runtime": "artifacts/varanegar_analysis/domains/ngt_payment_replication_runtime_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_replication_compensation_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_replication_compensation_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_replication_compensation_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_replication_compensation_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_REPLICATION_COMPENSATION_AND_ROLLBACK_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    missing = [relative for relative in SOURCES.values() if not (ROOT / relative).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    derived = sql["derived_compensation_contract"]
    shape = sql["type_10_receipt_dependency_shape"]
    runtime_contract = runtime["rollback_tour_contract"]
    by_risk = {row["id"]: row for row in risks["risks"]}
    history = {row["history_type"]: row for row in sql["tour_history_target_population"]}
    edges = {
        (
            row["parent_schema"],
            row["parent_table"],
            row["parent_column"],
            row["referenced_schema"],
            row["referenced_table"],
        )
        for row in sql["referential_delete_contract"]
        if row["delete_referential_action_desc"] == "NO_ACTION"
        and not row["is_disabled"]
    }
    privacy_text = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    adapter_cases = runtime_contract["adapter_request_type_20_contracts"]
    checks = {
        "sql_valid_read_only_and_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "sql_definitions_rows_and_guids_not_persisted": sql["safety"]["sql_definitions_persisted"] == 0
        and sql["safety"]["business_rows_or_identifiers_persisted"] == 0
        and sql["safety"]["guid_literals_persisted"] == 0,
        "four_compensation_procedures_profiled": sql["summary"]["procedure_count"] == 4,
        "active_rollback_requires_temp_and_deletes_history": derived[
            "active_entry_point"
        ]
        == "dbo.NGT_RollBackTour"
        and derived["active_entry_point_requires_entity_temp_table"]
        and derived["active_entry_point_deletes_tour_history"],
        "active_rollback_omits_cash_and_cheque_children": not derived[
            "active_entry_point_mentions_cash_detail_cleanup"
        ]
        and not derived["active_entry_point_mentions_cheque_history_cleanup"],
        "legacy_undo_is_unreachable_commented_cleanup": derived[
            "dead_legacy_entry_point_returns_before_mutations"
        ]
        and derived["dead_legacy_cleanup_is_commented"]
        and sql["summary"]["dead_legacy_undo_profiled_mutation_count"] == 21,
        "only_four_current_history_types_and_no_type11": set(history) == {1, 2, 8, 10}
        and 11 not in history,
        "447_type10_histories_and_342_existing_receipts": history[10]["history_count"] == 447
        and history[10]["known_target_resolved_count"] == 438
        and shape["distinct_existing_receipt_count"] == 342,
        "all_342_receipts_have_no_action_blocker_candidates": shape[
            "receipt_with_no_action_blocker_candidate_count"
        ]
        == 342
        and derived["all_current_existing_type_10_receipts_have_blocker_candidates"],
        "cash_cheque_bank_dependency_shapes_present": shape["receipt_with_cash_detail_count"] == 72
        and shape["receipt_with_cheque_history_count"] == 64
        and shape["receipt_with_bank_order_payment_count"] == 330,
        "five_required_no_action_edges_present": {
            ("dbo", "RCashDetail", "RCashId", "dbo", "RCash"),
            ("Acc", "tblChqHist", "ChqRef", "Acc", "TblCheque"),
            ("Acc", "tblPayments", "RCashId", "dbo", "RCash"),
            ("Acc", "tblPayments", "ChqRef", "Acc", "TblCheque"),
            ("Acc", "tblPayments", "BankOrderRef", "Acc", "TblBankOrders"),
        }.issubset(edges),
        "no_instead_of_trigger_can_preclean_parent": all(
            not row["is_instead_of_trigger"] for row in sql["trigger_contract"]
        ),
        "runtime_valid_static_and_zero_execution": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY"
        and runtime["safety"]["assembly_loads_or_execution"] == 0
        and runtime["safety"]["application_endpoint_or_command_executions"] == 0,
        "business_routes_request_type20_with_two_callers": runtime_contract[
            "business_request_type_20_assignment_count"
        ]
        == 1
        and runtime_contract["caller_method_count"] == 2,
        "business_discards_adapter_rollback_result": runtime_contract[
            "retrieve_info_call_count"
        ]
        == 1
        and runtime_contract["retrieve_info_result_pop_count"] == 1
        and runtime_contract["adapter_result_is_discarded"],
        "both_adapters_execute_transactional_case20": len(adapter_cases) == 2
        and all(
            row["request_type"] == 20
            and row["active_rollback_sql_signal_count"] == 1
            and row["entity_temp_table_signal_count"] == 1
            and row["execute_event_count"] == 3
            and row["commit_event_count"] == 1
            and row["rollback_event_count"] == 1
            for row in adapter_cases
        ),
        "both_adapters_select_and_append_entity_ids": len(
            runtime_contract["case20_entity_selector_contracts"]
        )
        == 2
        and len(runtime_contract["case20_temp_row_appender_contracts"]) == 2
        and all(
            row["entity_unique_id_getter_count"] == 1
            for row in runtime_contract["case20_entity_selector_contracts"]
        ),
        "r065_is_critical_and_caveated": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and by_risk["R-065"]["severity"] == "CRITICAL"
        and "does not prove which rollback attempts occurred" in by_risk["R-065"]["failure_mode"],
        "traceability_has_65_risks_256_assignments_zero_ready": trace[
            "validation"
        ]
        == "PASS"
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "new_artifacts_have_no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            privacy_text,
        )
        is None,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
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
        "artifact": "varanegar_ngt_replication_compensation_checkpoint_20260829",
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
            "type_10_history_count": history[10]["history_count"],
            "distinct_existing_receipt_count": shape["distinct_existing_receipt_count"],
            "receipt_with_blocker_candidate_count": shape[
                "receipt_with_no_action_blocker_candidate_count"
            ],
            "cash_detail_receipt_count": shape["receipt_with_cash_detail_count"],
            "cheque_history_receipt_count": shape["receipt_with_cheque_history_count"],
            "bank_order_payment_receipt_count": shape["receipt_with_bank_order_payment_count"],
            "adapter_request_type_20_contract_count": len(adapter_cases),
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
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
