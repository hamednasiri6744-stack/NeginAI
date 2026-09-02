"""Build the reporting/output module command outcome and retry envelope."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "gap": "artifacts/varanegar_analysis/varanegar_24h_continuation_gap_refresh_20260829.json",
    "closure": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "golden": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "print_batch": "artifacts/varanegar_analysis/domains/print_batch_contract_20260829.json",
    "return_template": "artifacts/varanegar_analysis/domains/return_report_template_boundary_20260829.json",
    "sale_print": "artifacts/varanegar_analysis/domains/sale_invoice_print_audit_boundary_20260829.json",
    "production_detail": "artifacts/varanegar_analysis/domains/production_detail_report_contract_20260829.json",
    "stock_reference": "artifacts/varanegar_analysis/domains/stock_report_reference_contract_20260829.json",
    "healthy_cardex": "artifacts/varanegar_analysis/domains/healthy_cardex_report_contract_20260829.json",
    "bank_summary": "artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_summary_ui_boundary_20260827.json",
    "bank_envelope": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_command_envelope_20260827.json",
    "treasury_envelope": "artifacts/varanegar_analysis/varanegar_treasury_command_outcome_envelope_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_24h_continuation_gap_refresh_checkpoint_20260829.json",
}
OUTCOMES = ["REJECTED_NO_EFFECT", "RENDERED_NOT_COMPLETED", "COMMITTED_COMPLETION", "PARTIAL_BATCH", "UNKNOWN_REQUIRES_READBACK"]
COMMON_REQUEST = ["command_id", "correlation_id", "actor_scope", "resource_scope", "output_kind", "document_or_query_identity", "template_or_query_hash", "filter_hash", "source_watermark", "expected_version"]
COMMON_RESPONSE = ["outcome_code", "committed", "render_receipt", "completion_receipt", "external_file_receipt", "per_item_outcomes", "durable_effect_summary", "retryable", "correlation_id"]
SURFACE_PROFILES = {
    "RPT-09": {"command": "reporting.print_batch", "source": "print_batch", "transaction_boundary": "per-item render and completion are separate; selected completion paths show no local rollback", "durable_effects": ["render result", "physical-print confirmation", "completion audit"], "retry_rule": "retry failed or unconfirmed items only; never reprint an already confirmed item blindly", "special_rule": "batch success is the fold of per-item outcomes, not the last child result"},
    "RPT-11": {"command": "reporting.print_return_document", "source": "return_template", "transaction_boundary": "external template render and physical-print audit are separate", "durable_effects": ["render receipt", "physical-print audit"], "retry_rule": "same request/template hash returns original outcome; a new intentional print uses a new command id", "special_rule": "template/query/formula identity remains unproven and blocks parity"},
    "RPT-12": {"command": "reporting.print_sale_invoice", "source": "sale_print", "transaction_boundary": "render/print and retained audit history are not one proven atomic boundary", "durable_effects": ["print attempt", "physical-print evidence", "print audit event"], "retry_rule": "read audit by command/document/template identity before retry; historical repeated prints are not automatically duplicates", "special_rule": "cancelled or absent current sale requires explicit output policy and provenance"},
    "RPT-14": {"command": "reporting.export_production_detail", "source": "production_detail", "transaction_boundary": "file export is an external event and must not mutate ERP facts", "durable_effects": ["export job", "content hash", "expiry"], "retry_rule": "same command/filter/watermark returns the same content receipt or a typed expired-result outcome", "special_rule": "FetchReason mapping and result parity remain unproven"},
    "RPT-15": {"command": "reporting.export_stock_reference", "source": "stock_reference", "transaction_boundary": "query and external output are separate read-side stages", "durable_effects": ["query receipt", "external output receipt"], "retry_rule": "retry external delivery from a pinned query receipt; do not silently rerun on a new watermark", "special_rule": "ten exact query bindings do not prove runtime formula or result parity"},
    "RPT-18": {"command": "reporting.print_healthy_cardex", "source": "healthy_cardex", "transaction_boundary": "legacy print attempt precedes render; requested is not completed", "durable_effects": ["PRINT_REQUESTED", "RENDER_SUCCEEDED", "PHYSICAL_PRINT_CONFIRMED", "PRINT_FAILED_OR_CANCELLED"], "retry_rule": "retry only from explicit failed/cancelled state; rendered-unconfirmed requires physical evidence", "special_rule": "dynamic filter becomes typed allowlisted AST, never raw where text"},
    "RPT-19": {"command": "reporting.export_bank_statement", "source": "bank_summary", "transaction_boundary": "signed summary read and external output event remain separate", "durable_effects": ["summary query receipt", "external file receipt"], "retry_rule": "reuse pinned signed metrics and watermark; do not recalculate under a new source state as the same command", "special_rule": "UI absolute-value/color presentation never replaces signed machine values or unproven formulas"},
    "RPT-20": {"command": "reporting.import_or_command_bank_statement", "source": "bank_envelope", "transaction_boundary": "reporting import job delegates financial mutation to the five treasury command receipts", "durable_effects": ["import job receipt", "per-row validation", "delegated treasury command receipts"], "retry_rule": "retry only failed rows by stable import-row identity; never duplicate a committed treasury receipt", "special_rule": "financial outcome is owned by the treasury command envelope, not inferred from the import UI"},
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    command_surfaces = [x for x in data["closure"]["surfaces"] if x["command_surface_present"]]
    surfaces = []
    for surface in command_surfaces:
        profile = SURFACE_PROFILES[surface["contract_id"]]
        surfaces.append({
            "contract_id": surface["contract_id"],
            "legacy_type": surface["legacy_type"],
            "ownership_class": surface["ownership_class"],
            **profile,
            "legacy_explicit_command_id": False,
            "legacy_runtime_outcome_parity": "UNPROVEN",
            "target_request": COMMON_REQUEST,
            "target_response": COMMON_RESPONSE,
            "allowed_outcomes": OUTCOMES,
            "status": "TARGET_CONTRACT_DESIGNED_NOT_IMPLEMENTED",
        })
    sale = data["sale_print"]["summary"]
    summary = {
        "command_surface_count": len(surfaces),
        "outcome_code_count": len(OUTCOMES),
        "common_request_field_count": len(COMMON_REQUEST),
        "common_response_field_count": len(COMMON_RESPONSE),
        "legacy_explicit_command_id_count": sum(x["legacy_explicit_command_id"] for x in surfaces),
        "partial_failure_fixture_count": sum(x["case_id"].endswith(".command_partial_failure") for x in data["golden"]["cases"]),
        "print_render_path_count": data["print_batch"]["summary"]["render_path_count"],
        "completion_gated_render_path_count": data["print_batch"]["summary"]["completion_gated_render_path_count"],
        "sale_print_event_count": sale["sale_print_event_count"],
        "repeated_sale_printed_document_count": sale["repeated_sale_printed_document_count"],
        "post_terminal_cancel_sale_print_event_count": sale["post_terminal_cancel_sale_print_event_count"],
        "bank_delegated_command_count": data["bank_envelope"]["summary"]["command_contract_count"],
        "runtime_outcome_parity_proven_count": 0,
        "implemented_command_count": 0,
        "owner_approved_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "eight_surfaces": len(surfaces) == len(SURFACE_PROFILES) == 8,
        "five_outcomes": len(OUTCOMES) == 5,
        "request_response_complete": len(COMMON_REQUEST) == 10 and len(COMMON_RESPONSE) == 9,
        "legacy_idempotency_gap": summary["legacy_explicit_command_id_count"] == 0,
        "eight_partial_fixtures": summary["partial_failure_fixture_count"] == 8,
        "print_paths_pinned": summary["print_render_path_count"] == 7 and summary["completion_gated_render_path_count"] == 4,
        "sale_history_pinned": summary["sale_print_event_count"] == 308432 and summary["repeated_sale_printed_document_count"] == 34840 and summary["post_terminal_cancel_sale_print_event_count"] == 143,
        "delegation_pinned": summary["bank_delegated_command_count"] == 5 and data["treasury_envelope"]["summary"]["command_count"] == 12,
        "completion_not_attempt": any("requested is not completed" in x["transaction_boundary"] for x in surfaces),
        "external_exports_no_erp_mutation": all("external" in x["transaction_boundary"] for x in surfaces if x["contract_id"] in {"RPT-14", "RPT-15", "RPT-19"}),
        "runtime_zero": summary["runtime_outcome_parity_proven_count"] == summary["implemented_command_count"] == summary["owner_approved_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_outcome_envelope_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_STATIC_AND_CONTRACT_SYNTHESIS", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "outcome_contract": {"allowed_outcomes": OUTCOMES, "request_fields": COMMON_REQUEST, "response_fields": COMMON_RESPONSE, "invariants": ["print requested, render succeeded, physical print confirmed and audit committed are distinct states", "preview never emits completion", "external export never mutates ERP business facts", "batch result preserves every per-item outcome", "same CommandId and payload returns original outcome; a conflicting payload is rejected", "unknown or partial durable effect requires read-back before retry", "bank import delegates financial mutation identity and outcome to treasury receipts"]},
        "surfaces": surfaces,
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-002", "R-005", "R-006", "R-007", "R-017", "R-023", "R-036", "R-059"],
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"static_output_boundaries": "HIGH", "target_outcome_design": "HIGH", "runtime_effect_parity": "UNPROVEN"},
        "limits": ["No report, print, export, import or treasury command was executed.", "Historical repeated print events are not classified as defects without request identity.", "Template/query/formula and runtime result parity remain separate gates."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
