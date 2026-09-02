"""Prioritize unmatched configured Varanegar routes for scope-freeze review."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


UNMATCHED_CONFIGURED_CLASSES = {
    "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL",
    "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED",
    "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT",
    "CONFIGURED_LEAF_NULL_OR_PLACEHOLDER_TARGET",
    "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _priority(route: dict[str, Any], raw: dict[str, Any]) -> tuple[str, list[str]]:
    classification = route["route_runtime_coverage_classification"]
    signals = []
    if route["is_show_in_container"] == 1:
        signals.append("container_visible_config")
    if route["menu_is_show"] == 1:
        signals.append("menu_is_show")
    if route["access_node_id"] is not None:
        signals.append("has_access_node")
    if raw["access_is_show"] is True:
        signals.append("access_node_is_show")
    if raw["is_action_menu"]:
        signals.append("action_menu")
    if raw["has_confirm"] == 1:
        signals.append("has_confirm")
    if raw["has_notify"] == 1:
        signals.append("has_notify")
    leaf_material = classification in {
        "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED",
        "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT",
        "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW",
    }
    material_signal = any(value in signals for value in (
        "container_visible_config", "menu_is_show", "access_node_is_show",
        "action_menu", "has_confirm", "has_notify",
    ))
    if leaf_material and material_signal:
        return "high", signals
    if leaf_material or (classification == "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL" and material_signal):
        return "medium", signals
    return "low", signals


def _next_evidence(classification: str) -> list[str]:
    return {
        "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL": [
            "review child-route semantics and whether shell survives as web navigation only",
            "do not implement a data-owning page from the shell name",
        ],
        "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED": [
            "resolve FormInfo class/file namespace against all TypeDefs and base/event launch paths",
            "confirm feature owner and acceptance behavior",
        ],
        "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT": [
            "obtain authorized deployment/plugin manifest or confirm retired integration",
            "confirm whether external capability is in target scope and who owns it",
        ],
        "CONFIGURED_LEAF_NULL_OR_PLACEHOLDER_TARGET": [
            "review versioned menu configuration and business-owner usage evidence",
            "retain placeholder status until owner disposition",
        ],
        "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW": [
            "perform controlled allowlist review of the static class/file target",
            "classify package and owner without persisting unsafe raw value",
        ],
    }[classification]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--navigation-map", required=True, type=Path)
    parser.add_argument("--routes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    navigation = _load(args.navigation_map)
    routes = _load(args.routes)
    raw_by_id = {row["menu_id"]: row for row in routes["routes"]}

    candidates = []
    for route in navigation["routes"]:
        classification = route["route_runtime_coverage_classification"]
        if classification not in UNMATCHED_CONFIGURED_CLASSES:
            continue
        raw = raw_by_id[route["menu_id"]]
        priority, signals = _priority(route, raw)
        candidates.append(
            {
                "menu_id": route["menu_id"],
                "parent_menu_id": route["parent_menu_id"],
                "root_menu_id": route["root_menu_id"],
                "hierarchy_depth": route["hierarchy_depth"],
                "menu_caption": route["menu_caption"],
                "class_name": raw["class_name"],
                "file_name": raw["file_name"],
                "access_node_key": raw["access_node_key"],
                "classification": classification,
                "priority": priority,
                "priority_signals": signals,
                "root_section_module_hints_not_final_ownership": route["root_section_module_hints"],
                "is_show_in_container": route["is_show_in_container"],
                "menu_is_show": route["menu_is_show"],
                "access_node_id": route["access_node_id"],
                "access_is_show": raw["access_is_show"],
                "show_modal": route["show_modal"],
                "is_action_menu": raw["is_action_menu"],
                "has_confirm": raw["has_confirm"],
                "has_notify": raw["has_notify"],
                "scope_disposition": "REVIEW_REQUIRED_NEVER_AUTO_RETIRED",
                "next_evidence": _next_evidence(classification),
            }
        )

    priority_counts = Counter(row["priority"] for row in candidates)
    classification_counts = Counter(row["classification"] for row in candidates)
    module_counts = Counter(
        module
        for row in candidates
        for module in row["root_section_module_hints_not_final_ownership"]
    )
    errors = []
    expected_count = sum(
        navigation["route_runtime_coverage_classification_counts"].get(name, 0)
        for name in UNMATCHED_CONFIGURED_CLASSES
    )
    if len(candidates) != expected_count:
        errors.append("candidate classification coverage mismatch")
    if set(raw_by_id) != {row["menu_id"] for row in navigation["routes"]}:
        errors.append("navigation/route id mismatch")
    if any(row["scope_disposition"] != "REVIEW_REQUIRED_NEVER_AUTO_RETIRED" for row in candidates):
        errors.append("unsafe automatic disposition")

    artifact = {
        "artifact": "varanegar_unmatched_configured_route_scope_freeze_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_SCOPE_REVIEW_FROM_REDACTED_STATIC_NAVIGATION_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "user_or_group_rights_read": 0,
            "routes_enabled_disabled_or_changed": 0,
            "raw_redacted_target_values_recovered_or_persisted": 0,
        },
        "summary": {
            "candidate_count": len(candidates),
            "shell_candidate_count": classification_counts["CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL"],
            "leaf_candidate_count": len(candidates) - classification_counts["CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL"],
            "priority_counts": dict(sorted(priority_counts.items())),
            "container_visible_candidate_count": sum(row["is_show_in_container"] == 1 for row in candidates),
            "candidate_with_access_node_count": sum(row["access_node_id"] is not None for row in candidates),
            "candidate_with_material_signal_count": sum(bool(set(row["priority_signals"]) & {"container_visible_config", "menu_is_show", "access_node_is_show", "action_menu", "has_confirm", "has_notify"}) for row in candidates),
            "auto_retired_count": 0,
            "validation_error_count": len(errors),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "root_module_hint_candidate_counts": dict(sorted(module_counts.items())),
        "priority_policy": {
            "high": "unmatched material leaf plus at least one visibility/action/confirm/notify signal",
            "medium": "unmatched material leaf without such signal, or a signaled navigation/selector shell",
            "low": "unsignaled shell or null/placeholder target",
            "disposition": "priority controls review order only; no candidate is automatically retained, implemented or retired",
        },
        "candidates": sorted(candidates, key=lambda row: ({"high": 0, "medium": 1, "low": 2}[row["priority"]], row["root_menu_id"], row["menu_id"])),
        "validation_errors": errors,
        "limits": [
            "Static visibility and AccessNode signals are not effective user permissions or usage evidence.",
            "External/absent-package is a deployment hint, not proof that a feature is unavailable.",
            "Scope freeze requires business-owner disposition and, where material, runtime or deployment evidence.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
