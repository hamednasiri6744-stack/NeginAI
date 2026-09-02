"""Extract the deployed NGT role/base authorization short-circuit contract.

Only static metadata and IL are read.  The sole persisted user string is the
allowlisted code-level role literal ``admin`` from the generated predicate.
No assembly is loaded or executed and no runtime identity/role data is read.
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
from dncil.clr.token import StringToken, Token

from extract_varanegar_ngt_authorization_runtime_boundary import (
    _owner_maps,
    _resolve_token,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _method(pe: dnfile.dnPE, type_names: dict[int, str], owner: str, name: str) -> Any:
    matches = [
        method.row
        for type_index, row in enumerate(pe.net.mdtables.TypeDef.rows, start=1)
        if type_names[type_index] == owner
        for method in (row.MethodList or [])
        if _text(method.row.Name) == name
    ]
    if len(matches) != 1:
        raise AssertionError({"owner": owner, "method": name, "matches": len(matches)})
    return matches[0]


def _analyze_method(
    pe: dnfile.dnPE,
    owner: str,
    name: str,
    allowlisted_literal_values: set[str] | None = None,
) -> dict[str, Any]:
    method_owners, field_owners, type_names = _owner_maps(pe)
    method = _method(pe, type_names, owner, name)
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
    calls: list[str] = []
    literals: list[str] = []
    for instruction in body.instructions:
        operand = instruction.operand
        if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
            operand, Token
        ):
            calls.append(
                _resolve_token(
                    pe, operand, method_owners, field_owners, type_names
                )
            )
        elif (
            allowlisted_literal_values is not None
            and instruction.mnemonic == "ldstr"
            and isinstance(operand, StringToken)
        ):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else _text(item.value)
            if value not in allowlisted_literal_values:
                raise AssertionError("non-allowlisted literal in targeted predicate")
            literals.append(value)
    return {
        "owner": owner,
        "method": name,
        "instruction_count": len(body.instructions),
        "opcode_sequence": [instruction.mnemonic for instruction in body.instructions],
        "ordered_calls": calls,
        "allowlisted_literals": literals,
    }


def _contains_subsequence(values: list[str], subsequence: list[str]) -> bool:
    return any(
        values[index : index + len(subsequence)] == subsequence
        for index in range(len(values) - len(subsequence) + 1)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ngt-webapi", required=True, type=Path)
    parser.add_argument("--common-webapi", required=True, type=Path)
    parser.add_argument("--endpoint-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    endpoint = json.loads(args.endpoint_artifact.read_text(encoding="utf-8"))
    endpoint_hashes = {
        row["file"]: row["sha256"] for row in endpoint["source"]["assemblies"]
    }
    source_paths = [args.ngt_webapi, args.common_webapi]
    for path in source_paths:
        if endpoint_hashes.get(path.name) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise AssertionError(f"endpoint hash mismatch: {path.name}")

    ngt_pe = dnfile.dnPE(str(args.ngt_webapi))
    common_pe = dnfile.dnPE(str(args.common_webapi))
    derived = "NGT.WebApi.Classes.AnatoliAuthorizeAttribute"
    derived_predicate = derived + "+<>c"
    base = "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute"
    base_predicate = base + "+<>c"
    derived_is_authorized = _analyze_method(ngt_pe, derived, "IsAuthorized")
    admin_predicate = _analyze_method(
        ngt_pe,
        derived_predicate,
        "<IsAuthorized>b__0_0",
        allowlisted_literal_values={"admin"},
    )
    base_is_authorized = _analyze_method(common_pe, base, "IsAuthorized")
    bypass_predicate = _analyze_method(
        common_pe, base_predicate, "<IsAuthorized>b__28_0"
    )

    if admin_predicate["allowlisted_literals"] != ["admin"]:
        raise AssertionError("unexpected role literal")
    derived_calls = derived_is_authorized["ordered_calls"]
    any_index = derived_calls.index("System.Linq.Enumerable.Any")
    base_call_index = derived_calls.index(
        "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute.IsAuthorized"
    )
    admin_true_branch_shape = _contains_subsequence(
        derived_is_authorized["opcode_sequence"],
        ["ldloc.3", "brfalse.s", "ldc.i4.1", "stloc.s", "br.s"],
    )
    predicate_exact = (
        admin_predicate["opcode_sequence"]
        == ["ldarg.1", "callvirt", "ldstr", "callvirt", "ret"]
        and admin_predicate["ordered_calls"]
        == ["System.String.ToLower", "System.String.Equals"]
    )
    base_calls = base_is_authorized["ordered_calls"]
    base_web_index = base_calls.index(
        "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute.HasWebApiAccess"
    )
    base_standard_index = base_calls.index(
        "System.Web.Http.AuthorizeAttribute.IsAuthorized"
    )
    bypass_predicate_exact = (
        bypass_predicate["opcode_sequence"] == ["ldarg.1", "callvirt", "ret"]
        and bypass_predicate["ordered_calls"]
        == [
            "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute.get_ByPassAuthorization"
        ]
    )

    contract = {
        "admin_role_literal": "admin",
        "derived_role_lookup_call_count": sum(
            target.endswith("UserManagerExtensions.GetRoles")
            for target in derived_calls
        ),
        "admin_predicate_is_case_insensitive_exact_equality": predicate_exact,
        "admin_true_branch_precedes_base_authorization": (
            any_index < base_call_index and admin_true_branch_shape
        ),
        "non_admin_path_calls_base_authorization": base_call_index > any_index,
        "base_checks_current_or_peer_attribute_bypass": (
            base_calls[0].endswith("get_ByPassAuthorization")
            and "Anatoli.Common.WebApi.BaseAnatoliAuthorizeAttribute.GetApiAuthorizeAttributes"
            in base_calls
            and bypass_predicate_exact
        ),
        "base_web_permission_check_precedes_standard_authorize": (
            base_web_index < base_standard_index
        ),
        "base_handles_web_permission_failure_as_unauthorized": (
            "System.Web.Http.AuthorizeAttribute.HandleUnauthorizedRequest"
            in base_calls
        ),
        "endpoint_explicit_bypass_declaration_count": endpoint["summary"][
            "endpoint_with_bypass_authorization_count"
        ],
        "roles_or_empty_only_endpoint_count": endpoint["summary"][
            "endpoint_shape_counts"
        ]["roles_or_empty_only"],
        "roles_only_endpoint_with_roles_contract_count": endpoint["summary"][
            "ngt_roles_only_endpoint_with_roles_contract_count"
        ],
    }
    required_true = [
        "admin_predicate_is_case_insensitive_exact_equality",
        "admin_true_branch_precedes_base_authorization",
        "non_admin_path_calls_base_authorization",
        "base_checks_current_or_peer_attribute_bypass",
        "base_web_permission_check_precedes_standard_authorize",
        "base_handles_web_permission_failure_as_unauthorized",
    ]
    if not all(contract[key] for key in required_true):
        raise AssertionError({key: contract[key] for key in required_true})

    artifact = {
        "artifact": "varanegar_ngt_authorization_role_short_circuit",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "assemblies": [
                {
                    "file": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
                for path in source_paths
            ],
            "endpoint_artifact": str(args.endpoint_artifact),
            "endpoint_artifact_sha256": hashlib.sha256(
                args.endpoint_artifact.read_bytes()
            ).hexdigest(),
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_TARGETED_AUTHORIZATION_IL",
            "assemblies_loaded_or_executed": 0,
            "config_files_read": 0,
            "allowlisted_code_role_literals_read_or_persisted": 1,
            "arbitrary_user_strings_read_or_persisted": 0,
            "runtime_role_or_identity_values_read_or_persisted": 0,
            "credentials_read_or_persisted": 0,
            "database_connections": 0,
        },
        "summary": {
            "target_method_count": 4,
            "target_method_body_error_count": 0,
            "admin_role_short_circuits_base_authorization": contract[
                "admin_true_branch_precedes_base_authorization"
            ],
            "non_admin_delegates_to_base_authorization": contract[
                "non_admin_path_calls_base_authorization"
            ],
            "base_web_permission_precedes_standard_authentication_and_roles": contract[
                "base_web_permission_check_precedes_standard_authorize"
            ],
            "explicit_endpoint_bypass_declaration_count": contract[
                "endpoint_explicit_bypass_declaration_count"
            ],
        },
        "contract": contract,
        "method_evidence": [
            derived_is_authorized,
            admin_predicate,
            base_is_authorized,
            bypass_predicate,
        ],
        "evidence_limits": [
            "Static IL proves code shape, not the current membership of any runtime identity.",
            "No claim is made that an admin-role assignment is appropriate or currently exploited.",
            "System.Web.Http.AuthorizeAttribute behavior is called by the base path but its external framework implementation is not re-derived here.",
            "Endpoint counts cover only HTTP/Route-attributed methods from the endpoint artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
