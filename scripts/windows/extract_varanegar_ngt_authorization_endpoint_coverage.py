"""Extract declared NGT Web API authorization coverage from .NET metadata only.

The deployed assembly is never loaded or executed.  Only type/method names,
HTTP/custom-attribute metadata, and the Resource/Action named arguments of the
NGT authorization attribute are persisted.  Role values and arbitrary custom
attribute strings are intentionally not persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token


NGT_AUTHORIZE = "NGT.WebApi.Classes.AnatoliAuthorizeAttribute"
STANDARD_AUTHORIZE = "System.Web.Http.AuthorizeAttribute"
CLAIMS_AUTHORIZE = "NGT.WebApi.Infrastructure.ClaimsAuthorizationAttribute"
ALLOW_ANONYMOUS = "System.Web.Http.AllowAnonymousAttribute"
ROUTE = "System.Web.Http.RouteAttribute"
HTTP_ATTRIBUTES = {
    "System.Web.Http.HttpGetAttribute": "GET",
    "System.Web.Http.HttpPostAttribute": "POST",
    "System.Web.Http.HttpPutAttribute": "PUT",
    "System.Web.Http.HttpDeleteAttribute": "DELETE",
    "System.Web.Http.HttpPatchAttribute": "PATCH",
    "System.Web.Http.HttpHeadAttribute": "HEAD",
    "System.Web.Http.HttpOptionsAttribute": "OPTIONS",
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _signature_hex(row: Any) -> str:
    value = getattr(getattr(row, "Signature", None), "value", b"")
    return bytes(value).hex() if value else ""


def _full_type_name(row: Any) -> str:
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    return f"{namespace}.{name}" if namespace else name


def _owner_maps(pe: dnfile.dnPE) -> tuple[dict[int, str], dict[int, int]]:
    method_owner_names: dict[int, str] = {}
    method_owner_indices: dict[int, int] = {}
    for type_index, row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = _full_type_name(row)
        for method in row.MethodList or []:
            method_owner_names[method.row_index] = owner
            method_owner_indices[method.row_index] = type_index
    return method_owner_names, method_owner_indices


def _attribute_owner(
    row: Any, method_owner_names: dict[int, str]
) -> str:
    constructor = getattr(row.Type, "row", None)
    if constructor is None:
        return "<unknown>"
    if type(constructor).__name__ == "MethodDefRow":
        return method_owner_names.get(row.Type.row_index, "<unknown>")
    parent = getattr(getattr(constructor, "Class", None), "row", None)
    return _full_type_name(parent) if parent is not None else "<unknown>"


def _compressed_uint(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError("unexpected_end_of_blob")
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
    raise ValueError("invalid_compressed_integer")


def _ser_string(data: bytes, offset: int) -> tuple[str | None, int]:
    if offset >= len(data):
        raise ValueError("unexpected_end_of_string")
    if data[offset] == 0xFF:
        return None, offset + 1
    length, offset = _compressed_uint(data, offset)
    end = offset + length
    if end > len(data):
        raise ValueError("truncated_string")
    return data[offset:end].decode("utf-8"), end


def _named_arguments(blob: bytes) -> dict[str, Any]:
    if len(blob) < 4 or blob[:2] != b"\x01\x00":
        raise ValueError("invalid_custom_attribute_prolog")
    offset = 2
    count = int.from_bytes(blob[offset : offset + 2], "little")
    offset += 2
    result: dict[str, Any] = {}
    for _ in range(count):
        if offset + 2 > len(blob):
            raise ValueError("truncated_named_argument")
        kind = blob[offset]
        element_type = blob[offset + 1]
        offset += 2
        if kind not in {0x53, 0x54}:  # field/property
            raise ValueError("unsupported_named_argument_kind")
        name, offset = _ser_string(blob, offset)
        if name is None:
            raise ValueError("null_named_argument_name")
        if element_type == 0x0E:  # string
            value, offset = _ser_string(blob, offset)
        elif element_type == 0x02:  # bool
            if offset >= len(blob):
                raise ValueError("truncated_boolean")
            value = bool(blob[offset])
            offset += 1
        else:
            raise ValueError(f"unsupported_named_argument_type_{element_type:#x}")
        result[name] = value
    if offset != len(blob):
        raise ValueError("custom_attribute_blob_has_unparsed_bytes")
    return result


def _attributes_by_parent(
    pe: dnfile.dnPE, method_owner_names: dict[int, str]
) -> tuple[dict[tuple[str, int], list[dict[str, Any]]], list[dict[str, Any]]]:
    indexed: dict[tuple[str, int], list[dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(pe.net.mdtables.CustomAttribute.rows, start=1):
        parent = getattr(row.Parent, "row", None)
        if parent is None:
            continue
        parent_table = type(parent).__name__
        if parent_table not in {"TypeDefRow", "MethodDefRow"}:
            continue
        owner = _attribute_owner(row, method_owner_names)
        entry: dict[str, Any] = {"attribute": owner}
        if owner == NGT_AUTHORIZE:
            try:
                args = _named_arguments(bytes(row.Value.value))
                entry["ngt_authorization"] = {
                    "roles_present": bool(args.get("Roles")),
                    "resource": args.get("Resource") or "",
                    "action": args.get("Action") or "",
                    "bypass_authorization": bool(args.get("ByPassAuthorization", False)),
                    "owner_key_present": bool(args.get("OwnerKey")),
                    "named_argument_count": len(args),
                }
            except Exception as exc:
                failures.append(
                    {
                        "custom_attribute_row": index,
                        "error_class": type(exc).__name__,
                    }
                )
                continue
        indexed.setdefault((parent_table, row.Parent.row_index), []).append(entry)
    return indexed, failures


def _base_type_indices(pe: dnfile.dnPE, type_index: int) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    current = type_index
    while current not in seen:
        seen.add(current)
        row = pe.net.mdtables.TypeDef.rows[current - 1]
        base = getattr(row.Extends, "row", None)
        if base is None or type(base).__name__ != "TypeDefRow":
            break
        current = row.Extends.row_index
        result.append(current)
    return result


def _direct_base_type_name(pe: dnfile.dnPE, type_index: int) -> str:
    row = pe.net.mdtables.TypeDef.rows[type_index - 1]
    base = getattr(row.Extends, "row", None)
    if base is None:
        return ""
    if type(base).__name__ in {"TypeDefRow", "TypeRefRow"}:
        return _full_type_name(base)
    return type(base).__name__


def _external_type_attributes(
    pe: dnfile.dnPE,
    indexed: dict[tuple[str, int], list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    by_name = {
        _full_type_name(row): index
        for index, row in enumerate(pe.net.mdtables.TypeDef.rows, start=1)
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for type_name, type_index in by_name.items():
        chain = [type_index, *_base_type_indices(pe, type_index)]
        result[type_name] = [
            entry
            for index in chain
            for entry in indexed.get(("TypeDefRow", index), [])
        ]
    return result


def _resolve_method_target(
    pe: dnfile.dnPE, token: Token, method_owner_names: dict[int, str]
) -> str:
    table = pe.net.mdtables.tables.get(token.table)
    if table is None or token.rid <= 0 or token.rid > len(table.rows):
        return f"unresolved:{token.value:#010x}"
    row = table.rows[token.rid - 1]
    table_name = getattr(table, "name", "")
    if table_name == "MethodDef":
        return f"{method_owner_names.get(token.rid, '<unknown>')}.{_text(row.Name)}"
    if table_name == "MemberRef":
        parent = getattr(getattr(row, "Class", None), "row", None)
        owner = _full_type_name(parent) if parent is not None else "<unknown>"
        return f"{owner}.{_text(row.Name)}"
    return f"{table_name}:{_text(getattr(row, 'Name', ''))}"


def _startup_filter_contract(
    pe: dnfile.dnPE, method_owner_names: dict[int, str]
) -> dict[str, Any]:
    target = None
    for row in pe.net.mdtables.TypeDef.rows:
        if _full_type_name(row) != "NGT.WebApi.Startup":
            continue
        for method in row.MethodList or []:
            if _text(method.row.Name) == "ConfigureWebApi":
                target = method.row
                break
    if target is None or not target.Rva:
        raise AssertionError("Startup.ConfigureWebApi not found")
    body = read_method_body_from_bytes(pe.get_data(target.Rva, 65536))
    calls: list[str] = []
    constructors: list[str] = []
    for instruction in body.instructions:
        if instruction.mnemonic not in {"call", "callvirt", "newobj"}:
            continue
        if not isinstance(instruction.operand, Token):
            continue
        resolved = _resolve_method_target(
            pe, instruction.operand, method_owner_names
        )
        calls.append(resolved)
        if instruction.mnemonic == "newobj":
            constructors.append(resolved)
    return {
        "method": "NGT.WebApi.Startup.ConfigureWebApi",
        "instruction_count": len(body.instructions),
        "map_http_attribute_routes_call_present": any(
            target.endswith("MapHttpAttributeRoutes") for target in calls
        ),
        "global_filter_add_call_count": sum(
            target.endswith("HttpFilterCollection.Add") for target in calls
        ),
        "constructed_filter_like_types": sorted(
            {
                target.rsplit("..ctor", 1)[0]
                for target in constructors
                if target.endswith(("Attribute..ctor", "Filter..ctor"))
            }
        ),
        "authorization_named_constructor_count": sum(
            "authoriz" in target.casefold() for target in constructors
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--base-assembly", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    pe = dnfile.dnPE(str(args.assembly))
    if not getattr(pe, "net", None):
        raise ValueError("not_dotnet")
    method_owner_names, method_owner_indices = _owner_maps(pe)
    indexed, failures = _attributes_by_parent(pe, method_owner_names)
    base_pe = dnfile.dnPE(str(args.base_assembly))
    base_method_owner_names, _ = _owner_maps(base_pe)
    base_indexed, base_failures = _attributes_by_parent(
        base_pe, base_method_owner_names
    )
    failures.extend(base_failures)
    external_attributes = _external_type_attributes(base_pe, base_indexed)
    startup_contract = _startup_filter_contract(pe, method_owner_names)
    type_names = {
        index: _full_type_name(row)
        for index, row in enumerate(pe.net.mdtables.TypeDef.rows, start=1)
    }

    endpoints: list[dict[str, Any]] = []
    for method_index, method in enumerate(pe.net.mdtables.MethodDef.rows, start=1):
        direct = indexed.get(("MethodDefRow", method_index), [])
        attribute_names = {row["attribute"] for row in direct}
        verbs = sorted(
            {HTTP_ATTRIBUTES[name] for name in attribute_names if name in HTTP_ATTRIBUTES}
        )
        has_route = ROUTE in attribute_names
        if not verbs and not has_route:
            continue
        type_index = method_owner_indices[method_index]
        type_chain = [type_index, *_base_type_indices(pe, type_index)]
        type_attributes = [
            row
            for index in type_chain
            for row in indexed.get(("TypeDefRow", index), [])
        ]
        type_attributes.extend(
            external_attributes.get(_direct_base_type_name(pe, type_index), [])
        )
        all_attributes = [*type_attributes, *direct]
        ngt = [
            row["ngt_authorization"]
            for row in all_attributes
            if row["attribute"] == NGT_AUTHORIZE
        ]
        standard_authorize = any(
            row["attribute"] == STANDARD_AUTHORIZE for row in all_attributes
        )
        claims_authorize = any(
            row["attribute"] == CLAIMS_AUTHORIZE for row in all_attributes
        )
        allow_anonymous = any(
            row["attribute"] == ALLOW_ANONYMOUS for row in all_attributes
        )
        resource_action_shapes = [
            (
                "resource_and_action"
                if item["resource"] and item["action"]
                else "resource_only"
                if item["resource"]
                else "action_only"
                if item["action"]
                else "roles_or_empty_only"
            )
            for item in ngt
        ]
        endpoints.append(
            {
                "controller": type_names[type_index],
                "direct_base_type": _direct_base_type_name(pe, type_index),
                "method": _text(method.Name),
                "method_metadata_token": f"{0x06000000 | method_index:#010x}",
                "signature_hex": _signature_hex(method),
                "http_verbs": verbs,
                "has_route_attribute": has_route,
                "allow_anonymous_declared_or_inherited": allow_anonymous,
                "standard_authorize_declared_or_inherited": standard_authorize,
                "claims_authorize_declared_or_inherited": claims_authorize,
                "ngt_authorize_attribute_count": len(ngt),
                "ngt_authorization_shapes": resource_action_shapes,
                "resource_action_contracts": [
                    {"resource": item["resource"], "action": action.strip()}
                    for item in ngt
                    if item["resource"] and item["action"]
                    for action in item["action"].split(",")
                    if action.strip()
                ],
                "roles_contract_present": any(item["roles_present"] for item in ngt),
                "bypass_authorization_declared": any(
                    item["bypass_authorization"] for item in ngt
                ),
            }
        )

    shape_counts: dict[str, int] = {}
    for endpoint in endpoints:
        shapes = endpoint["ngt_authorization_shapes"] or ["no_ngt_attribute"]
        for shape in set(shapes):
            shape_counts[shape] = shape_counts.get(shape, 0) + 1
    unclassified = [
        row
        for row in endpoints
        if row["ngt_authorize_attribute_count"] == 0
        and not row["standard_authorize_declared_or_inherited"]
        and not row["claims_authorize_declared_or_inherited"]
        and not row["allow_anonymous_declared_or_inherited"]
    ]
    mutating_verbs = {"POST", "PUT", "PATCH", "DELETE"}
    artifact = {
        "artifact": "varanegar_ngt_authorization_endpoint_coverage",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "assemblies": [
                {
                    "file": args.assembly.name,
                    "sha256": hashlib.sha256(args.assembly.read_bytes()).hexdigest(),
                    "bytes": args.assembly.stat().st_size,
                },
                {
                    "file": args.base_assembly.name,
                    "sha256": hashlib.sha256(
                        args.base_assembly.read_bytes()
                    ).hexdigest(),
                    "bytes": args.base_assembly.stat().st_size,
                },
            ]
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_CUSTOM_ATTRIBUTE_METADATA",
            "assemblies_loaded_or_executed": 0,
            "config_files_read": 0,
            "route_templates_persisted": 0,
            "role_values_persisted": 0,
            "arbitrary_custom_attribute_strings_persisted": 0,
            "credentials_read_or_persisted": 0,
            "database_connections": 0,
            "startup_method_bodies_read": 1,
        },
        "summary": {
            "custom_attribute_row_count": len(pe.net.mdtables.CustomAttribute.rows),
            "ngt_authorize_attribute_declaration_count": sum(
                row["attribute"] == NGT_AUTHORIZE
                for rows in indexed.values()
                for row in rows
            ),
            "attribute_declared_endpoint_count": len(endpoints),
            "endpoint_with_ngt_authorize_count": sum(
                row["ngt_authorize_attribute_count"] > 0 for row in endpoints
            ),
            "endpoint_with_standard_authorize_count": sum(
                row["standard_authorize_declared_or_inherited"] for row in endpoints
            ),
            "endpoint_with_claims_authorize_count": sum(
                row["claims_authorize_declared_or_inherited"] for row in endpoints
            ),
            "endpoint_with_allow_anonymous_count": sum(
                row["allow_anonymous_declared_or_inherited"] for row in endpoints
            ),
            "endpoint_with_bypass_authorization_count": sum(
                row["bypass_authorization_declared"] for row in endpoints
            ),
            "endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count": len(
                unclassified
            ),
            "mutating_endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count": sum(
                bool(set(row["http_verbs"]) & mutating_verbs)
                for row in unclassified
            ),
            "ngt_roles_only_endpoint_with_roles_contract_count": sum(
                "roles_or_empty_only" in row["ngt_authorization_shapes"]
                and row["roles_contract_present"]
                for row in endpoints
            ),
            "endpoint_shape_counts": dict(sorted(shape_counts.items())),
            "custom_attribute_parse_failure_count": len(failures),
            "conventional_endpoint_without_http_or_route_attribute_count": None,
        },
        "startup_global_filter_contract": startup_contract,
        "parse_failures": failures,
        "endpoints": sorted(
            endpoints, key=lambda row: (row["controller"], row["method"])
        ),
        "evidence_limits": [
            "Coverage is limited to methods declaring an HTTP verb or Route attribute.",
            "Convention-only public controller actions are not counted.",
            "Type-level NGT/Authorize/AllowAnonymous attributes are followed through local bases and the directly referenced Anatoli.Common.WebApi base type.",
            "No authorization-named constructor in Startup.ConfigureWebApi does not exclude authorization in external hosting configuration or middleware.",
            "Absence of a declaration does not exclude manual authorization checks inside synchronous or async method bodies.",
            "Attribute presence does not prove that a route is registered or reachable at runtime.",
            "Roles are recorded only as present/absent; role values are not persisted.",
            "Resource/Action strings are code-level permission contract names, not user or business data.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
