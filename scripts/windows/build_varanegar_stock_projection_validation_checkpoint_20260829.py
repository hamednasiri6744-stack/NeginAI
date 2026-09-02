"""Build the offline stock projection and post-validation checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "boundary": "artifacts/varanegar_analysis/domains/stock_projection_validation_boundary_20260829.json",
    "state_boundary": "artifacts/varanegar_analysis/domains/stock_voucher_state_boundary_20260829.json",
    "state_runtime": "artifacts/varanegar_analysis/domains/stock_voucher_state_runtime_boundary_20260829.json",
    "stock_reconciliation": "artifacts/varanegar_analysis/ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json",
    "stock_command_contract": "artifacts/varanegar_analysis/ui/varanegar_stock_voucher_command_contract_20260827.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_stock_voucher_state_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "extractor": "scripts/sql/extract_varanegar_stock_projection_validation_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_stock_projection_validation_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_stock_projection_validation_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/STOCK_PROJECTION_AND_POST_VALIDATION_FAILURE_BOUNDARY_20260829_FA.md",
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
    boundary = _load("boundary")
    previous = _load("previous_checkpoint")
    reconciliation = _load("stock_reconciliation")
    risks = _load("risk_register")
    trace = _load("traceability")
    contract = boundary["static_validation_and_projection_contract"]
    cardex = boundary["cardex_effect_contract"]
    projection = boundary["projection_snapshot"]
    profiles = {row["qualified_name"]: row for row in boundary["sql_module_profiles"]}
    r077 = next(row for row in risks["risks"] if row["id"] == "R-077")
    raw = (ROOT / SOURCES["boundary"]).read_text(encoding="utf-8")
    checks = {
        "read_only_redacted": boundary["validation"] == "PASS"
        and boundary["safety"]["database_updateability"] == "READ_ONLY"
        and boundary["safety"]["can_update"] == 0
        and boundary["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and boundary["safety"]["voucher_goods_stock_document_user_host_or_raw_row_values_persisted"] == 0
        and boundary["safety"]["sql_definitions_error_texts_or_business_identifiers_persisted"] == 0,
        "module_hash_and_coverage": boundary["summary"]["selected_sql_module_count"] == 10
        and len(boundary["sql_module_profiles"]) == 10
        and all(len(row["definition_sha256"]) == 64 for row in boundary["sql_module_profiles"]),
        "confirm_post_commit_advisory_shape": contract["confirm_first_commit_precedes_after_validation"]
        and contract["confirm_appends_after_message_without_abort_guard"]
        and contract["confirm_after_cursor_excludes_generated_type15_mode"],
        "unconfirm_advisory_before_commit_shape": contract["unconfirm_after_validation_precedes_commit"]
        and contract["unconfirm_appends_after_message_then_commits_without_abort_guard"],
        "after_message_only_validation": contract["after_has_no_local_transaction_raise_or_throw"]
        and contract["after_calls_four_expected_validation_modules"]
        and contract["after_uses_nolock_reads"]
        and profiles["inv.AfterInvVocherHdr"]["nolock_signal_count"] == 9
        and profiles["inv.AfterInvVocherHdr"]["dependency_count"] == 11,
        "after_type_exemptions": contract["after_type20_batch_state_update_precedes_validation"]
        and contract["after_skips_common_onhand_and_cardex_checks_for_types12_and13"]
        and contract["after_cardex_checks_only_when_confirmed"],
        "projection_and_guard_behavior": contract["header_projection_uses_cursor_and_can_rollback"]
        and contract["item_projection_uses_cursor_try_catch_and_can_rollback"]
        and contract["stock_negative_guard_is_set_based"]
        and contract["stock_negative_guard_has_session_and_replication_bypass"]
        and boundary["summary"]["active_projection_or_guard_trigger_count"] == 3,
        "cardex_rule_matrix": cardex["aggregate"]["row_count"] == 50
        and cardex["aggregate"]["voucher_type_count"] == 30
        and cardex["aggregate"]["positive_effect_row_count"] == 27
        and cardex["aggregate"]["negative_effect_row_count"] == 22
        and cardex["aggregate"]["zero_effect_row_count"] == 1
        and len(cardex["effect_matrix"]) == 50,
        "current_projection_clean": projection["stock_goods"]["row_count"] == 67161
        and boundary["summary"]["stock_projection_negative_component_count"] == 0
        and projection["stock_goods_detail"]["row_count"] == 0,
        "official_reconciliation_zero_residual": reconciliation["summary"]["cardex_only_mismatch_count"] == 1594
        and reconciliation["summary"]["official_formula_mismatch_count"] == 0
        and reconciliation["official_legacy_formula_reconciliation"]["overview"]["obligation_keys"] == 1594,
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r077_registered_and_caveated": r077["severity"] == "CRITICAL"
        and "no current validation failure or bypass incident is asserted" in r077["failure_mode"]
        and "message-only validation" in r077["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_or_secret_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
        ) is None
        and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None,
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
        "artifact": "varanegar_stock_projection_validation_checkpoint_20260829",
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
            "voucher_goods_stock_document_user_host_error_text_or_raw_row_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "selected_sql_module_count": boundary["summary"]["selected_sql_module_count"],
            "cardex_effect_rule_count": boundary["summary"]["cardex_effect_row_count"],
            "cardex_effect_voucher_type_count": boundary["summary"]["cardex_effect_voucher_type_count"],
            "stock_projection_row_count": boundary["summary"]["stock_projection_row_count"],
            "stock_projection_negative_component_count": boundary["summary"]["stock_projection_negative_component_count"],
            "official_formula_residual_count": reconciliation["summary"]["official_formula_mismatch_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
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
    print(payload["validation"])
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
