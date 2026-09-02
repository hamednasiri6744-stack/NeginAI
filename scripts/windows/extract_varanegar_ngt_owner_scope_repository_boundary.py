"""Extract owner-scope behavior of the deployed NGT repository layer.

Static PE metadata/IL only; assemblies are never loaded or executed.  The
artifact contains code identifiers and structural counts, not data or runtime
owner values.
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

from extract_varanegar_ngt_authorization_runtime_boundary import (
    _compressed_uint,
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
)


TARGETS = {
    "Anatoli.Common.DataAccess.dll": re.compile(
        r"^Anatoli\.Common\.DataAccess\.(?:Repositories\.(?:BaseAnatoliRepository|AnatoliRepository)`1(?:\+.*)?|Models\.(?:BaseModel|OwnerInfo))$"
    ),
    "NGT.DataAccess.dll": re.compile(
        r"^(?:NGT\.DataAccess\.AnatoliDbContext|NGT\.DataAccess\.Repositories\.(?:Account\.)?(?:PrincipalPermissionRepository|UserGroupUserRepository|PrincipalRepository|PermissionRepository))$"
    ),
}

SCOPE_SIGNAL = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|OwnerKey|BaseModel)",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _extends_contract(pe: dnfile.dnPE, type_row: Any, type_names: dict[int, str]) -> dict[str, Any]:
    coded = getattr(type_row, "Extends", None)
    row = getattr(coded, "row", None)
    if row is None:
        return {"kind": "none"}
    table_name = type(row).__name__
    if table_name == "TypeSpecRow":
        signature = bytes(getattr(getattr(row, "Signature", None), "value", b"") or b"")
        result: dict[str, Any] = {"kind": "TypeSpec", "signature_hex": signature.hex()}
        if len(signature) >= 3 and signature[0] == 0x15 and signature[1] in (0x11, 0x12):
            coded_index, _ = _compressed_uint(signature, 2)
            if coded_index is not None:
                tag = coded_index & 0x3
                rid = coded_index >> 2
                table = {0: "TypeDef", 1: "TypeRef", 2: "TypeSpec"}.get(tag)
                if table and rid:
                    target_table = getattr(pe.net.mdtables, table, None)
                    if target_table is not None and rid <= len(target_table.rows):
                        base_row = target_table.rows[rid - 1]
                        if table == "TypeDef":
                            result["generic_base"] = type_names.get(rid, "<unknown>")
                        elif table == "TypeRef":
                            namespace = _text(getattr(base_row, "TypeNamespace", ""))
                            name = _text(getattr(base_row, "TypeName", ""))
                            result["generic_base"] = f"{namespace}.{name}" if namespace else name
        return result
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    return {"kind": table_name, "base": f"{namespace}.{name}" if namespace else name}


def _analyze(path: Path, target_re: re.Pattern[str]) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError("not_dotnet")
    method_owners, field_owners, type_names = _owner_maps(pe)
    targets: list[dict[str, Any]] = []
    body_errors: list[dict[str, Any]] = []
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        if not target_re.search(owner):
            continue
        methods: list[dict[str, Any]] = []
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None:
                continue
            item: dict[str, Any] = {
                "method": _text(method.Name),
                "method_metadata_token": f"0x06{method_index.row_index:06x}",
                "parameter_count": _parameter_count(method),
                "signature_hex": _signature_bytes(method).hex(),
                "has_body": bool(method.Rva),
            }
            if not method.Rva:
                methods.append(item)
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                body_errors.append(
                    {"owner": owner, "method": item["method"], "error_class": type(exc).__name__}
                )
                item["body_error_class"] = type(exc).__name__
                methods.append(item)
                continue
            calls: list[str] = []
            fields: list[str] = []
            metadata_tokens: list[str] = []
            literal_count = 0
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                    calls.append(_resolve_token(pe, operand, method_owners, field_owners, type_names))
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    fields.append(_resolve_token(pe, operand, method_owners, field_owners, type_names))
                elif instruction.mnemonic == "ldtoken" and isinstance(operand, Token):
                    metadata_tokens.append(
                        _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    )
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    literal_count += 1
            item.update(
                {
                    "instruction_count": len(body.instructions),
                    "ordered_scope_calls": [call for call in calls if SCOPE_SIGNAL.search(call)],
                    "ordered_calls": calls
                    if item["method"]
                    in {"GetQuery", "GetQueryByOwner", "CalcExtraPredict", "Add", "Update"}
                    else [],
                    "referenced_scope_fields": sorted(set(field for field in fields if SCOPE_SIGNAL.search(field))),
                    "scope_metadata_tokens": sorted(
                        set(token for token in metadata_tokens if SCOPE_SIGNAL.search(token))
                    ),
                    "all_call_count": len(calls),
                    "redacted_string_literal_count": literal_count,
                    "opcode_sequence": [instruction.mnemonic for instruction in body.instructions],
                    "safe_instruction_trace": [
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            **(
                                {
                                    "operand": _resolve_token(
                                        pe,
                                        instruction.operand,
                                        method_owners,
                                        field_owners,
                                        type_names,
                                    )
                                }
                                if isinstance(instruction.operand, Token)
                                and not isinstance(instruction.operand, StringToken)
                                else {"operand": "<redacted-string-literal>"}
                                if isinstance(instruction.operand, StringToken)
                                else {"operand": instruction.operand}
                                if isinstance(instruction.operand, (int, float))
                                else {}
                            ),
                        }
                        for instruction in body.instructions
                    ]
                    if item["method"] in {"GetQueryByOwner", "CalcExtraPredict"}
                    else [],
                }
            )
            methods.append(item)
        targets.append(
            {
                "type": owner,
                "extends": _extends_contract(pe, type_row, type_names),
                "declared_method_count": len(methods),
                "methods": methods,
            }
        )
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "target_type_count": len(targets),
        "target_method_count": sum(row["declared_method_count"] for row in targets),
        "body_error_count": len(body_errors),
        "body_errors": body_errors,
        "target_types": targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--runtime-scope-artifact", required=True, type=Path)
    parser.add_argument("--authorization-runtime-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    runtime = json.loads(args.runtime_scope_artifact.read_text(encoding="utf-8-sig"))
    authorization = json.loads(
        args.authorization_runtime_artifact.read_text(encoding="utf-8-sig")
    )
    runtime_hashes = {row["file"]: row["sha256"] for row in runtime["source"]["assemblies"]}
    assemblies = [
        _analyze(args.source_directory / file_name, target_re)
        for file_name, target_re in TARGETS.items()
    ]
    common = next(row for row in assemblies if row["file"] == "Anatoli.Common.DataAccess.dll")
    ngt = next(row for row in assemblies if row["file"] == "NGT.DataAccess.dll")
    authorization_hashes = {
        row["file"]: row["sha256"] for row in authorization["assemblies"]
    }
    if common["sha256"] != authorization_hashes.get("Anatoli.Common.DataAccess.dll"):
        raise AssertionError("common data-access source drift")
    if ngt["sha256"] != authorization_hashes.get("NGT.DataAccess.dll"):
        raise AssertionError("NGT data-access source drift")
    if common["body_error_count"] or ngt["body_error_count"]:
        raise AssertionError({"target_body_errors": common["body_errors"] + ngt["body_errors"]})

    by_type = {
        row["type"]: row
        for assembly in assemblies
        for row in assembly["target_types"]
    }
    base_candidates = [
        row for name, row in by_type.items() if name.endswith(".BaseAnatoliRepository`1")
    ]
    if len(base_candidates) != 1:
        raise AssertionError({"base_repository_candidates": list(by_type)})
    base = base_candidates[0]
    base_family = [
        row
        for name, row in by_type.items()
        if name == base["type"] or name.startswith(base["type"] + "+")
    ]
    base_scope_methods = [
        {"owner": row["type"], **method}
        for row in base_family
        for method in row["methods"]
        if method.get("ordered_scope_calls")
        or method.get("referenced_scope_fields")
        or method.get("scope_metadata_tokens")
    ]
    concrete_names = (
        "NGT.DataAccess.Repositories.Account.PrincipalPermissionRepository",
        "NGT.DataAccess.Repositories.UserGroupUserRepository",
        "NGT.DataAccess.Repositories.PrincipalRepository",
    )
    missing = [name for name in concrete_names if name not in by_type]
    if missing:
        raise AssertionError({"missing_concrete_repositories": missing})
    concrete_bases = {name: by_type[name]["extends"] for name in concrete_names}
    owner_aware_bases = {
        "Anatoli.Common.DataAccess.Repositories.BaseAnatoliRepository`1",
        "Anatoli.Common.DataAccess.Repositories.AnatoliRepository`1",
    }
    concrete_inherit_base = all(
        row.get("generic_base", "") in owner_aware_bases
        for row in concrete_bases.values()
    )
    anatoli_base = by_type["Anatoli.Common.DataAccess.Repositories.AnatoliRepository`1"]
    calc_extra = [
        method for method in anatoli_base["methods"] if method["method"] == "CalcExtraPredict"
    ]
    if len(calc_extra) != 1:
        raise AssertionError({"calc_extra_predict_count": len(calc_extra)})
    calc_extra = calc_extra[0]
    calc_scope_calls = calc_extra["ordered_scope_calls"]
    calc_uses_data_owner_and_center = all(
        any(call.endswith(suffix) for call in calc_scope_calls)
        for suffix in (
            "get_DataOwnerKey",
            "get_DataOwnerCenterKey",
            "get_IgnoreDataOwnerCenterKey",
            "get_IsCenteralizedEntity",
        )
    )
    base_get_query = [method for method in base["methods"] if method["method"] == "GetQuery"]
    if len(base_get_query) != 1:
        raise AssertionError({"base_get_query_count": len(base_get_query)})
    base_get_query = base_get_query[0]
    anatoli_get_query_by_owner = [
        method for method in anatoli_base["methods"] if method["method"] == "GetQueryByOwner"
    ]
    if len(anatoli_get_query_by_owner) != 1:
        raise AssertionError(
            {"anatoli_get_query_by_owner_count": len(anatoli_get_query_by_owner)}
        )
    anatoli_get_query_by_owner = anatoli_get_query_by_owner[0]
    raw_get_query_returns_dbset = (
        base_get_query["ordered_calls"] == ["TypeSpecRow.get_DbSet"]
        and "CalcExtraPredict" not in " ".join(base_get_query["ordered_calls"])
    )
    owner_query_calls_calc_predicate = (
        "TypeSpecRow.CalcExtraPredict" in anatoli_get_query_by_owner["ordered_calls"]
        and "System.Linq.Queryable.Where" in anatoli_get_query_by_owner["ordered_calls"]
    )
    concrete_get_query_override_count = sum(
        any(method["method"] == "GetQuery" for method in by_type[name]["methods"])
        for name in concrete_names
    )

    authorization_methods = [
        {"type": type_row["type"], **method}
        for assembly in authorization["assemblies"]
        for type_row in assembly["candidate_types"]
        for method in type_row["methods"]
        if type_row["type"]
        == "NGT.Business.Domain.Authorization.AuthorizationDomain"
        and (
            (method["method"] == "GetPermissionsForPrincipal" and method.get("parameter_count") == 3)
            or (method["method"] == "GetPermissionsByGroup" and method.get("parameter_count") == 3)
        )
    ]
    if len(authorization_methods) != 2:
        raise AssertionError({"authorization_query_method_count": len(authorization_methods)})
    authorization_calls_raw_get_query = all(
        "TypeSpecRow.GetQuery" in method.get("calls", [])
        and not any(call.endswith("GetQueryByOwner") for call in method.get("calls", []))
        for method in authorization_methods
    )

    if not all(
        (
            concrete_inherit_base,
            calc_uses_data_owner_and_center,
            raw_get_query_returns_dbset,
            owner_query_calls_calc_predicate,
            concrete_get_query_override_count == 0,
            authorization_calls_raw_get_query,
        )
    ):
        raise AssertionError(
            {
                "concrete_inherit_owner_aware_base": concrete_inherit_base,
                "calc_uses_data_owner_and_center": calc_uses_data_owner_and_center,
                "raw_get_query_returns_dbset": raw_get_query_returns_dbset,
                "owner_query_calls_calc_predicate": owner_query_calls_calc_predicate,
                "concrete_get_query_override_count": concrete_get_query_override_count,
                "authorization_calls_raw_get_query": authorization_calls_raw_get_query,
            }
        )

    artifact = {
        "artifact": "varanegar_ngt_owner_scope_repository_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS",
        "source": {
            "assemblies": [
                {key: row[key] for key in ("file", "sha256", "bytes")}
                for row in assemblies
            ],
            "runtime_scope_artifact": str(args.runtime_scope_artifact),
            "runtime_scope_artifact_sha256": hashlib.sha256(args.runtime_scope_artifact.read_bytes()).hexdigest(),
            "authorization_runtime_artifact": str(args.authorization_runtime_artifact),
            "authorization_runtime_artifact_sha256": hashlib.sha256(
                args.authorization_runtime_artifact.read_bytes()
            ).hexdigest(),
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_TARGETED_OWNER_SCOPE_REPOSITORY_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "configuration_files_read": 0,
            "string_literal_values_persisted": 0,
            "runtime_owner_or_identity_values_read_or_persisted": 0,
        },
        "summary": {
            "analyzed_assembly_count": len(assemblies),
            "target_type_count": sum(row["target_type_count"] for row in assemblies),
            "target_method_count": sum(row["target_method_count"] for row in assemblies),
            "target_method_body_error_count": 0,
            "base_repository_scope_method_count": len(base_scope_methods),
            "authorization_repositories_inherit_owner_aware_base_count": sum(
                row.get("generic_base", "") in owner_aware_bases
                for row in concrete_bases.values()
            ),
            "authorization_repositories_inherit_owner_aware_base": concrete_inherit_base,
            "repository_calc_extra_predict_uses_data_owner_and_center": calc_uses_data_owner_and_center,
            "base_get_query_returns_raw_dbset": raw_get_query_returns_dbset,
            "get_query_by_owner_applies_calc_extra_predict": owner_query_calls_calc_predicate,
            "authorization_repository_get_query_override_count": concrete_get_query_override_count,
            "authorization_permission_queries_call_raw_get_query": authorization_calls_raw_get_query,
            "authorization_permission_query_uses_owner_filtered_repository_path": False,
        },
        "contract": {
            "base_repository_type": base["type"],
            "base_repository_scope_methods": base_scope_methods,
            "authorization_repository_base_types": concrete_bases,
            "all_selected_authorization_repositories_inherit_base": concrete_inherit_base,
            "owner_aware_repository_bases": sorted(owner_aware_bases),
            "calc_extra_predict_scope_contract": calc_extra,
            "raw_get_query_contract": base_get_query,
            "owner_filtered_get_query_contract": anatoli_get_query_by_owner,
            "authorization_permission_query_methods": authorization_methods,
        },
        "assembly_scan": assemblies,
        "evidence_limits": [
            "Inheritance and static scope calls do not prove the exact SQL predicate emitted for every query.",
            "Only authorization repositories and the common repository base are selected; all domain repositories are not enumerated.",
            "No runtime request, query, identity, owner key, or business row is observed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
