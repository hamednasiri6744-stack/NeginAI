"""Build an offline hash-pinned checkpoint for the NGT operation-date boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "operation_boundary": "artifacts/varanegar_analysis/domains/ngt_operation_date_boundary_20260829.json",
    "final_date_boundary": "artifacts/varanegar_analysis/ui/varanegar_final_date_diagnostic_contract_20260827.json",
    "return_crosswalk": "artifacts/varanegar_analysis/ui/varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "operation_extractor": "scripts/sql/extract_varanegar_ngt_operation_date_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_operation_date_checkpoint_20260829.py",
    "operation_tests": "tests/test_varanegar_ngt_operation_date_boundary.py",
    "operation_doc": "docs/varanegar_reconstruction/NGT_OPERATION_DATE_AND_REPLICATION_SELECTOR_BOUNDARY_20260829_FA.md",
    "final_date_doc": "docs/varanegar_reconstruction/FINAL_DATE_MANAGEMENT_CROSS_DOMAIN_BOUNDARY_20260827_FA.md",
    "return_crosswalk_doc": "docs/varanegar_reconstruction/NGT_RETURN_CROSSWALK_DIAGNOSTIC_20260827_FA.md",
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
    operation = _load("operation_boundary")
    final_date = _load("final_date_boundary")
    crosswalk = _load("return_crosswalk")
    risks = _load("risk_register")
    trace = _load("traceability")
    replication = next(
        row
        for row in operation["sql_consumers"]
        if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    risk = next((row for row in risks["risks"] if row["id"] == "R-060"), None)
    checks = {
        "operation_artifact_valid": operation["validation"] == "PASS",
        "operation_artifact_static_and_read_only": operation["safety"]["mode"]
        == "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_STATIC_TARGETED_IL",
        "database_read_only": operation["safety"]["database_updateability"] == "READ_ONLY",
        "database_update_denied": operation["safety"]["can_update"] == 0
        and operation["safety"]["denies_data_writes"] == 1,
        "no_command_or_assembly_execution": operation["safety"][
            "stored_procedure_or_application_command_executions"
        ]
        == 0
        and operation["safety"]["assemblies_loaded_or_executed"] == 0,
        "four_assemblies_analyzed": operation["summary"]["analyzed_assembly_count"] == 4,
        "method_body_count_27788": operation["summary"]["method_body_count"] == 27788,
        "zero_signal_named_body_errors": operation["summary"][
            "signal_named_method_body_error_count"
        ]
        == 0,
        "single_operation_date_setter_caller": operation["summary"][
            "operation_date_setter_caller_count"
        ]
        == 1,
        "four_operation_date_getter_callers": operation["summary"][
            "operation_date_getter_caller_count"
        ]
        == 4,
        "ngt_datetime_not_null": operation["contract"]["ngt_operation_date_type"]
        == "datetime"
        and operation["contract"]["ngt_operation_date_nullable"] is False,
        "ngt_default_is_1900": operation["ingest_persistence_contract"][
            "database_default_is_1900_sentinel_not_dotnet_default"
        ],
        "no_database_operation_date_check": operation["contract"][
            "operation_date_check_constraint_count"
        ]
        == 0,
        "no_return_table_trigger": operation["contract"]["table_trigger_count"] == 0,
        "save_path_rejects_dotnet_default": operation["ingest_persistence_contract"][
            "save_tour_data_rejects_dotnet_default_datetime"
        ],
        "distribution_path_assigns_now": operation["ingest_persistence_contract"][
            "add_distribution_tour_assigns_captured_now_to_operation_date"
        ],
        "current_ngt_rows_2": operation["summary"]["ngt_row_count"] == 2,
        "current_fru_rows_0": operation["summary"]["fru_row_count"] == 0,
        "current_sentinel_0": operation["summary"]["ngt_sentinel_operation_date_count"] == 0,
        "current_crosswalk_0": operation["summary"]["ngt_to_fru_exact_crosswalk_count"] == 0,
        "current_selector_call_date": operation["contract"][
            "current_date_selector_code_enum_name"
        ]
        == "CallDate",
        "current_selector_base_value_exact": operation["summary"][
            "date_setting_base_value_exact_match_count"
        ]
        == 1,
        "four_selector_semantics_mapped": set(
            operation["date_source_contract"]["sql_replication_case_sources"]
        )
        == {"CallDate", "OperationDate", "ServerDate", "ActiveDate"},
        "business_operation_date_uses_ngt_event": operation["date_source_contract"][
            "business_il_replication_overrides"
        ]["OperationDate"]
        == "NGT_RETURN_OPERATION_DATE",
        "sql_operation_date_uses_call_tour": operation["date_source_contract"][
            "sql_replication_case_sources"
        ]["OperationDate"]
        == "CALL_ACTIVITY_DATE_FALLBACK_TOUR_ACTIVITY_DATE",
        "sql_active_date_uses_global_open_sales_date": operation["date_source_contract"][
            "sql_replication_case_sources"
        ]["ActiveDate"]
        == "GLOBAL_OPEN_SALES_OPERATION_DATE",
        "global_date_guard_complete": all(
            operation["date_source_contract"]["global_operation_date_branch_guard"].values()
        ),
        "three_sql_cases_without_else": replication["date_selector_case_count"] == 3
        and replication["date_selector_case_without_else_count"] == 3,
        "eleven_sql_consumers": operation["summary"]["sql_consumer_count"] == 11,
        "five_global_date_consumers": operation["summary"][
            "sql_consumer_references_global_tbl_opr_date_count"
        ]
        == 5,
        "prior_final_date_contract_valid": final_date["validation"] == "PASS",
        "prior_return_crosswalk_contract_valid": crosswalk["validation"] == "PASS",
        "risk_register_valid_65": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84,
        "risk_060_high_and_caveated": risk is not None
        and risk["severity"] == "HIGH"
        and "No current wrong-date or accounting incident is asserted" in risk["failure_mode"],
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
        "artifact": "varanegar_operation_date_checkpoint_20260829",
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
            "business_rows_raw_ids_or_configuration_ids_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "analyzed_assembly_count": operation["summary"]["analyzed_assembly_count"],
            "method_body_count": operation["summary"]["method_body_count"],
            "ngt_return_row_count": operation["summary"]["ngt_row_count"],
            "current_selector": operation["contract"]["current_date_selector_code_enum_name"],
            "sql_consumer_count": operation["summary"]["sql_consumer_count"],
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
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
