"""Build an offline checkpoint for the NGT order-target deletion boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "deletion_boundary": "artifacts/varanegar_analysis/domains/ngt_order_target_deletion_boundary_20260829.json",
    "history_boundary": "artifacts/varanegar_analysis/domains/ngt_order_history_target_boundary_20260829.json",
    "history_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_order_history_checkpoint_20260829.json",
    "compensation_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_replication_compensation_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "extractor": "scripts/sql/extract_varanegar_ngt_order_target_deletion_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_order_deletion_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_order_target_deletion_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_ORDER_TARGET_DELETION_AND_TOMBSTONE_BOUNDARY_20260829_FA.md",
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
    boundary = _load("deletion_boundary")
    history = _load("history_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    summary = boundary["summary"]
    direct = boundary["direct_delete_module_profiles"]
    risk = next(row for row in risks["risks"] if row["id"] == "R-070")
    privacy = (ROOT / SOURCES["deletion_boundary"]).read_text(encoding="utf-8")
    checks = {
        "read_only_zero_execution": boundary["validation"] == "PASS"
        and boundary["safety"]["database_updateability"] == "READ_ONLY"
        and boundary["safety"]["can_update"] == 0
        and boundary["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "redacted": boundary["safety"]["business_rows_or_identifiers_persisted"] == 0
        and boundary["safety"]["sql_definitions_persisted"] == 0,
        "four_direct_delete_procedures": summary["module_referencing_target_count"] == 404
        and summary["direct_delete_module_count"] == 4
        and summary["executable_static_delete_candidate_count"] == 4,
        "only_rollback_knows_history": sum(row["tour_history_signal"] for row in direct) == 1
        and next(row for row in direct if row["tour_history_signal"])["object_name"]
        == "NGT_RollBackTour",
        "no_direct_crosswalk_reconciliation": summary["direct_delete_with_ngt_line_count"] == 0
        and summary["direct_delete_with_crosswalk_count"] == 0,
        "transaction_shape": summary["direct_delete_with_transaction_count"] == 3
        and summary["direct_delete_with_try_catch_count"] == 3
        and summary["direct_delete_with_xact_abort_count"] == 0,
        "three_active_delete_triggers": summary["active_delete_trigger_count"] == 3,
        "triggers_not_ngt_aware": summary["active_delete_trigger_with_replication_log_count"] == 1
        and summary["active_delete_trigger_with_ngt_crosswalk_count"] == 0
        and summary["active_delete_trigger_with_tour_history_count"] == 0,
        "no_system_tombstone": boundary["table_features"]["temporal_type_desc"]
        == "NON_TEMPORAL_TABLE"
        and not boundary["table_features"]["is_tracked_by_cdc"]
        and boundary["table_features"]["change_tracking_enabled"] == 0,
        "foreign_key_shape": summary["referencing_foreign_key_count"] == 12
        and summary["no_action_delete_foreign_key_count"] == 11
        and summary["cascade_delete_foreign_key_count"] == 1,
        "one_catalog_caller": summary["direct_delete_caller_count"] == 1,
        "current_missing_population": history["order_history_contract"]["missing_target_history_count"]
        == 5533,
        "r070_high_and_caveated": risk["severity"] == "HIGH"
        and "does not attribute any current missing target" in risk["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
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
        "artifact": "varanegar_ngt_order_deletion_checkpoint_20260829",
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
            "referencing_module_count": summary["module_referencing_target_count"],
            "direct_delete_procedure_count": summary["direct_delete_module_count"],
            "active_delete_trigger_count": summary["active_delete_trigger_count"],
            "ngt_aware_delete_procedure_count": summary[
                "direct_delete_with_tour_history_count"
            ],
            "risk_count": risks["summary"]["risk_count"],
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
