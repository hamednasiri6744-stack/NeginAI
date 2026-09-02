"""Build static command contracts for external, stock-confirm and manual vouchers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


TARGETS = {
    "VN.SDS.CreateVoucher.UI.ExternalVoucher.FormExternalVoucher": {
        "commands": [
            "accounting.external_voucher.generate",
            "accounting.external_voucher.confirm",
            "accounting.external_voucher.delete",
            "accounting.external_voucher.transfer",
        ],
        "boundary": "AUTOMATED_SOURCE_DOCUMENT_TO_ACCOUNTING_VOUCHER_ORCHESTRATION",
    },
    "VN.SDS.Stock.UI.ConfirmVocher.FormConfirmVocher": {
        "commands": ["stock_voucher.confirm_or_unconfirm"],
        "boundary": "FILTERED_STOCK_VOUCHER_CONFIRMATION_WORKLIST",
    },
    "VN.SDS.Treasury.UI.ManualVoucher.FormManualVoucherDataEntry2": {
        "commands": ["accounting.manual_voucher.save", "accounting.manual_voucher.cancel"],
        "boundary": "BALANCED_DEBIT_CREDIT_MANUAL_ACCOUNTING_COMMAND",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-form-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.all_form_contracts.read_text(encoding="utf-8-sig"))
    by_type = {row["type"]: row for row in source["forms"]}
    errors = [f"form missing: {name}" for name in TARGETS if name not in by_type]
    contracts = []
    all_calls: set[str] = set()
    for type_name, settings in TARGETS.items():
        if type_name not in by_type:
            continue
        row = by_type[type_name]
        contract = row["contract"]
        calls = contract["first_party_external_calls"]
        all_calls.update(calls)
        business_actions = sorted(
            call for call in calls
            if any(fragment in call for fragment in (
                ".DoExternalVoucher", ".SaveCommand", ".UpdateVocherConfirmUnonfirm",
                ".Confirm", ".UnConfirm", ".InternalCancelCommand",
            ))
        )
        config_calls = sorted(
            call for call in calls
            if any(fragment in call for fragment in ("ServerConfig", "FiscalYear", "UserSessionInfo"))
        )
        contracts.append({
            "form_type": type_name,
            "assembly": row["assembly"],
            "page_shape": row["page_shape"],
            "method_body_count": contract["method_body_count"],
            "write_like_methods": contract["write_like_methods"],
            "destructive_or_reversing_methods": contract["destructive_or_reversing_methods"],
            "permission_methods": contract["permission_methods"],
            "transaction_signal_calls": contract["transaction_signal_calls"],
            "business_action_calls": business_actions,
            "configuration_and_context_calls": config_calls,
            "called_module_families": contract["called_module_families"],
            "target_command_candidates": settings["commands"],
            "target_boundary": settings["boundary"],
            "owner_approved": False,
            "runtime_branch_effect_and_atomicity_proven": False,
        })
    fragments = {
        "EXTERNAL_VOUCHER_TYPE_AND_DC_SCOPE": ("ExternalVoucherType", "get_DCList"),
        "EXTERNAL_VOUCHER_DATE_WINDOW": ("MaxVoucherDate", "MinFreeOperationDate"),
        "EXTERNAL_VOUCHER_ISSUE_MODE": ("GetExternalVoucherIssueMode",),
        "SEPARATE_OFFICE_OR_HEADQUARTERS_CONFIGURATION": ("GetSeparateSaleOfficeCreateVoucher", "GetSeparateSetadCreateVoucher"),
        "GENERATE_CONFIRM_DELETE_TRANSFER_TRANSITIONS": ("DoExternalVoucherConfirmed", "DoExternalVoucherDelete", "DoExternalVoucherTransfer"),
        "STOCK_CONFIRM_FILTER_SCOPE": ("set_UserConfirmed", "set_VocherTypeCode", "set_StockDCRef"),
        "MANUAL_DEBIT_CREDIT_DIMENSION_GUARDS": ("CreditSLId", "DebitSLId", "FifthLedger", "SixthLedger", "SeventhLedger"),
        "MANUAL_VOUCHER_AMOUNT_AND_TYPE": ("get_Amount", "ManualVoucherType"),
    }
    signals = sorted(name for name, needles in fragments.items() if any(n.casefold() in call.casefold() for n in needles for call in all_calls))
    artifact = {
        "artifact": "varanegar_accounting_external_stock_confirm_manual_voucher_static_entrypoint_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_ALL_FORM_CALL_CONTRACTS",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "row_values_read_or_persisted": 0,
        },
        "summary": {
            "target_form_count": len(TARGETS),
            "resolved_target_form_count": len(contracts),
            "method_body_count": sum(row["method_body_count"] for row in contracts),
            "write_like_method_count": sum(len(row["write_like_methods"]) for row in contracts),
            "destructive_or_reversing_method_count": sum(len(row["destructive_or_reversing_methods"]) for row in contracts),
            "target_command_candidate_count": sum(len(row["target_command_candidates"]) for row in contracts),
            "unique_rule_signal_count": len(signals),
            "owner_approved_contract_count": 0,
            "runtime_branch_effect_and_atomicity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "rule_signals": signals,
        "validation_errors": errors,
        "limits": [
            "Compact static call contracts prove possible entrypoints, not effective configuration, selected rows, branch order or successful effects.",
            "The stock confirmation worklist may delegate transitions through inherited dual-list behavior not fully exposed in this compact form contract.",
            "External and manual voucher commands remain disabled for target implementation until transitive SQL, balancing and Golden reconciliation close.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
