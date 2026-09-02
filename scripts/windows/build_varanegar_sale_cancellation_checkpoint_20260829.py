"""Build the offline sale-cancellation evidence checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/sale_cancellation_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/sale_cancellation_runtime_boundary_20260829.json",
    "sale_conversion": "artifacts/varanegar_analysis/domains/sale_conversion_state_boundary_20260829.json",
    "distribution_exit": "artifacts/varanegar_analysis/domains/distribution_exit_lifecycle_boundary_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_sale_conversion_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_sale_cancellation_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_sale_cancellation_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_sale_cancellation_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_sale_cancellation_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/SALE_CANCELLATION_PAYMENT_STOCK_AND_ORDER_POINTER_BOUNDARY_20260829_FA.md",
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
    sql, runtime = _load("sql_boundary"), _load("runtime_boundary")
    previous, risks, trace = _load("previous_checkpoint"), _load("risk_register"), _load("traceability")
    static, managed = sql["static_cancellation_contract"], runtime["managed_cancellation_contract"]
    r080 = next(row for row in risks["risks"] if row["id"] == "R-080")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"]["sale_order_payment_exit_customer_user_host_or_raw_values_persisted"] == 0,
        "sql_hash_coverage": sql["summary"]["selected_sql_module_count"] == 5
        and all(len(row["definition_sha256"]) == 64 for row in sql["sql_module_profiles"]),
        "sql_transaction_and_triggers": static["cancel_has_local_transaction_try_catch_commit_and_rollback"]
        and static["cancel_directly_references_sale_order_payment_and_detail_domains"]
        and static["cancel_has_no_direct_exit_or_distribution_dependency"]
        and static["payment_trigger_deletes_direct_sale_payments_on_cancel"]
        and static["detail_trigger_records_header_state_change"]
        and static["stock_trigger_updates_stock_projection_on_cancel_or_state_change"],
        "current_payment_and_links": sql["summary"]["cancelled_sale_count"] == 61022
        and sql["summary"]["cancelled_sale_with_payment_count"] == 0
        and sql["summary"]["cancelled_sale_with_exit_link_count"] == 34401
        and sql["summary"]["cancelled_sale_with_dist_link_count"] == 34401
        and sql["summary"]["cancelled_sale_selected_by_order_count"] == 34630
        and sql["summary"]["cancelled_sale_selected_by_active_order_count"] == 34397,
        "terminal_projection": sql["terminal_detail_projection"]["overview"]["unexpected_terminal_count"] == 3
        and sql["terminal_detail_projection"]["overview"]["recent_unexpected_terminal_count"] == 0,
        "runtime_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["assembly_count"] == 3
        and runtime["summary"]["selected_method_count"] == 4
        and runtime["summary"]["selected_instruction_count"] == 390
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["safety"]["assembly_loads_or_executions"] == 0,
        "runtime_route": managed["ui_cancel_collects_cancel_reason_before_business_call"]
        and managed["ui_cancel_has_no_explicit_context_commit_or_rollback"]
        and managed["business_is_thin_adapter_delegate_without_explicit_context"]
        and managed["adapter_uses_named_cancel_procedure"]
        and managed["adapter_constructs_context_and_queries_or_executes"]
        and not managed["adapter_has_explicit_commit_signal"]
        and not managed["adapter_has_explicit_rollback_signal"]
        and not managed["physical_transaction_enlistment_between_managed_context_and_sql_local_transaction_proven"],
        "previous_checkpoint_chain": previous["validation"] == "PASS" and previous["summary"]["risk_count"] == 84,
        "r080_registered_and_caveated": r080["severity"] == "CRITICAL"
        and "state shape, not asserted corruption" in r080["failure_mode"]
        and "No live failure or unauthorized cancellation is asserted" in r080["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_or_secret_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw
        ) is None and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None,
    }
    failed = sorted(key for key, value in checks.items() if not value)
    manifest = [{"name": name, "path": relative, "size_bytes": (ROOT / relative).stat().st_size,
                 "sha256": _sha(ROOT / relative)} for name, relative in sorted(SOURCES.items())]
    return {
        "artifact": "varanegar_sale_cancellation_checkpoint_20260829", "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE", "database_connections": 0,
                   "network_reads_or_writes": 0, "live_ui_actions": 0, "assemblies_loaded_or_executed": 0,
                   "operational_commands_executed": 0,
                   "sale_order_payment_exit_customer_user_host_error_or_raw_values_read": 0},
        "source_manifest": manifest, "checks": checks, "failed_checks": failed,
        "summary": {"source_count": len(manifest), "passed_check_count": sum(checks.values()),
                    "failed_check_count": len(failed),
                    "selected_sql_module_count": sql["summary"]["selected_sql_module_count"],
                    "selected_runtime_method_count": runtime["summary"]["selected_method_count"],
                    "cancelled_sale_count": sql["summary"]["cancelled_sale_count"],
                    "cancelled_sale_with_payment_count": sql["summary"]["cancelled_sale_with_payment_count"],
                    "cancelled_sale_with_exit_link_count": sql["summary"]["cancelled_sale_with_exit_link_count"],
                    "unexpected_terminal_detail_count": sql["summary"]["cancelled_sale_unexpected_terminal_detail_count"],
                    "risk_count": risks["summary"]["risk_count"],
                    "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"]},
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
