"""Extract anonymous authorization coverage for the open Varanegar routes.

The extractor reads only static AccessNode configuration and aggregate legacy
rights from the read-only clone. It never persists identities, group names,
individual memberships, per-user grants, credentials, or business rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
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


CODE_TEXT = re.compile(r"^[A-Za-z0-9_.+\-]{1,240}$")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("cp1256")
    return str(value)


def _safe_text(value: Any, *, code: bool) -> dict[str, Any]:
    text = _text(value).strip()
    safe = bool(CODE_TEXT.fullmatch(text)) if code else (
        0 < len(text) <= 120
        and "\n" not in text
        and "\r" not in text
        and "@" not in text
        and "\\" not in text
        and "http://" not in text.casefold()
        and "https://" not in text.casefold()
    )
    result: dict[str, Any] = {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "length": len(text),
        "persisted_as": (
            "safe_code" if code and safe else
            "safe_static_caption" if safe else
            "fingerprint_only"
        ),
    }
    if safe:
        result["value"] = text
    return result


def _load_roots(crosswalk_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    roots: list[dict[str, Any]] = []
    for window in payload["open_form_routes"]:
        if window["route_match_count"] != 1:
            raise ValueError(f"open route is not unique: {window['ui_title']}")
        route = window["routes"][0]
        roots.append(
            {
                "ui_title": window["ui_title"],
                "menu_id": route["menu_id"],
                "access_node_id": int(route["access_node_id"]),
                "access_node_key": route["access_node_key"],
                "matched_form_type": route["matched_form_type"],
            }
        )
    return roots


def _descendants(
    all_nodes: list[dict[str, Any]], root_ids: set[int]
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    children: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_id = {int(row["AccessNodeId"]): row for row in all_nodes}
    for row in all_nodes:
        parent = row.get("ParentId")
        if parent is not None:
            children[int(parent)].append(row)

    depth: dict[int, int] = {}
    pending = [(node_id, 0) for node_id in sorted(root_ids)]
    while pending:
        node_id, node_depth = pending.pop(0)
        if node_id in depth and depth[node_id] <= node_depth:
            continue
        depth[node_id] = node_depth
        pending.extend(
            (int(child["AccessNodeId"]), node_depth + 1)
            for child in children.get(node_id, [])
        )
    return [by_id[node_id] for node_id in sorted(depth)], depth


def _rights_by_node(cursor: Any, node_ids: list[int]) -> dict[int, dict[str, Any]]:
    sql_ids = ",".join(str(node_id) for node_id in node_ids)
    direct = _rows(
        cursor,
        f"""
        SELECT AccessNodeId,AccessValue,COUNT_BIG(*) right_rows,
               COUNT(DISTINCT AppUserId) principals
        FROM dbo.UserRights
        WHERE AccessNodeId IN ({sql_ids})
        GROUP BY AccessNodeId,AccessValue
        ORDER BY AccessNodeId,AccessValue
        """,
    )
    groups = _rows(
        cursor,
        f"""
        SELECT AccessNodeId,AccessValue,COUNT_BIG(*) right_rows,
               COUNT(DISTINCT UserGroupId) principals
        FROM dbo.UserGroupRights
        WHERE AccessNodeId IN ({sql_ids})
        GROUP BY AccessNodeId,AccessValue
        ORDER BY AccessNodeId,AccessValue
        """,
    )
    effective = _rows(
        cursor,
        f"""
        WITH selected_nodes AS (
          SELECT AccessNodeId FROM dbo.AccessNode WHERE AccessNodeId IN ({sql_ids})
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
        SELECT AccessNodeId,COUNT_BIG(*) active_users,
               SUM(CASE WHEN IsAdmin=1 THEN 1 ELSE 0 END) admin_bypass,
               SUM(CASE WHEN IsAdmin=1 OR
                    ((direct_allow=1 OR group_allow=1) AND direct_deny=0 AND group_deny=0)
                    THEN 1 ELSE 0 END) effective_allow,
               SUM(CASE WHEN IsAdmin=0 AND (direct_deny=1 OR group_deny=1)
                    THEN 1 ELSE 0 END) explicit_deny,
               SUM(CASE WHEN IsAdmin=0 AND direct_deny=0 AND group_deny=0
                         AND direct_allow=0 AND group_allow=0
                    THEN 1 ELSE 0 END) neutral_no_allow
        FROM evaluated GROUP BY AccessNodeId ORDER BY AccessNodeId
        """,
    )
    result: dict[int, dict[str, Any]] = {
        node_id: {
            "direct": {"neutral": 0, "allow": 0, "deny": 0},
            "group": {"neutral": 0, "allow": 0, "deny": 0},
            "effective_active_users": None,
        }
        for node_id in node_ids
    }
    names = {0: "neutral", 1: "allow", 2: "deny"}
    for source_name, rows in (("direct", direct), ("group", groups)):
        for row in rows:
            result[int(row["AccessNodeId"])][source_name][names[int(row["AccessValue"])]] = {
                "right_rows": int(row["right_rows"]),
                "principals": int(row["principals"]),
            }
    for row in effective:
        result[int(row["AccessNodeId"])]["effective_active_users"] = {
            key: int(value)
            for key, value in row.items()
            if key != "AccessNodeId"
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    roots = _load_roots(args.crosswalk)
    root_ids = {row["access_node_id"] for row in roots}
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            all_nodes = _rows(
                cursor,
                """
                SELECT AccessNodeId,ParentId,AccessNodeKey,Caption,IsShow,
                       IsUsedInSDS,IsUsedInFRU,NodeOrder
                FROM dbo.AccessNode ORDER BY AccessNodeId
                """,
            )
            selected, depths = _descendants(all_nodes, root_ids)
            node_ids = [int(row["AccessNodeId"]) for row in selected]
            rights = _rights_by_node(cursor, node_ids)

    root_by_id = {row["access_node_id"]: row for row in roots}
    nodes = []
    for row in selected:
        node_id = int(row["AccessNodeId"])
        parent_id = int(row["ParentId"]) if row.get("ParentId") is not None else None
        root_id = node_id
        while root_id not in root_ids:
            parent = next(
                (candidate for candidate in selected if int(candidate["AccessNodeId"]) == parent_id),
                None,
            )
            if parent is None:
                break
            root_id = int(parent["AccessNodeId"])
            parent_id = int(parent["ParentId"]) if parent.get("ParentId") is not None else None
        nodes.append(
            {
                "access_node_id": node_id,
                "parent_id": int(row["ParentId"]) if row.get("ParentId") is not None else None,
                "root_access_node_id": root_id,
                "root_ui_title": root_by_id[root_id]["ui_title"],
                "depth": depths[node_id],
                "access_node_key": _safe_text(row["AccessNodeKey"], code=True),
                "caption": _safe_text(row["Caption"], code=False),
                "is_show": bool(row["IsShow"]),
                "is_used_in_sds": bool(row["IsUsedInSDS"]),
                "is_used_in_fru": bool(row["IsUsedInFRU"]),
                "rights": rights[node_id],
            }
        )

    command_nodes = [row for row in nodes if row["depth"] > 0]
    artifact = {
        "artifact": "varanegar_open_route_anonymous_authorization_matrix",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": {"server": SERVER, "database": DATABASE},
        "sources": {"menu_form_crosswalk": args.crosswalk.as_posix()},
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATE_AUTHORIZATION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "identities_or_group_names_persisted": 0,
            "individual_memberships_or_grants_persisted": 0,
            "business_rows_read_or_persisted": 0,
            "write_statements_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "open_route_count": len(roots),
            "authorization_node_count": len(nodes),
            "command_node_count": len(command_nodes),
            "hidden_command_node_count": sum(not row["is_show"] for row in command_nodes),
            "command_key_counts": dict(
                sorted(
                    Counter(
                        row["access_node_key"].get("value", "fingerprint_only")
                        for row in command_nodes
                    ).items()
                )
            ),
        },
        "effective_contract": (
            "Admin bypasses node evaluation. Otherwise any direct or group deny wins; "
            "without deny, at least one direct or group allow is required. Neutral is not allow."
        ),
        "erp_design_contract": [
            "Separate page visibility from command authorization.",
            "Separate functional authorization from DC, sale-office, stock, customer, and other data scopes.",
            "Model approve, reverse, undo, issue-exit, remove-exit, free/merge, print, and export as atomic capabilities.",
            "Evaluate feature entitlement, fiscal context, operation date, selection, and workflow transition after authorization.",
            "Keep legacy AccessNode and NGT RBAC as separate namespaces until an explicit audited crosswalk exists.",
            "Use immutable audit events for sensitive state transitions and enforce segregation-of-duties policies explicitly.",
        ],
        "limits": [
            "Aggregate clone rights describe authorization coverage, not the identity or effective menu of the current runtime user.",
            "The clone can drift from production; this artifact is a timestamped snapshot.",
            "AccessNode ancestry is configuration structure, not proof that every child check executes in every code path.",
            "A grant does not bypass workflow, feature, fiscal-year, date, selection, or data-partition guards.",
        ],
        "open_routes": roots,
        "nodes": nodes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
