"""Build a module-level treasury command outcome/retry envelope from pinned evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "edit": "artifacts/varanegar_analysis/ui/varanegar_treasury_edit_command_paths_20260827.json",
    "undo": "artifacts/varanegar_analysis/domains/received_cheque_undo_runtime_boundary_20260829.json",
    "delete": "artifacts/varanegar_analysis/domains/received_cheque_delete_runtime_boundary_20260829.json",
    "ngt_payment": "artifacts/varanegar_analysis/domains/ngt_payment_runtime_boundary_20260829.json",
    "ngt_replication": "artifacts/varanegar_analysis/domains/ngt_payment_replication_runtime_boundary_20260829.json",
    "bank_envelope": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_command_envelope_20260827.json",
    "bank_transaction": "artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_transaction_boundary_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_24h_continuation_wave01_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}

    commands = [
        {
            "id": "TR-CMD-01",
            "family": "legacy_edit",
            "command": "cash_receipt.edit",
            "evidence_level": "HASH_PINNED_STATIC_PATH",
            "transaction_owner": "legacy UI transaction Start/Commit/RollBack",
            "mutation_set": ["cash receipt", "receipt amount", "optional detail/customer link"],
            "legacy_outcome_ambiguity": "branch order and committed effect are not runtime-proven",
            "target_retry_rule": "same command_id returns the original typed outcome; otherwise read back receipt version and amount",
        },
        {
            "id": "TR-CMD-02",
            "family": "legacy_edit",
            "command": "received_cheque.edit",
            "evidence_level": "HASH_PINNED_STATIC_PATH",
            "transaction_owner": "legacy UI transaction Start/Commit/RollBack",
            "mutation_set": ["received cheque fields", "optional detail/customer link"],
            "legacy_outcome_ambiguity": "PreUpdate and inline SQL co-occur; successful atomic effect is not runtime-proven",
            "target_retry_rule": "read back by cheque identity and expected_version before retry",
        },
        {
            "id": "TR-CMD-03",
            "family": "legacy_edit",
            "command": "received_bank_draft.edit",
            "evidence_level": "HASH_PINNED_STATIC_PATH",
            "transaction_owner": "legacy UI transaction Start/Commit/RollBack",
            "mutation_set": ["received draft fields", "amount validation side effects"],
            "legacy_outcome_ambiguity": "validation and edit methods both expose transaction signals; runtime branch is unproven",
            "target_retry_rule": "read back draft amount/version and validation ledger before retry",
        },
        {
            "id": "TR-CMD-04",
            "family": "cheque_lifecycle",
            "command": "received_cheque.undo",
            "evidence_level": "HASH_PINNED_STATIC_PATH_WITH_CLONE_AGGREGATE",
            "transaction_owner": "outer form plus nested adapter transaction signals",
            "mutation_set": ["current cheque pointer", "history leaf", "cession branch when selected"],
            "legacy_outcome_ambiguity": "runtime form and branch-specific cession/delete reachability are unproven",
            "target_retry_rule": "read current pointer and ordered history; duplicate command_id returns original leaf transition",
        },
        {
            "id": "TR-CMD-05",
            "family": "cheque_lifecycle",
            "command": "received_cheque.delete",
            "evidence_level": "HASH_PINNED_STATIC_PATH_WITH_CLONE_AGGREGATE",
            "transaction_owner": "UNPROVEN for legacy dataset delete path",
            "mutation_set": ["received cheque dataset row", "retained lifecycle evidence"],
            "legacy_outcome_ambiguity": "legacy form has no explicit transaction signal and new form has no observed delete/update signal",
            "target_retry_rule": "missing current row is not success proof; reconcile immutable delete receipt and history before retry",
        },
        {
            "id": "TR-CMD-06",
            "family": "ngt_payment",
            "command": "tour_payment.save_changes",
            "evidence_level": "HASH_PINNED_STATIC_PATH",
            "transaction_owner": "EF DbContext transaction in SaveTourPaymentChanges",
            "mutation_set": ["payment headers", "payment details", "soft removals", "allocation totals"],
            "legacy_outcome_ambiguity": "57 underallocated clone rows exist; runtime effect parity is unproven",
            "target_retry_rule": "read aggregate allocation and version by tour/payment identity before retry",
        },
        {
            "id": "TR-CMD-07",
            "family": "ngt_replication",
            "command": "tour_payment.replicate_and_write_crosswalk",
            "evidence_level": "HASH_PINNED_STATIC_CONTROL_FLOW",
            "transaction_owner": "multiple commit signals around replication and crosswalk writeback",
            "mutation_set": ["back-office receipt", "receipt crosswalk fields", "replication progress"],
            "legacy_outcome_ambiguity": "linear IL shows commit before and after setters but one atomic runtime path is unproven",
            "target_retry_rule": "crosswalk identity is the idempotency anchor; ambiguous results require both-side readback",
        },
    ]
    for index, bank in enumerate(documents["bank_envelope"]["command_contracts"], start=8):
        commands.append(
            {
                "id": f"TR-CMD-{index:02d}",
                "family": "bank_reconciliation_target",
                "command": f"bank_reconciliation.{bank['command']}",
                "evidence_level": "TARGET_DESIGN_NOT_IMPLEMENTED",
                "transaction_owner": "one request-scoped application unit of work required",
                "mutation_set": bank["mutation_set"],
                "legacy_outcome_ambiguity": "target command execution and authenticated UAT count are zero",
                "target_retry_rule": "unique command_id plus session/version/snapshot readback returns the original typed outcome",
            }
        )

    target_envelope = {
        "request_fields": [
            "command_id",
            "actor_capabilities",
            "resource_scope",
            "fiscal_year",
            "operation_date",
            "expected_version",
            "policy_snapshot_version",
            "source_identity",
            "requested_transition",
        ],
        "guard_order": ["authenticate", "authorize action", "authorize resource scope", "validate state/version", "validate policy/date", "check idempotency", "begin unit of work"],
        "outcome_codes": ["COMMITTED", "REJECTED_NO_EFFECT", "REJECTED_WITH_DURABLE_EFFECT", "UNKNOWN_REQUIRES_READBACK"],
        "response_fields": ["outcome_code", "committed", "aggregate_version", "durable_effect_summary", "retryable", "correlation_id", "original_command_id"],
        "atomicity": "one explicit transaction owner per command; state, audit and outbox commit together",
        "idempotency": "unique command_id scoped to command family; duplicate payload returns original outcome; conflicting payload is rejected",
        "readback": "ambiguous transport/error paths read current aggregate, ordered history, crosswalk and audit/outbox before retry",
    }
    summary = {
        "command_count": len(commands),
        "legacy_static_command_count": sum(command["evidence_level"] != "TARGET_DESIGN_NOT_IMPLEMENTED" for command in commands),
        "target_design_only_command_count": sum(command["evidence_level"] == "TARGET_DESIGN_NOT_IMPLEMENTED" for command in commands),
        "legacy_edit_command_count": sum(command["family"] == "legacy_edit" for command in commands),
        "cheque_lifecycle_command_count": sum(command["family"] == "cheque_lifecycle" for command in commands),
        "ngt_payment_or_replication_command_count": sum(command["family"].startswith("ngt_") for command in commands),
        "bank_reconciliation_target_command_count": sum(command["family"] == "bank_reconciliation_target" for command in commands),
        "target_outcome_code_count": len(target_envelope["outcome_codes"]),
        "runtime_effect_parity_proven_count": 0,
        "executed_acceptance_case_count": 0,
        "owner_approved_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    undo = documents["undo"]["managed_undo_contract"]
    delete = documents["delete"]["managed_delete_contract"]
    payment = documents["ngt_payment"]["payment_save_transaction_and_allocation_contract"]
    replication = documents["ngt_replication"]["replicate_tour_crosswalk_writeback_contract"]
    checks = {
        "all_sources_pass": all(document["validation"] == "PASS" for document in documents.values()),
        "twelve_commands": summary["command_count"] == 12,
        "seven_static_five_design": summary["legacy_static_command_count"] == 7 and summary["target_design_only_command_count"] == 5,
        "three_edit_paths": documents["edit"]["summary"]["mutation_command_method_count"] == 3,
        "undo_transaction_signals": undo["legacy_undo_starts_transaction_before_delete_call"] and undo["adapter_has_rollback_signal"],
        "delete_transaction_gap_preserved": delete["legacy_delete_has_explicit_transaction_signal"] is False,
        "ngt_payment_transaction_pinned": payment["explicit_begin_transaction"] and payment["explicit_commit"] and payment["explicit_rollback"],
        "replication_ambiguity_preserved": replication["commit_exists_before_payment_setters_in_linear_il"] and replication["commit_exists_after_payment_setters_in_linear_il"],
        "five_bank_target_commands_unimplemented": documents["bank_envelope"]["summary"]["command_contract_count"] == 5
        and documents["bank_envelope"]["summary"]["implemented_command_count"] == 0,
        "bank_unit_of_work_required": documents["bank_transaction"]["target_contract"]["single_application_service_transaction_owner_required"],
        "base_counts_stable": documents["risk"]["summary"]["risk_count"] == 84
        and documents["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_treasury_command_outcome_envelope_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_EVIDENCE_SYNTHESIS",
            "database_connections": 0,
            "commands_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "sensitive_values_persisted": 0,
        },
        "summary": summary,
        "commands": commands,
        "target_outcome_retry_envelope": target_envelope,
        "risk_links": ["R-002", "R-005", "R-006", "R-007", "R-008", "R-023", "R-036", "R-043"],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ],
        "confidence": {"static_command_boundaries": "HIGH", "target_contract": "HIGH_DESIGN", "runtime_effect_parity": "UNPROVEN"},
        "limits": [
            "Bank-reconciliation commands are target designs, not implemented legacy paths.",
            "Static transaction calls do not prove runtime branch selection or atomic physical enlistment.",
            "No retry, UAT, owner approval or production incident was executed or observed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
