"""Map strong static field/property matches to read-only clone column candidates."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


MAX_COLUMNS_PER_PROPERTY = 50


def _split_property(call: str) -> tuple[str, str]:
    marker = call.rfind(".get_")
    marker = marker if marker >= 0 else call.rfind(".set_")
    if marker < 0:
        return call.rsplit(".", 1)[0], call.rsplit(".", 1)[-1]
    return call[:marker], call[marker + 5:]


def _entity_term(type_name: str) -> str:
    short = type_name.rsplit(".", 1)[-1]
    for suffix in ("EntityHelper", "DataAdapter", "Adapter", "Handler", "Entity"):
        if short.endswith(suffix) and len(short) > len(suffix):
            return short[: -len(suffix)]
    return short


def _normalized(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field-bindings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    bindings = json.loads(args.field_bindings.read_text(encoding="utf-8-sig"))
    strong_fields = []
    property_calls: dict[str, dict[str, str]] = {}
    for form in bindings["forms"]:
        for field in form["fields"]:
            if field["binding_candidate_status"] != "STRONG_NAME_AND_METHOD_COOCCURRENCE_CANDIDATE":
                continue
            strong_fields.append((form["form_type"], field))
            for call in field["strong_name_property_calls"]:
                type_name, property_name = _split_property(call)
                property_calls[call] = {"target_type": type_name, "property_name": property_name, "entity_term": _entity_term(type_name)}

    candidates_by_call: dict[str, list[dict[str, Any]]] = {}
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for call, contract in sorted(property_calls.items()):
                rows = _rows(
                    cursor,
                    """
                    SELECT TOP (200) s.name AS schema_name,o.name AS object_name,o.type,o.type_desc,
                           c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type,
                           c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed,
                           CASE WHEN pk.column_id IS NULL THEN 0 ELSE 1 END AS is_pk,
                           COALESCE(fko.outgoing_fk_count,0) AS outgoing_fk_count,
                           COALESCE(fki.incoming_fk_count,0) AS incoming_fk_count
                    FROM sys.columns c
                    JOIN sys.objects o ON o.object_id=c.object_id
                    JOIN sys.schemas s ON s.schema_id=o.schema_id
                    LEFT JOIN (
                        SELECT ic.object_id,ic.column_id FROM sys.indexes i
                        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                        WHERE i.is_primary_key=1
                    ) pk ON pk.object_id=c.object_id AND pk.column_id=c.column_id
                    LEFT JOIN (
                        SELECT parent_object_id AS object_id,parent_column_id AS column_id,COUNT(*) AS outgoing_fk_count
                        FROM sys.foreign_key_columns GROUP BY parent_object_id,parent_column_id
                    ) fko ON fko.object_id=c.object_id AND fko.column_id=c.column_id
                    LEFT JOIN (
                        SELECT referenced_object_id AS object_id,referenced_column_id AS column_id,COUNT(*) AS incoming_fk_count
                        FROM sys.foreign_key_columns GROUP BY referenced_object_id,referenced_column_id
                    ) fki ON fki.object_id=c.object_id AND fki.column_id=c.column_id
                    WHERE o.is_ms_shipped=0 AND o.type IN ('U','V') AND LOWER(c.name)=LOWER(%s)
                    ORDER BY CASE WHEN LOWER(o.name)=LOWER(%s) THEN 0
                                  WHEN LOWER(o.name) LIKE LOWER(%s) THEN 1 ELSE 2 END,
                             s.name,o.name,c.column_id
                    """,
                    (contract["property_name"], contract["entity_term"], f"%{contract['entity_term']}%"),
                )
                persisted = []
                for row in rows[:MAX_COLUMNS_PER_PROPERTY]:
                    object_name = f"{row['schema_name']}.{row['object_name']}"
                    object_norm = _normalized(row["object_name"])
                    entity_norm = _normalized(contract["entity_term"])
                    strength = "ENTITY_OBJECT_EXACT_AND_COLUMN_EXACT" if object_norm == entity_norm else "ENTITY_OBJECT_CONTAINS_AND_COLUMN_EXACT" if entity_norm and entity_norm in object_norm else "COLUMN_EXACT_ONLY"
                    persisted.append({
                        "object": object_name,
                        "object_type": str(row["type"]).strip(),
                        "object_type_desc": row["type_desc"],
                        "column": row["column_name"],
                        "data_type": row["data_type"],
                        "max_length": int(row["max_length"]),
                        "precision": int(row["precision"]),
                        "scale": int(row["scale"]),
                        "is_nullable": bool(row["is_nullable"]),
                        "is_identity": bool(row["is_identity"]),
                        "is_computed": bool(row["is_computed"]),
                        "is_primary_key": bool(row["is_pk"]),
                        "outgoing_fk_count": int(row["outgoing_fk_count"]),
                        "incoming_fk_count": int(row["incoming_fk_count"]),
                        "match_strength": strength,
                    })
                candidates_by_call[call] = persisted

    fields = []
    unique_columns: dict[tuple[str, str], dict[str, Any]] = {}
    for form_type, field in strong_fields:
        property_rows = []
        for call in field["strong_name_property_calls"]:
            contract = property_calls[call]
            candidates = candidates_by_call[call]
            for candidate in candidates:
                unique_columns[(candidate["object"], candidate["column"])] = candidate
            property_rows.append({
                "property_call": call,
                **contract,
                "candidate_column_count": len(candidates),
                "candidate_columns": [f"{row['object']}.{row['column']}" for row in candidates],
                "candidate_column_details": candidates,
                "stronger_entity_object_candidate_count": sum(row["match_strength"] != "COLUMN_EXACT_ONLY" for row in candidates),
                "exact_entity_object_candidate_count": sum(row["match_strength"] == "ENTITY_OBJECT_EXACT_AND_COLUMN_EXACT" for row in candidates),
                "truncated_at_cap": len(candidates) == MAX_COLUMNS_PER_PROPERTY,
                "link_status": "STATIC_COLUMN_CANDIDATES_ONLY" if candidates else "NO_EXACT_COLUMN_NAME_MATCH",
            })
        fields.append({
            "form_type": form_type,
            "field_name": field["field_name"],
            "clr_field_type": field["clr_field_type"],
            "property_candidates": property_rows,
            "field_has_column_candidate": any(row["candidate_column_count"] for row in property_rows),
            "field_has_stronger_entity_object_candidate": any(row["stronger_entity_object_candidate_count"] for row in property_rows),
            "runtime_binding_or_source_column_proven": False,
        })

    strength_counts = Counter(row["match_strength"] for row in unique_columns.values())
    errors = []
    if bindings.get("validation") != "PASS":
        errors.append("field binding source not PASS")
    artifact = {
        "artifact": "varanegar_data_entry_field_property_to_clone_column_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE", "max_columns_per_property": MAX_COLUMNS_PER_PROPERTY},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_COLUMN_KEY_AND_TYPE_METADATA_ONLY",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_module_definitions_or_string_literals_read_or_persisted": 0,
            "credentials_identities_grants_or_secrets_persisted": 0,
            "procedures_functions_views_triggers_or_application_commands_executed": 0,
            "live_ui_actions": 0,
            "runtime_binding_or_source_column_inferred_as_proven": 0,
        },
        "summary": {
            "strong_static_field_count": len(fields),
            "unique_property_call_count": len(property_calls),
            "property_call_with_column_candidate_count": sum(bool(rows) for rows in candidates_by_call.values()),
            "property_call_without_column_candidate_count": sum(not rows for rows in candidates_by_call.values()),
            "property_call_with_exact_entity_object_candidate_count": sum(
                any(row["match_strength"] == "ENTITY_OBJECT_EXACT_AND_COLUMN_EXACT" for row in rows)
                for rows in candidates_by_call.values()
            ),
            "field_with_column_candidate_count": sum(row["field_has_column_candidate"] for row in fields),
            "field_with_stronger_entity_object_candidate_count": sum(row["field_has_stronger_entity_object_candidate"] for row in fields),
            "unique_candidate_column_count": len(unique_columns),
            "candidate_match_strength_counts": dict(sorted(strength_counts.items())),
            "property_candidate_truncated_at_cap_count": sum(len(rows) == MAX_COLUMNS_PER_PROPERTY for rows in candidates_by_call.values()),
            "runtime_binding_or_source_column_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "fields": sorted(fields, key=lambda row: (row["form_type"], row["field_name"])),
        "columns": sorted(unique_columns.values(), key=lambda row: (row["object"], row["column"])),
        "validation_errors": errors,
        "limits": [
            "Exact column names can occur in many unrelated tables and views.",
            "Entity/type name correspondence increases confidence but is not an ORM or runtime binding proof.",
            "The read-only clone can be stale and no business rows or report/application commands were executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
