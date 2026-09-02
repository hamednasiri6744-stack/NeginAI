"""Build the idempotency, retry and storage-guard checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "boundary": "artifacts/varanegar_analysis/domains/idempotency_guard_boundary_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_command_outcome_commit_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "extractor": "scripts/sql/extract_varanegar_idempotency_guard_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_idempotency_guard_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_idempotency_guard_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/IDEMPOTENCY_RETRY_AND_STORAGE_GUARD_BOUNDARY_20260829_FA.md",
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
    boundary = _load("boundary")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    risk = next(item for item in risks["risks"] if item["id"] == "R-006")
    raw = (ROOT / SOURCES["boundary"]).read_text(encoding="utf-8")
    summary = boundary["summary"]
    contract = boundary["static_and_current_idempotency_contract"]
    checks = {
        "read_only_redacted": (
            boundary["validation"] == "PASS"
            and boundary["safety"]["database_updateability"] == "READ_ONLY"
            and boundary["safety"]["can_update"] == 0
            and boundary["safety"]["denies_data_writes"] == 1
            and boundary["safety"]["stored_procedure_trigger_form_report_or_application_command_executions"] == 0
            and boundary["safety"]["source_or_target_state_changed"] == 0
        ),
        "command_contract": (
            summary["selected_command_count"] == 10
            and summary["selected_command_with_explicit_idempotency_parameter_count"] == 0
            and summary["selected_command_with_id_allocator_count"] == 6
            and contract["all_selected_commands_lack_explicit_idempotency_parameter"]
            and contract["selected_mutating_commands_allocate_ids_but_have_no_retry_key"]
        ),
        "storage_guard_contract": (
            summary["selected_table_count"] == 7
            and summary["selected_table_with_semantic_unique_guard_count"] == 5
            and summary["current_guarded_duplicate_group_count"] == 0
            and summary["current_guarded_zero_population_shape_count"] == 1
            and contract["sale_has_no_semantic_unique_guard_for_one_active_sale_per_order"]
            and contract["sales_return_has_active_source_semantic_unique_guard"]
            and contract["distribution_exit_has_active_semantic_unique_guard"]
            and contract["sales_return_voucher_has_source_health_semantic_unique_guard"]
            and contract["printed_document_has_no_semantic_unique_guard"]
            and contract["pre_voucher_has_line_signature_semantic_unique_guard"]
        ),
        "current_shapes_are_caveated": (
            summary["current_sale_multi_active_order_group_count"] == 0
            and summary["printed_document_repeated_group_count"] == 55792
            and summary["tour_history_type8_duplicate_entity_group_count"] == 138
            and summary["tour_history_type10_duplicate_entity_group_count"] == 70
            and any("legitimate reprints" in item for item in boundary["evidence_limits"])
            and any("clean current duplicate" in item.lower() for item in boundary["evidence_limits"])
        ),
        "target_retry_contract": (
            "CommandId" in boundary["target_contract"]["request_identity"]
            and "PayloadHash" in boundary["target_contract"]["request_identity"]
            and "original typed outcome" in boundary["target_contract"]["same_key_same_payload"]
            and "reject before mutation" in boundary["target_contract"]["same_key_different_payload"]
            and "new CommandId" in boundary["target_contract"]["retry_vs_new_intent"]
        ),
        "r006_evidence": (
            risk["severity"] == "CRITICAL"
            and (ROOT / SOURCES["boundary"]).as_posix() in risk["evidence_refs"]
            and "command_id receipt" in risk["controls"]
            and "same-key replay returns original result" in risk["exit_criteria"]
            and risks["source_checkpoint"]["selected_high_impact_command_without_explicit_idempotency_parameter_count"]
            == 10
            and risks["source_checkpoint"]["selected_idempotency_storage_guard_current_duplicate_group_count"]
            == 0
        ),
        "previous_chain": (
            previous["validation"] == "PASS"
            and previous["summary"]["risk_count"] == 84
            and previous["summary"]["mapped_risk_assignment_count"] == 343
        ),
        "register_trace": (
            risks["summary"]["risk_count"] == 84
            and risks["summary"]["critical_count"] == 50
            and risks["summary"]["high_count"] == 31
            and trace["summary"]["unique_risk_count"] == 84
            and trace["summary"]["mapped_risk_assignment_count"] == 343
            and trace["summary"]["command_ready_module_count"] == 0
        ),
        "no_uuid_secret": (
            re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", raw) is None
            and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest = [
        {
            "name": name,
            "path": path,
            "size_bytes": (ROOT / path).stat().st_size,
            "sha256": _sha(ROOT / path),
        }
        for name, path in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_idempotency_guard_checkpoint_20260829",
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
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "selected_command_count": summary["selected_command_count"],
            "selected_command_with_explicit_idempotency_parameter_count": summary[
                "selected_command_with_explicit_idempotency_parameter_count"
            ],
            "selected_table_with_semantic_unique_guard_count": summary[
                "selected_table_with_semantic_unique_guard_count"
            ],
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
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
