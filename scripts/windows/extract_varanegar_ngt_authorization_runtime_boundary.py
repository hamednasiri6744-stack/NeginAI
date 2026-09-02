"""Extract the deployed NGT authorization evaluator boundary without loading code.

The extractor parses only .NET PE metadata and bounded IL for types whose names
or declared methods explicitly match authorization concepts. It never loads or
executes an assembly and never reads user strings, resources, or configuration.
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
from dncil.clr.token import Token


TARGET_FILES = (
    "Anatoli.Common.Business.dll",
    "Anatoli.Common.DataAccess.dll",
    "Anatoli.Common.WebApi.dll",
    "NGT.Business.dll",
    "NGT.Common.dll",
    "NGT.DataAccess.dll",
    "NGT.ViewModels.dll",
    "NGT.WebApi.dll",
)

TYPE_SIGNAL = re.compile(
    r"(?:^|[.])(?:.*(?:Authoriz|Permission|Principal|UserRole|"
    r"IdentityRole|RolePermission|PermissionCatalog).*)$",
    re.IGNORECASE,
)
METHOD_SIGNAL = re.compile(
    r"(?:Authoriz|Permission|Principal|UserRole|IdentityRole|"
    r"RolePermission|PermissionCatalog|Check.*Access|Has.*Access)",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _full_type_name(row: Any) -> str:
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    if name:
        return f"{namespace}.{name}" if namespace else name
    return type(row).__name__


def _type_name_map(pe: dnfile.dnPE) -> dict[int, str]:
    table = getattr(pe.net.mdtables, "TypeDef", None)
    if not table:
        return {}
    base_names = {
        index: _full_type_name(row) for index, row in enumerate(table.rows, start=1)
    }
    enclosing: dict[int, int] = {}
    nested_table = getattr(pe.net.mdtables, "NestedClass", None)
    if nested_table:
        for row in nested_table.rows:
            enclosing[row.NestedClass.row_index] = row.EnclosingClass.row_index

    resolved: dict[int, str] = {}

    def resolve(index: int, seen: frozenset[int] = frozenset()) -> str:
        if index in resolved:
            return resolved[index]
        if index in seen:
            return base_names[index]
        parent = enclosing.get(index)
        if parent is None:
            result = base_names[index]
        else:
            own_name = _text(table.rows[index - 1].TypeName)
            result = f"{resolve(parent, seen | {index})}+{own_name}"
        resolved[index] = result
        return result

    for index in base_names:
        resolve(index)
    return resolved


def _owner_maps(
    pe: dnfile.dnPE,
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    method_owners: dict[int, str] = {}
    field_owners: dict[int, str] = {}
    type_names = _type_name_map(pe)
    table = getattr(pe.net.mdtables, "TypeDef", None)
    if not table:
        return method_owners, field_owners, type_names
    for type_index, type_row in enumerate(table.rows, start=1):
        owner = type_names[type_index]
        for index in type_row.MethodList or []:
            method_owners[index.row_index] = owner
        for index in type_row.FieldList or []:
            field_owners[index.row_index] = owner
    return method_owners, field_owners, type_names


def _resolve_member_ref(row: Any) -> str:
    parent = getattr(getattr(row, "Class", None), "row", None)
    owner = _full_type_name(parent) if parent is not None else "<unknown>"
    return f"{owner}.{_text(getattr(row, 'Name', ''))}"


def _resolve_token(
    pe: dnfile.dnPE,
    token: Token,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
    type_names: dict[int, str],
) -> str:
    table = pe.net.mdtables.tables.get(token.table)
    if table is None or token.rid <= 0 or token.rid > len(table.rows):
        return f"unresolved:{token.value:#010x}"
    row = table.rows[token.rid - 1]
    table_name = getattr(table, "name", "")
    if table_name == "MemberRef":
        return _resolve_member_ref(row)
    if table_name == "MethodDef":
        return f"{method_owners.get(token.rid, '<unknown>')}.{_text(row.Name)}"
    if table_name == "Field":
        return f"{field_owners.get(token.rid, '<unknown>')}.{_text(row.Name)}"
    if table_name in {"TypeDef", "TypeRef"}:
        if table_name == "TypeDef":
            return type_names.get(token.rid, _full_type_name(row))
        return _full_type_name(row)
    if table_name == "MethodSpec":
        method_row = getattr(getattr(row, "Method", None), "row", None)
        if method_row is None:
            return "MethodSpec:<unknown>"
        if hasattr(method_row, "Class"):
            return _resolve_member_ref(method_row)
        return f"MethodSpec:{_text(getattr(method_row, 'Name', ''))}"
    return f"{table_name}:{_text(getattr(row, 'Name', ''))}"


def _signature_bytes(row: Any) -> bytes:
    value = getattr(getattr(row, "Signature", None), "value", b"")
    return bytes(value) if value else b""


def _compressed_uint(data: bytes, offset: int) -> tuple[int | None, int]:
    if offset >= len(data):
        return None, offset
    first = data[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    if first & 0xC0 == 0x80 and offset + 1 < len(data):
        return ((first & 0x3F) << 8) | data[offset + 1], offset + 2
    if first & 0xE0 == 0xC0 and offset + 3 < len(data):
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            offset + 4,
        )
    return None, offset


def _parameter_count(row: Any) -> int | None:
    signature = _signature_bytes(row)
    if not signature:
        return None
    offset = 1
    if signature[0] & 0x10:  # GENERIC: generic arity precedes parameter count.
        _, offset = _compressed_uint(signature, offset)
    count, _ = _compressed_uint(signature, offset)
    return count


def _token_detail(
    pe: dnfile.dnPE,
    token: Token,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
    type_names: dict[int, str],
) -> dict[str, Any]:
    target = _resolve_token(pe, token, method_owners, field_owners, type_names)
    table = pe.net.mdtables.tables.get(token.table)
    if table is None or token.rid <= 0 or token.rid > len(table.rows):
        return {"target": target, "metadata_token": f"{token.value:#010x}"}
    row = table.rows[token.rid - 1]
    signature = _signature_bytes(row)
    return {
        "target": target,
        "metadata_token": f"{token.value:#010x}",
        "metadata_table": getattr(table, "name", ""),
        "parameter_count": _parameter_count(row),
        "signature_hex": signature.hex(),
    }


def _integer_constant(instruction: Any) -> int | None:
    mnemonic = instruction.mnemonic
    if mnemonic == "ldc.i4.m1":
        return -1
    if mnemonic.startswith("ldc.i4.") and mnemonic[-1:].isdigit():
        return int(mnemonic[-1])
    if mnemonic in {"ldc.i4", "ldc.i4.s"} and isinstance(instruction.operand, int):
        return int(instruction.operand)
    return None


def _analyze(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError("not_dotnet")
    method_owners, field_owners, type_names = _owner_maps(pe)
    table = getattr(pe.net.mdtables, "TypeDef", None)
    types = [] if not table else table.rows

    candidates: list[tuple[str, Any, list[Any]]] = []
    for type_index, type_row in enumerate(types, start=1):
        full_name = type_names[type_index]
        methods = [
            index.row
            for index in (type_row.MethodList or [])
            if getattr(index, "row", None) is not None
        ]
        if TYPE_SIGNAL.search(full_name) or any(
            METHOD_SIGNAL.search(_text(method.Name)) for method in methods
        ):
            candidates.append((full_name, type_row, methods))

    candidate_types: list[dict[str, Any]] = []
    bodies_read = 0
    body_errors = 0
    for full_name, type_row, methods in candidates:
        method_rows: list[dict[str, Any]] = []
        for method in methods:
            method_name = _text(method.Name)
            is_signal_method = bool(METHOD_SIGNAL.search(method_name))
            if not (TYPE_SIGNAL.search(full_name) or is_signal_method):
                continue
            row: dict[str, Any] = {
                "method": method_name,
                "has_body": bool(method.Rva),
                "signal_method_name": is_signal_method,
                "parameter_count": _parameter_count(method),
                "signature_hex": _signature_bytes(method).hex(),
            }
            if not method.Rva:
                method_rows.append(row)
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                body_errors += 1
                row["body_error_class"] = type(exc).__name__
                method_rows.append(row)
                continue
            bodies_read += 1
            calls: set[str] = set()
            fields: set[str] = set()
            metadata_tokens: set[str] = set()
            integers: set[int] = set()
            branch_mnemonics: set[str] = set()
            call_details: list[dict[str, Any]] = []
            resolved_operations: list[tuple[str, str | None, int | None]] = []
            for instruction in body.instructions:
                operand = instruction.operand
                resolved_target: str | None = None
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
                    operand, Token
                ):
                    resolved_target = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    calls.add(resolved_target)
                    call_details.append(
                        _token_detail(
                            pe, operand, method_owners, field_owners, type_names
                        )
                    )
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    resolved_target = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    fields.add(resolved_target)
                elif instruction.mnemonic == "ldtoken" and isinstance(operand, Token):
                    resolved_target = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    metadata_tokens.add(resolved_target)
                if instruction.mnemonic.startswith(("br", "beq", "bne", "ble", "blt", "bge", "bgt")):
                    branch_mnemonics.add(instruction.mnemonic)
                constant = _integer_constant(instruction)
                if constant is not None:
                    integers.add(constant)
                resolved_operations.append(
                    (instruction.mnemonic, resolved_target, constant)
                )
            grant_comparison_constants: list[int] = []
            for index, (_, target, _) in enumerate(resolved_operations):
                if not target or not target.endswith(".get_Grant"):
                    continue
                pending: list[int] = []
                for mnemonic, following_target, constant in resolved_operations[
                    index + 1 : index + 25
                ]:
                    if constant is not None:
                        pending.append(constant)
                    if mnemonic == "ceq" or (
                        following_target
                        and following_target.endswith("Expression.Equal")
                    ):
                        grant_comparison_constants.extend(pending)
                        break
            row.update(
                {
                    "instruction_count": len(body.instructions),
                    "calls": sorted(calls),
                    "call_details": call_details,
                    "referenced_fields": sorted(fields),
                    "metadata_tokens": sorted(metadata_tokens),
                    "integer_constants": sorted(integers),
                    "grant_comparison_constants": sorted(
                        set(grant_comparison_constants)
                    ),
                    "branch_mnemonics": sorted(branch_mnemonics),
                }
            )
            if len(body.instructions) <= 32:
                row["opcode_sequence"] = [
                    instruction.mnemonic for instruction in body.instructions
                ]
            method_rows.append(row)
        candidate_types.append(
            {
                "type": full_name,
                "declared_method_count": len(methods),
                "methods": sorted(method_rows, key=lambda item: item["method"]),
            }
        )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "candidate_type_count": len(candidate_types),
        "candidate_method_count": sum(
            len(row["methods"]) for row in candidate_types
        ),
        "method_bodies_read": bodies_read,
        "method_body_error_count": body_errors,
        "candidate_types": sorted(candidate_types, key=lambda row: row["type"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    assemblies: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for file_name in TARGET_FILES:
        path = args.source_directory / file_name
        try:
            assemblies.append(_analyze(path))
        except Exception as exc:
            failures.append({"file": file_name, "error_class": type(exc).__name__})

    all_methods = [
        {
            "file": assembly["file"],
            "type": type_row["type"],
            **method,
        }
        for assembly in assemblies
        for type_row in assembly["candidate_types"]
        for method in type_row["methods"]
    ]

    def method(
        type_name: str, method_name: str, parameter_count: int | None = None
    ) -> dict[str, Any]:
        matches = [
            row
            for row in all_methods
            if row["type"] == type_name
            and row["method"] == method_name
            and (
                parameter_count is None
                or row.get("parameter_count") == parameter_count
            )
        ]
        if len(matches) != 1:
            raise AssertionError(
                {
                    "type": type_name,
                    "method": method_name,
                    "match_count": len(matches),
                }
            )
        return matches[0]

    web_guard = method(
        "NGT.WebApi.Classes.AnatoliAuthorizeAttribute", "HasWebApiAccess"
    )
    web_grant_predicate = method(
        "NGT.WebApi.Classes.AnatoliAuthorizeAttribute+<>c",
        "<HasWebApiAccess>b__1_0",
    )
    direct_query_candidates = [
        row
        for row in all_methods
        if row["type"] == "NGT.Business.Domain.Authorization.AuthorizationDomain"
        and row["method"] == "GetPermissionsForPrincipal"
        and row.get("grant_comparison_constants")
    ]
    if len(direct_query_candidates) != 1:
        raise AssertionError(
            {"direct_query_candidate_count": len(direct_query_candidates)}
        )
    direct_query = direct_query_candidates[0]
    group_query = method(
        "NGT.Business.Domain.Authorization.AuthorizationDomain",
        "GetPermissionsByGroup",
        3,
    )
    group_permission_callback = method(
        "NGT.Business.Domain.Authorization.AuthorizationDomain"
        "+<>c__DisplayClass56_0",
        "<GetPermissionsByGroup>b__2",
        1,
    )
    catalog_save = method(
        "NGT.Business.Domain.Authorization.AuthorizationDomain"
        "+<SaveNGTPermissionCatalogs>d__63",
        "MoveNext",
    )
    runtime_guard_contract = {
        "guard_type": web_guard["type"],
        "guard_method": web_guard["method"],
        "calls_direct_permission_query": any(
            call.endswith("AuthorizationDomain.GetPermissionsForPrincipal")
            for call in web_guard["calls"]
        ),
        "calls_group_permission_query": any(
            call.endswith("AuthorizationDomain.GetPermissionsByGroup")
            for call in web_guard["calls"]
        ),
        "unions_direct_and_group_results": "System.Linq.Enumerable.Union"
        in web_guard["calls"],
        "uses_any_grant_predicate": "System.Linq.Enumerable.Any"
        in web_guard["calls"],
        "guard_direct_query_parameter_counts": sorted(
            {
                row["parameter_count"]
                for row in web_guard["call_details"]
                if row["target"].endswith(
                    "AuthorizationDomain.GetPermissionsForPrincipal"
                )
            }
        ),
        "guard_group_query_parameter_counts": sorted(
            {
                row["parameter_count"]
                for row in web_guard["call_details"]
                if row["target"].endswith(
                    "AuthorizationDomain.GetPermissionsByGroup"
                )
            }
        ),
        "direct_query_grant_equality_constants": direct_query[
            "grant_comparison_constants"
        ],
        "direct_query_splits_action_on_comma": "System.String.Split"
        in direct_query["calls"],
        "direct_query_normalizes_action_lower_and_trim": (
            "System.String.ToLower" in direct_query["calls"]
            and "System.String.Trim" in direct_query["calls"]
        ),
        "direct_query_uses_exact_action_membership": (
            "System.Linq.Enumerable.Contains" in direct_query["metadata_tokens"]
        ),
        "direct_query_resource_name_equality_expression_present": (
            "Anatoli.DataAccess.Models.Identity.ApplicationModuleResource.get_Name"
            in direct_query["metadata_tokens"]
            and "System.Linq.Expressions.Expression.Equal"
            in direct_query["calls"]
        ),
        "group_query_parameter_count": group_query["parameter_count"],
        "group_query_grant_equality_constants": group_query[
            "grant_comparison_constants"
        ],
        "group_query_callback_calls_direct_query": any(
            call.endswith("AuthorizationDomain.GetPermissionsForPrincipal")
            for call in group_permission_callback["calls"]
        ),
        "group_query_callback_direct_query_parameter_counts": sorted(
            {
                row["parameter_count"]
                for row in group_permission_callback["call_details"]
                if row["target"].endswith(
                    "AuthorizationDomain.GetPermissionsForPrincipal"
                )
            }
        ),
        "post_union_veto_grant_equality_constants": web_grant_predicate[
            "grant_comparison_constants"
        ],
        "guard_catalog_named_call_count": sum(
            "catalog" in call.casefold() for call in web_guard["calls"]
        ),
        "catalog_save_creates_atomic_principal_permissions": (
            "Anatoli.DataAccess.Models.Identity.PrincipalPermission..ctor"
            in catalog_save["calls"]
            and "Anatoli.DataAccess.Models.Identity.PrincipalPermission.set_Grant"
            in catalog_save["calls"]
            and "Anatoli.DataAccess.Models.Identity.PermissionCatalog"
            ".get_PermissionCatalogPermissions"
            in catalog_save["calls"]
        ),
    }
    artifact = {
        "artifact": "varanegar_ngt_authorization_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "directory": str(args.source_directory),
            "target_files": list(TARGET_FILES),
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_DOTNET_METADATA_AND_BOUNDED_IL",
            "assemblies_loaded_or_executed": 0,
            "config_files_read": 0,
            "resources_read": 0,
            "user_strings_read_or_persisted": 0,
            "credentials_read_or_persisted": 0,
            "database_connections": 0,
        },
        "summary": {
            "target_file_count": len(TARGET_FILES),
            "analyzed_file_count": len(assemblies),
            "failed_file_count": len(failures),
            "candidate_type_count": sum(
                row["candidate_type_count"] for row in assemblies
            ),
            "candidate_method_count": len(all_methods),
            "method_bodies_read": sum(
                row["method_bodies_read"] for row in assemblies
            ),
            "method_body_error_count": sum(
                row["method_body_error_count"] for row in assemblies
            ),
            "method_calling_permission_named_member_count": sum(
                any(METHOD_SIGNAL.search(call) for call in method.get("calls", []))
                for method in all_methods
            ),
            "runtime_guard_uses_direct_and_group_atomic_queries": (
                runtime_guard_contract["calls_direct_permission_query"]
                and runtime_guard_contract["calls_group_permission_query"]
                and runtime_guard_contract["unions_direct_and_group_results"]
            ),
            "runtime_guard_direct_query_grant_value": (
                runtime_guard_contract["direct_query_grant_equality_constants"][0]
            ),
            "runtime_guard_action_contract_is_comma_split_exact_membership": (
                runtime_guard_contract["direct_query_splits_action_on_comma"]
                and runtime_guard_contract[
                    "direct_query_normalizes_action_lower_and_trim"
                ]
                and runtime_guard_contract[
                    "direct_query_uses_exact_action_membership"
                ]
            ),
            "runtime_guard_group_query_delegates_to_grant_filtered_direct_query": (
                runtime_guard_contract["guard_group_query_parameter_counts"] == [3]
                and runtime_guard_contract["group_query_parameter_count"] == 3
                and runtime_guard_contract[
                    "group_query_callback_calls_direct_query"
                ]
                and runtime_guard_contract[
                    "group_query_callback_direct_query_parameter_counts"
                ]
                == [3]
                and runtime_guard_contract[
                    "direct_query_grant_equality_constants"
                ]
                == [1]
            ),
            "runtime_guard_post_union_veto_grant_value": (
                runtime_guard_contract[
                    "post_union_veto_grant_equality_constants"
                ][0]
            ),
            "runtime_guard_catalog_named_call_count": runtime_guard_contract[
                "guard_catalog_named_call_count"
            ],
            "catalog_save_materializes_atomic_permission_rows": (
                runtime_guard_contract[
                    "catalog_save_creates_atomic_principal_permissions"
                ]
            ),
            "atomic_vs_catalog_precedence_proven": False,
            "legacy_to_ngt_crosswalk_proven": False,
        },
        "failures": failures,
        "runtime_guard_contract": runtime_guard_contract,
        "assemblies": assemblies,
        "evidence_limits": [
            "Candidate selection is name-based and can miss obfuscated or generic evaluators.",
            "Static metadata and IL do not prove runtime route reachability or the current authenticated user's effective permission.",
            "No atomic-versus-catalog precedence is claimed until a concrete evaluator call path is identified.",
            "No legacy AccessNode-to-NGT permission crosswalk is inferred from similar names.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
