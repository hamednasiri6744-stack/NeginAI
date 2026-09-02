"""Build an offline cross-domain matrix for Varanegar command outcomes and commits."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "voucher": "artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json",
    "stock": "artifacts/varanegar_analysis/domains/stock_projection_validation_boundary_20260829.json",
    "supplier_return": "artifacts/varanegar_analysis/ui/varanegar_supplier_receipt_component_diagnostic_contract_20260827.json",
    "return_sql": "artifacts/varanegar_analysis/domains/return_issue_cancel_boundary_20260829.json",
    "return_runtime": "artifacts/varanegar_analysis/domains/return_issue_cancel_runtime_boundary_20260829.json",
    "distribution_sql": "artifacts/varanegar_analysis/domains/distribution_exit_lifecycle_boundary_20260829.json",
    "distribution_runtime": "artifacts/varanegar_analysis/domains/distribution_exit_runtime_boundary_20260829.json",
    "sale_conversion_sql": "artifacts/varanegar_analysis/domains/sale_conversion_state_boundary_20260829.json",
    "sale_conversion_runtime": "artifacts/varanegar_analysis/domains/sale_conversion_runtime_boundary_20260829.json",
    "sale_cancel_sql": "artifacts/varanegar_analysis/domains/sale_cancellation_boundary_20260829.json",
    "sale_cancel_runtime": "artifacts/varanegar_analysis/domains/sale_cancellation_runtime_boundary_20260829.json",
    "print_runtime": "artifacts/varanegar_analysis/domains/sale_invoice_print_runtime_boundary_20260829.json",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case(
    case_id: str,
    domain: str,
    command: str,
    failure_channel: str,
    write_position: str,
    durability_decision: str,
    transaction_owner: str,
    classification: str,
    target_rule: str,
    evidence: list[str],
    caveat: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "domain": domain,
        "command": command,
        "business_failure_channel": failure_channel,
        "durable_write_position_relative_to_failure": write_position,
        "legacy_durability_decision": durability_decision,
        "physical_transaction_owner": transaction_owner,
        "outcome_classification": classification,
        "target_contract_rule": target_rule,
        "evidence": evidence,
        "caveat": caveat,
    }


def build() -> dict[str, Any]:
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    data = {name: _load(name) for name in SOURCES}
    if any(
        "validation" in value and value.get("validation") != "PASS"
        for value in data.values()
    ):
        raise AssertionError("all source artifacts must be validated")

    voucher = data["voucher"]
    business = voucher["deployed_call_and_transaction_contract"]["business_boundary"]
    procedures = voucher["procedure_contracts"]
    stock = data["stock"]["static_validation_and_projection_contract"]
    supplier = data["supplier_return"]["desktop_save_boundary"]
    return_sql = data["return_sql"]["static_issue_cancel_contract"]
    return_runtime = data["return_runtime"]["managed_return_contract"]
    dist_sql = data["distribution_sql"]["static_exit_contract"]
    dist_runtime = data["distribution_runtime"]["managed_exit_contract"]
    conversion_sql = data["sale_conversion_sql"]["static_conversion_and_projection_contract"]
    conversion_runtime = data["sale_conversion_runtime"]["managed_conversion_contract"]
    cancel_sql = data["sale_cancel_sql"]["static_cancellation_contract"]
    cancel_runtime = data["sale_cancel_runtime"]["managed_cancellation_contract"]
    print_runtime = data["print_runtime"]["managed_invoice_print_contract"]

    assertions = {
        "accounting_issue_result_precedes_write_but_business_commits": (
            business["message_type_one_is_validation_error"]
            and business["result_is_set_before_commit_even_for_business_error_rows"]
            and procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                "message_type_1_result_precedes_persistent_issue_mutation"
            ]
        ),
        "accounting_transfer_can_write_before_returned_error": (
            procedures["dbo.usp_DoExternalVoucherTransfer"]["semantic_signals"][
                "deletes_set_voucher_no_before_validation"
            ]
            and procedures["dbo.usp_DoExternalVoucherTransfer"]["semantic_signals"][
                "validation_can_return_without_exception"
            ]
            and procedures["dbo.usp_DoExternalVoucherTransfer"]["semantic_signals"][
                "returns_message_type_1_for_business_errors"
            ]
        ),
        "stock_confirm_message_is_post_commit_advisory": (
            stock["confirm_first_commit_precedes_after_validation"]
            and stock["confirm_appends_after_message_without_abort_guard"]
        ),
        "stock_unconfirm_message_does_not_block_commit": (
            stock["unconfirm_after_validation_precedes_commit"]
            and stock["unconfirm_appends_after_message_then_commits_without_abort_guard"]
        ),
        "supplier_return_desktop_caller_blocks_nonempty_message": (
            supplier["nonempty_validator_message_builds_validation_failure_before_commit"]
            and supplier["nonempty_validator_message_has_dispose_before_commit"]
            and supplier["empty_message_branch_targets_commit_block"]
        ),
        "sales_return_sql_uses_local_rollback_for_late_validation": (
            return_sql["generate_has_transaction_or_savepoint_commit_and_rollback"]
            and return_sql["generate_performs_some_validation_after_voucher_inserts"]
            and return_runtime["adapter_generate_has_explicit_commit"] is False
            and return_runtime["managed_to_sql_physical_transaction_enlistment_proven"] is False
        ),
        "distribution_commands_depend_on_caller_transaction": (
            dist_sql["create_has_no_local_transaction_or_savepoint"]
            and dist_sql["remove_has_no_local_begin_or_commit_but_has_catch_rollback"]
            and dist_runtime["normal_issue_ui_constructs_context_then_calls_create_then_commits"]
            and dist_runtime["normal_remove_ui_validates_then_constructs_context_removes_and_commits"]
            and dist_runtime["physical_transaction_enlistment_across_ui_and_nested_adapter_contexts_proven"]
            is False
        ),
        "sale_conversion_has_nested_commits_and_branchable_rollback": (
            conversion_sql["orchestrator_has_with_out_rollback_parameter_and_branches"]
            and conversion_sql["orchestrator_has_local_transaction_try_catch_commit_and_rollback"]
            and conversion_runtime["selected_methods_have_nested_business_and_adapter_commit_signals"]
            and conversion_runtime["physical_transaction_enlistment_across_business_and_adapter_contexts_proven"]
            is False
        ),
        "sale_cancel_sql_is_transaction_owner": (
            cancel_sql["cancel_has_local_transaction_try_catch_commit_and_rollback"]
            and cancel_runtime["ui_cancel_has_no_explicit_context_commit_or_rollback"]
            and cancel_runtime["adapter_has_explicit_commit_signal"] is False
            and cancel_runtime["adapter_has_explicit_rollback_signal"] is False
        ),
        "print_audit_is_success_gated_separate_commit": (
            print_runtime["single_print_calls_report_then_marks_only_after_printed_completed"]
            and print_runtime["collection_print_calls_report_then_marks_only_after_printed_completed"]
            and print_runtime["print_completion_uses_context_save_then_commit"]
            and print_runtime["print_completion_has_no_explicit_rollback"]
        ),
    }
    failed = sorted(name for name, passed in assertions.items() if not passed)

    typed_rejection_rule = (
        "REJECTED is a typed non-committing command outcome; display text is metadata and never "
        "controls durability."
    )
    atomic_failure_rule = (
        "Every failed precondition or postcondition aborts one server-owned transaction and leaves "
        "an immutable failed-attempt receipt without business writes."
    )
    cases = [
        _case(
            "OC-01",
            "accounting",
            "issue external accounting batch",
            "typed numeric result row interpreted as business validation",
            "business-error row is produced before persistent issue writes",
            "managed Business still reaches Commit after setting the validation result",
            "managed Business DataContext on the ordinary desktop path",
            "SAFE_ONLY_BY_CURRENT_STATEMENT_ORDER",
            typed_rejection_rule,
            ["voucher.business_boundary", "voucher.usp_DoExternalVoucher"],
            "No business-error mutation incident is asserted; safety depends on the current pre-write ordering.",
        ),
        _case(
            "OC-02",
            "accounting",
            "transfer external batch to journal",
            "typed numeric business-error result returned without exception",
            "number-crosswalk cleanup can occur before validation",
            "ordinary managed caller can Commit the rejected call's pre-validation cleanup",
            "managed Business DataContext; procedure has no local transaction",
            "REJECTED_RESULT_WITH_COMMITTABLE_PREWRITE",
            typed_rejection_rule,
            ["voucher.business_boundary", "voucher.usp_DoExternalVoucherTransfer"],
            "The current snapshot is clean; this is a reachable static path, not an observed retained inconsistency.",
        ),
        _case(
            "OC-03",
            "inventory",
            "confirm inventory voucher",
            "non-empty output message appended to the result",
            "direct no-ambient path commits header before After validation",
            "message has no abort guard and cannot reverse the preceding Commit",
            "SQL procedure for the direct path; an outer caller may add an ambient transaction",
            "POST_COMMIT_ADVISORY_FAILURE",
            atomic_failure_rule,
            ["stock.confirm_first_commit", "stock.confirm_after_message"],
            "No current validation-failure occurrence was observed.",
        ),
        _case(
            "OC-04",
            "inventory",
            "unconfirm inventory voucher",
            "non-empty output message appended to the result",
            "After validation runs before Commit",
            "message is not tested, so the caller proceeds to Commit",
            "SQL procedure or ambient caller, depending on entry route",
            "PRECOMMIT_ADVISORY_FAILURE",
            atomic_failure_rule,
            ["stock.unconfirm_after_before_commit", "stock.unconfirm_after_message"],
            "The static ordering proves capability, not a runtime failing branch.",
        ),
        _case(
            "OC-05",
            "procurement_payables",
            "save supplier return in desktop route",
            "non-empty validator message interpreted by the managed caller",
            "caller checks the message before its Commit block",
            "caller creates validation failure, disposes context and exits before Commit",
            "desktop managed DataContext",
            "CALLER_ENFORCED_REJECTION",
            typed_rejection_rule,
            ["supplier_return.desktop_save_boundary"],
            "The separate SDSNET SQL save route does not share this complete blocking behavior.",
        ),
        _case(
            "OC-06",
            "sales",
            "issue sales return inventory voucher",
            "SQL exception/catch rollback for late validation",
            "some packaging, batch and item checks occur after voucher inserts",
            "local transaction or savepoint rolls back on the exception path",
            "SQL generator; managed/SQL physical enlistment remains unproven",
            "LATE_VALIDATION_WITH_LOCAL_ROLLBACK",
            atomic_failure_rule,
            ["return_sql.generate", "return_runtime.generate_adapter"],
            "Static evidence does not prove every runtime branch or connection enlistment.",
        ),
        _case(
            "OC-07",
            "distribution",
            "issue or remove distribution exit",
            "exception or returned query result, route-dependent",
            "multi-table writes have no local transaction owner in the selected procedures",
            "ordinary UI commits a caller context after the nested Business/Adapter call",
            "caller/ambient transaction; physical nested-context enlistment unproven",
            "CALLER_DEPENDENT_ATOMICITY",
            atomic_failure_rule,
            ["distribution_sql.static_exit_contract", "distribution_runtime.managed_exit_contract"],
            "Current aggregate state is clean and does not prove all route executions.",
        ),
        _case(
            "OC-08",
            "sales",
            "convert order to sale",
            "exception with branchable rollback behavior",
            "orchestrator writes a multi-domain graph under a local transaction",
            "managed Business and Adapter both expose Commit signals; rollback can be branch-modified",
            "nested managed and SQL owners; one shared physical transaction is unproven",
            "NESTED_COMMIT_AND_BRANCHABLE_ROLLBACK",
            atomic_failure_rule,
            ["sale_conversion_sql.orchestrator", "sale_conversion_runtime.managed_conversion_contract"],
            "The runtime value and reachability of the no-rollback branch are not proven.",
        ),
        _case(
            "OC-09",
            "sales",
            "cancel sale",
            "SQL exception/catch rollback",
            "sale, payment, detail, stock and order effects occur inside a local SQL transaction plus triggers",
            "the procedure owns Commit/Rollback; selected managed methods do not",
            "SQL cancellation procedure",
            "SQL_OWNED_ATOMIC_COMMAND",
            atomic_failure_rule,
            ["sale_cancel_sql.static_cancellation_contract", "sale_cancel_runtime.managed_cancellation_contract"],
            "Trigger side effects remain part of the legacy correctness boundary.",
        ),
        _case(
            "OC-10",
            "reporting_documents",
            "record sale invoice print completion",
            "print engine completion status gates a separate persistence command",
            "audit rows are saved only after PrintedCompleted",
            "audit persistence uses Save then Commit without explicit managed rollback",
            "print-completion managed DataContext, separate from the print engine",
            "SUCCESS_GATED_SEPARATE_AUDIT_COMMIT",
            "Printing and print-audit recording are separate typed outcomes; a durable receipt must expose partial success and support idempotent reconciliation.",
            ["print_runtime.managed_invoice_print_contract"],
            "Template query parity and every runtime failure branch remain unexecuted.",
        ),
    ]

    classifications = sorted({case["outcome_classification"] for case in cases})
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
        "artifact": "varanegar_command_outcome_commit_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "purpose": "cross-domain outcome, validation, commit and rollback taxonomy for ERP reconstruction",
            "domains": sorted({case["domain"] for case in cases}),
            "source_artifact_count": len(SOURCES),
        },
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "raw_business_rows_ids_names_messages_or_sql_definitions_persisted": 0,
        },
        "source_manifest": manifest,
        "source_assertions": assertions,
        "failed_assertions": failed,
        "outcome_classes": classifications,
        "cases": cases,
        "target_invariants": [
            "A display message is never a transaction-control primitive.",
            "REJECTED, ACCEPTED, ACCEPTED_WITH_WARNING, PARTIAL_SUCCESS and UNKNOWN are explicit typed outcomes.",
            "Only ACCEPTED may advance business state; warnings are metadata on an accepted receipt.",
            "Every command has one observable server-owned physical transaction boundary.",
            "All business preconditions run before the first durable write whenever technically possible.",
            "A failed postcondition aborts the same transaction; it is not appended after Commit.",
            "A partial external side effect uses an outbox/inbox and a reconcilable receipt rather than pretending atomicity.",
            "Rollback failure or unknown commit outcome is quarantined as UNKNOWN, never reported as success.",
        ],
        "summary": {
            "case_count": len(cases),
            "domain_count": len({case["domain"] for case in cases}),
            "outcome_class_count": len(classifications),
            "case_with_unproven_physical_transaction_owner_count": sum(
                "unproven" in case["physical_transaction_owner"].lower() for case in cases
            ),
            "message_or_result_control_case_count": sum(
                any(token in case["business_failure_channel"].lower() for token in ("message", "result"))
                for case in cases
            ),
            "failed_assertion_count": len(failed),
        },
        "evidence_limits": [
            "This is an offline synthesis of previously validated static and aggregate artifacts.",
            "Static SQL and IL ordering proves code shape, not branch frequency, actor, production routing or runtime success.",
            "No new database, UI, report, procedure, trigger or assembly execution occurred.",
            "Clean current aggregates do not remove reachable failure-path risks.",
        ],
    }


def main() -> int:
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
