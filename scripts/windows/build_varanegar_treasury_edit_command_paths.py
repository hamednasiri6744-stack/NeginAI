"""Build focused static command paths for three legacy treasury edit forms."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


TARGETS = {
    "TreasuryOld.Forms.frmCashEdit": "cash_receipt_edit",
    "TreasuryOld.Forms.frmChequeEdit": "received_cheque_edit",
    "TreasuryOld.Forms.frmRCashDraftEdit": "received_bank_draft_edit",
}

TRANSACTION_SIGNALS = {
    "TreasuryOld.DataLayer.Transaction.Start",
    "TreasuryOld.DataLayer.Transaction.Commit",
    "TreasuryOld.DataLayer.Transaction.RollBack",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    located = {}
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] in TARGETS:
                located[target["type"]] = (assembly, target)

    contracts = []
    all_setters = set()
    all_fields = set()
    all_safe_fragments = set()
    command_method_count = 0
    validation_transaction_method_count = 0
    direct_execute_count = 0
    adapter_preupdate_count = 0
    entity_update_count = 0
    errors = []
    for type_name, workflow in TARGETS.items():
        if type_name not in located:
            errors.append(f"target type missing: {type_name}")
            continue
        assembly, target = located[type_name]
        methods = []
        for method in target["methods"]:
            calls = set(method["calls"])
            transaction = sorted(calls & TRANSACTION_SIGNALS)
            execute = sorted(call for call in calls if call.endswith(".ExecuteNonQuery"))
            preupdate = sorted(call for call in calls if call.endswith("Adapter.PreUpdate"))
            entity_update = sorted(
                call for call in calls
                if call.startswith("TreasuryOld.DataLayer.") and call.endswith(".Update")
            )
            setters = sorted(
                call for call in calls
                if call.startswith("TreasuryOld.DataLayer.") and ".set_" in call
            )
            fields = sorted(
                field for field in method["referenced_fields"]
                if field.startswith(type_name + ".")
            )
            safe_fragments = sorted({
                literal["safe_literal"]
                for literal in method["string_literals"]
                if literal.get("persisted_as") == "allowlisted_business_literal"
                and literal.get("safe_literal")
            })
            is_command = bool(execute or preupdate or entity_update)
            is_validation_transaction = bool(transaction and not is_command)
            if not (is_command or is_validation_transaction):
                continue
            command_method_count += int(is_command)
            validation_transaction_method_count += int(is_validation_transaction)
            direct_execute_count += int(bool(execute))
            adapter_preupdate_count += int(bool(preupdate))
            entity_update_count += int(bool(entity_update))
            all_setters.update(setters)
            all_fields.update(fields)
            all_safe_fragments.update(safe_fragments)
            methods.append({
                "method": method["method"],
                "instruction_count": method["instruction_count"],
                "classification": "MUTATION_COMMAND_STATIC_PATH" if is_command else "VALIDATION_WITH_TRANSACTION_STATIC_PATH",
                "transaction_signals": transaction,
                "execute_non_query_calls": execute,
                "adapter_preupdate_calls": preupdate,
                "entity_update_calls": entity_update,
                "entity_property_setters": setters,
                "referenced_form_fields": fields,
                "allowlisted_sql_or_business_fragments": safe_fragments,
                "runtime_execution_or_success_proven": False,
            })
        contracts.append({
            "workflow": workflow,
            "assembly": assembly["file"],
            "assembly_sha256": assembly["sha256"],
            "form_type": type_name,
            "method_body_count": len(target["methods"]),
            "selected_methods": methods,
            "selected_method_count": len(methods),
            "write_model": "DIRECT_UI_TRANSACTION_WITH_ENTITY_ADAPTER_AND_OPTIONAL_INLINE_SQL",
            "target_erp_boundary": "COMMAND_HANDLER_OWNS_TRANSACTION_UI_ONLY_SUBMITS_COMMAND",
            "legacy_behavior_to_preserve": "VALIDATION_SIDE_EFFECT_LEDGER_AND_CROSS_OBJECT_ATOMICITY_REQUIRE_SEPARATE_PROOF",
        })

    summary = {
        "target_form_count": len(TARGETS),
        "resolved_target_form_count": len(contracts),
        "target_method_body_count": sum(row["method_body_count"] for row in contracts),
        "mutation_command_method_count": command_method_count,
        "validation_with_transaction_method_count": validation_transaction_method_count,
        "method_with_direct_execute_non_query_count": direct_execute_count,
        "method_with_adapter_preupdate_count": adapter_preupdate_count,
        "method_with_entity_update_count": entity_update_count,
        "unique_entity_property_setter_count": len(all_setters),
        "unique_referenced_form_field_count": len(all_fields),
        "unique_allowlisted_sql_or_business_fragment_count": len(all_safe_fragments),
        "runtime_execution_success_idempotency_or_result_parity_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_edit_static_transaction_field_setter_and_inline_sql_paths",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "raw_non_allowlisted_literals_or_business_values_persisted": 0,
            "runtime_success_idempotency_or_result_parity_inferred": 0,
        },
        "summary": summary,
        "contracts": contracts,
        "validation_errors": errors,
        "limits": [
            "Static IL call co-occurrence does not prove branch order, runtime values, or successful commit.",
            "Allowlisted SQL fragments are partial structural evidence and are not reconstructed executable SQL.",
            "Legacy direct UI writes are evidence to encapsulate, not a target architecture recommendation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
