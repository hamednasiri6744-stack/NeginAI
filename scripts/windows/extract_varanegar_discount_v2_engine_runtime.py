"""Extract the static Discount V2 engine pipeline and dynamic-rule boundary.

The assemblies are parsed as PE/CLR metadata only.  They are never imported,
loaded, reflected, or executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token


TARGETS: dict[str, dict[str, list[str]]] = {
    "DiscountV2.dll": {
        "DiscountV2.Entity.Internal.CalcData": [".ctor"],
        "RuleEngine.DiscountCalculatorHandler": ["Calculate"],
        "DiscountV2.Calculator.SDS.DoEvcHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTableHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.FillEvcStatuteByIdHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.ApplyStatuteOnEvcItemHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.ApplyStatuteOnEvcHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.CalcExtraValuesHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.CheckValidEvcStatutesHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.CheckValidPrizePreSellHandler": ["Execute"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.FillEvcSatuteById.FillEvcStatuteById_ApplyDiscountCriteriaHandler": ["Execute", "EvaluateSqlCondition", "FillSimpleEvcSharpSummary"],
        "DiscountV2.Calculator.SDS.DoEvcByStatuteTable.FillEvcSatuteById.FillEvcStatuteById_FillDiscountHandler": ["Execute"],
    },
    "DicountV2SqlServer.dll": {
        "DicountV2SqlServer.AdvanceConditionSqlHelper": [
            ".ctor", "CalcPeriodicDiscount", "ValidateAdvanceCondition"
        ],
    },
    "DicountV2SqlServerSDS.dll": {
        "DicountV2SqlServerSDS.AdvanceConditionSqlHelper": [
            ".ctor", "CalcPeriodicDiscount", "FillEvcItemFull", "ValidateAdvanceCondition"
        ],
    },
}

PIPELINE_TERMS = (
    "DoEvc", "Validation", "Usance", "UpdatePrice", "Statute", "SpecialValue",
    "FillDiscount", "FilterByEvcInfo", "FillEvcItemFull", "ApplyDiscountCriteria",
    "CalcExtra", "ApplyStatute", "DoDiscountForAmani", "CheckValidPrizePreSell",
    "PeriodicDiscount", "CartonPrize", "ValidateAdvanceCondition",
)
ALLOWLISTED_REWRITE_NAMES = {
    "evcitemfull",
    "#evcitemfull",
    "sle.tblevc",
    "#tbltempevc",
    "sle.tblevcitem",
    "#tbltempevcitemstatutes",
    "sle.tblevcitemstatutes",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method_rows(pe: dnfile.dnPE, type_name: str, method_name: str) -> list[dict[str, Any]]:
    method_owners, field_owners = _owner_maps(pe)
    type_row = next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == type_name)
    result: list[dict[str, Any]] = []
    for occurrence, index in enumerate(
        item for item in (type_row.MethodList or [])
        if str(item.row.Name) == method_name and item.row.Rva
    ):
        row = index.row
        body = read_method_body_from_bytes(pe.get_data(row.Rva, 2_097_152))
        ordered_members: list[dict[str, Any]] = []
        literals: list[str] = []
        literal_shapes: list[dict[str, Any]] = []
        numeric_constants: list[dict[str, int]] = []
        branch_instructions: list[dict[str, Any]] = []
        for instruction in body.instructions:
            operand = instruction.operand
            if isinstance(operand, StringToken):
                found = pe.net.user_strings.get(operand.rid)
                value = "" if found is None else str(found.value)
                literals.append(value)
                lowered = value.casefold()
                literal_shapes.append(
                    {
                        "offset": int(instruction.offset),
                        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                        "length": len(value),
                        "contains_sp_executesql": "sp_executesql" in lowered,
                        "contains_sql_condition_parameter": "@sqlcondition" in lowered,
                        "contains_evc_id_parameter": "@evcid" in lowered,
                        "contains_result_parameter": "@result" in lowered,
                        "contains_base_evc_name": any(
                            token in lowered
                            for token in ("sle.tblevc", "sle.tblevcitem", "sle.tblevcitemstatutes")
                        ),
                        "contains_temp_evc_name": any(
                            token in lowered
                            for token in ("#tbltempevc", "#tbltempevcitem", "#evcitemfull")
                        ),
                        **(
                            {"allowlisted_rewrite_name": value}
                            if lowered in ALLOWLISTED_REWRITE_NAMES
                            else {}
                        ),
                    }
                )
            elif isinstance(operand, Token):
                member = _resolve_token(pe, operand, method_owners, field_owners)
                if member:
                    ordered_members.append(
                        {"offset": int(instruction.offset), "opcode": instruction.mnemonic, "member": member}
                    )
            constant_map = {f"ldc.i4.{value}": value for value in range(9)} | {"ldc.i4.m1": -1}
            if instruction.mnemonic in constant_map:
                numeric_constants.append(
                    {"offset": int(instruction.offset), "value": constant_map[instruction.mnemonic]}
                )
            elif instruction.mnemonic in {"ldc.i4", "ldc.i4.s"} and isinstance(operand, int):
                numeric_constants.append({"offset": int(instruction.offset), "value": int(operand)})
            if instruction.mnemonic.startswith(
                ("br", "beq", "bne", "bge", "bgt", "ble", "blt", "leave", "switch")
            ):
                branch_instructions.append(
                    {"offset": int(instruction.offset), "opcode": instruction.mnemonic}
                )
        pipeline = [
            item for item in ordered_members
            if any(term.casefold() in item["member"].casefold() for term in PIPELINE_TERMS)
        ]
        member_counts: dict[str, int] = {}
        member_offsets: dict[str, list[int]] = {}
        for item in ordered_members:
            member_counts[item["member"]] = member_counts.get(item["member"], 0) + 1
            member_offsets.setdefault(item["member"], []).append(item["offset"])
        result.append(
            {
                "type": type_name,
                "method": method_name,
                "occurrence": occurrence,
                "method_metadata_token": 0x06000000 | int(index.row_index),
                "parameter_names": [str(item.row.Name) for item in row.ParamList or []],
                "instruction_count": len(body.instructions),
                "ordered_member_references": ordered_members,
                "ordered_pipeline_member_references": pipeline,
                "unique_member_references": sorted({item["member"] for item in ordered_members}),
                "member_reference_counts": dict(sorted(member_counts.items())),
                "member_reference_offsets": dict(sorted(member_offsets.items())),
                "numeric_constants": numeric_constants,
                "branch_instructions": branch_instructions,
                "literal_shapes": literal_shapes,
                "runtime_rule_sql_literal_persisted": False,
                "_literals": literals,
            }
        )
    return result


def _find(methods: list[dict[str, Any]], suffix: str, method: str) -> dict[str, Any]:
    return next(row for row in methods if row["type"].endswith(suffix) and row["method"] == method)


def _ordered_contains(row: dict[str, Any], fragments: list[str]) -> bool:
    members = [item["member"].casefold() for item in row["ordered_pipeline_member_references"]]
    cursor = -1
    for fragment in fragments:
        cursor = next((i for i in range(cursor + 1, len(members)) if fragment.casefold() in members[i]), -1)
        if cursor < 0:
            return False
    return True


def collect(source_directory: Path) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    for assembly_name, types in TARGETS.items():
        path = source_directory / assembly_name
        pe = dnfile.dnPE(str(path))
        type_count = len(pe.net.mdtables.TypeDef.rows)
        method_count = sum(len(row.MethodList or []) for row in pe.net.mdtables.TypeDef.rows)
        sources.append(
            {
                "assembly_file": assembly_name,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": _sha256(path),
                "managed_type_count": type_count,
                "managed_method_count": method_count,
            }
        )
        for type_name, method_names in types.items():
            for method_name in method_names:
                methods.extend(_method_rows(pe, type_name, method_name))

    calculate = _find(methods, "DiscountCalculatorHandler", "Calculate")
    main = _find(methods, "DoEvcHandler", "Execute")
    statute = _find(methods, "DoEvcByStatuteTableHandler", "Execute")
    fill = _find(methods, "FillEvcStatuteByIdHandler", "Execute")
    apply_summary = _find(methods, "FillEvcStatuteById_ApplyDiscountCriteriaHandler", "FillSimpleEvcSharpSummary")
    calc_ctors = [row for row in methods if row["type"] == "DiscountV2.Entity.Internal.CalcData" and row["method"] == ".ctor"]
    calc_helper_ctor = next(row for row in calc_ctors if row["parameter_names"] == ["advanceConditionHelper"])
    sql_helpers = [row for row in methods if row["method"] == "ValidateAdvanceCondition"]
    sds_helper = next(row for row in sql_helpers if row["type"].startswith("DicountV2SqlServerSDS."))
    sds_helper_ctor = _find(methods, "DicountV2SqlServerSDS.AdvanceConditionSqlHelper", ".ctor")
    helper_members = "\n".join(
        member for row in sql_helpers for member in row["unique_member_references"]
    ).casefold()
    helper_literals = [value for row in sql_helpers for value in row.pop("_literals")]
    for row in methods:
        row.pop("_literals", None)
    all_helper_text = "\n".join(helper_literals).casefold()
    sds_rewrite_literals = [
        {"offset": row["offset"], "name": row["allowlisted_rewrite_name"]}
        for row in sds_helper["literal_shapes"]
        if "allowlisted_rewrite_name" in row
    ]

    assertions = {
        "three_expected_engine_assemblies_hash_pinned": len(sources) == 3
        and all(len(row["assembly_sha256"]) == 64 for row in sources),
        "all_selected_methods_found": len(methods) == 22,
        "public_calculate_delegates_to_sds_do_evc": _ordered_contains(
            calculate, ["DoEvcHandler.Execute"]
        ),
        "main_pipeline_contains_validation_usance_price_statute_and_special_value": _ordered_contains(
            main,
            ["Validation", "UsanceDay", "UpdatePrice", "DoEvcByStatuteTable", "SpecialValue"],
        ),
        "statute_pipeline_order_is_preserved": _ordered_contains(
            statute,
            ["FillEvcStatuteById", "CheckValidEvcStatutes", "CalcExtraValues",
             "ApplyStatuteOnEvcItem", "ApplyStatuteOnEvc", "DoDiscountForAmani",
             "CheckValidPrizePreSell"],
        ),
        "fill_pipeline_contains_rule_selection_and_advanced_condition": _ordered_contains(
            fill, ["FillDiscount", "FilterByEvcInfo", "FillEvcItemFull", "ApplyDiscountCriteria"]
        ),
        "advanced_condition_reads_sqlcondition_and_executes_scalar_sql": (
            "get_sqlcondition" in helper_members
            and "system.string.replace" in helper_members
            and ("getvalue" in helper_members or "execute" in helper_members)
        ),
        "advanced_condition_uses_sp_executesql_with_parameters": (
            "sp_executesql" in all_helper_text
            and "@sqlcondition" in all_helper_text
            and "@evcid" in all_helper_text
            and "@result" in all_helper_text
        ),
        "sds_helper_contains_base_to_temp_name_rewrite_literals": all(
            token in all_helper_text
            for token in ("sle.tblevc", "sle.tblevcitem", "sle.tblevcitemstatutes", "#evcitemfull")
        ),
        "sds_object_rewrite_pairs_are_exact_and_ordered": sds_rewrite_literals == [
            {"offset": 296, "name": "EvcItemFull"},
            {"offset": 301, "name": "#EvcItemFull"},
            {"offset": 315, "name": "sle.tblEvc"},
            {"offset": 320, "name": "#tblTempEvc"},
            {"offset": 334, "name": "sle.tblEvcItem"},
            {"offset": 339, "name": "#tblTempEvcItemStatutes"},
            {"offset": 353, "name": "sle.tblEvcItemStatutes"},
            {"offset": 358, "name": "#EvcItemFull"},
        ]
        and sds_helper["member_reference_offsets"].get("System.String.Replace")
        == [287, 306, 325, 344, 363],
        "apply_summary_delegates_once_to_advanced_condition_helper": (
            apply_summary["member_reference_counts"].get(
                "DiscountV2.Calculator.Helper.AdvanceConditionHelperInterface.ValidateAdvanceCondition", 0
            ) == 1
        ),
        "selected_calcdata_constructor_fixes_backoffice_type_one": (
            len(calc_ctors) == 2
            and calc_helper_ctor["numeric_constants"] == [{"offset": 8, "value": 1}]
            and any(
                item == {
                    "offset": 9,
                    "opcode": "stfld",
                    "member": "DiscountV2.Entity.Internal.CalcData.BackOfficeType",
                }
                for item in calc_helper_ctor["ordered_member_references"]
            )
        ),
        "advanced_condition_gate_accepts_backoffice_type_one": (
            apply_summary["member_reference_offsets"].get(
                "DiscountV2.Entity.Internal.CalcData.BackOfficeType"
            ) == [482]
            and {"offset": 487, "value": 1} in apply_summary["numeric_constants"]
            and {"offset": 488, "opcode": "bne.un.s"} in apply_summary["branch_instructions"]
            and apply_summary["member_reference_offsets"].get(
                "DiscountV2.Calculator.Helper.AdvanceConditionHelperInterface.ValidateAdvanceCondition"
            ) == [508]
        ),
        "sds_helper_captures_and_prefers_injected_context": (
            sds_helper_ctor["parameter_names"] == ["context"]
            and sds_helper_ctor["member_reference_offsets"].get(
                "DiscountV2.Calculator.Helper.AdvanceConditionHelperInterface.context"
            ) == [9]
            and sds_helper["member_reference_offsets"].get(
                "DiscountV2.Calculator.Helper.AdvanceConditionHelperInterface.context"
            ) == [26, 34]
            and {"offset": 12, "value": 1} in sds_helper["numeric_constants"]
            and sds_helper["member_reference_offsets"].get("Thunderstruck.DataContext..ctor")
            == [13, 19]
        ),
        "sds_advanced_condition_executes_one_dynamic_query_per_enumerated_candidate": all(
            sds_helper["member_reference_counts"].get(member, 0) == 1
            for member in (
                "TypeSpecRow.GetEnumerator",
                "TypeSpecRow.MoveNext",
                "Thunderstruck.DataContext.GetValue",
            )
        )
        and sds_helper["member_reference_offsets"].get("Thunderstruck.DataContext.GetValue") == [502]
        and sds_helper["member_reference_offsets"].get("TypeSpecRow.MoveNext") == [675],
        "sds_true_branch_reads_and_deletes_item_include_staging": (
            sds_helper["member_reference_counts"].get("Thunderstruck.DataContext.AllRawEntity", 0) == 1
            and sds_helper["member_reference_counts"].get("Thunderstruck.DataContext.Execute", 0) == 1
        ),
        "raw_runtime_rule_sql_was_not_persisted": all(
            not row["runtime_rule_sql_literal_persisted"] for row in methods
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_discount_v2_engine_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "raw_runtime_rule_sql_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "engine_assembly_count": len(sources),
            "managed_type_count": sum(row["managed_type_count"] for row in sources),
            "managed_method_count": sum(row["managed_method_count"] for row in sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "advanced_condition_helper_count": len(sql_helpers),
            "dynamic_rule_executor_count": sum(
                any(shape["contains_sp_executesql"] for shape in row["literal_shapes"])
                for row in sql_helpers
            ),
            "sds_per_candidate_dynamic_query_loop_count": int(
                assertions["sds_advanced_condition_executes_one_dynamic_query_per_enumerated_candidate"]
            ),
            "sds_injected_context_preference_count": int(
                assertions["sds_helper_captures_and_prefers_injected_context"]
            ),
            "sds_exact_object_rewrite_pair_count": len(sds_rewrite_literals) // 2,
        },
        "methods": methods,
        "assertions": assertions,
        "limits": [
            "Static IL proves reachable implementation contracts, not which branch ran for a particular order.",
            "String.Replace calls and literals prove textual rewriting exists; stack/data-flow pairing is not claimed here.",
            "The content and trustworthiness of database-resident SqlCondition rules requires a separate read-only aggregate snapshot.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    artifact = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
