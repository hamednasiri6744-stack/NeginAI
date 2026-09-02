"""Correlate bank-reconciliation IL permission aliases with clone access nodes.

Only static access-node configuration and aggregate right-value counts are
returned. No user or group identifier, name, membership, or business row is
selected or persisted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _rows,
)


ALIASES = ("TransferList", "ReconciliationSetup")
EXPECTED_CHILDREN = {
    "TransferList": {"View", "AddNew", "Edit", "Delete"},
    "ReconciliationSetup": {"View", "Edit", "Delete"},
}
ACCESS_VALUE_MEANING = {0: "neutral", 1: "allow", 2: "deny"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-guards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    guards = _load(args.command_guards)
    if guards.get("validation") != "PASS":
        raise ValueError("validated bank reconciliation command guards are required")
    observed_aliases = {
        row["observed_permission_alias"]
        for row in guards["target_contract"]["authorization_layers"]
    }

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            nodes = _rows(
                cursor,
                """
                WITH roots AS (
                    SELECT AccessNodeId,ParentId,AccessNodeKey,IsShow,NodeOrder,
                           IsUsedInSDS
                    FROM dbo.AccessNode
                    WHERE AccessNodeKey IN (%s,%s)
                )
                SELECT n.AccessNodeId,n.ParentId,n.AccessNodeKey,
                       p.AccessNodeKey AS ParentAccessNodeKey,
                       n.IsShow,n.NodeOrder,n.IsUsedInSDS,
                       CASE WHEN r.AccessNodeId IS NULL THEN 0 ELSE 1 END AS IsAliasRoot
                FROM dbo.AccessNode n
                LEFT JOIN dbo.AccessNode p ON p.AccessNodeId=n.ParentId
                LEFT JOIN roots r ON r.AccessNodeId=n.AccessNodeId
                WHERE n.AccessNodeId IN (SELECT AccessNodeId FROM roots)
                   OR n.ParentId IN (SELECT AccessNodeId FROM roots)
                ORDER BY n.ParentId,n.NodeOrder,n.AccessNodeId
                """,
                ALIASES,
            )
            assignments = _rows(
                cursor,
                """
                WITH roots AS (
                    SELECT AccessNodeId FROM dbo.AccessNode
                    WHERE AccessNodeKey IN (%s,%s)
                ), target_nodes AS (
                    SELECT AccessNodeId FROM roots
                    UNION
                    SELECT AccessNodeId FROM dbo.AccessNode
                    WHERE ParentId IN (SELECT AccessNodeId FROM roots)
                ), assignments AS (
                    SELECT 'direct' AS assignment_source,AccessNodeId,AccessValue
                    FROM dbo.UserRights
                    WHERE AccessNodeId IN (SELECT AccessNodeId FROM target_nodes)
                    UNION ALL
                    SELECT 'group',AccessNodeId,AccessValue
                    FROM dbo.UserGroupRights
                    WHERE AccessNodeId IN (SELECT AccessNodeId FROM target_nodes)
                )
                SELECT assignment_source,AccessNodeId,AccessValue,
                       COUNT_BIG(*) AS assignment_count
                FROM assignments
                GROUP BY assignment_source,AccessNodeId,AccessValue
                ORDER BY AccessNodeId,assignment_source,AccessValue
                """,
                ALIASES,
            )
            effective = _rows(
                cursor,
                """
                WITH roots AS (
                    SELECT AccessNodeId FROM dbo.AccessNode
                    WHERE AccessNodeKey IN (%s,%s)
                ), selected_nodes AS (
                    SELECT AccessNodeId FROM roots
                    UNION
                    SELECT AccessNodeId FROM dbo.AccessNode
                    WHERE ParentId IN (SELECT AccessNodeId FROM roots)
                ), active_users AS (
                    SELECT AppUserId,IsAdmin FROM dbo.AppUser
                    WHERE IsActive=1 AND ISNULL(IsDeleted,0)=0
                ), evaluated AS (
                    SELECT n.AccessNodeId,u.AppUserId,u.IsAdmin,
                           MAX(CASE WHEN d.AccessValue=1 THEN 1 ELSE 0 END) direct_allow,
                           MAX(CASE WHEN d.AccessValue=2 THEN 1 ELSE 0 END) direct_deny,
                           MAX(CASE WHEN g.AccessValue=1 THEN 1 ELSE 0 END) group_allow,
                           MAX(CASE WHEN g.AccessValue=2 THEN 1 ELSE 0 END) group_deny
                    FROM selected_nodes n CROSS JOIN active_users u
                    LEFT JOIN dbo.UserRights d
                      ON d.AccessNodeId=n.AccessNodeId AND d.AppUserId=u.AppUserId
                    LEFT JOIN dbo.UserGroupXAppUser m ON m.AppUserId=u.AppUserId
                    LEFT JOIN dbo.UserGroupRights g
                      ON g.AccessNodeId=n.AccessNodeId AND g.UserGroupId=m.UserGroupId
                    GROUP BY n.AccessNodeId,u.AppUserId,u.IsAdmin
                )
                SELECT e.AccessNodeId,COUNT_BIG(*) AS active_user_count,
                       SUM(CASE WHEN IsAdmin=1 THEN 1 ELSE 0 END) AS admin_bypass_count,
                       SUM(CASE WHEN IsAdmin=1 OR
                            ((direct_allow=1 OR group_allow=1) AND direct_deny=0 AND group_deny=0)
                            THEN 1 ELSE 0 END) AS effective_allow_count,
                       SUM(CASE WHEN IsAdmin=0 AND (direct_deny=1 OR group_deny=1)
                            THEN 1 ELSE 0 END) AS explicit_deny_count,
                       SUM(CASE WHEN IsAdmin=0 AND direct_deny=0 AND group_deny=0
                                 AND direct_allow=0 AND group_allow=0
                            THEN 1 ELSE 0 END) AS neutral_no_allow_count
                FROM evaluated e
                GROUP BY e.AccessNodeId ORDER BY e.AccessNodeId
                """,
                ALIASES,
            )

    node_rows = [
        {
            "access_node_id": int(row["AccessNodeId"]),
            "parent_id": int(row["ParentId"]) if row["ParentId"] is not None else None,
            "access_node_key": row["AccessNodeKey"],
            "parent_access_node_key": row["ParentAccessNodeKey"],
            "is_show": bool(row["IsShow"]),
            "node_order": float(row["NodeOrder"]) if row["NodeOrder"] is not None else None,
            "is_used_in_sds": bool(row["IsUsedInSDS"]),
            "is_alias_root": bool(row["IsAliasRoot"]),
        }
        for row in nodes
    ]
    assignment_rows = [
        {
            "assignment_source": row["assignment_source"],
            "access_node_id": int(row["AccessNodeId"]),
            "access_value": int(row["AccessValue"]),
            "access_value_meaning": ACCESS_VALUE_MEANING.get(int(row["AccessValue"]), "unknown"),
            "assignment_count": int(row["assignment_count"]),
        }
        for row in assignments
    ]
    effective_rows = [
        {
            "access_node_id": int(row["AccessNodeId"]),
            "active_user_count": int(row["active_user_count"]),
            "admin_bypass_count": int(row["admin_bypass_count"]),
            "effective_allow_count": int(row["effective_allow_count"]),
            "explicit_deny_count": int(row["explicit_deny_count"]),
            "neutral_no_allow_count": int(row["neutral_no_allow_count"]),
        }
        for row in effective
    ]
    root_by_id = {
        row["access_node_id"]: row
        for row in node_rows
        if row["is_alias_root"]
    }
    alias_contracts = []
    for alias in ALIASES:
        root = next((row for row in root_by_id.values() if row["access_node_key"] == alias), None)
        children = [] if root is None else sorted(
            row["access_node_key"]
            for row in node_rows
            if row["parent_id"] == root["access_node_id"]
        )
        alias_contracts.append(
            {
                "legacy_alias": alias,
                "root_access_node_id": None if root is None else root["access_node_id"],
                "parent_access_node_key": None if root is None else root["parent_access_node_key"],
                "child_keys": children,
                "has_dedicated_confirm_child": "Confirm" in children,
            }
        )

    errors: list[str] = []
    if observed_aliases != set(ALIASES):
        errors.append("IL permission alias set changed")
    if len(root_by_id) != len(ALIASES):
        errors.append("one or more permission alias roots are missing")
    for row in alias_contracts:
        if set(row["child_keys"]) != EXPECTED_CHILDREN[row["legacy_alias"]]:
            errors.append(f"permission child set changed: {row['legacy_alias']}")
        if row["parent_access_node_key"] != "OtherOperation":
            errors.append(f"permission parent changed: {row['legacy_alias']}")
    if any(row["access_value"] not in ACCESS_VALUE_MEANING for row in assignment_rows):
        errors.append("unsupported access-value code observed")
    if len(effective_rows) != len(node_rows):
        errors.append("aggregate effective-node coverage incomplete")
    if any(
        row["active_user_count"]
        != row["effective_allow_count"]
        + row["explicit_deny_count"]
        + row["neutral_no_allow_count"]
        for row in effective_rows
    ):
        errors.append("aggregate effective outcome partition mismatch")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_permission_alias_catalog_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_STATIC_ACCESS_NODE_AND_AGGREGATE_RIGHT_VALUE_COUNTS",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "user_group_or_membership_identity_values_persisted": 0,
            "identities_processed_transiently_for_aggregate_effective_counts": 1,
            "individual_right_rows_persisted": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "application_or_sql_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "observed_il_alias_count": len(observed_aliases),
            "catalog_alias_root_count": len(root_by_id),
            "catalog_child_node_count": sum(not row["is_alias_root"] for row in node_rows),
            "aggregate_assignment_bucket_count": len(assignment_rows),
            "effective_node_count": len(effective_rows),
            "active_user_count_per_node": min(
                (row["active_user_count"] for row in effective_rows), default=0
            ),
            "admin_bypass_count_per_node": min(
                (row["admin_bypass_count"] for row in effective_rows), default=0
            ),
            "effective_allow_count_min": min(
                (row["effective_allow_count"] for row in effective_rows), default=0
            ),
            "effective_allow_count_max": max(
                (row["effective_allow_count"] for row in effective_rows), default=0
            ),
            "direct_allow_assignment_count": sum(
                row["assignment_count"]
                for row in assignment_rows
                if row["assignment_source"] == "direct" and row["access_value"] == 1
            ),
            "group_allow_assignment_count": sum(
                row["assignment_count"]
                for row in assignment_rows
                if row["assignment_source"] == "group" and row["access_value"] == 1
            ),
            "deny_assignment_count": sum(
                row["assignment_count"]
                for row in assignment_rows
                if row["access_value"] == 2
            ),
            "validation_error_count": len(errors),
        },
        "alias_contracts": alias_contracts,
        "access_nodes": node_rows,
        "aggregate_assignment_buckets": assignment_rows,
        "aggregate_effective_active_user_counts": effective_rows,
        "effective_permission_contract": {
            "admin_bypass_observed_in_prior_authorization_contract": True,
            "deny_overrides_allow": True,
            "neutral_is_not_allow": True,
            "at_least_one_direct_or_group_allow_required_without_deny": True,
            "aggregate_active_user_effective_counts_computed": True,
            "current_user_or_role_effective_permission_computed": False,
        },
        "target_contract": {
            "legacy_aliases_are_target_capability_names": False,
            "legacy_edit_implies_confirm": False,
            "distinct_capabilities_required": [
                "bank_reconciliation.view",
                "bank_reconciliation.import_statement",
                "bank_reconciliation.match_instrument",
                "bank_reconciliation.unmatch_instrument",
                "bank_reconciliation.confirm",
                "bank_reconciliation.cancel",
            ],
            "authorization_also_requires_data_scope_operation_context_and_state_validation": True,
        },
        "validation_errors": errors,
        "limits": [
            "Aggregate assignment counts are not unique-user counts and do not establish any person's effective permission.",
            "Legacy aliases are coarse evidence and must not be copied as the target capability model.",
            "User identifiers were processed transiently only to aggregate effective outcomes; no identity or individual right row was persisted.",
            "No application command, form, stored procedure or business row was executed or read.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
