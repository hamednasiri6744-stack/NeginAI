"""Extract anonymous aggregate authorization for the DiscountRules route.

Only the read-only clone is queried. No user/group names, identifiers,
individual assignments, credentials, business rows, or rule values are saved.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows
from extract_varanegar_route_authorization_matrix import _descendants, _rights_by_node, _safe_text, _text


FORM = "VN.SDS.MainData.UI.Discount.FormDiscount"
EXPECTED_ROOT_ID = 404
EXPECTED_ROOT_KEY = "DiscountRules"
EXPECTED_COMMAND_KEYS = {"View", "New", "Edit", "Delete"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    crosswalk = json.loads(args.crosswalk.read_text(encoding="utf-8-sig"))
    routes = [row for row in crosswalk["crosswalk"] if row.get("matched_form_type") == FORM]
    errors: list[str] = []
    if len(routes) != 1:
        errors.append(f"expected one exact route, found {len(routes)}")
    route = routes[0]
    root_id = int(route["access_node_id"])
    root_key = route["access_node_key"].get("value")
    if root_id != EXPECTED_ROOT_ID or root_key != EXPECTED_ROOT_KEY:
        errors.append("discount route identity changed")

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
            selected, depths = _descendants(all_nodes, {root_id})
            node_ids = [int(row["AccessNodeId"]) for row in selected]
            rights = _rights_by_node(cursor, node_ids)

    nodes = []
    for row in selected:
        node_id = int(row["AccessNodeId"])
        nodes.append({
            "access_node_id": node_id,
            "parent_id": int(row["ParentId"]) if row.get("ParentId") is not None else None,
            "depth": depths[node_id],
            "access_node_key": _safe_text(row["AccessNodeKey"], code=True),
            "caption": _safe_text(row["Caption"], code=False),
            "is_show": bool(row["IsShow"]),
            "rights": rights[node_id],
        })
    command_nodes = [row for row in nodes if row["depth"] == 1]
    command_keys = {row["access_node_key"].get("value") for row in command_nodes}
    if command_keys != EXPECTED_COMMAND_KEYS:
        errors.append(f"command keys changed: {sorted(command_keys)}")
    if any(row["rights"]["effective_active_users"] is None for row in nodes):
        errors.append("effective active-user aggregate missing")

    by_key = {row["access_node_key"].get("value"): row for row in nodes}
    command_effective_allow = {
        key: by_key[key]["rights"]["effective_active_users"]["effective_allow"]
        for key in sorted(EXPECTED_COMMAND_KEYS)
    }
    command_explicit_deny = {
        key: by_key[key]["rights"]["effective_active_users"]["explicit_deny"]
        for key in sorted(EXPECTED_COMMAND_KEYS)
    }
    artifact = {
        "artifact": "varanegar_discount_rule_anonymous_aggregate_authorization_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "form": FORM},
        "source": {"crosswalk": args.crosswalk.as_posix()},
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATE_AUTHORIZATION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "identities_or_group_names_persisted": 0,
            "individual_memberships_or_grants_persisted": 0,
            "business_or_rule_rows_read_or_persisted": 0,
            "write_statements_executed": 0,
        },
        "summary": {
            "root_access_node_id": root_id,
            "authorization_node_count": len(nodes),
            "command_node_count": len(command_nodes),
            "visible_command_node_count": sum(row["is_show"] for row in command_nodes),
            "active_user_count": by_key[EXPECTED_ROOT_KEY]["rights"]["effective_active_users"]["active_users"],
            "admin_bypass_count": by_key[EXPECTED_ROOT_KEY]["rights"]["effective_active_users"]["admin_bypass"],
            "root_effective_allow_count": by_key[EXPECTED_ROOT_KEY]["rights"]["effective_active_users"]["effective_allow"],
            "root_neutral_no_allow_count": by_key[EXPECTED_ROOT_KEY]["rights"]["effective_active_users"]["neutral_no_allow"],
            "command_effective_allow_counts": command_effective_allow,
            "command_explicit_deny_counts": command_explicit_deny,
            "validation_error_count": len(errors),
        },
        "route": {
            "menu_id": int(route["menu_id"]),
            "form_info_id": int(route["form_info_id"]),
            "access_node_id": root_id,
            "access_node_key": route["access_node_key"],
            "matched_form_type": route["matched_form_type"],
            "match_quality": route["match_quality"],
        },
        "nodes": nodes,
        "effective_contract": "Admin bypasses evaluation. Otherwise deny wins; without deny, at least one direct or group allow is required. Neutral is not allow.",
        "interpretation": {
            "separate_view_new_edit_delete_nodes_proven": command_keys == EXPECTED_COMMAND_KEYS,
            "separate_review_or_publish_node_proven": False,
            "same_effective_allow_count_proves_same_principals": False,
            "screen_visibility_proves_api_authorization": False,
            "conclusion": "DiscountRules has separate visible View/New/Edit/Delete AccessNodes. The clone aggregate has equal effective-allow counts on all four commands, but anonymous aggregates cannot prove the allowed identities are identical. No separate Review or Publish command node is present in this subtree.",
        },
        "target_requirement": "Keep view, draft, edit, review, publish, deactivate and rollback as independently enforced API capabilities; deny by default and persist an authorization decision trace.",
        "validation_errors": errors,
        "limits": [
            "Aggregate rights do not identify the current runtime user or any individual principal.",
            "Equal command counts do not prove the same principals have each command.",
            "Configured AccessNodes do not prove every application or API path evaluates them.",
            "The read-only clone is a timestamped snapshot and may drift from production.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
