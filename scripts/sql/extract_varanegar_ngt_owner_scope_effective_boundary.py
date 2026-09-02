"""Extract aggregate NGT owner-scope consistency from the read-only clone.

No identifiers, names, owner keys, memberships, credentials, or business rows
are persisted.  Queries are aggregate-only and the connection is safety-gated
to the local read-only clone and write-denied analysis login.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


def _one(cursor: Any, sql: str) -> dict[str, Any]:
    rows = _rows(cursor, sql)
    if len(rows) != 1:
        raise AssertionError({"expected_single_aggregate_row": len(rows)})
    return rows[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-scope-artifact", required=True, type=Path)
    parser.add_argument("--repository-scope-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    runtime = json.loads(args.runtime_scope_artifact.read_text(encoding="utf-8-sig"))
    repository = json.loads(
        args.repository_scope_artifact.read_text(encoding="utf-8-sig")
    )
    if runtime["validation"] != "PASS" or repository["validation"] != "PASS":
        raise AssertionError("scope input artifact is not validated")
    if not runtime["summary"]["header_fallback_chain_is_center_to_data_owner_to_owner"]:
        raise AssertionError("runtime fallback contract changed")
    if repository["summary"]["authorization_permission_query_uses_owner_filtered_repository_path"]:
        raise AssertionError("repository authorization path contract changed")

    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        inventory = _one(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.Applications) applications,
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationOwners) application_owners,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwners) data_owners,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwnerCenters) data_owner_centers,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwnerCenters WHERE IsActive=1 AND IsRemoved=0) active_not_removed_centers,
              (SELECT COUNT_BIG(*) FROM NGT.Principals) principals,
              (SELECT COUNT_BIG(*) FROM NGT.Users) users,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroups) user_groups,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers) user_group_memberships,
              (SELECT COUNT_BIG(*) FROM NGT.Permissions) permissions,
              (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions) principal_permissions
            """,
        )
        hierarchy = _one(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationOwners ao LEFT JOIN NGT.Applications a ON a.Id=ao.ApplicationId WHERE a.Id IS NULL) orphan_application_owner_application,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwners d LEFT JOIN NGT.ApplicationOwners ao ON ao.Id=d.ApplicationOwnerId WHERE ao.Id IS NULL) orphan_data_owner_application_owner,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwnerCenters c LEFT JOIN NGT.DataOwners d ON d.Id=c.DataOwnerId WHERE d.Id IS NULL) orphan_center_data_owner,
              (SELECT COUNT_BIG(*) FROM NGT.Principals p LEFT JOIN NGT.ApplicationOwners ao ON ao.Id=p.ApplicationOwnerId WHERE ao.Id IS NULL) orphan_principal_application_owner,
              (SELECT COUNT_BIG(*) FROM NGT.Users u LEFT JOIN NGT.ApplicationOwners ao ON ao.Id=u.ApplicationOwnerId WHERE u.ApplicationOwnerId IS NOT NULL AND ao.Id IS NULL) orphan_user_application_owner,
              (SELECT COUNT_BIG(*) FROM NGT.Users u LEFT JOIN NGT.DataOwners d ON d.Id=u.DataOwnerId WHERE u.DataOwnerId IS NOT NULL AND d.Id IS NULL) orphan_user_data_owner,
              (SELECT COUNT_BIG(*) FROM NGT.Users u LEFT JOIN NGT.DataOwnerCenters c ON c.Id=u.DataOwnerCenterId WHERE u.DataOwnerCenterId IS NOT NULL AND c.Id IS NULL) orphan_user_center,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroups g LEFT JOIN NGT.Principals p ON p.Id=g.PrincipalId WHERE p.Id IS NULL) orphan_group_principal,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.Users u ON u.Id=m.UserId WHERE m.UserId IS NOT NULL AND u.Id IS NULL) orphan_membership_user,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.Users u ON u.Id=m.UserId JOIN NGT.Principals p ON p.Id=m.UserId WHERE m.UserId IS NOT NULL AND u.Id IS NULL) orphan_membership_user_key_matches_principal,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.UserGroups g ON g.Id=m.UserGroupId WHERE g.Id IS NULL) orphan_membership_group
            """,
        )
        scope_consistency = _one(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.Users u JOIN NGT.DataOwners d ON d.Id=u.DataOwnerId WHERE u.ApplicationOwnerId<>d.ApplicationOwnerId) user_data_owner_application_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.Users u JOIN NGT.DataOwnerCenters c ON c.Id=u.DataOwnerCenterId WHERE u.DataOwnerId<>c.DataOwnerId) user_center_data_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.Users u JOIN NGT.Principals p ON p.Id=u.PrincipalId WHERE u.ApplicationOwnerId<>p.ApplicationOwnerId) user_principal_application_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroups g JOIN NGT.DataOwners d ON d.Id=g.DataOwnerId WHERE g.ApplicationOwnerId<>d.ApplicationOwnerId) group_data_owner_application_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroups g JOIN NGT.DataOwnerCenters c ON c.Id=g.DataOwnerCenterId WHERE g.DataOwnerId<>c.DataOwnerId) group_center_data_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroups g JOIN NGT.Principals p ON p.Id=g.PrincipalId WHERE g.ApplicationOwnerId<>p.ApplicationOwnerId) group_principal_application_owner_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m JOIN NGT.UserGroups g ON g.Id=m.UserGroupId WHERE m.ApplicationOwnerId<>g.ApplicationOwnerId OR m.DataOwnerId<>g.DataOwnerId OR m.DataOwnerCenterId<>g.DataOwnerCenterId) membership_group_scope_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m JOIN NGT.Users u ON u.Id=m.UserId WHERE m.ApplicationOwnerId<>u.ApplicationOwnerId OR m.DataOwnerId<>u.DataOwnerId OR m.DataOwnerCenterId<>u.DataOwnerCenterId) membership_user_scope_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers WHERE UserId IS NULL) membership_null_user
            """,
        )
        key_collision = _one(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationOwners ao JOIN NGT.DataOwners d ON d.Id=ao.Id) application_owner_data_owner_key_collisions,
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationOwners ao JOIN NGT.DataOwnerCenters c ON c.Id=ao.Id) application_owner_center_key_collisions,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwners d JOIN NGT.DataOwnerCenters c ON c.Id=d.Id) data_owner_center_key_collisions,
              (SELECT COUNT_BIG(*) FROM NGT.DataOwners d JOIN NGT.DataOwnerCenters c ON c.Id=d.Id AND c.DataOwnerId=d.Id) valid_data_owner_to_default_center_same_key,
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationOwners ao JOIN NGT.DataOwners d ON d.Id=ao.Id AND d.ApplicationOwnerId=ao.Id JOIN NGT.DataOwnerCenters c ON c.Id=d.Id AND c.DataOwnerId=d.Id) valid_full_three_level_same_key_hierarchies
            """,
        )
        center_status = _rows(
            cursor,
            """
            SELECT c.IsActive,c.IsRemoved,COUNT(DISTINCT c.Id) centers,
                   COUNT(DISTINCT u.Id) referencing_users,
                   COUNT(DISTINCT g.Id) referencing_groups,
                   COUNT(DISTINCT m.Id) referencing_memberships
            FROM NGT.DataOwnerCenters c
            LEFT JOIN NGT.Users u ON u.DataOwnerCenterId=c.Id
            LEFT JOIN NGT.UserGroups g ON g.DataOwnerCenterId=c.Id
            LEFT JOIN NGT.UserGroupUsers m ON m.DataOwnerCenterId=c.Id
            GROUP BY c.IsActive,c.IsRemoved ORDER BY c.IsActive,c.IsRemoved
            """,
        )
        permission_scope = _one(
            cursor,
            """
            WITH permission_application AS (
              SELECT p.Id permission_id,am.ApplicationId
              FROM NGT.Permissions p
              JOIN NGT.ApplicationModuleResources r ON r.Id=p.ApplicationModuleResourceId
              JOIN NGT.ApplicationModules am ON am.Id=r.ApplicationModuleId
            ), principal_application AS (
              SELECT p.Id principal_id,ao.ApplicationId
              FROM NGT.Principals p
              JOIN NGT.ApplicationOwners ao ON ao.Id=p.ApplicationOwnerId
            )
            SELECT
              COUNT_BIG(*) principal_permission_rows_with_complete_application_chain,
              SUM(CASE WHEN pp.[Grant]=1 THEN 1 ELSE 0 END) grant_one_rows_with_complete_application_chain,
              SUM(CASE WHEN pa.ApplicationId<>pr.ApplicationId THEN 1 ELSE 0 END) cross_application_principal_permission_rows,
              SUM(CASE WHEN pp.[Grant]=1 AND pa.ApplicationId<>pr.ApplicationId THEN 1 ELSE 0 END) cross_application_grant_one_rows,
              COUNT(DISTINCT CASE WHEN pp.[Grant]=1 AND pa.ApplicationId<>pr.ApplicationId THEN pp.PrincipalId END) cross_application_grant_one_principals,
              COUNT(DISTINCT CASE WHEN pp.[Grant]=1 AND pa.ApplicationId<>pr.ApplicationId THEN pp.Permission_Id END) cross_application_grant_one_permissions
            FROM NGT.PrincipalPermissions pp
            JOIN permission_application pa ON pa.permission_id=pp.Permission_Id
            JOIN principal_application pr ON pr.principal_id=pp.PrincipalId
            """,
        )
        permission_chain = _one(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.Permissions p LEFT JOIN NGT.ApplicationModuleResources r ON r.Id=p.ApplicationModuleResourceId WHERE r.Id IS NULL) permission_resource_orphans,
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationModuleResources r LEFT JOIN NGT.ApplicationModules m ON m.Id=r.ApplicationModuleId WHERE m.Id IS NULL) resource_module_orphans,
              (SELECT COUNT_BIG(*) FROM NGT.ApplicationModules m LEFT JOIN NGT.Applications a ON a.Id=m.ApplicationId WHERE a.Id IS NULL) module_application_orphans,
              (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions pp LEFT JOIN NGT.Permissions p ON p.Id=pp.Permission_Id WHERE p.Id IS NULL) principal_permission_permission_orphans,
              (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions pp LEFT JOIN NGT.Principals p ON p.Id=pp.PrincipalId WHERE p.Id IS NULL) principal_permission_principal_orphans
            """,
        )
        group_effective = _one(
            cursor,
            """
            WITH permission_application AS (
              SELECT p.Id permission_id,am.ApplicationId
              FROM NGT.Permissions p
              JOIN NGT.ApplicationModuleResources r ON r.Id=p.ApplicationModuleResourceId
              JOIN NGT.ApplicationModules am ON am.Id=r.ApplicationModuleId
            )
            SELECT
              COUNT_BIG(*) active_membership_grant_one_expansions,
              SUM(CASE WHEN g.ApplicationOwnerId<>m.ApplicationOwnerId OR g.DataOwnerId<>m.DataOwnerId OR g.DataOwnerCenterId<>m.DataOwnerCenterId THEN 1 ELSE 0 END) expansion_membership_group_scope_mismatch,
              SUM(CASE WHEN u.ApplicationOwnerId<>m.ApplicationOwnerId OR u.DataOwnerId<>m.DataOwnerId OR u.DataOwnerCenterId<>m.DataOwnerCenterId THEN 1 ELSE 0 END) expansion_membership_user_scope_mismatch,
              SUM(CASE WHEN gao.ApplicationId<>pa.ApplicationId THEN 1 ELSE 0 END) expansion_group_permission_application_mismatch,
              COUNT(DISTINCT CASE WHEN gao.ApplicationId<>pa.ApplicationId THEN m.UserId END) users_with_group_permission_application_mismatch
            FROM NGT.UserGroupUsers m
            JOIN NGT.Users u ON u.Id=m.UserId
            JOIN NGT.UserGroups g ON g.Id=m.UserGroupId
            JOIN NGT.ApplicationOwners gao ON gao.Id=g.ApplicationOwnerId
            JOIN NGT.PrincipalPermissions pp ON pp.PrincipalId=g.PrincipalId AND pp.[Grant]=1
            JOIN permission_application pa ON pa.permission_id=pp.Permission_Id
            WHERE m.IsRemoved=0 AND g.IsRemoved=0 AND ISNULL(u.IsRemoved,0)=0
            """,
        )
        owner_multiplicity = _rows(
            cursor,
            """
            WITH x AS (
              SELECT 'application_owners_per_application' metric,ApplicationId parent_id,COUNT_BIG(*) child_count FROM NGT.ApplicationOwners GROUP BY ApplicationId
              UNION ALL
              SELECT 'data_owners_per_application_owner',ApplicationOwnerId,COUNT_BIG(*) FROM NGT.DataOwners GROUP BY ApplicationOwnerId
              UNION ALL
              SELECT 'centers_per_data_owner',DataOwnerId,COUNT_BIG(*) FROM NGT.DataOwnerCenters GROUP BY DataOwnerId
            )
            SELECT metric,child_count,COUNT_BIG(*) parent_count
            FROM x GROUP BY metric,child_count ORDER BY metric,child_count
            """,
        )
    finally:
        connection.close()

    mismatch_total = sum(int(value or 0) for value in scope_consistency.values())
    application_grant_mismatch = int(permission_scope["cross_application_grant_one_rows"] or 0)
    group_expansion_mismatch = int(
        group_effective["expansion_group_permission_application_mismatch"] or 0
    )
    artifact = {
        "artifact": "varanegar_ngt_owner_scope_effective_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS",
        "source": {
            "runtime_scope_artifact": str(args.runtime_scope_artifact),
            "runtime_scope_artifact_sha256": hashlib.sha256(args.runtime_scope_artifact.read_bytes()).hexdigest(),
            "repository_scope_artifact": str(args.repository_scope_artifact),
            "repository_scope_artifact_sha256": hashlib.sha256(args.repository_scope_artifact.read_bytes()).hexdigest(),
        },
        "safety": {
            **safety,
            "mode": "AGGREGATE_ONLY_LOCAL_READ_ONLY_CLONE",
            "operational_procedures_executed": 0,
            "application_commands_or_endpoints_executed": 0,
            "write_statements_executed": 0,
            "owner_or_principal_identifiers_persisted": 0,
            "identity_names_memberships_or_credentials_persisted": 0,
            "business_rows_persisted": 0,
        },
        "summary": {
            **inventory,
            "hierarchy_orphan_count": sum(
                int(value or 0)
                for key, value in hierarchy.items()
                if key != "orphan_membership_user_key_matches_principal"
            ),
            "scope_consistency_mismatch_count": mismatch_total,
            "cross_type_owner_key_collision_count": sum(
                int(key_collision[key] or 0)
                for key in (
                    "application_owner_data_owner_key_collisions",
                    "application_owner_center_key_collisions",
                    "data_owner_center_key_collisions",
                )
            ),
            "cross_application_grant_one_row_count": application_grant_mismatch,
            "active_group_expansion_application_mismatch_count": group_expansion_mismatch,
            "data_owner_to_center_fallback_resolves_default_center_count": int(
                key_collision["valid_data_owner_to_default_center_same_key"] or 0
            ),
            "header_fallback_same_key_resolves_valid_full_hierarchy": int(
                key_collision["valid_full_three_level_same_key_hierarchies"] or 0
            )
            > 0,
            "authorization_permission_repository_path_is_owner_filtered": False,
            "current_snapshot_cross_application_effective_grant_detected": (
                application_grant_mismatch > 0 or group_expansion_mismatch > 0
            ),
        },
        "owner_hierarchy_integrity": hierarchy,
        "user_group_scope_consistency": scope_consistency,
        "cross_type_owner_key_collisions": key_collision,
        "data_owner_center_status_distribution": center_status,
        "permission_application_scope": permission_scope,
        "permission_chain_integrity": permission_chain,
        "active_group_permission_expansion": group_effective,
        "owner_multiplicity_distribution": owner_multiplicity,
        "interpretation": {
            "runtime_permission_path": "GetQuery (raw DbSet), not GetQueryByOwner/CalcExtraPredict",
            "data_query_path": "OwnerInfo carries three keys; owner-aware repositories can apply application/data/center and removed predicates",
            "same_key_fallback": "A missing DataOwnerCenter can resolve the same-key default center for one DataOwner; a missing DataOwner cannot resolve the ApplicationOwner key to a valid DataOwner in this snapshot",
            "membership_scope": "Membership rows match group scope; most differ from user center scope, so group-scope assignment is not treated as corruption without owner confirmation",
            "incident_claimed": False,
        },
        "evidence_limits": [
            "Snapshot aggregate consistency does not prove future inserts, all deployments, or runtime request authorization.",
            "No request with altered owner headers was sent; exploitability and anonymous reachability are not tested.",
            "No owner, principal, user, group, permission, or membership identifier is persisted.",
            "Owner-aware repository behavior is derived from static IL; generated SQL was not captured.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
