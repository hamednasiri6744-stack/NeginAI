"""Map the complete Varanegar menu tree to target ERP module hints."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DOMAIN_TO_MODULES = {
    1: ("organization_context",), 2: ("master_data",),
    3: ("master_data", "organization_context"), 4: ("master_data",),
    5: ("master_data",), 6: ("pricing_rules",), 7: ("sales",),
    8: ("inventory",), 9: ("distribution",), 10: ("receivables_treasury",),
    11: ("sales", "inventory", "receivables_treasury"),
    12: ("receivables_treasury",), 13: ("procurement_payables",),
    14: ("procurement_payables",), 15: ("procurement_payables", "accounting"),
    16: ("identity_authorization",), 17: ("configuration",), 18: ("accounting",),
}

# Section-level navigation hints. Multi-module roots remain multi-module; this is
# not coerced into a single aggregate owner.
ROOT_MODULE_HINTS = {
    10: ("configuration",),
    500: ("master_data",),
    140000: ("master_data",),
    20: ("sales",),
    100: ("master_data",),
    1500: ("pricing_rules",),
    30: ("inventory", "procurement_payables", "accounting"),
    300: ("sales", "reporting_documents"),
    1100: ("procurement_payables",),
    1103: ("configuration", "master_data"),
    600: ("inventory",),
    1200: ("inventory",),
    75000: ("inventory",),
    1250: ("sales",),
    400: ("sales",),
    10000: ("sales",),
    30000: ("sales",),
    15000000: ("accounting",),
    20000: ("receivables_treasury", "procurement_payables"),
    210: ("accounting",),
    800: ("inventory", "accounting"),
    8500: ("accounting",),
    200: ("procurement_payables", "accounting"),
    3000: ("sales",),
    80000: ("reporting_documents", "receivables_treasury", "procurement_payables"),
    900: ("configuration",),
    9500: ("reporting_documents",),
    50000: ("reporting_documents",),
    60000: ("integration_migration", "sales"),
    110000: ("integration_migration", "sales"),
    120000: ("sales", "master_data"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    routes = _load(args.routes)
    crosswalk = _load(args.crosswalk)
    blueprint = _load(args.blueprint)
    binary_inventory = _load(args.binary_inventory)
    by_id = {row["menu_id"]: row for row in routes["routes"]}
    cross_by_id = {row["menu_id"]: row for row in crosswalk["crosswalk"]}
    module_ids = {row["id"] for row in blueprint["modules"]}
    runtime_names = {row["name"].casefold() for row in binary_inventory["files"]}
    runtime_stems = {
        name[:-4] if name.endswith((".dll", ".exe")) else name
        for name in runtime_names
    }
    child_counts = Counter(row["parent_menu_id"] for row in routes["routes"])

    def safe_value(record: dict[str, Any] | None) -> str | None:
        if not record:
            return None
        value = record.get("value")
        return value if isinstance(value, str) else None

    def references_present_runtime(value: str | None) -> bool:
        if not value:
            return False
        lowered = value.casefold()
        return lowered in runtime_names or any(
            lowered == stem or lowered.startswith(stem + ".")
            for stem in runtime_stems
        )

    def route_classification(route: dict[str, Any], matched: dict[str, Any]) -> str:
        if matched["matched_form_type"] is not None:
            return "RUNTIME_FORM_MATCHED"
        if route["form_info_id"] is None:
            return "NAVIGATION_ONLY_NO_FORM_CONFIG"
        if child_counts[route["menu_id"]]:
            return "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL"
        file_value = safe_value(route["file_name"])
        class_value = safe_value(route["class_name"])
        if (file_value or "").upper() == "NULL" or (class_value or "").upper() == "NULL":
            return "CONFIGURED_LEAF_NULL_OR_PLACEHOLDER_TARGET"
        if references_present_runtime(file_value) or references_present_runtime(class_value):
            return "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED"
        if file_value is None and class_value is None:
            return "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW"
        return "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT"

    orphan_parent_ids: set[int] = set()
    cycle_menu_ids: set[int] = set()

    def lineage(menu_id: int) -> list[int]:
        result = []
        seen = set()
        current = menu_id
        while current in by_id:
            if current in seen:
                cycle_menu_ids.update(seen)
                break
            seen.add(current)
            result.append(current)
            parent = by_id[current]["parent_menu_id"]
            if parent is None:
                break
            if parent not in by_id:
                orphan_parent_ids.add(parent)
                break
            current = parent
        return list(reversed(result))

    rows = []
    root_counts: Counter[int] = Counter()
    module_hint_counts: Counter[str] = Counter()
    matched_domain_counts: Counter[str] = Counter()
    route_classification_counts: Counter[str] = Counter()
    for route in routes["routes"]:
        chain = lineage(route["menu_id"])
        root_id = chain[0]
        root_counts[root_id] += 1
        matched = cross_by_id[route["menu_id"]]
        section_hints = list(ROOT_MODULE_HINTS.get(root_id, ()))
        domain_hints = list(DOMAIN_TO_MODULES.get(matched["matched_primary_domain_id"], ()))
        effective = sorted(set(section_hints) | set(domain_hints))
        classification = route_classification(route, matched)
        route_classification_counts[classification] += 1
        module_hint_counts.update(effective)
        matched_domain_counts.update(domain_hints)
        rows.append(
            {
                "menu_id": route["menu_id"],
                "parent_menu_id": route["parent_menu_id"],
                "root_menu_id": root_id,
                "hierarchy_depth": len(chain) - 1,
                "menu_caption": route["menu_caption"],
                "menu_kind": route["menu_kind"],
                "menu_is_show": route["menu_is_show"],
                "is_show_in_container": route["is_show_in_container"],
                "is_action_menu": route["is_action_menu"],
                "form_info_id": route["form_info_id"],
                "access_node_id": route["access_node_id"],
                "show_modal": route["show_modal"],
                "matched_form_type": matched["matched_form_type"],
                "matched_primary_domain_id": matched["matched_primary_domain_id"],
                "match_quality": matched["match_quality"],
                "route_runtime_coverage_classification": classification,
                "root_section_module_hints": section_hints,
                "matched_form_domain_module_hints": domain_hints,
                "effective_module_hints_not_final_ownership": effective,
            }
        )

    root_rows = []
    for root_id in sorted(root_counts):
        route = by_id[root_id]
        subtree = [row for row in rows if row["root_menu_id"] == root_id]
        root_rows.append(
            {
                "root_menu_id": root_id,
                "caption": route["menu_caption"],
                "class_name": route["class_name"],
                "access_node_key": route["access_node_key"],
                "module_hints_not_final_ownership": list(ROOT_MODULE_HINTS.get(root_id, ())),
                "route_count_including_root": len(subtree),
                "configured_form_route_count": sum(row["form_info_id"] is not None for row in subtree),
                "runtime_matched_form_count": sum(row["matched_form_type"] is not None for row in subtree),
                "container_visible_config_count": sum(row["is_show_in_container"] == 1 for row in subtree),
                "access_node_route_count": sum(row["access_node_id"] is not None for row in subtree),
                "action_menu_count": sum(bool(row["is_action_menu"]) for row in subtree),
                "maximum_depth": max(row["hierarchy_depth"] for row in subtree),
                "runtime_coverage_classification_counts": dict(sorted(Counter(row["route_runtime_coverage_classification"] for row in subtree).items())),
            }
        )

    errors = []
    if len(by_id) != routes["summary"]["route_row_count"]:
        errors.append("duplicate menu id")
    if set(ROOT_MODULE_HINTS) != set(root_counts):
        errors.append("root mapping coverage mismatch")
    unknown_modules = {module for values in ROOT_MODULE_HINTS.values() for module in values} - module_ids
    if unknown_modules:
        errors.append("unknown module hints")
    if orphan_parent_ids:
        errors.append("orphan parent menu ids")
    if cycle_menu_ids:
        errors.append("menu cycles")
    if set(by_id) != set(cross_by_id):
        errors.append("route/crosswalk menu id mismatch")
    if sum(route_classification_counts.values()) != len(rows):
        errors.append("route classification coverage mismatch")

    artifact = {
        "artifact": "varanegar_complete_navigation_tree_target_module_hint_map",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_NAVIGATION_DERIVATION_FROM_REDACTED_STATIC_ROUTE_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "user_or_group_rights_read": 0,
            "business_rows_or_values_persisted": 0,
        },
        "summary": {
            "route_count": len(rows),
            "root_section_count": len(root_rows),
            "configured_form_route_count": sum(row["form_info_id"] is not None for row in rows),
            "runtime_matched_form_count": sum(row["matched_form_type"] is not None for row in rows),
            "runtime_matched_form_with_primary_domain_count": sum(row["matched_primary_domain_id"] is not None for row in rows),
            "container_visible_config_count": sum(row["is_show_in_container"] == 1 for row in rows),
            "route_with_access_node_count": sum(row["access_node_id"] is not None for row in rows),
            "action_menu_count": sum(bool(row["is_action_menu"]) for row in rows),
            "modal_route_count": sum(bool(row["show_modal"]) for row in rows),
            "maximum_hierarchy_depth": max(row["hierarchy_depth"] for row in rows),
            "orphan_parent_count": len(orphan_parent_ids),
            "cycle_menu_count": len(cycle_menu_ids),
            "module_hint_assignment_count": sum(module_hint_counts.values()),
            "matched_domain_module_assignment_count": sum(matched_domain_counts.values()),
            "validation_error_count": len(errors),
        },
        "route_runtime_coverage_classification_counts": dict(sorted(route_classification_counts.items())),
        "module_hint_route_counts": dict(sorted(module_hint_counts.items())),
        "matched_domain_module_route_counts": dict(sorted(matched_domain_counts.items())),
        "root_sections": root_rows,
        "routes": rows,
        "open_form_routes": crosswalk["open_form_routes"],
        "limits": [
            "Root-section module hints describe navigation grouping and are not final aggregate ownership.",
            "The catalog is global static configuration, not the effective menu of any signed-in user.",
            "Unmatched runtime forms and routes can reflect legacy, external, disabled or dynamically loaded components.",
            "Visible configuration does not authorize a query or command; server-side capability and scope checks remain mandatory.",
        ],
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
