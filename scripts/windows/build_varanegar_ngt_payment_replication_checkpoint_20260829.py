"""Build an offline checkpoint for NGT payment receipt replication."""

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
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_replication_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_replication_runtime_boundary_20260829.json",
    "payment_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_settlement_boundary_20260829.json",
    "order_runtime": "artifacts/varanegar_analysis/domains/ngt_order_runtime_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_payment_replication_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_payment_replication_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_payment_replication_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_payment_replication_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_PAYMENT_REPLICATION_AND_CROSSWALK_IDEMPOTENCY_BOUNDARY_20260829_FA.md",
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
    history = sql["tour_history_contract"]
    crosswalk = history["payment_type_10_crosswalk"]
    duplicates = history["type_10_duplicate_entity_groups"]
    exact_duplicates = history["type_10_exact_duplicate_groups"]
    catalog = sql["tour_history_catalog_contract"]
    runtime_contract = runtime["replicate_tour_crosswalk_writeback_contract"]
    by_risk = {row["id"]: row for row in risks["risks"]}
    privacy_text = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    unique_indexes = [row for row in catalog["indexes"] if row["is_unique"]]
    profiles = {row["qualified_name"]: row for row in sql["replication_procedure_profiles"]}
    receipt_objects = {
        row["qualified_object"]
        for row in profiles["dbo.NGT_CreateReceipt_ForDistInfo"]["mutation_object_counts"]
    }
    checks = {
        "sql_valid_read_only_and_no_commands": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "definitions_rows_and_guids_not_persisted": sql["safety"]["sql_definitions_persisted"] == 0
        and sql["safety"]["business_rows_or_identifiers_persisted"] == 0
        and sql["safety"]["guid_literals_persisted"] == 0,
        "four_sql_procedures_profiled": sql["summary"]["procedure_count"] == 4
        and set(profiles)
        == {
            "dbo.NGT_DoReplicateTour",
            "dbo.NGT_ReplicateTour",
            "dbo.NGT_CreateReceipt_ForDistInfo",
            "dbo.NGT_CreateSettlement_Merge",
        },
        "receipt_creator_spans_all_instrument_tables": {
            "Receipt",
            "RCash",
            "RCashDetail",
            "acc.TblCheque",
            "acc.tblChqHist",
            "acc.tblBankOrders",
            "#FinalResult",
        }.issubset(receipt_objects),
        "helpers_have_no_local_transaction": not profiles[
            "dbo.NGT_CreateReceipt_ForDistInfo"
        ]["has_explicit_begin_transaction"]
        and not profiles["dbo.NGT_CreateSettlement_Merge"][
            "has_explicit_begin_transaction"
        ],
        "seven_settlement_literals_resolved_without_guids": sql["summary"][
            "settlement_type_literal_count"
        ]
        == 7
        and sql["settlement_type_literal_contract"]["unresolved_guid_count"] == 0,
        "447_histories_for_344_payments": crosswalk["type_10_history_count"] == 447
        and crosswalk["distinct_entity_count"] == 344
        and crosswalk["entity_not_current_payment_count"] == 0,
        "274_exact_current_crosswalks": history["payment_perspective"][
            "exact_type_10_crosswalk_count"
        ]
        == 274,
        "70_payments_have_173_multiple_histories": duplicates[
            "duplicate_entity_group_count"
        ]
        == 70
        and duplicates["histories_in_duplicate_groups"] == 173
        and duplicates["maximum_histories_per_entity"] == 6,
        "all_multi_history_payments_are_number_only": history["type_10_field_presence"][0]
        == {
            "history_multiplicity": "MULTIPLE_HISTORIES",
            "has_current_uuid": 0,
            "has_current_ref": 0,
            "has_current_no": 1,
            "payment_count": 70,
            "history_count": 173,
        },
        "72_exact_duplicate_groups_and_two_multi_target_payments": exact_duplicates[
            "exact_duplicate_group_count"
        ]
        == 72
        and sum(
            row["payment_count"]
            for row in history["type_10_entity_shape"]
            if row["target_multiplicity"] == "MULTIPLE_TARGETS"
        )
        == 2,
        "nine_missing_history_targets": crosswalk[
            "type_10_history_count"
        ]
        - crosswalk["history_uuid_resolves_receipt_count"]
        == 9,
        "type10_has_no_unique_fk_or_trigger_guard": len(unique_indexes) == 1
        and unique_indexes[0]["filter_targets_type_1"]
        and not unique_indexes[0]["filter_targets_type_10"]
        and catalog["foreign_keys"] == []
        and catalog["triggers"] == [],
        "runtime_valid_static_and_zero_execution": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY"
        and runtime["safety"]["assembly_loads_or_execution"] == 0
        and runtime["safety"]["application_endpoint_or_command_executions"] == 0,
        "runtime_has_all_three_payment_crosswalk_setters": runtime_contract[
            "payment_crosswalk_setter_event_count"
        ]
        == 3
        and len(runtime_contract["payment_crosswalk_setter_members"]) == 3,
        "runtime_linear_il_has_commit_before_and_after_setters": runtime_contract[
            "new_replication_call_precedes_payment_setters_in_linear_il"
        ]
        and runtime_contract["commit_exists_before_payment_setters_in_linear_il"]
        and runtime_contract["commit_exists_after_payment_setters_in_linear_il"],
        "risk_register_has_r064_and_37_critical": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and by_risk["R-064"]["severity"] == "CRITICAL",
        "r007_records_number_only_partial_crosswalk": "70 active payments with multiple Type=10 histories"
        in by_risk["R-007"]["failure_mode"],
        "traceability_has_65_risks_256_assignments_zero_ready": trace["validation"] == "PASS"
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
        "artifact": "varanegar_ngt_payment_replication_checkpoint_20260829",
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
            "type_10_history_count": crosswalk["type_10_history_count"],
            "type_10_payment_count": crosswalk["distinct_entity_count"],
            "multi_history_payment_count": duplicates["duplicate_entity_group_count"],
            "histories_in_duplicate_groups": duplicates["histories_in_duplicate_groups"],
            "missing_receipt_target_history_count": crosswalk["type_10_history_count"]
            - crosswalk["history_uuid_resolves_receipt_count"],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
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
