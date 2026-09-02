"""Extract static UI configuration and permission gates for order-to-sale policy controls."""

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
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
)


ASSEMBLY = "VN.SDS.Sales.UI.dll"
TARGET_TYPE = "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale"
CONTROL_NAMES = (
    "DeleteItmsCheckEdit",
    "CustAdamEtebarBedehkariSabtCheckEdit",
    "CustAdamEtebarAsnadiSabtCheckEdit",
    "DealerAdamEtebarBedehkariSabtCheckEdit",
    "DealerAdamEtebarAsnadiSabtCheckEdit",
    "AdamEtebarMaxSabtCheckEdit",
)
CONFIG_GETTERS = (
    "get_CheckSaleItmStock",
    "get_SaleBedLimit",
    "get_SaleAsnLimit",
    "get_SaleBedLimitDealer",
    "get_SaleAsnLimitDealer",
    "get_SaleMaxLimit",
    "get_IsDiscountV2Active",
    "get_SiteType",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _relevant(member: str) -> bool:
    lowered = member.casefold()
    return (
        member.startswith(TARGET_TYPE + ".")
        or any(name in member for name in CONTROL_NAMES)
        or any(name in member for name in CONFIG_GETTERS)
        or any(word in lowered for word in ("permission", "persmission", "authorize", "accessright", "setad"))
        or any(
            word in lowered
            for word in (
                "oprdate",
                "operationddate",
                "createsaledate",
                "isdatevalid",
                "datetimetosolar",
                "closeoprdate",
            )
        )
        or member.endswith(
            (
                ".set_Enabled",
                ".set_Visible",
                ".set_ReadOnly",
                ".set_Checked",
                ".set_EditValue",
                ".get_Checked",
                ".get_EditValue",
            )
        )
    )


def _constant(instruction: Any) -> int | float | None:
    values = {
        "ldc.i4.m1": -1,
        "ldc.i4.0": 0,
        "ldc.i4.1": 1,
        "ldc.i4.2": 2,
        "ldc.i4.3": 3,
        "ldc.i4.4": 4,
        "ldc.i4.5": 5,
        "ldc.i4.6": 6,
        "ldc.i4.7": 7,
        "ldc.i4.8": 8,
    }
    if instruction.mnemonic in values:
        return values[instruction.mnemonic]
    if instruction.mnemonic in {"ldc.i4", "ldc.i4.s", "ldc.i8", "ldc.r4", "ldc.r8"}:
        return instruction.operand if isinstance(instruction.operand, (int, float)) else None
    return None


def _summary(pe, instruction, method_owners, field_owners, allow_all_tokens=False):
    row: dict[str, Any] = {"offset": int(instruction.offset), "opcode": instruction.mnemonic}
    value = _constant(instruction)
    if value is not None:
        row["numeric_constant"] = value
    operand = instruction.operand
    if instruction.mnemonic.startswith(("br", "beq", "bne", "ble", "blt", "bge", "bgt", "leave")):
        target = getattr(operand, "offset", operand)
        if isinstance(target, int):
            row["branch_target_offset"] = target
    if isinstance(operand, StringToken):
        item = pe.net.user_strings.get(operand.rid)
        text = "" if item is None else str(item.value)
        row["string_fingerprint"] = {
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "length": len(text),
            "raw_value_persisted": False,
        }
    elif isinstance(operand, Token):
        member = _resolve_token(pe, operand, method_owners, field_owners)
        if allow_all_tokens or _relevant(member):
            row["member"] = member
        else:
            row["operand_class"] = "NON_ALLOWLISTED_METADATA_TOKEN"
    return row


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    path = source_directory / ASSEMBLY
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    config_getter_signatures = []
    for row_index, row in enumerate(pe.net.mdtables.MemberRef.rows, 1):
        name = str(row.Name)
        if name not in CONFIG_GETTERS:
            continue
        raw_signature = bytes(row.Signature.value)
        config_getter_signatures.append(
            {
                "member": _resolve_token(
                    pe,
                    Token(0x0A000000 | row_index),
                    method_owners,
                    field_owners,
                ),
                "signature_hex": raw_signature.hex(),
                "returns_cli_int32": raw_signature.endswith(b"\x08"),
            }
        )
    types = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
    target = types.get(TARGET_TYPE)
    errors = []
    methods = []
    if target is None:
        errors.append("target type absent")
    else:
        for index in target.MethodList or []:
            row = index.row
            if row is None or not row.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
            except Exception as exc:
                errors.append(f"{row.Name}:{type(exc).__name__}")
                continue
            instructions = list(body.instructions)
            events = []
            literal_count = 0
            allow_all_tokens = str(row.Name) in {
                "ApplySetadPermission",
                "CheckSetOprDate",
                "OperationCheckSodorSale",
                "IsDateValid",
            }
            for position, instruction in enumerate(instructions):
                if isinstance(instruction.operand, StringToken):
                    literal_count += 1
                if not isinstance(instruction.operand, Token) or isinstance(instruction.operand, StringToken):
                    continue
                member = _resolve_token(pe, instruction.operand, method_owners, field_owners)
                if not (allow_all_tokens or _relevant(member)):
                    continue
                start = max(0, position - 8)
                stop = min(len(instructions), position + 4)
                events.append(
                    {
                        "member": member,
                        "instruction_window": [
                            _summary(pe, item, method_owners, field_owners, allow_all_tokens)
                            for item in instructions[start:stop]
                        ],
                    }
                )
            if events:
                methods.append(
                    {
                        "method": str(row.Name),
                        "instruction_count": len(instructions),
                        "has_exception_regions": bool(body.exception_handlers),
                        "string_literal_count": literal_count,
                        "events": events,
                    }
                )

    def selected(name: str) -> list[dict[str, Any]]:
        return [row for row in methods if row["method"] == name]

    def method_stream(name: str) -> list[dict[str, Any]]:
        rows = selected(name)
        if len(rows) != 1:
            return []
        by_offset = {
            instruction["offset"]: instruction
            for event in rows[0]["events"]
            for instruction in event["instruction_window"]
        }
        return [by_offset[offset] for offset in sorted(by_offset)]

    def config_states(getter: str, control: str) -> list[dict[str, Any]]:
        stream = method_stream("SetDefaultForCheckEdits")
        getter_member = next(
            (
                event["member"]
                for method in methods
                for event in method["events"]
                if getter in event["member"]
            ),
            None,
        )
        positions = [index for index, row in enumerate(stream) if row.get("member") == getter_member]
        states = []
        for ordinal, position in enumerate(positions):
            stop = positions[ordinal + 1] if ordinal + 1 < len(positions) else min(len(stream), position + 28)
            segment = stream[position:stop]
            config_value = 0
            if any(row.get("numeric_constant") == 1 for row in segment[:4]):
                config_value = 1
            if any(row.get("numeric_constant") == 2 for row in segment[:4]):
                config_value = 2

            def assigned(setter_suffix: str) -> int | None:
                for index, row in enumerate(segment):
                    if not row.get("member", "").endswith(setter_suffix):
                        continue
                    prior = segment[max(0, index - 4):index]
                    if not any(control in item.get("member", "") for item in prior):
                        continue
                    constants = [item["numeric_constant"] for item in prior if "numeric_constant" in item]
                    if constants:
                        return int(constants[-1])
                return None

            states.append(
                {
                    "server_config_value": config_value,
                    "control_enabled": assigned(".set_Enabled"),
                    "control_checked": assigned(".set_Checked"),
                }
            )
        return sorted(states, key=lambda row: row["server_config_value"])

    permission = selected("ApplySetadPermission")
    defaults = selected("SetDefaultForCheckEdits")
    load = selected("FormCreateSaleByOrder_Load")
    config_control_pairs = (
        ("get_SaleAsnLimit", "CustAdamEtebarAsnadiSabtCheckEdit", "CUSTOMER_DOCUMENT_CREDIT"),
        ("get_SaleBedLimit", "CustAdamEtebarBedehkariSabtCheckEdit", "CUSTOMER_DEBT_CREDIT"),
        ("get_SaleBedLimitDealer", "DealerAdamEtebarBedehkariSabtCheckEdit", "DEALER_DEBT_CREDIT"),
        ("get_SaleAsnLimitDealer", "DealerAdamEtebarAsnadiSabtCheckEdit", "DEALER_DOCUMENT_CREDIT"),
        ("get_SaleMaxLimit", "AdamEtebarMaxSabtCheckEdit", "CUSTOMER_MAXIMUM_LIMIT"),
        ("get_CheckSaleItmStock", "DeleteItmsCheckEdit", "STOCK_SHORTAGE_PARTIAL_CONVERSION"),
    )
    configuration_state_contracts = [
        {
            "policy": policy,
            "server_config_getter": getter,
            "ui_control": control,
            "states": config_states(getter, control),
        }
        for getter, control, policy in config_control_pairs
    ]
    credit_expected = [
        {"server_config_value": 0, "control_enabled": 0, "control_checked": 1},
        {"server_config_value": 1, "control_enabled": 1, "control_checked": 0},
        {"server_config_value": 2, "control_enabled": 0, "control_checked": 0},
    ]
    stock_expected = [
        {"server_config_value": 0, "control_enabled": 1, "control_checked": 0},
        {"server_config_value": 1, "control_enabled": 0, "control_checked": 1},
        {"server_config_value": 2, "control_enabled": 0, "control_checked": 0},
    ]
    apply_members = {
        event["member"] for row in permission for event in row["events"]
    }
    permission_named_calls = [
        member
        for member in apply_members
        if any(word in member.casefold() for word in ("permission", "persmission", "authorize", "accessright"))
    ]
    assertions = {
        "assembly_hash_matches_inventory": actual == expected.get(ASSEMBLY),
        "target_type_found": target is not None,
        "target_methods_decode_without_error": not errors,
        "permission_method_covered_once": len(permission) == 1,
        "default_policy_method_covered_once": len(defaults) == 1,
        "load_method_covered_once": len(load) == 1,
        "all_six_policy_controls_referenced": all(
            any(name in event["member"] for method in methods for event in method["events"])
            for name in CONTROL_NAMES
        ),
        "all_eight_config_getters_referenced": all(
            any(name in event["member"] for method in methods for event in method["events"])
            for name in CONFIG_GETTERS
        ),
        "six_policy_config_getters_return_nonnullable_cli_int32": all(
            row["returns_cli_int32"]
            for row in config_getter_signatures
            if any(name in row["member"] for name in CONFIG_GETTERS)
            and not any(name in row["member"] for name in ("get_SiteType", "get_IsDiscountV2Active"))
        ) and sum(
            row["returns_cli_int32"] for row in config_getter_signatures
        ) == 6,
        "five_credit_or_limit_controls_have_0_bypass_1_user_choice_2_enforced_mapping": all(
            row["states"] == credit_expected
            for row in configuration_state_contracts
            if row["policy"] != "STOCK_SHORTAGE_PARTIAL_CONVERSION"
        ),
        "stock_control_has_0_user_choice_1_forced_partial_2_enforced_mapping": next(
            row for row in configuration_state_contracts
            if row["policy"] == "STOCK_SHORTAGE_PARTIAL_CONVERSION"
        )["states"] == stock_expected,
        "apply_setad_permission_has_no_permission_decision_call": not permission_named_calls,
        "apply_setad_permission_only_uses_site_type_dc_and_select_button": {
            "VN.SDS.Common.MainData.Entity.ServerConfig.ServerConfigEntity.get_SiteType",
            "Application.BaseData.UserSessionInfo.get_DCRef",
            "Application.BaseTemaplateV2.UIBase.FormBaseV2Dialog.MenuButtonSelect",
            "System.Windows.Forms.ToolStripItem.set_Enabled",
        }.issubset(apply_members),
        "assemblies_were_not_loaded_or_executed": True,
    }
    control_event_index = {
        name: [
            {"method": method["method"], "member": event["member"]}
            for method in methods
            for event in method["events"]
            if name in event["member"]
        ]
        for name in CONTROL_NAMES
    }
    config_event_index = {
        name: [
            {"method": method["method"], "member": event["member"]}
            for method in methods
            for event in method["events"]
            if name in event["member"]
        ]
        for name in CONFIG_GETTERS
    }
    return {
        "artifact": "varanegar_order_sale_policy_gate_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": {
            "assembly_file": ASSEMBLY,
            "assembly_bytes": path.stat().st_size,
            "assembly_sha256": actual,
            "inventory_sha256_match": actual == expected.get(ASSEMBLY),
            "target_type": TARGET_TYPE,
        },
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "application_form_or_command_executions": 0,
            "raw_strings_config_values_or_business_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "matched_method_count": len(methods),
            "matched_event_count": sum(len(row["events"]) for row in methods),
            "policy_control_count": len(CONTROL_NAMES),
            "config_getter_count": len(CONFIG_GETTERS),
            "decode_error_count": len(errors),
        },
        "assertions": assertions,
        "control_event_index": control_event_index,
        "config_event_index": config_event_index,
        "config_getter_signatures": config_getter_signatures,
        "configuration_state_contracts": configuration_state_contracts,
        "selected_permission_method_contract": {
            "method": "ApplySetadPermission",
            "named_permission_decision_calls": permission_named_calls,
            "observed_inputs": ["SERVER_CONFIG_SITE_TYPE", "USER_SESSION_DCREF"],
            "observed_target": "MENU_BUTTON_SELECT_ENABLED",
            "policy_control_permission_enforcement_proven": False,
            "form_or_menu_open_authorization_outside_selected_method_proven": False,
        },
        "errors": errors,
        "methods": methods,
        "limits": [
            "Static IL establishes UI and configuration dependencies, not the effective runtime permission of any identity.",
            "String literals are fingerprinted only, so a permission resource key is not inferred from a caption or message.",
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
