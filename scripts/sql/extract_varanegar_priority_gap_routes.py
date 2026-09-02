"""Resolve static FormInfo/Menu/AccessNode routes for seven priority form gaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _rows


TARGET_CLASSES = (
    "frmBankReconciliation",
    "frmBankReconciliationList",
    "frmChek",
    "frmList",
    "frmReconciliation",
    "frmReconciliationSetup",
    "FormSpecialOptionsDistrict",
)
SAFE_CODE = re.compile(r"^[A-Za-z0-9_.+\-]{1,240}$")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("cp1256")
    return str(value)


def _safe(value: Any, *, caption: bool = False) -> dict[str, Any] | None:
    if value is None:
        return None
    value = _text(value).strip()
    allowed = (
        0 < len(value) <= 120
        and "\n" not in value
        and "\r" not in value
        and "@" not in value
        and "\\" not in value
        and (caption or bool(SAFE_CODE.fullmatch(value)))
    )
    row: dict[str, Any] = {
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "length": len(value),
        "persisted_as": "safe_static_caption" if caption and allowed else "safe_code" if allowed else "fingerprint_only",
    }
    if allowed:
        row["value"] = value
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    placeholders = ",".join("%s" for _ in TARGET_CLASSES)
    query = f"""
        SELECT f.FormInfoId form_info_id,f.ClassName class_name,f.FileName file_name,
               f.AccessNodeId access_node_id,f.ShowModal show_modal,
               a.ParentId access_parent_id,a.AccessNodeKey access_node_key,
               a.IsShow access_is_show,a.LevelOfNode access_level,
               m.ID menu_id,m.MenuRef parent_menu_id,m.Caption menu_caption,
               m.IsShow menu_is_show,m.IsShowInContainer is_show_in_container,
               m.Kind menu_kind,m.IsActionMenu is_action_menu
        FROM dbo.tblFormInfo f
        LEFT JOIN dbo.AccessNode a ON a.AccessNodeId=f.AccessNodeId
        LEFT JOIN GNR.tblMenuConfig m ON m.FormInfoId=f.FormInfoId
        WHERE f.ClassName IN ({placeholders})
           OR f.ClassName LIKE '%%Reconciliation%%'
           OR f.ClassName LIKE '%%SpecialOptionsDistrict%%'
        ORDER BY f.ClassName,m.ID
    """
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            raw_rows = _rows(cursor, query, TARGET_CLASSES)

    rows = [
        {
            "form_info_id": row["form_info_id"],
            "class_name": _safe(row["class_name"]),
            "file_name": _safe(row["file_name"]),
            "access_node_id": row["access_node_id"],
            "show_modal": row["show_modal"],
            "access_parent_id": row["access_parent_id"],
            "access_node_key": _safe(row["access_node_key"]),
            "access_is_show": row["access_is_show"],
            "access_level": row["access_level"],
            "menu_id": row["menu_id"],
            "parent_menu_id": row["parent_menu_id"],
            "menu_caption": _safe(row["menu_caption"], caption=True),
            "menu_is_show": row["menu_is_show"],
            "is_show_in_container": row["is_show_in_container"],
            "menu_kind": row["menu_kind"],
            "is_action_menu": row["is_action_menu"],
        }
        for row in raw_rows
    ]
    matched_values = {
        row["class_name"].get("value")
        for row in rows
        if row["class_name"] and row["class_name"].get("value")
    }
    artifact = {
        "artifact": "varanegar_priority_form_gap_static_route_evidence",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_STATIC_CONFIGURATION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "user_or_group_right_rows_read": 0,
            "user_identities_persisted": 0,
            "operational_business_rows_read": 0,
            "write_statements_executed": 0,
            "credentials_persisted": 0,
        },
        "summary": {
            "target_class_count": len(TARGET_CLASSES),
            "matched_static_row_count": len(rows),
            "matched_distinct_class_count": len(matched_values),
            "row_with_menu_route_count": sum(row["menu_id"] is not None for row in rows),
            "row_with_container_visible_route_count": sum(row["is_show_in_container"] == 1 for row in rows),
            "row_with_access_node_count": sum(row["access_node_id"] is not None for row in rows),
        },
        "target_classes": list(TARGET_CLASSES),
        "matched_class_names": sorted(matched_values),
        "rows": rows,
        "limits": [
            "Only static FormInfo/Menu/AccessNode configuration is read; no user/group rights or business rows are read.",
            "A missing FormInfo/menu row does not prove a dead form; parent constructor, reflection or legacy launchers remain possible.",
            "Configured AccessNode does not prove effective permission for any user.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
