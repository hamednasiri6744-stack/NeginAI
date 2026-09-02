"""Build an offline checkpoint for the NGT Type=8 sale-replication boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_sale_replication_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_sale_replication_runtime_boundary_20260829.json",
    "order_boundary": "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json",
    "return_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_return_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_sale_replication_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_sale_replication_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_sale_replication_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_ngt_sale_replication_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/NGT_SALE_REPLICATION_TYPE8_IDEMPOTENCY_BOUNDARY_20260829_FA.md",
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
    contract = sql["sale_replication_contract"]
    runtime_contract = runtime["sale_runtime_contract"]
    risk = next(row for row in risks["risks"] if row["id"] == "R-068")
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
        "type8_counts": contract["history_count"] == 3731
        and contract["entity_count"] == 3593,
        "138_duplicate_pairs": contract["multi_history_entity_count"] == 138
        and contract["history_in_multi_group_count"] == 276
        and contract["max_history_per_entity"] == 2,
        "duplicates_same_target_timestamp": contract[
            "duplicate_same_target_entity_count"
        ]
        == 138
        and contract["duplicate_same_timestamp_entity_count"] == 138,
        "zero_multi_target_or_missing_target": contract["multi_target_entity_count"] == 0
        and contract["missing_current_sale_target_count"] == 0,
        "header_crosswalk_matches": contract["missing_ngt_order_count"] == 0
        and contract["header_invoice_uuid_mismatch_count"] == 0
        and contract["header_invoice_ref_mismatch_count"] == 0,
        "no_unique_guards": not contract["type_8_history_unique_guard_present"]
        and not contract["order_invoice_crosswalk_unique_guard_present"],
        "runtime_static_zero_execution": runtime["validation"] == "PASS"
        and runtime["safety"]["assembly_loads_or_execution"] == 0,
        "three_invoice_setters": runtime_contract["sale_crosswalk_setter_count"] == 3,
        "replication_precedes_transaction_and_setters": runtime_contract[
            "new_replication_call_precedes_managed_transaction_in_linear_il"
        ]
        and runtime_contract[
            "new_replication_call_precedes_sale_crosswalk_setters_in_linear_il"
        ],
        "commits_span_setters": runtime_contract[
            "managed_commit_exists_before_sale_crosswalk_setters_in_linear_il"
        ]
        and runtime_contract[
            "managed_commit_exists_after_sale_crosswalk_setters_in_linear_il"
        ],
        "r068_critical_and_caveated": risk["severity"] == "CRITICAL"
        and "does not prove duplicate Sale, stock or accounting effects"
        in risk["failure_mode"],
        "risk_totals": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31,
        "trace_totals": trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            privacy,
        )
        is None,
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
        "artifact": "varanegar_ngt_sale_replication_checkpoint_20260829",
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
            "type_8_history_count": contract["history_count"],
            "type_8_entity_count": contract["entity_count"],
            "duplicate_same_target_entity_count": contract[
                "duplicate_same_target_entity_count"
            ],
            "sale_crosswalk_setter_count": runtime_contract[
                "sale_crosswalk_setter_count"
            ],
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
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
