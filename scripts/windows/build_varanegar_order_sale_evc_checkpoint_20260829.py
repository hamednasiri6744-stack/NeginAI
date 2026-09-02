"""Build the Discount V2 EVC split and persistence checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "runtime": "artifacts/varanegar_analysis/domains/order_sale_evc_runtime_boundary_20260829.json",
    "sql": "artifacts/varanegar_analysis/domains/order_sale_evc_sql_boundary_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_datacontext_transaction_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "runtime_extractor": "scripts/windows/extract_varanegar_order_sale_evc_runtime_boundary.py",
    "sql_extractor": "scripts/sql/extract_varanegar_order_sale_evc_sql_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_order_sale_evc_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_order_sale_evc_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_EVC_SPLIT_AND_DISCOUNT_V2_BOUNDARY_20260829_FA.md",
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
    runtime = _load("runtime")
    sql = _load("sql")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    r079 = next(row for row in risks["risks"] if row["id"] == "R-079")
    r004 = next(row for row in risks["risks"] if row["id"] == "R-004")
    checks = {
        "static_runtime_scan_passes": (
            runtime["validation"] == "PASS"
            and runtime["summary"]["assembly_count"] == 4
            and runtime["summary"]["managed_inventory_assembly_scan_count"] == 59
            and runtime["summary"]["managed_inventory_parse_error_count"] == 0
            and all(row["inventory_sha256_match"] for row in runtime["source"])
            and runtime["safety"]["assembly_loads_or_executions"] == 0
        ),
        "typed_flag_path_defaults_to_fallback": (
            runtime["summary"]["calc_for_discount_v2_setter_callsite_count"] == 1
            and runtime["assertions"]["calc_flag_has_no_typed_setter_after_constructor"]
            and runtime["assertions"]["discount_v2_entry_is_reached_from_order_to_sale_form"]
        ),
        "runtime_temp_name_mismatch_is_bounded": (
            runtime["inventory_temp_table_literal_scan"]["double_temp_name_literal_files"]
            == ["VN.SDS.Sales.DataAccess.dll"]
            and runtime["inventory_temp_table_literal_scan"]["double_temp_create_literal_files"] == []
            and runtime["inventory_temp_table_literal_scan"]["single_temp_create_literal_files"]
            == ["VN.SDS.Sales.DataAccess.dll"]
        ),
        "read_only_sql_boundary_passes": (
            sql["validation"] == "PASS"
            and sql["summary"]["selected_module_count"] == 5
            and sql["summary"]["single_temp_name_module_count"] == 5
            and sql["summary"]["double_temp_name_module_count"] == 0
            and sql["safety"]["data_mutations"] == 0
        ),
        "sql_fallback_and_persistence_are_explicit": (
            sql["assertions"]["calc_for_discount_v2_default_is_zero"]
            and sql["assertions"]["legacy_evc_branch_is_guarded_by_flag_zero"]
            and sql["assertions"]["legacy_branch_fills_evc_and_builds_single_usance_temp"]
            and sql["assertions"]["create_sale_by_evc_reads_single_temp_and_persists_rows"]
            and sql["assertions"]["current_clone_has_single_disabled_discount_v2_key"]
        ),
        "diagnostic_export_is_bounded_and_integrated": (
            runtime["assertions"]["discount_v2_toolbar_exposes_unpermissioned_test_data_checkbox"]
            and runtime["assertions"]["test_data_export_serializes_full_calcdata_to_gzip_bytes"]
            and runtime["assertions"]["test_data_export_has_no_named_encryption_call"]
            and runtime["assertions"]["diagnostic_export_executes_legacy_do_evc_before_managed_promotion"]
            and (ROOT / SOURCES["runtime"]).as_posix() in r004["evidence_refs"]
            and "full CalcData" in r004["failure_mode"]
            and sql["summary"]["discount_v2_enabled_key_count"] == 0
            and runtime["summary"]["runtime_share_diagnostic_file_count"] == 0
        ),
        "r079_integrates_evc_evidence_without_count_inflation": (
            (ROOT / SOURCES["runtime"]).as_posix() in r079["evidence_refs"]
            and (ROOT / SOURCES["sql"]).as_posix() in r079["evidence_refs"]
            and "two-calculation fallback" in r079["failure_mode"]
            and "#SaleSaleItemPaymentUsance" in r079["failure_mode"]
            and risks["summary"]["risk_count"] == 84
        ),
        "source_metrics_are_integrated": (
            risks["source_checkpoint"]["order_sale_evc_managed_assembly_scan_count"] == 59
            and risks["source_checkpoint"]["order_sale_evc_calc_flag_setter_callsite_count"] == 1
            and risks["source_checkpoint"]["order_sale_evc_double_temp_sql_module_count"] == 0
            and risks["source_checkpoint"]["order_sale_evc_double_temp_create_literal_count"] == 0
        ),
        "previous_and_traceability_chain_pass": (
            previous["validation"] == "PASS"
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
        "artifact": "varanegar_order_sale_evc_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_HASH_PINNED_STATIC_AND_READ_ONLY_SQL_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
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
            "selected_sql_module_count": sql["summary"]["selected_module_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main() -> int:
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
