"""Build target command contracts and unexecuted acceptance obligations for treasury edits."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


COMMANDS = (
    {
        "command": "treasury.edit_cash_receipt_instrument",
        "legacy_form": "TreasuryOld.Forms.frmCashEdit",
        "aggregate": "cash_receipt_instrument",
        "input_fields": ["command_id", "expected_version", "receipt_id", "cash_detail_id", "customer_id", "amount", "comment", "organization_context"],
        "authoritative_targets": ["cash instrument aggregate", "cash detail", "receipt amount projection", "audit/outbox"],
        "source_anchors": ["dbo.RCash", "dbo.RCashDetail", "dbo.Receipt"],
        "special_guards": ["receipt is editable", "amount is positive and within settlement/receipt invariant", "safe/currency context is compatible"],
    },
    {
        "command": "treasury.edit_received_cheque",
        "legacy_form": "TreasuryOld.Forms.frmChequeEdit",
        "aggregate": "received_cheque",
        "input_fields": ["command_id", "expected_version", "cheque_id", "receipt_id", "bank_id", "cheque_type_id", "cheque_no", "cheque_date", "amount", "branch_code", "branch_name", "account_no", "account_name", "issued_for", "comment", "customer_id", "sayad_no", "organization_context"],
        "authoritative_targets": ["received cheque aggregate", "cheque change history", "receipt linkage", "accounting projection", "audit/outbox"],
        "source_anchors": ["dbo.RCheque", "Acc.TblCheque", "dbo.tblRChequeLog", "dbo.Receipt"],
        "special_guards": ["cheque status is editable", "number/date/amount rules", "duplicate number policy", "Sayad policy is owner-confirmed", "manual customer and receipt linkage are consistent"],
    },
    {
        "command": "treasury.edit_received_bank_draft",
        "legacy_form": "TreasuryOld.Forms.frmRCashDraftEdit",
        "aggregate": "received_bank_draft",
        "input_fields": ["command_id", "expected_version", "draft_id", "receipt_id", "bank_id", "bank_account_id", "draft_type_id", "draft_no", "draft_date", "arrival_date", "amount", "branch_code", "branch_name", "customer_id", "comment", "organization_context"],
        "authoritative_targets": ["received bank draft aggregate", "receipt linkage", "bank-order accounting projection", "audit/outbox"],
        "source_anchors": ["dbo.RCashDraft", "Acc.TblBankOrders", "dbo.Receipt"],
        "special_guards": ["draft status is editable", "number/date/arrival-date/amount rules", "duplicate number policy", "bank account is allowed for user scope", "manual customer and receipt linkage are consistent"],
    },
)

CASE_TEMPLATES = (
    ("ALLOW_HAPPY_PATH", "authorized valid edit commits one aggregate version and declared effects"),
    ("DENY_CAPABILITY", "missing edit capability creates no mutation"),
    ("DENY_ORGANIZATION_SCOPE", "out-of-scope DC/office/safe/account creates no mutation"),
    ("REQUIRED_FIELD_MISSING", "required business input is rejected before mutation"),
    ("INVALID_AMOUNT", "zero, negative, overflow or precision-invalid amount is rejected"),
    ("INVALID_BUSINESS_DATE", "invalid Persian date or forbidden business-date boundary is rejected"),
    ("INVALID_STATUS_TRANSITION", "non-editable lifecycle state is rejected"),
    ("STALE_EXPECTED_VERSION", "optimistic concurrency conflict creates no mutation"),
    ("REPLAY_SAME_PAYLOAD", "same command_id and fingerprint returns original result with no duplicate effect"),
    ("REPLAY_DIFFERENT_PAYLOAD", "same command_id with different fingerprint is rejected as conflict"),
    ("FAULT_BEFORE_PRIMARY_WRITE", "transaction rolls back and command remains safely retryable"),
    ("FAULT_AFTER_PRIMARY_BEFORE_DEPENDENT_EFFECT", "no partial accepted outcome; rollback or explicit recoverable unknown"),
    ("FAULT_AFTER_COMMIT_BEFORE_RESPONSE", "retry returns the committed original outcome"),
    ("RECONCILE_PRIMARY_AND_RECEIPT", "aggregate and receipt/control total reconcile"),
    ("RECONCILE_HISTORY_ACCOUNTING_OUTBOX", "history, accounting projection and outbox effects reconcile exactly once"),
    ("LEGACY_VIEW_TRIGGER_EFFECT_PARITY", "retained/replaced legacy view-trigger effects match approved snapshot"),
    ("NO_VARANEGAR_WRITE_BACK", "target command and tests never write to Varanegar or the clone"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-paths", required=True, type=Path)
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--trigger-semantics", required=True, type=Path)
    parser.add_argument("--view-lineage", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    inputs = {name: json.loads(path.read_text(encoding="utf-8-sig")) for name, path in {
        "command_paths": args.command_paths,
        "source_model": args.source_model,
        "trigger_semantics": args.trigger_semantics,
        "view_lineage": args.view_lineage,
    }.items()}
    errors = [f"{name} source is not PASS" for name, payload in inputs.items() if payload.get("validation") != "PASS"]

    contracts = []
    obligations = []
    for command in COMMANDS:
        contracts.append({
            **command,
            "target_module": "receivables_treasury",
            "authorization": {"capability": command["command"], "scope": "organization_context plus instrument-specific safe/account scope", "deny_by_default": True},
            "transaction_contract": "one local transaction owns aggregate, receipt/control-total, history/accounting projection and outbox receipt",
            "idempotency_contract": "unique command_id plus payload fingerprint; same replay returns original, different replay conflicts",
            "concurrency_contract": "expected_version compare-and-swap",
            "failure_contract": "rollback before commit; after commit original result is recoverable from command receipt",
            "reconciliation_contract": "source snapshot/crosswalk plus count/amount/status/history/accounting effect controls",
            "source_write_policy": "VARANEGAR_AND_CLONE_READ_ONLY_NO_WRITE_BACK",
            "owner_approved": False,
            "implementation_ready": False,
        })
        for index, (case_type, expectation) in enumerate(CASE_TEMPLATES, 1):
            obligations.append({
                "case_id": f"TREAS-{command['aggregate'].upper()}-{index:02d}",
                "surface": command["command"],
                "target_module": "receivables_treasury",
                "case_type": case_type,
                "expected_outcome": expectation,
                "execution_target": "TARGET_ISOLATED_TEST_DATABASE_ONLY",
                "status": "UNEXECUTED_ACCEPTANCE_OBLIGATION",
                "owner_approved": False,
                "legacy_or_clone_command_executed": False,
            })

    summary = {
        "target_command_contract_count": len(contracts),
        "acceptance_obligation_count": len(obligations),
        "obligation_per_command_count": len(CASE_TEMPLATES),
        "owner_approved_contract_count": sum(row["owner_approved"] for row in contracts),
        "implemented_contract_count": sum(row["implementation_ready"] for row in contracts),
        "executed_acceptance_obligation_count": sum(row["status"] != "UNEXECUTED_ACCEPTANCE_OBLIGATION" for row in obligations),
        "runtime_effect_or_result_parity_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "negin_erp_treasury_edit_target_command_contracts_and_unexecuted_acceptance_obligations",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_CONTRACT_DERIVATION_FROM_REDACTED_STATIC_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_values_identities_or_grants_read_or_persisted": 0,
            "owner_approval_implementation_or_production_readiness_inferred": 0,
        },
        "summary": summary,
        "contracts": contracts,
        "acceptance_obligations": obligations,
        "promotion_gate": "obligations become executable Golden cases only after owner field/rule decisions and target test fixture implementation",
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
