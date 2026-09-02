"""Extract the deployed NGT application/data-owner scope propagation boundary.

The extractor parses .NET PE metadata and IL only.  It never loads an assembly,
invokes application code, reads configuration, or observes a request/identity.
Only narrowly allowlisted owner-header code literals may be persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_ngt_authorization_runtime_boundary import (
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
    _token_detail,
)


TARGET_FILES = (
    "Anatoli.Common.WebApi.dll",
    "NGT.Business.dll",
    "NGT.WebApi.dll",
)

SCOPE_SIGNAL = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerKey|OwnerInfo)",
    re.IGNORECASE,
)

# These are protocol/code identifiers, not runtime values.  Anything else is
# counted as redacted and is never copied into the artifact.
SAFE_LITERAL = re.compile(
    r"^(?:ApplicationOwner(?:Key|Id)?|DataOwner(?:Center)?(?:Key|Id)?|OwnerKey)$",
    re.IGNORECASE,
)

TRACE_METHODS = {
    ("Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute", "get_OwnerKey"),
    ("Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute", "get_DataOwnerKey"),
    ("Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute", "get_DataOwnerCenterKey"),
    ("Anatoli.Common.WebApi.ValidateModelAttribute", "get_OwnerInfo"),
    ("Anatoli.Common.WebApi.Controllers.BaseAnatoliApiController", "get_OwnerInfo"),
    ("Anatoli.Common.WebApi.Controllers.BaseAnatoliApiController", "GetUserId"),
    ("NGT.Business.Domain.Authorization.AuthorizationDomain", ".ctor"),
    ("NGT.WebApi.Classes.AnatoliAuthorizeAttribute", "HasWebApiAccess"),
    ("NGT.WebApi.Classes.AnatoliAuthorizeAttribute", "GetUserId"),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _safe_trace_operand(
    pe: dnfile.dnPE,
    operand: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
    type_names: dict[int, str],
) -> dict[str, Any]:
    if isinstance(operand, StringToken):
        item = pe.net.user_strings.get(operand.rid)
        value = "" if item is None else _text(item.value)
        return {
            "operand": value if SAFE_LITERAL.fullmatch(value) else "<redacted-non-scope-literal>"
        }
    if isinstance(operand, Token):
        return {
            "operand": _resolve_token(
                pe, operand, method_owners, field_owners, type_names
            )
        }
    if isinstance(operand, (int, float)):
        return {"operand": operand}
    return {}


def _analyze(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError("not_dotnet")
    method_owners, field_owners, type_names = _owner_maps(pe)
    type_table = pe.net.mdtables.TypeDef
    selected: list[dict[str, Any]] = []
    method_body_count = 0
    method_body_error_count = 0
    body_errors: list[dict[str, Any]] = []
    safe_literal_count = 0
    redacted_literal_count = 0

    for type_index, type_row in enumerate(type_table.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(method.Name)
            method_body_count += 1
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                method_body_error_count += 1
                body_errors.append(
                    {
                        "owner": owner,
                        "method": method_name,
                        "parameter_count": _parameter_count(method),
                        "error_class": type(exc).__name__,
                        "scope_named_method_or_type": bool(
                            SCOPE_SIGNAL.search(owner) or SCOPE_SIGNAL.search(method_name)
                        ),
                    }
                )
                continue
            ordered_calls: list[str] = []
            ordered_call_details: list[dict[str, Any]] = []
            referenced_fields: list[str] = []
            safe_literals: list[str] = []
            method_redacted_literal_count = 0
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                    target = _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    ordered_calls.append(target)
                    ordered_call_details.append(
                        _token_detail(pe, operand, method_owners, field_owners, type_names)
                    )
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    referenced_fields.append(
                        _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    )
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    if SAFE_LITERAL.fullmatch(value):
                        safe_literals.append(value)
                        safe_literal_count += 1
                    else:
                        method_redacted_literal_count += 1
                        redacted_literal_count += 1

            signal_targets = [
                value
                for value in [owner, method_name, *ordered_calls, *referenced_fields]
                if SCOPE_SIGNAL.search(value)
            ]
            if not signal_targets and (owner, method_name) not in TRACE_METHODS:
                continue
            selected.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "ordered_scope_calls": [
                        value for value in ordered_calls if SCOPE_SIGNAL.search(value)
                    ],
                    "guid_parse_call_count": sum(
                        value == "System.Guid.Parse" for value in ordered_calls
                    ),
                    "authorization_domain_constructor_call_parameter_counts": [
                        detail.get("parameter_count")
                        for detail in ordered_call_details
                        if detail["target"]
                        == "NGT.Business.Domain.Authorization.AuthorizationDomain..ctor"
                    ],
                    "referenced_scope_fields": sorted(
                        set(value for value in referenced_fields if SCOPE_SIGNAL.search(value))
                    ),
                    "allowlisted_code_literals": safe_literals,
                    "redacted_non_scope_literal_count": method_redacted_literal_count,
                    "opcode_sequence": [instruction.mnemonic for instruction in body.instructions],
                    "safe_instruction_trace": [
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            **_safe_trace_operand(
                                pe,
                                instruction.operand,
                                method_owners,
                                field_owners,
                                type_names,
                            ),
                        }
                        for instruction in body.instructions
                    ]
                    if (owner, method_name) in TRACE_METHODS
                    else [],
                }
            )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "method_body_count": method_body_count,
        "method_body_error_count": method_body_error_count,
        "selected_scope_method_count": len(selected),
        "allowlisted_code_literal_count": safe_literal_count,
        "redacted_non_scope_literal_count": redacted_literal_count,
        "body_errors": body_errors,
        "selected_methods": selected,
    }


def _find(
    methods: list[dict[str, Any]], owner: str, name: str, parameter_count: int | None = None
) -> dict[str, Any]:
    matches = [
        row
        for row in methods
        if row["owner"] == owner
        and row["method"] == name
        and (parameter_count is None or row["parameter_count"] == parameter_count)
    ]
    if len(matches) != 1:
        raise AssertionError(
            {"owner": owner, "method": name, "parameter_count": parameter_count, "matches": len(matches)}
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--authorization-runtime-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    authorization = json.loads(
        args.authorization_runtime_artifact.read_text(encoding="utf-8-sig")
    )
    expected_hashes = {row["file"]: row["sha256"] for row in authorization["assemblies"]}
    assemblies = [_analyze(args.source_directory / name) for name in TARGET_FILES]
    for row in assemblies:
        if expected_hashes.get(row["file"]) != row["sha256"]:
            raise AssertionError(f"authorization source hash mismatch: {row['file']}")

    methods = [
        {"file": assembly["file"], **method}
        for assembly in assemblies
        for method in assembly["selected_methods"]
    ]
    scope_named_body_errors = [
        {"file": assembly["file"], **row}
        for assembly in assemblies
        for row in assembly["body_errors"]
        if row["scope_named_method_or_type"]
    ]
    if scope_named_body_errors:
        raise AssertionError({"scope_named_body_errors": scope_named_body_errors})
    base_owner = "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute"
    data_owner = _find(methods, base_owner, "get_DataOwnerKey", 0)
    center_owner = _find(methods, base_owner, "get_DataOwnerCenterKey", 0)
    owner_key = _find(methods, base_owner, "get_OwnerKey", 0)
    has_owner = _find(methods, base_owner, "get_HasOwnerKey", 0)
    owner_info = _find(
        methods,
        "NGT.Business.Domain.Authorization.AuthorizationDomain",
        "GetBackOfficeOwnerInfo",
    )
    authorization_constructor = _find(
        methods,
        "NGT.Business.Domain.Authorization.AuthorizationDomain",
        ".ctor",
        4,
    )
    authorization_constructor_one = _find(
        methods,
        "NGT.Business.Domain.Authorization.AuthorizationDomain",
        ".ctor",
        1,
    )
    authorization_constructor_three = _find(
        methods,
        "NGT.Business.Domain.Authorization.AuthorizationDomain",
        ".ctor",
        3,
    )
    web_guard = _find(
        methods,
        "NGT.WebApi.Classes.AnatoliAuthorizeAttribute",
        "HasWebApiAccess",
        0,
    )
    controller_owner_info = _find(
        methods,
        "Anatoli.Common.WebApi.Controllers.BaseAnatoliApiController",
        "get_OwnerInfo",
        0,
    )
    validation_owner_info = _find(
        methods,
        "Anatoli.Common.WebApi.ValidateModelAttribute",
        "get_OwnerInfo",
        0,
    )

    call_counter = Counter(
        call
        for row in methods
        for call in row["ordered_scope_calls"]
    )
    consumer_methods = [
        row
        for row in methods
        if any(
            call.endswith(("get_DataOwnerKey", "get_DataOwnerCenterKey", "get_ApplicationOwnerKey"))
            for call in row["ordered_scope_calls"]
        )
    ]
    header_literals = sorted(
        set(
            literal
            for row in (owner_key, data_owner, center_owner)
            for literal in row["allowlisted_code_literals"]
        ),
        key=str.casefold,
    )

    contract = {
        "owner_key_reads_and_parses_direct_request_value": owner_key["guid_parse_call_count"] == 1,
        "has_owner_key_probes_owner_key_getter": any(
            call.endswith("get_OwnerKey") for call in has_owner["ordered_scope_calls"]
        ),
        "data_owner_header_missing_falls_back_to_owner_key": any(
            call.endswith("get_OwnerKey") for call in data_owner["ordered_scope_calls"]
        ),
        "data_owner_center_header_missing_falls_back_to_data_owner_key": any(
            call.endswith("get_DataOwnerKey") for call in center_owner["ordered_scope_calls"]
        ),
        "header_values_are_parsed_as_guid": all(
            row["guid_parse_call_count"] == 1
            for row in (data_owner, center_owner)
        ),
        "allowlisted_owner_header_literals": header_literals,
        "authorization_domain_four_parameter_constructor_sets_all_three_owner_keys": all(
            any(call.endswith(suffix) for call in authorization_constructor["ordered_scope_calls"])
            for suffix in (
                "set_ApplicationOwnerKey",
                "set_DataOwnerKey",
                "set_DataOwnerCenterKey",
            )
        ),
        "authorization_domain_one_parameter_constructor_repeats_one_key_three_times": (
            authorization_constructor_one["opcode_sequence"][:5]
            == ["ldarg.0", "ldarg.1", "ldarg.1", "ldarg.1", "call"]
            and authorization_constructor_one[
                "authorization_domain_constructor_call_parameter_counts"
            ]
            == [3]
        ),
        "authorization_domain_three_parameter_constructor_delegates_positionally_to_four": (
            authorization_constructor_three["opcode_sequence"][:4]
            == ["ldarg.0", "ldarg.1", "ldarg.2", "ldarg.3"]
            and authorization_constructor_three[
                "authorization_domain_constructor_call_parameter_counts"
            ]
            == [4]
        ),
        "web_permission_guard_reads_owner_key_but_not_data_owner_headers": (
            sum(call.endswith("get_OwnerKey") for call in web_guard["ordered_scope_calls"])
            == 2
            and not any(
                call.endswith(("get_DataOwnerKey", "get_DataOwnerCenterKey"))
                for call in web_guard["ordered_scope_calls"]
            )
            and web_guard["authorization_domain_constructor_call_parameter_counts"]
            == [1, 1]
        ),
        "controller_owner_info_materializes_all_three_headers_and_current_user": all(
            any(call.endswith(suffix) for call in controller_owner_info["ordered_scope_calls"])
            for suffix in (
                "set_ApplicationOwnerKey",
                "set_DataOwnerKey",
                "set_DataOwnerCenterKey",
                "set_UserId",
            )
        ),
        "model_validation_owner_info_materializes_all_three_headers_without_user": (
            all(
                any(call.endswith(suffix) for call in validation_owner_info["ordered_scope_calls"])
                for suffix in (
                    "set_ApplicationOwnerKey",
                    "set_DataOwnerKey",
                    "set_DataOwnerCenterKey",
                )
            )
            and not any(
                call.endswith("set_UserId") for call in validation_owner_info["ordered_scope_calls"]
            )
        ),
        "back_office_owner_info_uses_explicit_owner_keys": any(
            call.endswith(("get_ApplicationOwnerKey", "get_DataOwnerKey", "get_DataOwnerCenterKey"))
            for call in owner_info["ordered_scope_calls"]
        ),
        "scope_consumer_method_count": len(consumer_methods),
        "scope_consumer_declaring_type_count": len(set(row["owner"] for row in consumer_methods)),
        "scope_call_counts": dict(sorted(call_counter.items())),
    }
    required_true = (
        "owner_key_reads_and_parses_direct_request_value",
        "has_owner_key_probes_owner_key_getter",
        "data_owner_header_missing_falls_back_to_owner_key",
        "data_owner_center_header_missing_falls_back_to_data_owner_key",
        "header_values_are_parsed_as_guid",
        "authorization_domain_four_parameter_constructor_sets_all_three_owner_keys",
        "authorization_domain_one_parameter_constructor_repeats_one_key_three_times",
        "authorization_domain_three_parameter_constructor_delegates_positionally_to_four",
        "web_permission_guard_reads_owner_key_but_not_data_owner_headers",
        "controller_owner_info_materializes_all_three_headers_and_current_user",
        "model_validation_owner_info_materializes_all_three_headers_without_user",
    )
    if not all(contract[key] for key in required_true):
        raise AssertionError({key: contract[key] for key in required_true})

    artifact = {
        "artifact": "varanegar_ngt_owner_scope_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS",
        "source": {
            "assemblies": [
                {key: row[key] for key in ("file", "sha256", "bytes")}
                for row in assemblies
            ],
            "authorization_runtime_artifact": str(args.authorization_runtime_artifact),
            "authorization_runtime_artifact_sha256": hashlib.sha256(
                args.authorization_runtime_artifact.read_bytes()
            ).hexdigest(),
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_TARGETED_OWNER_SCOPE_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "configuration_files_read": 0,
            "runtime_requests_or_endpoints_invoked": 0,
            "runtime_identity_or_header_values_read_or_persisted": 0,
            "allowlisted_code_protocol_literals_read_or_persisted": sum(
                row["allowlisted_code_literal_count"] for row in assemblies
            ),
            "non_scope_literals_persisted": 0,
        },
        "summary": {
            "analyzed_assembly_count": len(assemblies),
            "method_body_count": sum(row["method_body_count"] for row in assemblies),
            "method_body_error_count": sum(row["method_body_error_count"] for row in assemblies),
            "scope_named_method_body_error_count": len(scope_named_body_errors),
            "selected_scope_method_count": len(methods),
            "scope_consumer_method_count": contract["scope_consumer_method_count"],
            "scope_consumer_declaring_type_count": contract["scope_consumer_declaring_type_count"],
            "header_fallback_chain_is_center_to_data_owner_to_owner": (
                contract["data_owner_header_missing_falls_back_to_owner_key"]
                and contract["data_owner_center_header_missing_falls_back_to_data_owner_key"]
            ),
            "header_values_are_parsed_as_guid": contract["header_values_are_parsed_as_guid"],
            "authorization_domain_four_parameter_constructor_sets_all_three_owner_keys": contract[
                "authorization_domain_four_parameter_constructor_sets_all_three_owner_keys"
            ],
            "authorization_domain_one_parameter_constructor_repeats_one_key_three_times": contract[
                "authorization_domain_one_parameter_constructor_repeats_one_key_three_times"
            ],
            "web_permission_guard_reads_owner_key_but_not_data_owner_headers": contract[
                "web_permission_guard_reads_owner_key_but_not_data_owner_headers"
            ],
        },
        "contract": contract,
        "assembly_scan": [
            {
                key: row[key]
                for key in (
                    "file",
                    "sha256",
                    "bytes",
                    "method_body_count",
                    "method_body_error_count",
                    "selected_scope_method_count",
                    "allowlisted_code_literal_count",
                    "redacted_non_scope_literal_count",
                )
            }
            for row in assemblies
        ],
        "non_scope_named_body_errors": [
            {"file": assembly["file"], **row}
            for assembly in assemblies
            for row in assembly["body_errors"]
            if not row["scope_named_method_or_type"]
        ],
        "selected_methods": methods,
        "evidence_limits": [
            "Static IL proves code shape and call sites, not the values supplied by a runtime request.",
            "A fallback chain does not prove that every endpoint validates owner membership or tenant consistency.",
            "Only three deployed assemblies are scanned; data-access/model-only propagation may exist elsewhere.",
            "No claim is made that a GUID selected from a header belongs to the authenticated principal.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
