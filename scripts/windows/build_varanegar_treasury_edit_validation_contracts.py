"""Build focused static validation and configuration contracts for treasury edits."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


SELECTED = {
    "TreasuryOld.Forms.frmCashEdit": {"BtnOk_Click": "combined_validation_and_command"},
    "TreasuryOld.Forms.frmChequeEdit": {"CheckRules": "validation", "btnOk_Click": "command_after_validation"},
    "TreasuryOld.Forms.frmRCashDraftEdit": {
        "IsDataValid": "validation",
        "ValidateRCashDraftAmount": "balance_validation",
        "txtRCashDraftDate_Leave": "derived_arrival_date",
        "btnOk_Click": "command_after_validation",
    },
}


def _signals(calls: set[str], fragments: list[str]) -> list[str]:
    text = "\n".join(sorted(calls) + fragments).casefold()
    checks = {
        "PERSIAN_DATE_VALIDATION_OR_CONVERSION": ("persiandate", "solardateisvalid"),
        "OPERATION_OR_LAST_DATE_BOUNDARY": ("oprdate", "get_lastdate"),
        "RECEIPT_STATUS_GUARD": ("get_receiptstatusid",),
        "RECEIPT_INSTRUMENT_TOTAL_GUARD": ("get_rbankdrafts", "get_rcashs", "get_rcheques", "get_rcashdrafts"),
        "SETTLEMENT_AMOUNT_GUARD": ("settlementadapter", "get_settlementamount"),
        "SAFE_OR_BANK_BALANCE_GUARD": ("getsafecashbalance", "getcashbalancebydate", "getbalanceamountbydate"),
        "CUSTOMER_REQUIRED_CONFIGURATION": ("get_customeridrequired",),
        "DUPLICATE_INSTRUMENT_NUMBER_CONFIGURATION": ("notinsertduplicatercashdraftno",),
        "FUTURE_DATE_CONFIGURATION": ("insertwithdategreatherthantoday",),
        "ARRIVAL_DATE_INTERVAL_CONFIGURATION": ("get_vosuldateinterval",),
        "CHEQUE_STATUS_OR_LAST_HISTORY_GUARD": ("get_rchequestatusid", "statref = 3"),
        "FIELD_FOCUS_ON_REJECTION": ("control.focus",),
        "TRANSACTION_ENVELOPE": ("transaction.start", "transaction.commit", "transaction.rollback"),
        "DIRECT_SQL_MUTATION": ("executenonquery", "update acc.tbl", "update receipt", "update rcashdetail"),
    }
    return sorted(name for name, needles in checks.items() if any(needle in text for needle in needles))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    contracts = []
    errors = []
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] not in SELECTED:
                continue
            wanted = SELECTED[target["type"]]
            selected_methods = []
            for method in target["methods"]:
                if method["method"] not in wanted:
                    continue
                calls = set(method["calls"])
                fragments = sorted({row["safe_literal"] for row in method["string_literals"] if row.get("safe_literal")})
                selected_methods.append({
                    "method": method["method"],
                    "role": wanted[method["method"]],
                    "instruction_count": method["instruction_count"],
                    "referenced_form_fields": sorted(ref for ref in method["referenced_fields"] if ref.startswith(target["type"] + ".")),
                    "data_or_configuration_calls": sorted(call for call in calls if call.startswith("TreasuryOld.") or call.startswith("Receipt.")),
                    "date_validation_or_conversion_calls": sorted(call for call in calls if "Date" in call or "Persian" in call),
                    "error_or_focus_calls": sorted(call for call in calls if call.startswith("Error.") or call.endswith(".Focus")),
                    "allowlisted_sql_or_business_fragments": fragments,
                    "rule_signals": _signals(calls, fragments),
                    "exact_branch_condition_message_and_effect_proven": False,
                })
            missing = set(wanted) - {row["method"] for row in selected_methods}
            if missing:
                errors.append(f"missing methods for {target['type']}: {','.join(sorted(missing))}")
            contracts.append({
                "assembly": assembly["file"],
                "assembly_sha256": assembly["sha256"],
                "form_type": target["type"],
                "selected_method_count": len(selected_methods),
                "methods": selected_methods,
                "rule_interpretation_status": "STATIC_RULE_SIGNAL_REQUIRES_OWNER_AND_RUNTIME_GOLDEN_PROOF",
            })
    all_methods = [method for row in contracts for method in row["methods"]]
    summary = {
        "target_form_count": len(SELECTED),
        "resolved_target_form_count": len(contracts),
        "selected_validation_or_command_method_count": len(all_methods),
        "selected_instruction_count": sum(row["instruction_count"] for row in all_methods),
        "unique_referenced_form_field_count": len({field for row in all_methods for field in row["referenced_form_fields"]}),
        "unique_rule_signal_count": len({signal for row in all_methods for signal in row["rule_signals"]}),
        "method_with_transaction_signal_count": sum("TRANSACTION_ENVELOPE" in row["rule_signals"] for row in all_methods),
        "method_with_direct_sql_mutation_signal_count": sum("DIRECT_SQL_MUTATION" in row["rule_signals"] for row in all_methods),
        "exact_branch_condition_message_and_effect_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_edit_static_validation_configuration_balance_and_date_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "application_or_business_commands_executed": 0,
            "raw_non_allowlisted_literals_business_values_or_error_messages_persisted": 0,
            "runtime_branch_rule_or_effect_parity_inferred": 0,
        },
        "summary": summary,
        "contracts": contracts,
        "validation_errors": errors,
        "limits": [
            "Rule signals are method-level co-occurrence and do not prove exact branch predicates or message text.",
            "Configuration keys identify conditional behavior but not the effective runtime value for every context.",
            "No validation or command method was executed; owner-approved Golden values remain required.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
