"""Extract the deployed NGT configuration runtime boundary without execution.

The SQL side is handled by the companion configuration-precedence extractor.
This extractor reads PE metadata and IL only. It does not load assemblies, read
configuration files, call application endpoints, or retain arbitrary strings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token


WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_ngt_authorization_runtime_boundary import (  # noqa: E402
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
)


TARGET_FILES = (
    "NGT.Common.dll",
    "NGT.Business.dll",
    "NGT.DataAccess.dll",
    "NGT.WebApi.dll",
)

SIGNAL = re.compile(
    r"(?:AppSettings?|DeviceSettings?|DeviceSettingKeyTypes?|SettingDomain|"
    r"SettingRepository|Configuration|GetBackOfficeSettings|TourDeviceSetting|"
    r"MandatoryCustomerVisit|InventoryControl|MaxDistance|OrderRowLimit|"
    r"MaxOrderAmount|MinOrderAmount|DiscountControl)",
    re.IGNORECASE,
)

SAFE_LITERAL = re.compile(
    r"^(?:AppSettings?|DeviceSettings?|DeviceSettingKeyTypes?|"
    r"NGT_TourAppSettingModel|NGT_TourBackOfficeSettingModel|"
    r"NGT_TourDeviceSettingModel|TourDeviceSettingModel|"
    r"MandatoryCustomerVisit|InventoryControl|MaxDistance|OrderRowLimit|"
    r"OrderRowLimitMin|MaxOrderAmount|MinOrderAmount|DiscountControl|"
    r"SettlementDiscountPercent|MaximumOrderAmount|MinimumOrderAmount|"
    r"MaximumOrderItemCount|MinimumOrderItemCount|IsRemoved|DeviceSettingNo)$",
    re.IGNORECASE,
)

SELECTION_CALL = re.compile(
    r"(?:^|\.)(?:GetQueryByOwner|GetQuery|FirstOrDefault|First|SingleOrDefault|Single|"
    r"Where|Any|Find|FindAll|FindAsync|FindAllAsync|GetById|GetByIdAsync|ToList|ToListAsync|"
    r"AsNoTracking|Include|GetCache|MemoryCache)$",
    re.IGNORECASE,
)

SCOPE_SIGNAL = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|CurrentUser|DCRef)",
    re.IGNORECASE,
)

WINDOW_SIGNAL = re.compile(
    r"(?:AppSettings?|DeviceSettings?|DeviceUsers?|DeviceSettingNo|SubSystemType|"
    r"IsRemoved|ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|UserUniqueId|"
    r"GetQueryByOwner|FirstOrDefault|SingleOrDefault|Expression\.(?:Equal|NotEqual|AndAlso))",
    re.IGNORECASE,
)

CRITICAL_FIELD_SIGNAL = re.compile(
    r"(?:MandatoryCustomerVisit|DisplayunitbyBasedOnUniqueId|SettlementDiscountPercent|"
    r"MaxOrderAmount|MinOrderAmount|OrderRowLimit|DiscountControl)",
    re.IGNORECASE,
)

COMPOSITION_CALL = re.compile(
    r"NGT\.Business\.Domain\.DeviceSettingDomain\.Get(?:AppSetting|General|Tracking|"
    r"PreSale|HotSale|Dist|BackOffice|Inquiry|Print|TaskPriority|Report)Configs$|\.AddRange$",
    re.IGNORECASE,
)

BEHAVIOR_CALL = re.compile(
    r"(?:^|\.)(?:BeginTransaction|Commit|Rollback|SaveChanges|SaveChangesAsync|Add|AddAsync|"
    r"AddRange|Update|UpdateAsync|Remove|RemoveAsync|RemoveRange|Delete|DeleteAsync|"
    r"Find|FindAsync|FindAll|FindAllAsync|GetById|GetByIdAsync)$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _analyze_assembly(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    selected: list[dict[str, Any]] = []
    body_count = 0
    body_errors: list[dict[str, Any]] = []
    redacted_literal_count = 0
    allowlisted_literal_count = 0

    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(method.Name)
            body_count += 1
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                body_errors.append(
                    {
                        "owner": owner,
                        "method": method_name,
                        "error_class": type(exc).__name__,
                        "signal_named": bool(SIGNAL.search(owner) or SIGNAL.search(method_name)),
                    }
                )
                continue

            calls: list[str] = []
            fields: list[str] = []
            safe_literals: list[str] = []
            instructions: list[dict[str, Any]] = []
            method_redacted = 0
            for instruction in body.instructions:
                operand = instruction.operand
                row: dict[str, Any] = {
                    "offset": instruction.offset,
                    "opcode": instruction.mnemonic,
                }
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    calls.append(resolved)
                    row["operand"] = resolved
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    fields.append(resolved)
                    row["operand"] = resolved
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    if SAFE_LITERAL.fullmatch(value):
                        safe_literals.append(value)
                        allowlisted_literal_count += 1
                        row["operand"] = value
                    else:
                        method_redacted += 1
                        redacted_literal_count += 1
                        row["operand"] = "<redacted-non-allowlisted-literal>"
                elif isinstance(operand, Token):
                    row["operand"] = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                elif isinstance(operand, (int, float)):
                    row["operand"] = operand
                instructions.append(row)

            signals = [owner, method_name, *calls, *fields, *safe_literals]
            if not any(SIGNAL.search(value) for value in signals):
                continue
            signal_positions = [
                index
                for index, row in enumerate(instructions)
                if WINDOW_SIGNAL.search(_text(row.get("operand", "")))
            ]
            critical_positions = [
                index
                for index, row in enumerate(instructions)
                if CRITICAL_FIELD_SIGNAL.search(_text(row.get("operand", "")))
            ]
            semantic_references = sorted(
                {
                    _text(row.get("operand", ""))
                    for row in instructions
                    if WINDOW_SIGNAL.search(_text(row.get("operand", "")))
                }
            )
            selected.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "signal_calls": sorted(set(value for value in calls if SIGNAL.search(value))),
                    "selection_calls": sorted(set(value for value in calls if SELECTION_CALL.search(value))),
                    "scope_calls": sorted(set(value for value in calls if SCOPE_SIGNAL.search(value))),
                    "signal_fields": sorted(set(value for value in fields if SIGNAL.search(value))),
                    "scope_fields": sorted(set(value for value in fields if SCOPE_SIGNAL.search(value))),
                    "semantic_references": semantic_references,
                    "composition_call_sequence": [
                        value for value in calls if COMPOSITION_CALL.search(value)
                    ],
                    "behavior_calls_in_order": [
                        value for value in calls if BEHAVIOR_CALL.search(value)
                    ],
                    "allowlisted_code_literals": sorted(set(safe_literals)),
                    "redacted_non_allowlisted_literal_count": method_redacted,
                    "has_conditional_branch": any(
                        instruction.mnemonic.startswith("br") or instruction.mnemonic == "switch"
                        for instruction in body.instructions
                    ),
                    "has_exception_regions": bool(body.exception_handlers),
                    "signal_instruction_windows": [
                        instructions[max(0, index - 18): min(len(instructions), index + 19)]
                        for index in signal_positions[:20]
                    ],
                    "critical_field_instruction_windows": [
                        instructions[max(0, index - 14): min(len(instructions), index + 15)]
                        for index in critical_positions[:20]
                    ],
                }
            )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "method_body_count": body_count,
        "method_body_error_count": len(body_errors),
        "body_errors": body_errors,
        "selected_method_count": len(selected),
        "allowlisted_code_literal_count": allowlisted_literal_count,
        "redacted_non_allowlisted_literal_count": redacted_literal_count,
        "selected_methods": selected,
    }


def collect(source_directory: Path) -> dict[str, Any]:
    assemblies = [_analyze_assembly(source_directory / name) for name in TARGET_FILES]
    selected = [
        {"file": assembly["file"], **method}
        for assembly in assemblies
        for method in assembly["selected_methods"]
    ]
    errors = [
        {"file": assembly["file"], **row}
        for assembly in assemblies
        for row in assembly["body_errors"]
    ]
    runtime_selection = [
        method
        for method in selected
        if method["selection_calls"]
        and (
            SIGNAL.search(method["owner"])
            or SIGNAL.search(method["method"])
            or method["signal_calls"]
            or method["signal_fields"]
        )
    ]
    scope_aware = [method for method in runtime_selection if method["scope_calls"] or method["scope_fields"]]
    is_removed_methods = [
        method for method in runtime_selection
        if any("isremoved" in value.casefold() for value in method["semantic_references"])
    ]
    key_runtime = [
        method
        for method in selected
        if (
            method["owner"] in {
                "NGT.Business.Domain.DeviceSettingDomain",
                "NGT.Business.Domain.AppSettingDomain",
                "NGT.Business.Domain.BackOfficeSettingDomain",
            }
            and method["method"] in {
                "GetDeviceSettings", "GetDistributionDeviceSetting", "GetVanSaleDeviceSetting",
                "GetAppSetting", "GetSettings", "GetAppSettingConfigs", "GetGeneralConfigs",
            }
        )
        or (
            re.search(r"(?:DeviceSettingDomain|AppSettingDomain)\+<(?:Add|Update|Remove|GetDeviceSettings|GetDistributionDeviceSetting|GetVanSaleDeviceSetting|GetBackOfficeConfigs|GetSettings)>", method["owner"])
            and method["method"] == "MoveNext"
        )
    ]
    return {
        "artifact": "varanegar_ngt_configuration_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "assembly_directory": str(source_directory),
            "assemblies": [
                {
                    "file": assembly["file"],
                    "sha256": assembly["sha256"],
                    "bytes": assembly["bytes"],
                }
                for assembly in assemblies
            ],
        },
        "safety": {
            "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
            "assemblies_loaded_or_executed": 0,
            "application_endpoints_or_commands_called": 0,
            "configuration_files_or_values_read": 0,
            "non_allowlisted_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(assemblies),
            "method_body_count": sum(a["method_body_count"] for a in assemblies),
            "method_body_error_count": len(errors),
            "signal_named_body_error_count": sum(1 for row in errors if row["signal_named"]),
            "selected_method_count": len(selected),
            "runtime_selection_method_count": len(runtime_selection),
            "scope_aware_runtime_selection_method_count": len(scope_aware),
            "runtime_selection_method_with_is_removed_signal_count": len(is_removed_methods),
        },
        "assembly_scan": [
            {key: value for key, value in assembly.items() if key not in {"selected_methods", "body_errors"}}
            for assembly in assemblies
        ],
        "body_errors": errors,
        "runtime_selection_methods": runtime_selection,
        "key_runtime_method_contracts": [
            {
                key: method[key]
                for key in (
                    "file", "owner", "method", "parameter_count", "instruction_count",
                    "selection_calls", "scope_calls", "semantic_references",
                    "composition_call_sequence", "behavior_calls_in_order",
                    "has_conditional_branch", "has_exception_regions",
                )
            }
            for method in key_runtime
        ],
        "selected_methods": selected,
        "evidence_limits": [
            "Static IL proves compiled call and field references, not the active request path or current runtime values.",
            "Compiler-generated predicates can carry scope or removed-state checks outside the parent method.",
            "Non-allowlisted strings are redacted, so arbitrary query text and configuration values are not asserted.",
            "Referenced framework repository calls do not alone prove their internal filtering semantics.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    payload = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
