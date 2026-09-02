"""Build an offline checkpoint for supplier cost apply/reapply evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/supplier_cost_apply_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/supplier_cost_apply_runtime_boundary_20260829.json",
    "supplier_component": "artifacts/varanegar_analysis/ui/varanegar_supplier_receipt_component_diagnostic_contract_20260827.json",
    "order_delete_checkpoint": "artifacts/varanegar_analysis/varanegar_ngt_order_delete_log_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_supplier_cost_apply_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_supplier_cost_apply_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_supplier_cost_apply_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_supplier_cost_apply_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/SUPPLIER_COST_APPLY_REAPPLY_ATOMICITY_BOUNDARY_20260829_FA.md",
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
    risks = _load("risk_register")
    trace = _load("traceability")
    sequence = sql["apply_reapply_sequence_contract"]
    parity = {row["Status"]: row for row in sql["status_price_parity"]}
    managed = runtime["managed_apply_reapply_contract"]
    r071 = next(row for row in risks["risks"] if row["id"] == "R-071")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_form_or_application_command_executions"] == 0,
        "sql_redacted": sql["safety"]["business_rows_identifiers_amounts_or_prices_persisted"] == 0
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "core_transaction_gap": sql["summary"]["core_apply_module_count"] == 5
        and sql["summary"]["core_module_with_local_transaction_count"] == 0,
        "apply_sequence": sequence["apply_deletes_then_inserts_price"]
        and not sequence["apply_updates_header_status"]
        and sequence["fast_apply_deletes_then_inserts_price_then_sets_status"],
        "reapply_pre_marks_status": sequence["reapply_sets_status_before_fast_apply"],
        "current_applied_parity": parity[1]["distinct_item_count"] == 29078
        and parity[1]["item_with_price_count"] == 29078
        and parity[1]["item_without_price_count"] == 0,
        "current_unapplied_parity": parity[0]["distinct_item_count"] == 1354
        and parity[0]["item_with_price_count"] == 0
        and parity[0]["item_without_price_count"] == 1354,
        "cross_status_disjoint": sql["cross_status_item_contract"]["related_item_count"] == 30432
        and sql["cross_status_item_contract"]["cross_status_item_count"] == 0,
        "price_integrity_boundary": sql["voucher_item_price_integrity"]["price_row_count"] == 1419656
        and sql["voucher_item_price_integrity"]["orphan_price_row_count"] == 95
        and sql["voucher_item_price_integrity"]["unique_primary_key_on_item_id"]
        and not sql["voucher_item_price_integrity"]["foreign_key_to_voucher_item_present"],
        "runtime_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["summary"]["selected_method_count"] == 4,
        "runtime_reapply_gap": managed["reapply_business_calls_adapter"]
        and managed["reapply_adapter_queries_allowlisted_reapply_procedure"]
        and not managed["reapply_selected_path_has_begin_transaction_signal"]
        and not managed["reapply_selected_path_has_data_context_commit_signal"],
        "runtime_apply_commit_boundary": managed["apply_business_calls_adapter"]
        and managed["apply_adapter_calls_data_context_execute"]
        and managed["apply_business_has_commit_signal"]
        and managed["apply_adapter_call_precedes_business_commit_in_linear_il"],
        "runtime_claim_limits": not managed["managed_data_context_constructor_transaction_semantics_proven"]
        and not managed["branch_specific_commit_reachability_proven"],
        "r071_registered": r071["severity"] == "CRITICAL"
        and "structural failure window" in r071["failure_mode"]
        and "not a current partial-apply incident" in r071["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
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
        "artifact": "varanegar_supplier_cost_apply_checkpoint_20260829",
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
            "applied_invoice_count": sql["summary"]["applied_invoice_count"],
            "applied_related_item_count": sql["summary"]["applied_related_item_count"],
            "unapplied_invoice_count": sql["summary"]["unapplied_invoice_count"],
            "unapplied_related_item_count": sql["summary"]["unapplied_related_item_count"],
            "orphan_price_row_count": sql["summary"]["orphan_price_row_count"],
            "runtime_selected_method_count": runtime["summary"]["selected_method_count"],
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
