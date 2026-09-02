"""Correlate the empty SpecialOptionsDistrict form with clone catalog metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


TARGET = "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict"
CATALOG_PATTERNS = (
    "%specialoption%",
    "%districtoption%",
    "%specialdistrict%",
    "%districtspecial%",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _form_candidate(assembly_contracts: dict[str, Any]) -> dict[str, Any]:
    for assembly in assembly_contracts.get("assemblies", []):
        for form in assembly.get("form_candidates", []):
            if form.get("type") == TARGET:
                return form
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly-contracts", required=True, type=Path)
    parser.add_argument("--priority-routes", required=True, type=Path)
    parser.add_argument("--call-graph", required=True, type=Path)
    parser.add_argument("--root-entrypoints", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    assembly_contracts = _load(args.assembly_contracts)
    priority_routes = _load(args.priority_routes)
    call_graph = _load(args.call_graph)
    root_entrypoints = _load(args.root_entrypoints)
    declared_fields = _load(args.declared_fields)

    form = _form_candidate(assembly_contracts)
    call_contract = next(
        (row for row in call_graph.get("priority_form_contracts", []) if row.get("type") == TARGET),
        {},
    )
    call_resolution = next(
        (row for row in call_graph.get("resolutions", []) if row.get("type") == TARGET),
        {},
    )
    root_resolution = next(
        (row for row in root_entrypoints.get("resolutions", []) if row.get("type") == TARGET),
        {},
    )
    declared = next(
        (row for row in declared_fields.get("forms", []) if row.get("form_type") == TARGET),
        {},
    )

    object_predicate = " OR ".join("LOWER(o.name) LIKE %s" for _ in CATALOG_PATTERNS)
    column_predicate = " OR ".join(
        [*("LOWER(o.name) LIKE %s" for _ in CATALOG_PATTERNS),
         *("LOWER(c.name) LIKE %s" for _ in CATALOG_PATTERNS)]
    )
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            objects = _rows(
                cursor,
                f"""
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,o.type_desc,
                       SUM(CASE WHEN o.type='U' AND p.index_id IN (0,1) THEN p.rows ELSE 0 END) AS row_count_metadata
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.partitions p ON p.object_id=o.object_id
                WHERE o.is_ms_shipped=0 AND ({object_predicate})
                GROUP BY o.object_id,s.name,o.name,o.type_desc
                ORDER BY s.name,o.name
                """,
                CATALOG_PATTERNS,
            )
            columns = _rows(
                cursor,
                f"""
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,o.type_desc,
                       c.column_id,c.name AS column_name,t.name AS data_type,c.is_nullable
                FROM sys.columns c
                JOIN sys.objects o ON o.object_id=c.object_id
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                JOIN sys.types t ON t.user_type_id=c.user_type_id
                WHERE o.is_ms_shipped=0 AND ({column_predicate})
                ORDER BY s.name,o.name,c.column_id
                """,
                CATALOG_PATTERNS + CATALOG_PATTERNS,
            )

    object_by_id = {int(row["object_id"]): row for row in objects}
    for row in columns:
        object_by_id.setdefault(
            int(row["object_id"]),
            {
                "object_id": row["object_id"],
                "schema_name": row["schema_name"],
                "object_name": row["object_name"],
                "type_desc": row["type_desc"],
                "row_count_metadata": None,
            },
        )

    catalog_candidates = []
    for object_id, row in sorted(
        object_by_id.items(),
        key=lambda item: (item[1]["schema_name"].casefold(), item[1]["object_name"].casefold()),
    ):
        catalog_candidates.append(
            {
                "schema": row["schema_name"],
                "object": row["object_name"],
                "object_type": row["type_desc"],
                "row_count_metadata": (
                    None if row.get("row_count_metadata") is None else int(row["row_count_metadata"] or 0)
                ),
                "matching_columns": [
                    {
                        "ordinal": int(column["column_id"]),
                        "name": column["column_name"],
                        "data_type": column["data_type"],
                        "nullable": bool(column["is_nullable"]),
                    }
                    for column in columns
                    if int(column["object_id"]) == object_id
                ],
            }
        )

    contract = call_contract.get("contract", {})
    external_reference_count = (
        int(root_resolution.get("constructor_entrypoint_count", 0))
        + int(root_resolution.get("exact_string_reference_count", 0))
    )
    errors = []
    if not form or not call_contract or not call_resolution or not root_resolution or not declared:
        errors.append("one or more required static evidence rows are missing")
    if priority_routes.get("summary", {}).get("matched_static_row_count", 0) != 0:
        errors.append("priority route evidence changed")
    if declared.get("declared_control_field_count") != 0:
        errors.append("derived form is no longer field-empty")
    if external_reference_count != 0:
        errors.append("external entrypoint evidence changed")

    artifact = {
        "artifact": "varanegar_special_options_district_static_and_clone_catalog_assessment",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_AND_OFFLINE_METADATA_CORRELATION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_or_trigger_definitions_persisted": 0,
            "assemblies_loaded_or_executed": 0,
            "procedures_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": {
            "form_method_count": int(form.get("method_count", 0)),
            "form_business_method_count": len(form.get("business_methods", [])),
            "direct_declared_field_count": int(declared.get("declared_control_field_count", 0)),
            "inherited_base_field_count": int(declared.get("inherited_base_field_count", 0)),
            "static_route_count": int(priority_routes.get("summary", {}).get("matched_static_row_count", 0)),
            "external_launcher_or_reference_count": external_reference_count,
            "clone_catalog_candidate_count": len(catalog_candidates),
            "clone_catalog_matching_column_count": len(columns),
            "validation_error_count": len(errors),
        },
        "static_evidence": {
            "form_type": TARGET,
            "base_type": form.get("base_type"),
            "methods": form.get("methods", []),
            "business_methods": form.get("business_methods", []),
            "first_party_external_calls": contract.get("first_party_external_calls", []),
            "call_graph_status": call_resolution.get("status"),
            "all_assembly_entrypoint_status": root_resolution.get("status"),
            "direct_declared_fields": declared.get("fields", []),
            "base_type_chain": declared.get("base_type_chain", []),
        },
        "catalog_patterns": list(CATALOG_PATTERNS),
        "clone_catalog_candidates": catalog_candidates,
        "assessment": {
            "classification": "PLACEHOLDER_OR_DYNAMIC_FEATURE_CANDIDATE_UNRESOLVED",
            "deletion_or_scope_exclusion_authorized": False,
            "target_schema_or_command_inference_allowed": False,
            "next_evidence_gate": "business owner confirmation or an observed runtime launcher/data-object binding in an isolated authenticated session",
        },
        "validation_errors": errors,
        "limits": [
            "Zero narrow English catalog-name candidates cannot rule out differently named or Persian configuration objects.",
            "No static route or external constructor does not prove that reflection, resources or runtime factories never open the form.",
            "Inherited framework fields are capabilities, not evidence of visible domain controls.",
            "No business rows, module definitions, DLLs, forms, commands, procedures or triggers were read or executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
