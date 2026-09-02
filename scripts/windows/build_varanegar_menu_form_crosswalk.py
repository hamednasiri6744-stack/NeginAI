"""Crosswalk static menu routes, runtime form types, and open UI titles."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _value(record: dict[str, Any]) -> str:
    return str(record.get("value") or "")


def _normalize_persian(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .replace("‌", "")
        .strip()
        .casefold(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", required=True, type=Path)
    parser.add_argument("--forms", required=True, type=Path)
    parser.add_argument("--ui", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    routes = _load(args.routes)
    forms = _load(args.forms)
    ui = _load(args.ui)
    by_full = {row["type"]: row for row in forms["forms"]}
    by_simple: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in forms["forms"]:
        by_simple[row["type"].rsplit(".", 1)[-1]].append(row)

    crosswalk = []
    for route in routes["routes"]:
        file_name = _value(route["file_name"])
        class_name = _value(route["class_name"])
        matched = None
        quality = "unmatched"
        if file_name in by_full:
            matched = by_full[file_name]
            quality = "exact_route_target_type"
        elif class_name in by_full:
            matched = by_full[class_name]
            quality = "exact_class_type"
        elif class_name and len(by_simple.get(class_name, [])) == 1:
            matched = by_simple[class_name][0]
            quality = "unique_simple_class_name"
        crosswalk.append(
            {
                "menu_id": route["menu_id"],
                "parent_menu_id": route["parent_menu_id"],
                "menu_caption": route["menu_caption"],
                "is_show_in_container": route["is_show_in_container"],
                "menu_kind": route["menu_kind"],
                "form_info_id": route["form_info_id"],
                "access_node_id": route["access_node_id"],
                "access_node_key": route["access_node_key"],
                "show_modal": route["show_modal"],
                "matched_form_type": matched["type"] if matched else None,
                "matched_form_family": matched["family"] if matched else None,
                "matched_primary_domain_id": matched["primary_domain_id"] if matched else None,
                "matched_page_shape": matched["page_shape"] if matched else None,
                "match_quality": quality,
            }
        )

    caption_routes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in crosswalk:
        caption = _value(row["menu_caption"])
        if caption:
            caption_routes[_normalize_persian(caption)].append(row)
    main_title = max(
        ui["safe_named_controls"], key=lambda row: len(row["safe_label"])
    )["safe_label"]
    open_titles = sorted(
        {
            row["safe_label"]
            for row in ui["safe_named_controls"]
            if row["control_type"] == "ControlType.Window"
            and row["safe_label"] != main_title
        }
    )
    open_routes = []
    for title in open_titles:
        matches = caption_routes.get(_normalize_persian(title), [])
        open_routes.append(
            {
                "ui_title": title,
                "route_match_count": len(matches),
                "routes": [
                    {
                        "menu_id": row["menu_id"],
                        "access_node_id": row["access_node_id"],
                        "access_node_key": row["access_node_key"],
                        "matched_form_type": row["matched_form_type"],
                        "match_quality": row["match_quality"],
                    }
                    for row in matches
                ],
            }
        )

    artifact = {
        "artifact": "varanegar_menu_form_runtime_crosswalk",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {
            "routes": args.routes.as_posix(),
            "forms": args.forms.as_posix(),
            "ui": args.ui.as_posix(),
        },
        "safety": {
            "mode": "DERIVED_FROM_READ_ONLY_REDACTED_EVIDENCE",
            "live_ui_actions": 0,
            "database_queries_executed_by_builder": 0,
            "user_or_group_rights_read": 0,
            "operational_business_rows_read_or_persisted": 0,
        },
        "summary": {
            "route_count": len(crosswalk),
            "route_with_form_config_count": sum(row["form_info_id"] is not None for row in crosswalk),
            "matched_runtime_form_count": sum(row["matched_form_type"] is not None for row in crosswalk),
            "container_configured_route_count": sum(row["is_show_in_container"] == 1 for row in crosswalk),
            "open_window_count": len(open_routes),
            "open_window_with_unique_route_count": sum(row["route_match_count"] == 1 for row in open_routes),
            "match_quality_counts": dict(sorted(Counter(row["match_quality"] for row in crosswalk).items())),
        },
        "limits": [
            "Configured menu visibility is not effective user authorization.",
            "Open-form matching uses normalized static captions and does not inspect row values.",
            "A route target proves the configured class; runtime redirection would require separate evidence.",
        ],
        "open_form_routes": open_routes,
        "crosswalk": crosswalk,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
