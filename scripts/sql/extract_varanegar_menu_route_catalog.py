"""Extract the Varanegar menu/form/access-node route catalog from the clone.

Only static application configuration is read. User identities, user/group
rights, URLs, credentials, and operational business rows are excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
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


def _safe_code(value: Any) -> dict[str, Any]:
    text = _text(value).strip()
    record: dict[str, Any] = {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "length": len(text),
        "persisted_as": "safe_code" if CODE_TEXT.fullmatch(text) else "fingerprint_only",
    }
    if record["persisted_as"] == "safe_code":
        record["value"] = text
    return record


def _safe_caption(value: Any) -> dict[str, Any]:
    text = _text(value).strip()
    is_safe = (
        0 < len(text) <= 120
        and "\n" not in text
        and "\r" not in text
        and "@" not in text
        and "\\" not in text
        and "http://" not in text.casefold()
        and "https://" not in text.casefold()
    )
    record: dict[str, Any] = {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "length": len(text),
        "persisted_as": "safe_static_caption" if is_safe else "fingerprint_only",
    }
    if is_safe:
        record["value"] = text
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            counts = _rows(
                cursor,
                """
                SELECT 'GNR.tblMenuConfig' object_name,COUNT_BIG(*) row_count FROM GNR.tblMenuConfig
                UNION ALL
                SELECT 'dbo.tblFormInfo',COUNT_BIG(*) FROM dbo.tblFormInfo
                UNION ALL
                SELECT 'dbo.AccessNode',COUNT_BIG(*) FROM dbo.AccessNode
                """,
            )
            raw_rows = _rows(
                cursor,
                """
                SELECT m.ID menu_id,m.MenuRef parent_menu_id,m.Caption menu_caption,
                       m.ItemOrder item_order,m.IsShow menu_is_show,m.Kind menu_kind,
                       m.FormInfoId form_info_id,m.IsShowInContainer is_show_in_container,
                       m.IsShowInFararu is_show_in_fararu,m.VNLite vn_lite,
                       m.HasConfirm has_confirm,m.HasNotify has_notify,
                       m.IsActionMenu is_action_menu,
                       f.ClassName class_name,f.FileName file_name,
                       f.ResourceId resource_id,f.OpenReason open_reason,
                       f.AccessNodeId access_node_id,f.ShowModal show_modal,
                       a.ParentId access_parent_id,a.AccessNodeKey access_node_key,
                       a.IsShow access_is_show,a.LevelOfNode access_level,
                       a.IsUsedInSDS is_used_in_sds,a.IsUsedInFRU is_used_in_fru
                FROM GNR.tblMenuConfig m
                LEFT JOIN dbo.tblFormInfo f ON f.FormInfoId=m.FormInfoId
                LEFT JOIN dbo.AccessNode a ON a.AccessNodeId=f.AccessNodeId
                ORDER BY m.MenuRef,m.ItemOrder,m.ID
                """,
            )

    routes = []
    for row in raw_rows:
        routes.append(
            {
                "menu_id": row["menu_id"],
                "parent_menu_id": row["parent_menu_id"],
                "menu_caption": _safe_caption(row["menu_caption"]),
                "item_order": row["item_order"],
                "menu_is_show": row["menu_is_show"],
                "menu_kind": row["menu_kind"],
                "form_info_id": row["form_info_id"],
                "is_show_in_container": row["is_show_in_container"],
                "is_show_in_fararu": row["is_show_in_fararu"],
                "vn_lite": row["vn_lite"],
                "has_confirm": row["has_confirm"],
                "has_notify": row["has_notify"],
                "is_action_menu": row["is_action_menu"],
                "class_name": _safe_code(row["class_name"]),
                "file_name": _safe_code(row["file_name"]),
                "resource_id": row["resource_id"],
                "open_reason": row["open_reason"],
                "access_node_id": row["access_node_id"],
                "show_modal": row["show_modal"],
                "access_parent_id": row["access_parent_id"],
                "access_node_key": _safe_code(row["access_node_key"]),
                "access_is_show": row["access_is_show"],
                "access_level": row["access_level"],
                "is_used_in_sds": row["is_used_in_sds"],
                "is_used_in_fru": row["is_used_in_fru"],
            }
        )

    artifact = {
        "artifact": "varanegar_static_menu_form_access_route_catalog",
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
            "urls_read_or_persisted": 0,
            "operational_business_rows_read": 0,
            "write_statements_executed": 0,
            "credentials_persisted": 0,
        },
        "summary": {
            "source_row_counts": {row["object_name"]: row["row_count"] for row in counts},
            "route_row_count": len(routes),
            "route_with_form_count": sum(row["form_info_id"] is not None for row in routes),
            "container_visible_config_count": sum(row["is_show_in_container"] == 1 for row in routes),
            "action_menu_count": sum(row["is_action_menu"] == 1 for row in routes),
            "modal_route_count": sum(row["show_modal"] == 1 for row in routes),
            "route_with_access_node_count": sum(row["access_node_id"] is not None for row in routes),
            "menu_kind_counts": dict(sorted(Counter(str(row["menu_kind"]) for row in routes).items())),
        },
        "limits": [
            "This is the global configured route catalog, not the effective menu of the current signed-in user.",
            "HasAccess requires user/group rights and runtime feature locks, neither is inferred from a configured route.",
            "URLs are deliberately not read or persisted.",
        ],
        "routes": routes,
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
