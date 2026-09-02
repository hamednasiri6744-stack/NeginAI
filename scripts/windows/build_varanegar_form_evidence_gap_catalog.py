"""Classify remaining evidence gaps across the complete Varanegar form catalog."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


CHILD_SHAPES = {"dialog", "selector", "dual_list_assignment", "data_entry", "master_detail_entry"}
MODULE_DOMAIN_CANDIDATES = {
    "MainData": ["organization/master_data/pricing/configuration"],
    "Sales": ["sales/returns/distribution"],
    "Stock": ["inventory/procurement"],
    "Treasury": ["treasury/accounting"],
    "TreasuryOld": ["receivables/payables/legacy_treasury"],
    "CreateVoucher": ["accounting"],
    "Setting": ["authorization/configuration/infrastructure"],
}
FRAMEWORK_OR_SYSTEM_SURFACE = re.compile(
    r"(?:ApplicationSessionForm|\.SampleForm\.|\.MainForm$|frmChangeControlSize$|"
    r"frmShowErrors$|frmReportPreview(?:MultiReport)?$|frmLogin$|frmLogOff$|"
    r"frmchangePwd$|FormZoomChart$|\.TestSaveMode\.)"
)
INTEGRATION_OR_COMPLIANCE_SURFACE = re.compile(r"(?:\.HIX\.|\.TTAC\.)")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form-catalog", required=True, type=Path)
    parser.add_argument("--all-form-calls", required=True, type=Path)
    parser.add_argument("--menu-crosswalk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    catalog = _load(args.form_catalog)
    calls = _load(args.all_form_calls)
    crosswalk = _load(args.menu_crosswalk)
    calls_by_type = {row["type"]: row for row in calls["forms"]}
    route_rows_by_type: dict[str, list[dict[str, Any]]] = {}
    for row in crosswalk["crosswalk"]:
        type_name = row.get("matched_form_type")
        if type_name:
            route_rows_by_type.setdefault(type_name, []).append(row)

    rows = []
    for form in catalog["forms"]:
        type_name = form["type"]
        call_row = calls_by_type.get(type_name)
        route_rows = route_rows_by_type.get(type_name, [])
        visible_routes = [row for row in route_rows if row["is_show_in_container"] == 1]
        hidden_routes = [row for row in route_rows if row["is_show_in_container"] != 1]
        called_modules = [] if call_row is None else call_row["contract"]["called_module_families"]
        direct_calls = [] if call_row is None else call_row["contract"]["first_party_external_calls"]
        write_like = [] if call_row is None else call_row["contract"]["write_like_methods"]
        permission_like = [] if call_row is None else call_row["contract"]["permission_methods"]
        if FRAMEWORK_OR_SYSTEM_SURFACE.search(type_name):
            surface_classification = "framework_or_system_shell"
        elif INTEGRATION_OR_COMPLIANCE_SURFACE.search(type_name):
            surface_classification = "integration_or_compliance_surface"
        else:
            surface_classification = "business_or_unclassified_surface"
        gaps = []
        actions = []
        if form["form_evidence_confidence"] != "high":
            gaps.append("medium_confidence_form_candidate")
            actions.append("confirm type/base/form identity from route, inheritance or resource metadata")
        if form["primary_domain_id"] is None:
            gaps.append("no_primary_domain_mapping")
            actions.append("map from owning aggregate, business/data-access calls and menu semantics")
        if call_row is not None and not direct_calls:
            gaps.append("no_direct_first_party_call")
            actions.append("trace base class, interface, reflection, ORM and event wiring")
        if not route_rows:
            route_class = (
                "unrouted_likely_child_surface"
                if form["page_shape"] in CHILD_SHAPES
                else "unrouted_surface_needs_entrypoint_review"
            )
            if route_class == "unrouted_surface_needs_entrypoint_review":
                gaps.append("no_direct_menu_route_for_non_child_shape")
                actions.append("find parent launcher, action-menu, modal or hidden feature route")
        elif visible_routes:
            route_class = "direct_visible_route"
        else:
            route_class = "direct_hidden_or_non_container_route"
        if write_like and not permission_like:
            gaps.append("write_like_without_local_permission_method")
            actions.append("prove inherited/menu/server authorization before classifying any command")

        if surface_classification == "framework_or_system_shell":
            priority = "low"
        elif surface_classification == "integration_or_compliance_surface":
            priority = "medium"
        elif "medium_confidence_form_candidate" in gaps:
            priority = "high"
        elif (
            "no_primary_domain_mapping" in gaps
            and (
                "no_direct_first_party_call" in gaps
                or "no_direct_menu_route_for_non_child_shape" in gaps
            )
        ):
            priority = "high"
        elif any(
            gap in gaps
            for gap in (
                "no_primary_domain_mapping",
                "no_direct_first_party_call",
                "no_direct_menu_route_for_non_child_shape",
            )
        ):
            priority = "medium"
        else:
            priority = "low"
        candidate_groups = sorted(
            {
                group
                for module in called_modules
                for group in MODULE_DOMAIN_CANDIDATES.get(module, [])
            }
        )
        if surface_classification == "framework_or_system_shell":
            candidate_groups = sorted(set(candidate_groups + ["platform/identity/reporting_shell"]))
        elif surface_classification == "integration_or_compliance_surface":
            candidate_groups = sorted(set(candidate_groups + ["integration/compliance"]))
        rows.append(
            {
                "assembly": form["assembly"],
                "type": type_name,
                "confidence": form["form_evidence_confidence"],
                "page_shape": form["page_shape"],
                "surface_classification": surface_classification,
                "primary_domain_id": form["primary_domain_id"],
                "domain_match_count": len(form["domain_matches"]),
                "called_module_families": called_modules,
                "candidate_domain_groups_not_a_mapping": candidate_groups,
                "direct_first_party_call_count": len(direct_calls),
                "write_like_method_count": len(write_like),
                "local_permission_method_count": len(permission_like),
                "route": {
                    "classification": route_class,
                    "route_count": len(route_rows),
                    "visible_route_count": len(visible_routes),
                    "hidden_or_non_container_route_count": len(hidden_routes),
                    "route_ids": sorted(row["menu_id"] for row in route_rows),
                },
                "gap_codes": gaps,
                "priority": priority,
                "next_evidence_actions": sorted(set(actions)),
            }
        )

    priority_counts = Counter(row["priority"] for row in rows)
    gap_counts = Counter(gap for row in rows for gap in row["gap_codes"])
    route_counts = Counter(row["route"]["classification"] for row in rows)
    surface_counts = Counter(row["surface_classification"] for row in rows)
    artifact = {
        "artifact": "varanegar_complete_form_evidence_gap_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_RUNTIME_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_rows_or_values_persisted": 0,
        },
        "summary": {
            "form_candidate_count": len(rows),
            "high_confidence_form_count": sum(row["confidence"] == "high" for row in rows),
            "medium_confidence_candidate_count": sum(row["confidence"] != "high" for row in rows),
            "unmapped_primary_domain_count": sum(row["primary_domain_id"] is None for row in rows),
            "high_confidence_unmapped_primary_domain_count": sum(row["primary_domain_id"] is None and row["confidence"] == "high" for row in rows),
            "high_confidence_without_direct_first_party_call_count": sum(row["confidence"] == "high" and row["direct_first_party_call_count"] == 0 for row in rows),
            "form_with_any_direct_route_count": sum(row["route"]["route_count"] > 0 for row in rows),
            "form_with_visible_direct_route_count": sum(row["route"]["visible_route_count"] > 0 for row in rows),
            "unrouted_likely_child_surface_count": sum(row["route"]["classification"] == "unrouted_likely_child_surface" for row in rows),
            "unrouted_non_child_shape_review_count": sum(row["route"]["classification"] == "unrouted_surface_needs_entrypoint_review" for row in rows),
            "write_like_without_local_permission_method_count": sum("write_like_without_local_permission_method" in row["gap_codes"] for row in rows),
            "priority_counts": dict(sorted(priority_counts.items())),
            "gap_counts": dict(sorted(gap_counts.items())),
            "route_classification_counts": dict(sorted(route_counts.items())),
            "surface_classification_counts": dict(sorted(surface_counts.items())),
        },
        "forms": sorted(rows, key=lambda row: ({"high": 0, "medium": 1, "low": 2}[row["priority"]], row["assembly"], row["type"])),
        "interpretation_rules": [
            "No direct route is expected for many child dialogs/selectors/data-entry forms and is not itself a defect.",
            "No local permission method does not prove missing authorization; inherited/menu/server checks remain possible.",
            "Candidate domain groups are routing hints, never final domain assignments.",
            "No direct call does not prove a dead form; base/interface/reflection/ORM/event paths remain possible.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
