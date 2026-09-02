"""Build the DataContext transaction ownership and order-sale split checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "runtime": "artifacts/varanegar_analysis/domains/datacontext_transaction_runtime_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_order_sale_authorization_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "extractor": "scripts/windows/extract_varanegar_datacontext_transaction_runtime.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_datacontext_transaction_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_datacontext_transaction_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/DATACONTEXT_TRANSACTION_OWNERSHIP_AND_ORDER_SALE_SPLIT_20260829_FA.md",
    "conversion_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_CONVERSION_TRANSACTION_AND_STATE_BOUNDARY_20260829_FA.md",
    "policy_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_POLICY_OVERRIDE_AND_PARTIAL_CONVERSION_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name):
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    runtime = _load("runtime")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    checks = {
        "static_hash_pinned_package_scan": (
            runtime["validation"] == "PASS"
            and runtime["summary"]["required_assembly_count"] == 3
            and runtime["summary"]["managed_inventory_assembly_scan_count"] == 59
            and runtime["summary"]["inventory_parse_error_count"] == 0
            and all(row["inventory_sha256_match"] for row in runtime["source"])
            and runtime["safety"]["assembly_loads_or_executions"] == 0
        ),
        "default_no_transaction_contract": (
            runtime["contract"]["transaction_enum"] == {"Begin": 0, "No": 1}
            and runtime["contract"]["default_datacontext_mode"] == "NO_TRANSACTION"
            and runtime["contract"]["commit_without_db_transaction"] == "NO_OP"
            and runtime["contract"]["rollback_without_db_transaction"] == "NO_OP"
        ),
        "per_context_provider_connection": (
            runtime["contract"]["context_connection_ownership"]
            == "NEW_PROVIDER_AND_CONNECTION_PER_CONTEXT_BY_DEFAULT"
            and runtime["assertions"]["each_mode_context_builds_provider_and_connection"]
            and runtime["assertions"]["commands_bind_provider_connection_and_transaction"]
        ),
        "no_packaged_custom_factory_setter": (
            runtime["summary"]["custom_provider_or_connection_factory_setter_callsite_count"] == 0
            and runtime["assertions"]["no_packaged_custom_provider_or_connection_factory_setter_callsite"]
        ),
        "discount_v2_split_transaction": (
            runtime["assertions"]["discount_v2_preparation_uses_no_transaction_context"]
            and runtime["assertions"]["adapter_conversion_uses_begin_context_and_commit"]
            and runtime["assertions"]["business_v2_calls_transactional_adapter_delegate_overload"]
            and not runtime["contract"]["discount_v2_preparation_and_sale_conversion_share_physical_transaction"]
        ),
        "direct_core_fallback_not_transaction_owner": runtime["assertions"][
            "direct_core_overload_falls_back_to_default_context_without_commit"
        ],
        "r079_integrated_without_count_inflation": (
            (ROOT / SOURCES["runtime"]).as_posix() in risk["evidence_refs"]
            and "proven split EVC-preparation/conversion transaction boundary" in risk["failure_mode"]
            and risks["summary"]["risk_count"] == 84
            and risks["source_checkpoint"]["datacontext_managed_assembly_scan_count"] == 59
            and risks["source_checkpoint"]["datacontext_custom_factory_setter_callsite_count"] == 0
            and risks["source_checkpoint"]["datacontext_order_sale_split_transaction"] is True
        ),
        "register_trace_and_previous_chain": (
            previous["validation"] == "PASS"
            and previous["summary"]["risk_count"] == 84
            and trace["summary"]["unique_risk_count"] == 84
            and trace["summary"]["mapped_risk_assignment_count"] == 343
            and trace["summary"]["command_ready_module_count"] == 0
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest = [
        {"name": name, "path": path, "size_bytes": (ROOT / path).stat().st_size, "sha256": _sha(ROOT / path)}
        for name, path in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_datacontext_transaction_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_HASH_PINNED_STATIC_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "managed_inventory_assembly_scan_count": runtime["summary"]["managed_inventory_assembly_scan_count"],
            "custom_factory_setter_callsite_count": runtime["summary"]["custom_provider_or_connection_factory_setter_callsite_count"],
            "selected_order_sale_method_count": runtime["summary"]["selected_order_sale_method_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
