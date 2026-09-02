"""Join deployed NGT authorization IL with privacy-safe clone aggregates.

This extractor is read-only.  It consumes the separately generated static-IL
artifact, validates its hash and safety contract, and queries only aggregate
authorization counts from the local read-only clone.  It never persists names,
identifiers, credentials, membership rows, or per-principal permissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runtime_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    safety = payload.get("safety", {})
    summary = payload.get("summary", {})
    if safety.get("assemblies_loaded_or_executed") != 0:
        raise AssertionError("runtime artifact did not preserve static-only safety")
    if summary.get("failed_file_count") != 0:
        raise AssertionError("runtime artifact has unanalyzed assemblies")
    expected = {
        "runtime_guard_uses_direct_and_group_atomic_queries": True,
        "runtime_guard_direct_query_grant_value": 1,
        "runtime_guard_action_contract_is_comma_split_exact_membership": True,
        "runtime_guard_group_query_delegates_to_grant_filtered_direct_query": True,
        "runtime_guard_post_union_veto_grant_value": -1,
        "runtime_guard_catalog_named_call_count": 0,
        "catalog_save_materializes_atomic_permission_rows": True,
    }
    observed = {key: summary.get(key) for key in expected}
    if observed != expected:
        raise AssertionError({"runtime_contract_mismatch": observed})
    return payload


def _load_endpoint_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    safety = payload.get("safety", {})
    summary = payload.get("summary", {})
    if safety.get("assemblies_loaded_or_executed") != 0:
        raise AssertionError("endpoint artifact did not preserve static-only safety")
    if summary.get("custom_attribute_parse_failure_count") != 0:
        raise AssertionError("endpoint artifact has unparsed authorization attributes")
    if summary.get("endpoint_with_bypass_authorization_count") != 0:
        raise AssertionError("unexpected explicit authorization bypass declaration")
    return payload


def _load_manual_guard_contract(
    path: Path, endpoint_artifact: Path
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    safety = payload.get("safety", {})
    summary = payload.get("summary", {})
    if safety.get("assemblies_loaded_or_executed") != 0:
        raise AssertionError("manual-guard artifact did not preserve static safety")
    if summary.get("body_error_count") != 0:
        raise AssertionError("manual-guard artifact has unread method bodies")
    if payload.get("source", {}).get("endpoint_artifact_sha256") != _sha256(
        endpoint_artifact
    ):
        raise AssertionError("manual-guard endpoint artifact hash mismatch")
    return payload


def _load_role_short_circuit_contract(
    path: Path, endpoint_artifact: Path
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    safety = payload.get("safety", {})
    summary = payload.get("summary", {})
    if safety.get("assemblies_loaded_or_executed") != 0:
        raise AssertionError("role-short-circuit artifact violated static safety")
    if summary.get("target_method_body_error_count") != 0:
        raise AssertionError("role-short-circuit artifact has body errors")
    if not summary.get("admin_role_short_circuits_base_authorization"):
        raise AssertionError("admin short-circuit contract not proven")
    if payload.get("source", {}).get("endpoint_artifact_sha256") != _sha256(
        endpoint_artifact
    ):
        raise AssertionError("role-short-circuit endpoint hash mismatch")
    return payload


def _grant_distribution(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH classified AS (
          SELECT pp.PrincipalId,pp.Permission_Id,
          CASE
            WHEN EXISTS (
              SELECT 1 FROM NGT.UserGroups g
              WHERE g.PrincipalId=pp.PrincipalId
            ) THEN 'group'
            WHEN EXISTS (
              SELECT 1 FROM NGT.Users u
              WHERE u.Id=pp.PrincipalId OR u.PrincipalId=pp.PrincipalId
            ) THEN 'user'
            ELSE 'other_principal'
          END principal_kind,
          CONVERT(int,pp.[Grant]) grant_value
          FROM NGT.PrincipalPermissions pp
        )
        SELECT principal_kind,grant_value,
          COUNT_BIG(*) permission_rows,
          COUNT(DISTINCT PrincipalId) principals,
          COUNT(DISTINCT Permission_Id) permissions
        FROM classified
        GROUP BY principal_kind,grant_value
        ORDER BY principal_kind,grant_value
        """,
    )


def _group_membership_reachability(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH classified AS (
          SELECT pp.PrincipalId,pp.Permission_Id,
                 CONVERT(int,pp.[Grant]) grant_value,
                 CASE WHEN EXISTS (
                      SELECT 1
                      FROM NGT.UserGroups g
                      JOIN NGT.UserGroupUsers m ON m.UserGroupId=g.Id
                      JOIN NGT.Users u ON u.Id=m.UserId
                      WHERE g.PrincipalId=pp.PrincipalId
                        AND ISNULL(g.IsRemoved,0)=0
                        AND ISNULL(m.IsRemoved,0)=0
                        AND ISNULL(u.IsRemoved,0)=0
                        AND ISNULL(u.IsActive,0)=1
                        AND ISNULL(u.IsDeactive,0)=0
                 ) THEN 1 ELSE 0 END has_active_member
          FROM NGT.PrincipalPermissions pp
          WHERE EXISTS (
            SELECT 1 FROM NGT.UserGroups g WHERE g.PrincipalId=pp.PrincipalId
          )
        )
        SELECT grant_value,
               COUNT_BIG(*) permission_rows,
               COUNT(DISTINCT PrincipalId) group_principals,
               COUNT(DISTINCT Permission_Id) permissions,
               SUM(has_active_member) rows_on_group_with_active_member
        FROM classified
        GROUP BY grant_value
        ORDER BY grant_value
        """,
    )


def _direct_group_overlap(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH direct_permission AS (
          SELECT DISTINCT u.Id user_id,pp.Permission_Id permission_id,
                          CONVERT(int,pp.[Grant]) grant_value
          FROM NGT.Users u
          JOIN NGT.PrincipalPermissions pp
            ON pp.PrincipalId=u.Id OR pp.PrincipalId=u.PrincipalId
        ),
        inherited_permission AS (
          SELECT DISTINCT m.UserId user_id,pp.Permission_Id permission_id,
                          CONVERT(int,pp.[Grant]) grant_value
          FROM NGT.UserGroupUsers m
          JOIN NGT.UserGroups g ON g.Id=m.UserGroupId
          JOIN NGT.PrincipalPermissions pp ON pp.PrincipalId=g.PrincipalId
          WHERE ISNULL(m.IsRemoved,0)=0 AND ISNULL(g.IsRemoved,0)=0
        ),
        overlap AS (
          SELECT d.user_id,d.permission_id,d.grant_value direct_grant,
                 g.grant_value group_grant
          FROM direct_permission d
          JOIN inherited_permission g
            ON g.user_id=d.user_id AND g.permission_id=d.permission_id
        )
        SELECT COUNT_BIG(*) overlapping_user_permission_directions,
               COUNT(DISTINCT user_id) users,
               COUNT(DISTINCT permission_id) permissions,
               COALESCE(SUM(CASE WHEN direct_grant=1 AND group_grant=0 THEN 1 ELSE 0 END),0)
                 direct_one_group_zero,
               COALESCE(SUM(CASE WHEN direct_grant=0 AND group_grant=1 THEN 1 ELSE 0 END),0)
                 direct_zero_group_one,
               COALESCE(SUM(CASE WHEN direct_grant=group_grant THEN 1 ELSE 0 END),0)
                 same_direction
        FROM overlap
        """,
    )[0]


def _catalog_direct_link_materialization(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH expanded AS (
          SELECT DISTINCT pc.PrincipalId,link.PermissionId,
                          CONVERT(int,pc.[Grant]) grant_value
          FROM NGT.PrincipalPermissionCatalogs pc
          JOIN NGT.PermissionCatalogPermissions link
            ON link.PermissionCatalogId=pc.PermissionCatalog_Id
        )
        SELECT
          (SELECT COUNT_BIG(*) FROM expanded) distinct_direct_link_expansions,
          (SELECT COUNT_BIG(*) FROM expanded e WHERE EXISTS (
             SELECT 1 FROM NGT.PrincipalPermissions pp
             WHERE pp.PrincipalId=e.PrincipalId
               AND pp.Permission_Id=e.PermissionId
               AND CONVERT(int,pp.[Grant])=e.grant_value
          )) matched_atomic_same_direction,
          (SELECT COUNT_BIG(*) FROM expanded e WHERE NOT EXISTS (
             SELECT 1 FROM NGT.PrincipalPermissions pp
             WHERE pp.PrincipalId=e.PrincipalId
               AND pp.Permission_Id=e.PermissionId
               AND CONVERT(int,pp.[Grant])=e.grant_value
          )) missing_atomic_same_direction,
          (SELECT COUNT_BIG(*) FROM expanded e WHERE EXISTS (
             SELECT 1 FROM NGT.PrincipalPermissions pp
             WHERE pp.PrincipalId=e.PrincipalId
               AND pp.Permission_Id=e.PermissionId
               AND CONVERT(int,pp.[Grant])<>e.grant_value
          )) atomic_opposite_direction,
          (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs)
            principal_catalog_rows,
          (SELECT COUNT_BIG(*) FROM NGT.PermissionCatalogPermissions)
            catalog_permission_links
        """,
    )[0]


def _direction_value_window(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions
           WHERE CONVERT(int,[Grant])=-1) atomic_negative_one,
          (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions
           WHERE CONVERT(int,[Grant]) NOT IN (0,1)) atomic_outside_zero_one,
          (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs
           WHERE CONVERT(int,[Grant])=-1) catalog_negative_one,
          (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs
           WHERE CONVERT(int,[Grant]) NOT IN (0,1)) catalog_outside_zero_one
        """,
    )[0]


def _permission_contract_coverage(
    cursor: Any, endpoint_artifact: dict[str, Any]
) -> dict[str, Any]:
    contracts = sorted(
        {
            (contract["resource"], contract["action"])
            for endpoint in endpoint_artifact["endpoints"]
            for contract in endpoint["resource_action_contracts"]
            if contract["resource"] and contract["action"]
        }
    )
    match_distribution: dict[str, int] = {}
    missing: list[dict[str, str]] = []
    for resource, action in contracts:
        row = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) matches
            FROM NGT.Permissions p
            JOIN NGT.ApplicationModuleResources r
              ON r.Id=p.ApplicationModuleResourceId
            JOIN NGT.PermissionActions a ON a.Id=p.PermissionActionId
            WHERE LOWER(r.Name)=LOWER(%s) AND LOWER(a.Name)=LOWER(%s)
            """,
            (resource, action),
        )[0]
        matches = int(row["matches"])
        key = str(matches)
        match_distribution[key] = match_distribution.get(key, 0) + 1
        if matches == 0:
            missing.append({"resource": resource, "action": action})
    return {
        "declared_endpoint_resource_action_count": sum(
            len(endpoint["resource_action_contracts"])
            for endpoint in endpoint_artifact["endpoints"]
        ),
        "unique_normalized_resource_action_count": len(contracts),
        "permission_row_match_count_distribution": dict(
            sorted(match_distribution.items(), key=lambda item: int(item[0]))
        ),
        "resource_action_absent_from_all_application_owners": missing,
        "absent_contract_count": len(missing),
        "multirow_contract_count": sum(
            count
            for matches, count in match_distribution.items()
            if int(matches) > 1
        ),
        "multiplicity_scope_note": (
            "Multiple rows can belong to different application-owner scopes; "
            "multiplicity is not labeled a duplicate defect."
        ),
    }


def _admin_role_population(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.Roles WHERE LOWER(Name)='admin')
            admin_role_rows,
          (SELECT COUNT_BIG(*)
           FROM NGT.UserRoles ur JOIN NGT.Roles r ON r.Id=ur.RoleId
           WHERE LOWER(r.Name)='admin') admin_assignment_rows,
          (SELECT COUNT(DISTINCT ur.UserId)
           FROM NGT.UserRoles ur JOIN NGT.Roles r ON r.Id=ur.RoleId
           WHERE LOWER(r.Name)='admin') admin_subjects
        """,
    )[0]


def collect(
    runtime_artifact: Path,
    endpoint_artifact: Path,
    manual_guard_artifact: Path,
    role_short_circuit_artifact: Path,
) -> dict[str, Any]:
    runtime = _load_runtime_contract(runtime_artifact)
    endpoints = _load_endpoint_contract(endpoint_artifact)
    manual_guards = _load_manual_guard_contract(
        manual_guard_artifact, endpoint_artifact
    )
    role_short_circuit = _load_role_short_circuit_contract(
        role_short_circuit_artifact, endpoint_artifact
    )
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        distribution = _grant_distribution(cursor)
        group_reachability = _group_membership_reachability(cursor)
        overlap = _direct_group_overlap(cursor)
        catalog = _catalog_direct_link_materialization(cursor)
        value_window = _direction_value_window(cursor)
        endpoint_permission_coverage = _permission_contract_coverage(
            cursor, endpoints
        )
        admin_role_population = _admin_role_population(cursor)
        atomic_zero_rows = sum(
            int(row["permission_rows"])
            for row in distribution
            if int(row["grant_value"]) == 0
        )
        atomic_one_rows = sum(
            int(row["permission_rows"])
            for row in distribution
            if int(row["grant_value"]) == 1
        )
        return {
            "artifact": "varanegar_ngt_authorization_effective_boundary",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone(),
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only deployed-IL contract plus aggregate clone evidence",
                "privacy_policy": (
                    "no names, identifiers, credentials, memberships, or "
                    "per-principal permission rows persisted"
                ),
            },
            "safety": {
                "target_is_local": True,
                "database_name": safety["database_name"],
                "updateability": safety["updateability"],
                "can_select": safety["can_select"],
                "can_view_definition": safety["can_view_definition"],
                "can_update": safety["can_update"],
                "denies_data_writes": safety["denies_data_writes"],
                "operational_procedures_executed": 0,
                "assemblies_loaded_or_executed": 0,
                "identity_values_read_or_persisted": 0,
                "raw_membership_or_permission_rows_persisted": 0,
            },
            "runtime_evidence": {
                "artifact_path": str(runtime_artifact),
                "artifact_sha256": _sha256(runtime_artifact),
                "source_assembly_hashes": {
                    row["file"]: row["sha256"] for row in runtime["assemblies"]
                },
                "guard_contract": runtime["runtime_guard_contract"],
                "endpoint_artifact_path": str(endpoint_artifact),
                "endpoint_artifact_sha256": _sha256(endpoint_artifact),
                "endpoint_declaration_summary": endpoints["summary"],
                "startup_global_filter_contract": endpoints[
                    "startup_global_filter_contract"
                ],
                "manual_guard_artifact_path": str(manual_guard_artifact),
                "manual_guard_artifact_sha256": _sha256(manual_guard_artifact),
                "manual_guard_summary": manual_guards["summary"],
                "role_short_circuit_artifact_path": str(
                    role_short_circuit_artifact
                ),
                "role_short_circuit_artifact_sha256": _sha256(
                    role_short_circuit_artifact
                ),
                "role_short_circuit_contract": role_short_circuit["contract"],
            },
            "snapshot": {
                "atomic_direction_distribution_by_principal_kind": distribution,
                "group_permission_rows_and_active_membership": group_reachability,
                "direct_group_permission_overlap": overlap,
                "catalog_direct_link_materialization": catalog,
                "direction_value_window": value_window,
                "endpoint_permission_contract_coverage": endpoint_permission_coverage,
                "admin_role_population_without_identities": admin_role_population,
            },
            "summary": {
                "atomic_zero_rows": atomic_zero_rows,
                "atomic_one_rows": atomic_one_rows,
                "runtime_direct_and_group_paths_require_grant_one": True,
                "runtime_post_union_negative_one_veto_present": True,
                "snapshot_negative_one_row_count": int(
                    value_window["atomic_negative_one"]
                ),
                "runtime_guard_reads_catalog_rows_directly": False,
                "catalog_save_materializes_atomic_rows": True,
                "catalog_direct_link_expansion_fully_matches_atomic_direction": (
                    int(catalog["missing_atomic_same_direction"]) == 0
                    and int(catalog["atomic_opposite_direction"]) == 0
                ),
                "legacy_to_ngt_crosswalk_proven": False,
                "runtime_endpoint_coverage_proven": False,
                "attribute_declared_endpoint_count": endpoints["summary"][
                    "attribute_declared_endpoint_count"
                ],
                "endpoint_without_ngt_standard_claims_or_anonymous_declaration_count": endpoints[
                    "summary"
                ][
                    "endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"
                ],
                "mutating_endpoint_without_ngt_standard_claims_or_anonymous_declaration_count": endpoints[
                    "summary"
                ][
                    "mutating_endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"
                ],
                "endpoint_without_named_manual_authorization_decision_signal_count": manual_guards[
                    "summary"
                ]["endpoint_without_named_manual_authorization_decision_signal_count"],
                "mutating_endpoint_without_named_manual_authorization_decision_signal_count": manual_guards[
                    "summary"
                ][
                    "mutating_endpoint_without_named_manual_authorization_decision_signal_count"
                ],
                "resource_action_contract_absent_from_all_application_owners_count": endpoint_permission_coverage[
                    "absent_contract_count"
                ],
                "admin_role_short_circuits_base_authorization": role_short_circuit[
                    "summary"
                ]["admin_role_short_circuits_base_authorization"],
                "admin_role_current_assignment_subject_count": int(
                    admin_role_population["admin_subjects"]
                ),
            },
            "conclusions": [
                {
                    "confidence": "confirmed_static_il_and_snapshot",
                    "statement": (
                        "The deployed three-parameter direct and group Web API "
                        "queries admit Grant=1 rows; group evaluation delegates "
                        "to that same filtered direct query."
                    ),
                },
                {
                    "confidence": "confirmed_static_il",
                    "statement": (
                        "After direct/group union, the guard veto predicate tests "
                        "Grant=-1; the snapshot currently contains no such atomic row."
                    ),
                },
                {
                    "confidence": "confirmed_static_metadata_bounded_scope",
                    "statement": (
                        "Among HTTP/Route-attributed methods, some actions have no "
                        "NGT, standard, claims, or anonymous declaration; no "
                        "authorization-named global filter is constructed in the "
                        "deployed Startup.ConfigureWebApi method."
                    ),
                },
                {
                    "confidence": "confirmed_named_static_il_signals_with_limits",
                    "statement": (
                        "Direct and async MoveNext bodies for all declaration-gap "
                        "endpoints contain no named authorization-decision signal; "
                        "permission-data and identity-context calls are not counted "
                        "as enforcement."
                    ),
                },
                {
                    "confidence": "confirmed_static_il_and_aggregate_snapshot",
                    "statement": (
                        "The exact case-insensitive admin role predicate returns "
                        "before base Web-permission and standard authorization; "
                        "the current clone has aggregate admin-role assignments."
                    ),
                },
                {
                    "confidence": "confirmed_static_il",
                    "statement": (
                        "The Web API guard does not query catalog rows directly; "
                        "the save path materializes catalog selections as atomic rows."
                    ),
                },
            ],
            "evidence_limits": [
                "Static IL proves deployed code shape, not authenticated endpoint reachability.",
                "Grant=0 is a stored direction value; this artifact avoids labeling it deny beyond the observed guard filter.",
                "Catalog parity covers direct PermissionCatalogPermissions links only; recursive parent/child expansion is not inferred.",
                "No legacy AccessNode-to-NGT permission crosswalk is established.",
                "No unauthorized runtime incident or exploit is claimed.",
                "Absence of a method/type/global-filter declaration does not exclude manual checks, external host policy, or convention-only routes.",
                "Absence of named decision calls in direct/async IL does not exclude obfuscated or delegated enforcement.",
                "Permission-row multiplicity can reflect ApplicationOwner scope selected from request context.",
                "Admin assignment counts contain no identities and do not prove inappropriate use or an incident.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-artifact", required=True, type=Path)
    parser.add_argument("--endpoint-artifact", required=True, type=Path)
    parser.add_argument("--manual-guard-artifact", required=True, type=Path)
    parser.add_argument("--role-short-circuit-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(
        args.runtime_artifact,
        args.endpoint_artifact,
        args.manual_guard_artifact,
        args.role_short_circuit_artifact,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
        + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
