"""Build an offline, hash-pinned checkpoint for the NGT return boundary."""

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
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_return_replication_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_return_runtime_boundary_20260829.json",
    "diagnostic": "artifacts/varanegar_analysis/ui/varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json",
    "compensation_boundary": "artifacts/varanegar_analysis/domains/ngt_replication_compensation_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_return_replication_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_return_runtime_boundary.py",
    "diagnostic_extractor": "scripts/sql/extract_varanegar_ngt_return_crosswalk_diagnostic_contract.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_return_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_return_replication_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_RETURN_REPLICATION_AND_INGEST_ATOMICITY_BOUNDARY_20260829_FA.md",
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
    contract = sql["replication_contract"]
    runtime_contract = runtime["return_runtime_contract"]
    by_risk = {row["id"]: row for row in risks["risks"]}
    profiles = {row["qualified_name"]: row for row in sql["procedure_profiles"]}
    privacy_text = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_valid_read_only_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "sql_rows_definitions_guids_not_persisted": sql["safety"][
            "business_rows_or_identifiers_persisted"
        ]
        == 0
        and sql["safety"]["sql_definitions_persisted"] == 0
        and sql["safety"]["guid_literals_persisted"] == 0,
        "four_return_procedures_profiled": sql["summary"]["procedure_count"] == 4,
        "do_replicate_is_transactional_and_caveated": profiles[
            "dbo.NGT_DoReplicateTour"
        ]["has_explicit_transaction"]
        and profiles["dbo.NGT_DoReplicateTour"]["has_try_catch"]
        and profiles["dbo.NGT_DoReplicateTour"]["has_explicit_rollback"],
        "sql_commit_precedes_return_order_writeback": contract[
            "do_replicate_tour_commits_before_return_order_writeback"
        ],
        "no_return_history_unique_guard": not contract[
            "return_tour_history_entity_unique_index_present"
        ],
        "no_return_line_crosswalk_unique_guard": not contract[
            "return_line_backoffice_crosswalk_unique_constraint_present"
        ],
        "two_active_lines_split_history_state": contract["active_return_line_count"] == 2
        and contract["active_line_without_history_count"] == 1
        and contract["active_line_with_history_count"] == 1,
        "historical_target_missing_and_no_current_order": contract[
            "historical_result_current_order_missing_count"
        ]
        == 1
        and contract["current_order_target_count"] == 0,
        "runtime_valid_static_zero_execution": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY"
        and runtime["safety"]["assembly_loads_or_execution"] == 0,
        "runtime_five_assemblies_no_body_errors": runtime["summary"]["assembly_count"] == 5
        and runtime["summary"]["method_body_error_count"] == 0,
        "replication_precedes_managed_transaction": runtime_contract[
            "new_replication_call_precedes_managed_transaction_in_linear_il"
        ],
        "replication_precedes_return_crosswalk": runtime_contract[
            "new_replication_call_precedes_return_crosswalk_setters_in_linear_il"
        ],
        "eight_return_setters_profiled": runtime_contract[
            "replicate_tour_return_crosswalk_setter_count"
        ]
        == 8
        and runtime_contract["replicate_tour_line_crosswalk_setter_count"] == 6
        and runtime_contract["replicate_tour_call_collection_setter_count"] == 2,
        "managed_commit_signals_span_crosswalk": runtime_contract[
            "managed_commit_exists_before_return_crosswalk_setters_in_linear_il"
        ]
        and runtime_contract[
            "managed_commit_exists_after_return_crosswalk_setters_in_linear_il"
        ],
        "cancel_endpoint_reaches_domain": runtime_contract["cancel_endpoint_present"]
        and runtime_contract["cancel_endpoint_calls_domain_count"] == 1,
        "update_has_three_saves_zero_transaction": runtime_contract[
            "update_from_ngt_save_changes_count"
        ]
        == 3
        and runtime_contract["update_from_ngt_transaction_event_count"] == 0,
        "caller_adds_fourth_save_zero_transaction": runtime_contract[
            "update_from_ngt_caller_count"
        ]
        == 1
        and runtime_contract["update_from_ngt_caller_save_changes_count"] == 1
        and runtime_contract["update_from_ngt_caller_transaction_event_count"] == 0,
        "r066_critical_r067_high_and_caveated": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and by_risk["R-066"]["severity"] == "CRITICAL"
        and by_risk["R-067"]["severity"] == "HIGH"
        and "not that a duplicate return currently exists"
        in by_risk["R-066"]["failure_mode"]
        and "does not prove that a partial update incident occurred"
        in by_risk["R-067"]["failure_mode"],
        "traceability_67_risks_263_assignments_zero_ready": trace["validation"] == "PASS"
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
        "artifact": "varanegar_ngt_return_checkpoint_20260829",
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
            "active_return_line_count": contract["active_return_line_count"],
            "line_without_history_count": contract["active_line_without_history_count"],
            "historical_target_missing_count": contract[
                "historical_result_current_order_missing_count"
            ],
            "return_crosswalk_setter_count": runtime_contract[
                "replicate_tour_return_crosswalk_setter_count"
            ],
            "update_save_boundary_count": runtime_contract[
                "update_from_ngt_save_changes_count"
            ]
            + runtime_contract["update_from_ngt_caller_save_changes_count"],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "high_risk_count": risks["summary"]["high_count"],
            "mapped_risk_assignment_count": trace["summary"][
                "mapped_risk_assignment_count"
            ],
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
