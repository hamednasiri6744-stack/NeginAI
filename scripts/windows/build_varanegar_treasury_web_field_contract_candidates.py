"""Merge treasury control, property, view-lineage and validation evidence for web reconstruction."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


TARGETS = {
    "TreasuryOld.Forms.frmCashEdit": "cash_receipt_edit",
    "TreasuryOld.Forms.frmChequeEdit": "received_cheque_edit",
    "TreasuryOld.Forms.frmRCashDraftEdit": "received_bank_draft_edit",
}


def _property_name(call: str) -> str:
    marker = call.rfind(".get_")
    marker = marker if marker >= 0 else call.rfind(".set_")
    return call[marker + 5:] if marker >= 0 else call.rsplit(".", 1)[-1]


def _target_type(call: str) -> str:
    marker = call.rfind(".get_")
    marker = marker if marker >= 0 else call.rfind(".set_")
    return call[:marker] if marker >= 0 else call.rsplit(".", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field-types", required=True, type=Path)
    parser.add_argument("--field-bindings", required=True, type=Path)
    parser.add_argument("--field-sql-columns", required=True, type=Path)
    parser.add_argument("--view-lineage", required=True, type=Path)
    parser.add_argument("--validation-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    typed = json.loads(args.field_types.read_text(encoding="utf-8-sig"))
    bindings = json.loads(args.field_bindings.read_text(encoding="utf-8-sig"))
    sql_columns = json.loads(args.field_sql_columns.read_text(encoding="utf-8-sig"))
    view_lineage = json.loads(args.view_lineage.read_text(encoding="utf-8-sig"))
    validations = json.loads(args.validation_contracts.read_text(encoding="utf-8-sig"))
    sources = {"field_types": typed, "field_bindings": bindings, "field_sql_columns": sql_columns, "view_lineage": view_lineage, "validation_contracts": validations}
    errors = [f"{name} source is not PASS" for name, payload in sources.items() if payload.get("validation") != "PASS"]

    typed_map = {row["form_type"]: row for row in typed["forms"]}
    binding_map = {(row["form_type"], field["field_name"]): field for row in bindings["forms"] for field in row["fields"]}
    sql_map = {(row["form_type"], row["field_name"]): row for row in sql_columns["fields"]}
    validation_map = {}
    for form in validations["contracts"]:
        for method in form["methods"]:
            for full_field in method["referenced_form_fields"]:
                field_name = full_field[len(form["form_type"]) + 1:]
                validation_map.setdefault((form["form_type"], field_name), []).append(method)
    lineage_map = {}
    for view in view_lineage["views"]:
        for row in view["described_result_columns"]:
            if row["is_hidden"]:
                continue
            if row["source_object"] and row["source_column"]:
                lineage_map[(view["view"], row["name"])] = [{
                    "source_object": row["source_object"], "source_column": row["source_column"],
                    "resolution": "SQL_SERVER_DESCRIBED_RESULT_SOURCE_LINEAGE",
                }]
        for row in view["parsed_select_lineage_candidates"]:
            key = (view["view"], row["output_column"])
            if key not in lineage_map and row["source_identifier_candidates"]:
                lineage_map[key] = [{
                    "source_object": item["source_object_candidate"], "source_column": item["source_column"],
                    "resolution": "PARSED_IDENTIFIER_" + item["resolution"],
                } for item in row["source_identifier_candidates"]]

    forms = []
    all_fields = []
    for form_type, workflow in TARGETS.items():
        if form_type not in typed_map:
            errors.append(f"typed form missing: {form_type}")
            continue
        fields = []
        for typed_field in typed_map[form_type]["fields"]:
            field_name = typed_field["field_name"]
            binding = binding_map[(form_type, field_name)]
            calls = binding["strong_name_property_calls"]
            source_candidates = []
            property_candidates = []
            sql_field = sql_map.get((form_type, field_name))
            sql_by_call = {row["property_call"]: row for row in (sql_field or {}).get("property_candidates", [])}
            for call in calls:
                property_name = _property_name(call)
                target_type = _target_type(call)
                property_candidates.append({"property_call": call, "property_name": property_name, "target_type": target_type})
                short = target_type.rsplit(".", 1)[-1]
                view_name = "dbo.RCheque" if short == "RCheque" else "dbo.RCashDraft" if short == "RCashDraft" else None
                if view_name and (view_name, property_name) in lineage_map:
                    source_candidates.extend({"property_call": call, **row} for row in lineage_map[(view_name, property_name)])
                    continue
                for candidate in (sql_by_call.get(call) or {}).get("candidate_column_details", []):
                    if candidate["match_strength"] == "ENTITY_OBJECT_EXACT_AND_COLUMN_EXACT":
                        source_candidates.append({
                            "property_call": call, "source_object": candidate["object"], "source_column": candidate["column"],
                            "resolution": "ENTITY_OBJECT_AND_COLUMN_EXACT_NAME_CANDIDATE",
                        })
            unique_sources = {(row["property_call"], row["source_object"], row["source_column"], row["resolution"]): row for row in source_candidates}
            physical_sources = {(row["source_object"], row["source_column"]) for row in unique_sources.values()}
            conflicting_sources = len(physical_sources) > 1
            method_rows = validation_map.get((form_type, field_name), [])
            method_uses = [{"method": row["method"], "role": row["role"], "rule_signals": row["rule_signals"]} for row in method_rows]
            if unique_sources and conflicting_sources:
                status = "STATIC_PROPERTY_WITH_CONFLICTING_UNDERLYING_COLUMN_CANDIDATES"
            elif unique_sources:
                status = "STATIC_PROPERTY_AND_UNDERLYING_COLUMN_CANDIDATE"
            elif property_candidates:
                status = "STATIC_PROPERTY_ONLY_CANDIDATE"
            elif method_uses:
                status = "VALIDATION_OR_COMMAND_FIELD_WITHOUT_PROPERTY_CANDIDATE"
            else:
                status = "DECLARED_CONTROL_NO_FIELD_CONTRACT_CANDIDATE"
            row = {
                "field_name": field_name,
                "clr_field_type": typed_field["clr_field_type"],
                "resolved_control_kind": typed_field["resolved_control_kind"],
                "usage_signals": typed_field["usage_signals"],
                "property_candidates": property_candidates,
                "source_column_candidates": list(unique_sources.values()),
                "multiple_underlying_source_candidate_conflict": conflicting_sources,
                "validation_or_command_method_uses": method_uses,
                "target_web_field_contract_status": status,
                "runtime_binding_requiredness_effective_rule_or_write_mapping_proven": False,
            }
            fields.append(row)
            all_fields.append({"form_type": form_type, **row})
        forms.append({
            "workflow": workflow,
            "form_type": form_type,
            "field_count": len(fields),
            "status_counts": dict(sorted(Counter(row["target_web_field_contract_status"] for row in fields).items())),
            "fields": fields,
        })

    status_counts = Counter(row["target_web_field_contract_status"] for row in all_fields)
    summary = {
        "target_form_count": len(TARGETS),
        "resolved_target_form_count": len(forms),
        "declared_field_count": len(all_fields),
        "field_status_counts": dict(sorted(status_counts.items())),
        "field_with_strong_property_candidate_count": sum(bool(row["property_candidates"]) for row in all_fields),
        "field_with_underlying_source_column_candidate_count": sum(bool(row["source_column_candidates"]) for row in all_fields),
        "field_with_conflicting_underlying_source_candidates_count": sum(row["multiple_underlying_source_candidate_conflict"] for row in all_fields),
        "field_with_validation_or_command_method_use_count": sum(bool(row["validation_or_command_method_uses"]) for row in all_fields),
        "unique_underlying_source_column_candidate_count": len({(item["source_object"], item["source_column"]) for row in all_fields for item in row["source_column_candidates"]}),
        "runtime_binding_requiredness_effective_rule_or_write_mapping_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_edit_merged_web_field_contract_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_MERGE_OF_REDACTED_PERSISTED_FIELD_LINEAGE_AND_RULE_EVIDENCE",
            "database_connections": 0, "network_reads_or_writes": 0, "live_ui_actions": 0,
            "assemblies_or_application_commands_executed": 0,
            "business_rows_values_literals_or_messages_read_or_persisted": 0,
            "runtime_binding_requiredness_rule_or_write_mapping_inferred_as_proven": 0,
        },
        "summary": summary,
        "forms": forms,
        "validation_errors": errors,
        "limits": ["Candidates merge static evidence and remain non-authoritative until runtime/owner Golden proof.", "Labels and controls are not paired by visual order.", "A field can participate in multiple branches or settings and still not be a persisted source field."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
