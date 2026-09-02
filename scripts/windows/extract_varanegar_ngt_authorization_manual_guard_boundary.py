"""Classify manual authorization signals on NGT endpoint declaration gaps.

Reads only static .NET metadata and IL.  For async endpoints it follows the
AsyncStateMachineAttribute to the generated MoveNext body.  Signal names are
evidence candidates only; they do not prove a deny branch or route reachability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token

from extract_varanegar_ngt_authorization_runtime_boundary import (
    _owner_maps,
    _resolve_token,
)


ASYNC_ATTRIBUTE = "System.Runtime.CompilerServices.AsyncStateMachineAttribute"
AUTHORIZATION_DECISION_SIGNAL = re.compile(
    r"(?:HasWebApiAccess|[.]IsAuthorized|Check.*Access|Has.*Permission|"
    r"GetRoles|IsAuthenticated|AuthorizeCore|HandleUnauthorizedRequest|"
    r"Unauthorized|Forbidden|AccessDenied|GetUsersRights|CheckUserRights)",
    re.IGNORECASE,
)
AUTHORIZATION_DATA_SIGNAL = re.compile(
    r"(?:AuthorizationDomain|PermissionDomain|PermissionRepository|"
    r"Models[.]Identity[.]Permission|AuthorizationModels)",
    re.IGNORECASE,
)
IDENTITY_CONTEXT_SIGNAL = re.compile(
    r"(?:CurrentUserId|UserManager|ClaimsIdentity|ClaimsPrincipal|GetUserId)",
    re.IGNORECASE,
)
DENY_SIGNAL = re.compile(r"(?:Unauthorized|Forbidden|Deny|AccessDenied)", re.IGNORECASE)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _full_type_name(row: Any) -> str:
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    return f"{namespace}.{name}" if namespace else name


def _attribute_owner(row: Any, method_owners: dict[int, str]) -> str:
    constructor = getattr(row.Type, "row", None)
    if constructor is None:
        return "<unknown>"
    if type(constructor).__name__ == "MethodDefRow":
        return method_owners.get(row.Type.row_index, "<unknown>")
    parent = getattr(getattr(constructor, "Class", None), "row", None)
    return _full_type_name(parent) if parent is not None else "<unknown>"


def _compressed_uint(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | data[offset + 1], offset + 2
    return (
        ((first & 0x1F) << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3],
        offset + 4,
    )


def _ser_string(data: bytes, offset: int) -> tuple[str | None, int]:
    if data[offset] == 0xFF:
        return None, offset + 1
    length, offset = _compressed_uint(data, offset)
    end = offset + length
    return data[offset:end].decode("utf-8"), end


def _async_state_types(
    pe: dnfile.dnPE, method_owners: dict[int, str]
) -> dict[int, str]:
    result: dict[int, str] = {}
    for row in pe.net.mdtables.CustomAttribute.rows:
        parent = getattr(row.Parent, "row", None)
        if type(parent).__name__ != "MethodDefRow":
            continue
        if _attribute_owner(row, method_owners) != ASYNC_ATTRIBUTE:
            continue
        blob = bytes(row.Value.value)
        if len(blob) < 5 or blob[:2] != b"\x01\x00":
            continue
        state_type, offset = _ser_string(blob, 2)
        if state_type and blob[offset:] == b"\x00\x00":
            result[row.Parent.row_index] = state_type
    return result


def _body_contract(
    pe: dnfile.dnPE,
    method: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
    type_names: dict[int, str],
    body_kind: str,
) -> dict[str, Any]:
    if not method.Rva:
        return {"body_kind": body_kind, "has_body": False}
    try:
        body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
    except Exception as exc:
        return {
            "body_kind": body_kind,
            "has_body": True,
            "body_error_class": type(exc).__name__,
        }
    targets: set[str] = set()
    branch_count = 0
    throw_count = 0
    for instruction in body.instructions:
        if instruction.mnemonic.startswith(
            ("br", "beq", "bne", "ble", "blt", "bge", "bgt")
        ):
            branch_count += 1
        if instruction.mnemonic == "throw":
            throw_count += 1
        if isinstance(instruction.operand, Token) and (
            instruction.mnemonic in {"call", "callvirt", "newobj", "ldtoken"}
            or "fld" in instruction.mnemonic
        ):
            targets.add(
                _resolve_token(
                    pe,
                    instruction.operand,
                    method_owners,
                    field_owners,
                    type_names,
                )
            )
    return {
        "body_kind": body_kind,
        "has_body": True,
        "instruction_count": len(body.instructions),
        "branch_count": branch_count,
        "throw_count": throw_count,
        "authorization_decision_signal_targets": sorted(
            target
            for target in targets
            if AUTHORIZATION_DECISION_SIGNAL.search(target)
        ),
        "authorization_data_signal_targets": sorted(
            target for target in targets if AUTHORIZATION_DATA_SIGNAL.search(target)
        ),
        "identity_context_signal_targets": sorted(
            target for target in targets if IDENTITY_CONTEXT_SIGNAL.search(target)
        ),
        "deny_signal_targets": sorted(
            target for target in targets if DENY_SIGNAL.search(target)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--endpoint-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    endpoint_payload = json.loads(args.endpoint_artifact.read_text(encoding="utf-8"))
    endpoint_hashes = {
        row["file"]: row["sha256"]
        for row in endpoint_payload["source"]["assemblies"]
    }
    assembly_hash = hashlib.sha256(args.assembly.read_bytes()).hexdigest()
    if endpoint_hashes.get(args.assembly.name) != assembly_hash:
        raise AssertionError("endpoint artifact assembly hash mismatch")

    pe = dnfile.dnPE(str(args.assembly))
    method_owners, field_owners, type_names = _owner_maps(pe)
    async_types = _async_state_types(pe, method_owners)
    type_index_by_name = {name: index for index, name in type_names.items()}
    selected = [
        row
        for row in endpoint_payload["endpoints"]
        if row["ngt_authorize_attribute_count"] == 0
        and not row["standard_authorize_declared_or_inherited"]
        and not row["claims_authorize_declared_or_inherited"]
        and not row["allow_anonymous_declared_or_inherited"]
    ]

    rows: list[dict[str, Any]] = []
    body_error_count = 0
    for endpoint in selected:
        method_index = int(endpoint["method_metadata_token"], 16) & 0x00FFFFFF
        method = pe.net.mdtables.MethodDef.rows[method_index - 1]
        bodies = [
            _body_contract(
                pe,
                method,
                method_owners,
                field_owners,
                type_names,
                "endpoint_method",
            )
        ]
        state_type = async_types.get(method_index)
        if state_type:
            type_index = type_index_by_name.get(state_type)
            if type_index is None:
                bodies.append(
                    {
                        "body_kind": "async_move_next",
                        "has_body": False,
                        "body_error_class": "AsyncStateTypeNotResolved",
                    }
                )
            else:
                move_next = [
                    item.row
                    for item in pe.net.mdtables.TypeDef.rows[type_index - 1].MethodList
                    if _text(item.row.Name) == "MoveNext"
                ]
                if len(move_next) != 1:
                    bodies.append(
                        {
                            "body_kind": "async_move_next",
                            "has_body": False,
                            "body_error_class": "AsyncMoveNextNotUnique",
                        }
                    )
                else:
                    bodies.append(
                        _body_contract(
                            pe,
                            move_next[0],
                            method_owners,
                            field_owners,
                            type_names,
                            "async_move_next",
                        )
                    )
        body_error_count += sum("body_error_class" in body for body in bodies)
        decision = sorted(
            {
                target
                for body in bodies
                for target in body.get("authorization_decision_signal_targets", [])
            }
        )
        authorization_data = sorted(
            {
                target
                for body in bodies
                for target in body.get("authorization_data_signal_targets", [])
            }
        )
        identity = sorted(
            {
                target
                for body in bodies
                for target in body.get("identity_context_signal_targets", [])
            }
        )
        deny = sorted(
            {
                target
                for body in bodies
                for target in body.get("deny_signal_targets", [])
            }
        )
        rows.append(
            {
                "controller": endpoint["controller"],
                "method": endpoint["method"],
                "method_metadata_token": endpoint["method_metadata_token"],
                "http_verbs": endpoint["http_verbs"],
                "async_state_machine_followed": bool(state_type),
                "bodies": bodies,
                "authorization_decision_signal_targets": decision,
                "authorization_data_signal_targets": authorization_data,
                "identity_context_signal_targets": identity,
                "deny_signal_targets": deny,
                "manual_authorization_decision_candidate": bool(decision or deny),
                "authorization_data_only_candidate": bool(authorization_data)
                and not bool(decision or deny),
                "identity_context_only_candidate": bool(identity)
                and not bool(decision or deny or authorization_data),
            }
        )

    mutating = {"POST", "PUT", "PATCH", "DELETE"}
    artifact = {
        "artifact": "varanegar_ngt_authorization_manual_guard_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "assembly": args.assembly.name,
            "sha256": assembly_hash,
            "endpoint_artifact": str(args.endpoint_artifact),
            "endpoint_artifact_sha256": hashlib.sha256(
                args.endpoint_artifact.read_bytes()
            ).hexdigest(),
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_ENDPOINT_AND_ASYNC_IL",
            "assemblies_loaded_or_executed": 0,
            "config_files_read": 0,
            "user_strings_read_or_persisted": 0,
            "route_templates_read_or_persisted": 0,
            "role_or_identity_values_read_or_persisted": 0,
            "credentials_read_or_persisted": 0,
            "database_connections": 0,
        },
        "summary": {
            "selected_declaration_gap_endpoint_count": len(rows),
            "async_state_machine_followed_count": sum(
                row["async_state_machine_followed"] for row in rows
            ),
            "body_error_count": body_error_count,
            "endpoint_with_manual_authorization_decision_candidate_count": sum(
                row["manual_authorization_decision_candidate"] for row in rows
            ),
            "endpoint_with_authorization_data_only_candidate_count": sum(
                row["authorization_data_only_candidate"] for row in rows
            ),
            "endpoint_with_identity_context_only_candidate_count": sum(
                row["identity_context_only_candidate"] for row in rows
            ),
            "endpoint_without_named_authorization_decision_data_or_identity_signal_count": sum(
                not row["manual_authorization_decision_candidate"]
                and not row["authorization_data_only_candidate"]
                and not row["identity_context_only_candidate"]
                for row in rows
            ),
            "endpoint_without_named_manual_authorization_decision_signal_count": sum(
                not row["manual_authorization_decision_candidate"] for row in rows
            ),
            "mutating_endpoint_without_named_manual_authorization_decision_signal_count": sum(
                bool(set(row["http_verbs"]) & mutating)
                and not row["manual_authorization_decision_candidate"]
                for row in rows
            ),
        },
        "endpoints": sorted(rows, key=lambda row: (row["controller"], row["method"])),
        "evidence_limits": [
            "A named authorization-decision or deny signal does not prove that every branch denies before side effects.",
            "Authorization/permission data access is classified separately and is not treated as an enforcement decision.",
            "Identity-context use can be actor attribution or data filtering rather than authorization.",
            "Absence of a named signal does not exclude obfuscated logic, external calls, host policy, or middleware.",
            "No endpoint was invoked and no authenticated or anonymous runtime request was sent.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if body_error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
