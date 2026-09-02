"""Extract hash-pinned desktop authorization signals around order-to-sale conversion."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_SCRIPTS))
from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token  # noqa: E402


TARGETS = {
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale": {
            "AcceptCommandOld",
            "AcceptCommandDiscountV2",
            "ApplySetadPermission",
            "CheckSetOprDate",
        }
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.Order.OrderHandler": {
            "CreateSaleByOrder",
            "CreateSaleByOrderUsingDiscountV2",
            "CreateSaleByOrderV2",
            "HasOrderTypePermission",
            "HasUserAcssesToThisOrder",
        }
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter": {
            "CreateSaleByOrder",
            "HasOrderTypePermission",
        }
    },
}

ALLOWLISTED_LITERALS = {
    "sle.usp_sdsnet_Order_OrderTypePermission",
    "exec sle.usp_sdsnet_Order_OrderTypePermission {0} , {1} , {2}",
    "sle.usp_sdsnet_CreateSaleByOrder",
    "SLE.usp_CreateSaleByOrder",
}
PERMISSION_TERMS = (
    "permission",
    "persmission",
    "authorization",
    "authorize",
    "acsses",
    "areaaccess",
    "useraccess",
    "userright",
    "groupright",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _permission_member(member: str) -> bool:
    value = member.casefold()
    return any(term in value for term in PERMISSION_TERMS)


def _decode_method(pe, assembly, owner, index, method_owners, field_owners):
    row = index.row
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
    calls = []
    literals = []
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            found = pe.net.user_strings.get(operand.rid)
            value = "" if found is None else str(found.value)
            allowlisted = value if value in ALLOWLISTED_LITERALS else None
            literals.append(
                {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "allowlisted_value": allowlisted,
                    "raw_non_allowlisted_value_persisted": False,
                }
            )
        elif isinstance(operand, Token):
            calls.append(_resolve_token(pe, operand, method_owners, field_owners))
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(row.Name),
        "method_rid": int(index.row_index),
        "parameter_count": len(row.ParamList or []),
        "instruction_count": len(body.instructions),
        "calls": sorted(set(calls)),
        "permission_or_access_calls": sorted(set(call for call in calls if _permission_member(call))),
        "string_literals": literals,
    }


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources = []
    selected = []
    errors = []
    form_all_permission_calls = []
    order_type_permission_ui_callsites = []
    type_method_counts = {}

    for assembly, types in TARGETS.items():
        path = source_directory / assembly
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        sources.append(
            {
                "assembly_file": assembly,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": actual == expected.get(assembly),
            }
        )
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        type_rows = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, names in types.items():
            type_row = type_rows.get(owner)
            if type_row is None:
                errors.append({"assembly": assembly, "type": owner, "error": "TYPE_ABSENT"})
                continue
            type_method_counts[f"{assembly}:{owner}"] = len(type_row.MethodList or [])
            found = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in names:
                    continue
                found.add(str(row.Name))
                try:
                    selected.append(_decode_method(pe, assembly, owner, index, method_owners, field_owners))
                except Exception as exc:
                    errors.append({"assembly": assembly, "type": owner, "method": str(row.Name), "error": type(exc).__name__})
            for name in names - found:
                errors.append({"assembly": assembly, "type": owner, "method": name, "error": "METHOD_ABSENT"})

        if assembly == "VN.SDS.Sales.UI.dll":
            form_owner = "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale"
            for type_row in pe.net.mdtables.TypeDef.rows:
                owner = _full_type_name(type_row)
                for index in type_row.MethodList or []:
                    row = index.row
                    if row is None or not row.Rva:
                        continue
                    try:
                        body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
                    except Exception:
                        continue
                    members = [
                        _resolve_token(pe, item.operand, method_owners, field_owners)
                        for item in body.instructions
                        if isinstance(item.operand, Token)
                    ]
                    if owner == form_owner:
                        for member in sorted(set(value for value in members if _permission_member(value))):
                            form_all_permission_calls.append({"method": str(row.Name), "member": member})
                    if "VN.SDS.Sales.Business.Order.OrderHandler.HasOrderTypePermission" in members:
                        order_type_permission_ui_callsites.append({"type": owner, "method": str(row.Name)})

    conversion_methods = [
        row
        for row in selected
        if row["method"] in {"AcceptCommandOld", "AcceptCommandDiscountV2", "CreateSaleByOrder", "CreateSaleByOrderUsingDiscountV2", "CreateSaleByOrderV2"}
    ]
    order_permission_methods = [row for row in selected if row["method"] == "HasOrderTypePermission"]
    access_helpers = [row for row in selected if row["method"] == "HasUserAcssesToThisOrder"]
    allowlisted_literals = {
        literal["allowlisted_value"]
        for row in selected
        for literal in row["string_literals"]
        if literal["allowlisted_value"]
    }
    assertions = {
        "all_source_hashes_match": all(row["inventory_sha256_match"] for row in sources),
        "selected_methods_complete": len(selected) == 12 and not errors,
        "order_to_sale_form_has_no_permission_or_access_member_call": form_all_permission_calls == [],
        "selected_conversion_methods_have_no_permission_or_access_member_call": all(
            row["permission_or_access_calls"] == [] for row in conversion_methods
        ),
        "order_type_permission_is_called_from_order_lists_not_conversion_form": (
            len(order_type_permission_ui_callsites) == 10
            and all(row["type"].endswith(("FormOrderList", "FormLoanOrderList")) for row in order_type_permission_ui_callsites)
            and all(row["type"] != "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale" for row in order_type_permission_ui_callsites)
        ),
        "business_order_type_permission_delegates_to_adapter": any(
            "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter.HasOrderTypePermission" in row["calls"]
            for row in order_permission_methods
        ),
        "adapter_order_type_permission_reads_session_actor_and_named_procedure": (
            "exec sle.usp_sdsnet_Order_OrderTypePermission {0} , {1} , {2}" in allowlisted_literals
            and any("Application.BaseData.UserSessionInfo.get_UserRef" in row["calls"] for row in order_permission_methods)
        ),
        "business_area_access_helper_reads_general_config": (
            len(access_helpers) == 1
            and "VN.SDS.Common.MainData.Entity.GeneralConfig.GeneralConfigEntity.get_AreaAccess" in access_helpers[0]["calls"]
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_order_sale_authorization_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "form_or_application_command_executions": 0,
            "raw_non_allowlisted_strings_business_values_or_identities_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(selected),
            "selected_conversion_method_count": len(conversion_methods),
            "order_to_sale_form_permission_call_count": len(form_all_permission_calls),
            "order_type_permission_ui_callsite_count": len(order_type_permission_ui_callsites),
            "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
            "method_or_coverage_error_count": len(errors),
        },
        "type_method_counts": type_method_counts,
        "contract": {
            "order_to_sale_form_permission_or_access_calls": form_all_permission_calls,
            "order_type_permission_ui_callsites": order_type_permission_ui_callsites,
            "selected_conversion_action_authorization": "NOT_PROVEN",
            "form_or_menu_open_authorization_outside_exact_form_type": "NOT_PROVEN",
            "target_requirement": "SERVER_ENFORCED_DISTINCT_CONVERT_ORDER_TO_SALE_ACTION_AND_RESOURCE_SCOPE",
        },
        "assertions": assertions,
        "errors": errors,
        "methods": selected,
        "limits": [
            "Static IL absence in selected methods and exact form type does not prove absence of base-form, menu, endpoint or deployment authorization.",
            "The order-type rights helper protects observed list actions and has no observed conversion-form callsite.",
            "No effective permission or scope is inferred for any identity.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    artifact = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
