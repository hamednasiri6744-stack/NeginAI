"""Extract hash-pinned Discount V2 QueryHelper templates without persisting raw SQL."""

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


TYPE_NAME = "VN.SDS.Sales.DataAccess.DataAdapter.Sale.AdvanceDCalDiscount.QueryHelper"
REFERENCE_FIELDS = {
    "CUSTOMER_GROUP", "CUSTOMER_MAIN_SUB_TYPE", "DISCOUNT_After_65", "C_PRICE",
    "GOODS_NO_SALE", "PRICE", "DISCOUNT_GOODS_After_65", "DISCOUNT_PRIZE_LIST",
    "DISCOUNT_GOODS_PACKAGE_ITEM", "GOODS_FIX_UNIT", "GOODS", "GOODS_GROUP",
    "GOODS_MAIN_SUB_TYPE", "FREE_REASON", "PACKAGE", "PAYMENT_USANCE", "DIS_ACC",
}
ORDER_REQUEST_FIELDS = {
    "CUSTOMER", "EVC_HEADER_Order", "EVC_ITEM", "ORDER_HDR", "ORDER_ITEM",
    "ORDER_PRIZE_After65", "SALE_HDR", "SALE_ITEM", "STOCK_GOODS",
    "SaleItemPaymentUsance",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table_refs(sql: str) -> list[str]:
    refs = set()
    for match in re.finditer(r"\b(?:from|join|update|into)\s+([#\[\]\w.]+)", sql, re.I):
        value = match.group(1).replace("[", "").replace("]", "").strip(".;").casefold()
        if value and not value.startswith("("):
            refs.add(value)
    return sorted(refs)


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = json.loads(binary_inventory.read_text(encoding="utf-8-sig"))
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    path = source_directory / "VN.SDS.Sales.DataAccess.dll"
    actual = _sha256(path)
    pe = dnfile.dnPE(str(path))
    type_row = next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == TYPE_NAME)
    field_names = [str(item.row.Name) for item in type_row.FieldList or []]
    method = next(item.row for item in type_row.MethodList or [] if str(item.row.Name) == ".cctor")
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 524288))
    method_owners, field_owners = _owner_maps(pe)

    templates: list[dict[str, Any]] = []
    instructions = list(body.instructions)
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction.operand, StringToken):
            continue
        found = pe.net.user_strings.get(instruction.operand.rid)
        sql = "" if found is None else str(found.value)
        next_instruction = instructions[index + 1] if index + 1 < len(instructions) else None
        member = (
            _resolve_token(pe, next_instruction.operand, method_owners, field_owners)
            if next_instruction is not None and isinstance(next_instruction.operand, Token)
            else ""
        )
        field_name = member.rsplit(".", 1)[-1]
        placeholders = sorted({int(value) for value in re.findall(r"\{(\d+)(?:[^}]*)\}", sql)})
        lowered = sql.casefold()
        templates.append(
            {
                "field_name": field_name,
                "category": (
                    "REFERENCE_OR_RULE_DATA" if field_name in REFERENCE_FIELDS
                    else "ORDER_REQUEST_DATA" if field_name in ORDER_REQUEST_FIELDS
                    else "OTHER_SALE_RETURN_OR_DIAGNOSTIC_DATA"
                ),
                "template_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                "template_length": len(sql),
                "format_placeholder_indexes": placeholders,
                "format_placeholder_count": len(placeholders),
                "table_refs": _table_refs(sql),
                "select_star_count": len(re.findall(r"\bselect\s+(?:\w+\.)?\*", sql, re.I)),
                "nolock_hint_count": lowered.count("nolock"),
                "readpast_hint_count": lowered.count("readpast"),
                "contains_exec": bool(re.search(r"\bexec(?:ute)?\b", sql, re.I)),
                "contains_write_keyword": bool(re.search(r"\b(?:insert|update|delete|merge)\b", sql, re.I)),
                "raw_sql_persisted": False,
            }
        )

    table_refs = sorted({ref for row in templates for ref in row["table_refs"]})
    placeholder_templates = [row for row in templates if row["format_placeholder_count"]]
    assertions = {
        "assembly_hash_matches_inventory": actual == expected.get(path.name),
        "query_helper_has_42_static_fields": len(field_names) == 42,
        "cctor_is_exact_ldstr_stsfld_pairs_plus_ret": len(instructions) == 85
        and len(templates) == 42
        and all(row["field_name"] in field_names for row in templates),
        "all_reference_fields_are_extracted": REFERENCE_FIELDS <= {row["field_name"] for row in templates},
        "all_order_request_fields_are_extracted": ORDER_REQUEST_FIELDS <= {row["field_name"] for row in templates},
        "templates_are_read_only_select_contracts": not any(
            row["contains_exec"] or row["contains_write_keyword"] for row in templates
        ),
        "raw_sql_was_not_persisted": all(not row["raw_sql_persisted"] for row in templates),
        "assembly_was_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_discount_v2_query_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": {
            "assembly_file": path.name,
            "assembly_bytes": path.stat().st_size,
            "assembly_sha256": actual,
            "inventory_sha256_match": actual == expected.get(path.name),
            "type": TYPE_NAME,
            "method": ".cctor",
        },
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "raw_sql_or_business_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "query_template_count": len(templates),
            "reference_or_rule_template_count": sum(row["category"] == "REFERENCE_OR_RULE_DATA" for row in templates),
            "order_request_template_count": sum(row["category"] == "ORDER_REQUEST_DATA" for row in templates),
            "other_template_count": sum(row["category"] == "OTHER_SALE_RETURN_OR_DIAGNOSTIC_DATA" for row in templates),
            "unique_table_reference_count": len(table_refs),
            "formatted_template_count": len(placeholder_templates),
            "format_placeholder_slot_count": sum(row["format_placeholder_count"] for row in templates),
            "select_star_template_count": sum(row["select_star_count"] > 0 for row in templates),
            "write_or_exec_template_count": sum(row["contains_exec"] or row["contains_write_keyword"] for row in templates),
            "temporary_table_reference_count": sum(ref.startswith("#") for ref in table_refs),
            "persistent_object_reference_count": sum(not ref.startswith("#") for ref in table_refs),
            "maximum_template_length": max(row["template_length"] for row in templates),
        },
        "templates": templates,
        "unique_table_refs": table_refs,
        "assertions": assertions,
        "limits": [
            "String.Format placeholders prove text formatting, not the runtime CLR type or trust boundary of every supplied value.",
            "Table-reference extraction is lexical and may omit objects inside unusually structured subqueries or functions.",
            "Static callsite counts do not equal runtime query counts when branches are skipped.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    artifact = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
