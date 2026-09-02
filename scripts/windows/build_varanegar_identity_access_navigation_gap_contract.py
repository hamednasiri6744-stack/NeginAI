"""Derive identity/access administration navigation gaps without reading identities or grants."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


KEYWORDS = (
    "کاربر",
    "کاربری",
    "دسترسی",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_value(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    raw = value.get("value")
    return raw if isinstance(raw, str) else ""


def _capability(caption: str) -> str:
    if "گروه" in caption and "اطلاعات" in caption:
        return "group_data_scope_assignment"
    if "کاربر" in caption and "اطلاعات" in caption:
        return "user_data_scope_assignment"
    if "گروه" in caption:
        return "user_group_administration"
    if "کاربر" in caption and "صندوق" in caption:
        return "user_cashbox_scope_assignment"
    if "کاربر" in caption:
        return "user_administration_or_scope"
    if "انبار" in caption or "مالی" in caption:
        return "inventory_financial_scope_assignment"
    if "ویژه" in caption:
        return "special_access_assignment"
    return "access_administration_shell"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--navigation", required=True, type=Path)
    parser.add_argument("--role-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    navigation = _load(args.navigation)
    role_contract = _load(args.role_contract)
    errors: list[str] = []
    if navigation.get("validation") != "PASS":
        errors.append("navigation source is not PASS")
    if role_contract.get("validation") not in (None, "PASS"):
        errors.append("role contract source is not usable")
    if not role_contract.get("role_template_count"):
        errors.append("role contract has no templates")

    routes = []
    for route in navigation.get("routes", []):
        caption = _safe_value(route.get("menu_caption"))
        if not caption or not any(keyword in caption for keyword in KEYWORDS):
            continue
        routes.append(
            {
                "menu_id": route.get("menu_id"),
                "parent_menu_id": route.get("parent_menu_id"),
                "root_menu_id": route.get("root_menu_id"),
                "hierarchy_depth": route.get("hierarchy_depth"),
                "static_caption": caption,
                "form_info_id": route.get("form_info_id"),
                "access_node_id": route.get("access_node_id"),
                "runtime_coverage_classification": route.get(
                    "route_runtime_coverage_classification"
                ),
                "matched_form_type": route.get("matched_form_type"),
                "target_capability_candidate": _capability(caption),
                "effective_user_or_group_grant_proven": False,
                "runtime_form_behavior_proven": False,
            }
        )
    routes.sort(key=lambda row: (row["root_menu_id"] or -1, row["menu_id"] or -1))

    classification_counts = Counter(
        row["runtime_coverage_classification"] for row in routes
    )
    capability_counts = Counter(row["target_capability_candidate"] for row in routes)
    if not routes:
        errors.append("no identity/access navigation candidates found")
    if any(row["matched_form_type"] for row in routes):
        errors.append("unexpected runtime form match in identity/access gap set")

    artifact = {
        "artifact": "varanegar_identity_access_administration_navigation_gap_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_STATIC_NAVIGATION_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "user_group_identity_or_grant_rows_read_or_persisted": 0,
            "credentials_or_secrets_persisted": 0,
        },
        "summary": {
            "identity_access_route_candidate_count": len(routes),
            "runtime_matched_form_count": sum(bool(row["matched_form_type"]) for row in routes),
            "route_with_form_info_count": sum(row["form_info_id"] is not None for row in routes),
            "route_with_access_node_count": sum(row["access_node_id"] is not None for row in routes),
            "runtime_coverage_classification_counts": dict(sorted(classification_counts.items())),
            "target_capability_candidate_counts": dict(sorted(capability_counts.items())),
            "effective_user_or_group_grant_proven_count": 0,
            "runtime_form_behavior_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "target_contract": {
            "model": "deny_first_capability_plus_scope_with_separate_user_and_group_assignment",
            "required_explain_fields": [
                "decision",
                "capability",
                "scope",
                "source_role_or_exception",
                "deny_reason",
                "policy_version",
            ],
            "invariants": [
                "group membership does not silently override an explicit deny",
                "data scope is separate from action capability",
                "special access is time-bounded, reasoned and audited",
                "cashbox, stock, financial and all-user-document scopes are explicit capabilities",
                "no UI navigation visibility alone proves effective authorization",
            ],
            "first_allowed_slice": "read_only_role_capability_scope_catalog_without_person_identity",
            "write_gate": "owner-approved policy, authenticated UAT, segregation-of-duties cases and immutable audit on an isolated target",
        },
        "routes": routes,
        "evidence_limits": [
            "The relevant administration packages or types are absent, unmatched or navigation-only in the captured runtime package.",
            "No identity, group membership, password, token or effective grant row was read.",
            "Static menu captions and access-node identifiers do not prove runtime authorization behavior.",
            "The existing target role contract remains a design contract until authenticated role UAT is executed.",
        ],
        "source_paths": {
            "navigation": args.navigation.as_posix(),
            "role_contract": args.role_contract.as_posix(),
        },
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
