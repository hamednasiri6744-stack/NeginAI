"""Build the offline received-cheque and receipt deletion checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/received_cheque_delete_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/received_cheque_delete_runtime_boundary_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_received_cheque_undo_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_received_cheque_delete_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_received_cheque_delete_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_received_cheque_delete_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_received_cheque_delete_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/RECEIVED_CHEQUE_AND_RECEIPT_DELETION_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    contract = sql["static_delete_contract"]
    managed = runtime["managed_delete_contract"]
    coverage = sql["retained_master_lifecycle_log"]["logged_id_coverage"]
    fk_actions = {
        row["delete_referential_action_desc"]
        for row in sql["storage_contract"]["incoming_foreign_keys"]
    }
    r075 = next(row for row in risks["risks"] if row["id"] == "R-075")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_and_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"][
            "cheque_receipt_customer_amount_bank_comment_operator_or_log_script_values_persisted"
        ]
        == 0
        and sql["safety"]["sql_definitions_or_log_ids_persisted"] == 0,
        "static_candidate_population": sql["summary"]["selected_sql_module_count"] == 10
        and sql["summary"]["direct_master_delete_candidate_count"] == 7
        and contract["all_expected_direct_candidates_delete_master"],
        "direct_delete_route_separation": contract[
            "usp_chq_delete_validates_then_owns_atomic_history_master_delete"
        ]
        and contract["view_delete_trigger_directly_deletes_master_without_history_or_receipt"]
        and contract["receipt_save_owns_transaction_or_savepoint"]
        and contract["receipt_save_has_history_master_receipt_delete_sequence"]
        and contract["receipt_save_calls_before_rcheque"],
        "master_delete_population": sql["summary"]["retained_master_delete_event_count"] == 31
        and sql["summary"]["recent_master_delete_event_count"] == 11,
        "master_delete_current_absence_parity": coverage["logged_id_count"] == 8261
        and coverage["currently_present_count"] == 8230
        and coverage["currently_absent_count"] == 31
        and coverage["both_event_count"] == 31
        and coverage["insert_only_but_absent_count"] == 0
        and coverage["deleted_but_present_count"] == 0,
        "tail_partition": sql["summary"]["receipt_delete_tail_master_count"] == 23
        and sql["summary"]["receipt_update_tail_master_count"] == 7
        and sql["summary"]["isolated_tail_master_count"] == 1
        and sql["summary"]["master_delete_without_history_lookback_count"] == 0,
        "receipt_delete_batch_cardinality": sql["summary"]["receipt_delete_batch_count"] == 19
        and sql["summary"]["receipt_delete_tail_master_count"] == 23
        and sql["summary"]["receipt_delete_tail_history_count"] == 23,
        "receipt_delete_population": sql["summary"]["retained_receipt_delete_event_count"] == 2351
        and sql["summary"]["recent_receipt_delete_event_count"] == 238,
        "storage_non_temporal": len(sql["storage_contract"]["table_capabilities"]) == 5
        and all(
            row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
            and not row["is_tracked_by_cdc"]
            and row["change_tracking_enabled"] == 0
            for row in sql["storage_contract"]["table_capabilities"]
        ),
        "mixed_fk_delete_actions": fk_actions == {"NO_ACTION", "CASCADE"}
        and any(
            row["child_table"] == "tblRChequeLog"
            and row["delete_referential_action_desc"] == "CASCADE"
            for row in sql["storage_contract"]["incoming_foreign_keys"]
        ),
        "runtime_hash_and_coverage": runtime["validation"] == "PASS"
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["summary"]["selected_method_count"] == 2
        and runtime["summary"]["selected_instruction_count"] == 34,
        "runtime_legacy_delete_sequence": managed["legacy_delete_has_confirmation"]
        and managed["legacy_delete_marks_dataset_row_deleted"]
        and managed["legacy_delete_flushes_rcheque_dataset"]
        and managed["legacy_confirmation_precedes_row_delete_and_update_in_linear_il"]
        and not managed["legacy_delete_has_explicit_transaction_signal"],
        "runtime_new_form_and_limits": managed["new_delete_has_confirmation"]
        and not managed["new_delete_has_dataset_delete_or_update_signal"]
        and not managed["runtime_form_selection_proven"]
        and not managed["dataset_update_to_sql_trigger_branch_reachability_proven"],
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r075_registered_and_caveated": r075["severity"] == "HIGH"
        and "not proving its invocation" in r075["failure_mode"]
        and "attribution must not be fabricated" in r075["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_or_secret_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
        )
        is None
        and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None,
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
        "artifact": "varanegar_received_cheque_delete_checkpoint_20260829",
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
            "cheque_receipt_customer_amount_bank_comment_operator_or_log_id_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "retained_master_delete_count": sql["summary"]["retained_master_delete_event_count"],
            "recent_master_delete_count": sql["summary"]["recent_master_delete_event_count"],
            "receipt_delete_batch_count": sql["summary"]["receipt_delete_batch_count"],
            "receipt_delete_tail_master_count": sql["summary"]["receipt_delete_tail_master_count"],
            "receipt_update_tail_master_count": sql["summary"]["receipt_update_tail_master_count"],
            "isolated_tail_master_count": sql["summary"]["isolated_tail_master_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
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
    print(payload["validation"])
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
