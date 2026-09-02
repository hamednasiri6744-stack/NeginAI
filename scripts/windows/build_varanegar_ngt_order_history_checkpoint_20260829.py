"""Build an offline checkpoint for NGT Type=1 history target reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_order_history_target_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_order_history_runtime_boundary_20260829.json",
    "order_boundary": "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json",
    "sale_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_sale_replication_checkpoint_20260829.json",
    "return_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_return_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_order_history_target_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_order_history_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_order_history_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_order_history_target_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_ORDER_HISTORY_MISSING_TARGET_RECONCILIATION_BOUNDARY_20260829_FA.md",
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
    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    contract = sql["order_history_contract"]
    runtime_contract = runtime["order_history_runtime_contract"]
    risk = next(row for row in risks["risks"] if row["id"] == "R-069")
    privacy = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_or_application_command_executions"] == 0,
        "sql_redacted": sql["safety"]["business_rows_or_identifiers_persisted"] == 0
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "type1_partition": contract["history_count"] == 1118244
        and contract["resolved_same_target_count"] == 1112711
        and contract["missing_target_history_count"] == 5533,
        "neither_key_resolves": contract["uuid_only_target_match_count"] == 0
        and contract["ref_only_target_match_count"] == 0
        and contract["uuid_ref_conflict_target_count"] == 0,
        "crosswalks_match_history": contract["missing_target_line_crosswalk_match_count"] == 5533,
        "active_uncanceled_no_sale": contract["missing_target_removed_line_count"] == 0
        and contract["missing_target_removed_parent_count"] == 0
        and contract["missing_target_canceled_parent_count"] == 0
        and contract["missing_target_parent_with_type8_count"] == 0,
        "parent_shape": contract["parent_with_missing_target_count"] == 1022
        and contract["all_targets_missing_parent_count"] == 1021
        and contract["mixed_resolved_missing_parent_count"] == 1,
        "mixed_parent_shape": contract["mixed_parent_history_line_count"] == 16
        and contract["mixed_parent_missing_line_count"] == 1,
        "target_shape": contract["distinct_missing_target_pair_count"] == 1024
        and contract["target_shared_by_multiple_parent_count"] == 0
        and contract["max_parent_per_missing_target"] == 1,
        "recent_population": contract["recent_three_month_missing_history_count"] == 634
        and contract["recent_three_month_parent_with_missing_target_count"] == 114,
        "type1_history_unique_guard": contract["type1_entity_unique_index_present"] is True,
        "runtime_static_zero_execution": runtime["validation"] == "PASS"
        and runtime["safety"]["assembly_loads_or_execution"] == 0,
        "three_order_setters": runtime_contract["order_line_crosswalk_setter_count"] == 3,
        "replication_precedes_transaction_and_setters": runtime_contract[
            "new_replication_precedes_managed_transaction_in_linear_il"
        ] and runtime_contract[
            "new_replication_precedes_order_crosswalk_setters_in_linear_il"
        ],
        "commits_span_setters": runtime_contract[
            "managed_commit_exists_before_order_crosswalk_setters_in_linear_il"
        ] and runtime_contract[
            "managed_commit_exists_after_order_crosswalk_setters_in_linear_il"
        ],
        "r069_critical_and_caveated": risk["severity"] == "CRITICAL"
        and "does not authorize recreation" in risk["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
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
        "artifact": "varanegar_ngt_order_history_checkpoint_20260829",
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
            "type1_history_count": contract["history_count"],
            "missing_target_history_count": contract["missing_target_history_count"],
            "affected_parent_count": contract["parent_with_missing_target_count"],
            "recent_missing_parent_count": contract[
                "recent_three_month_parent_with_missing_target_count"
            ],
            "order_crosswalk_setter_count": runtime_contract[
                "order_line_crosswalk_setter_count"
            ],
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
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
