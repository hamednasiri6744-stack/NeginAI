"""Find clone SQL catalog candidates for statically traced report DataAccess types."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


IGNORED_SHORT_NAMES = {
    "DBConnector",
    "DataContext",
    "Transaction",
    "ApplicationSession",
    "DC",
}
MAX_CANDIDATES_PER_TERM = 40


def _normalized(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _term_from_type(type_name: str) -> str | None:
    short = type_name.rsplit(".", 1)[-1]
    if short.startswith("<") or short in IGNORED_SHORT_NAMES:
        return None
    for suffix in ("DataAdapter", "Adapter"):
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break
    return short if len(short) >= 4 else None


def _term_from_member(member: str) -> str | None:
    cleaned = re.sub(r"^(?:get_|Get)", "", member)
    if len(cleaned) < 6:
        return None
    signals = ("Report", "Cardex", "Statement", "SaleNumbers", "TblExit", "DistRef", "AreaNames")
    return cleaned if any(signal.casefold() in cleaned.casefold() for signal in signals) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    graph = json.loads(args.report_graph.read_text(encoding="utf-8-sig"))

    report_terms: dict[str, list[str]] = {}
    report_type_terms: dict[str, list[str]] = {}
    report_member_terms: dict[str, list[str]] = {}
    for report in graph["reports"]:
        types = set(report["direct_ui_to_data_access_types"]) | set(report["business_to_data_access_types"])
        type_terms = sorted({term for type_name in types if (term := _term_from_type(type_name))})
        business_types = set(report["ui_to_business_types"])
        members = [
            edge["called_member"]
            for edge in graph["business_to_data_access_edges"]
            if edge["source_business_type"] in business_types
        ] + [
            edge["called_member"]
            for edge in graph["ui_first_party_edges"]
            if edge["source_report_type"] == report["report_type"] and edge["target_layer"] == "data_access"
        ]
        member_terms = sorted({term for member in members if (term := _term_from_member(member))})
        terms = sorted(set(type_terms) | set(member_terms))
        report_terms[report["report_type"]] = terms
        report_type_terms[report["report_type"]] = type_terms
        report_member_terms[report["report_type"]] = member_terms
    unique_terms = sorted({term for terms in report_terms.values() for term in terms})

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            matches_by_term: dict[str, list[dict[str, Any]]] = {}
            all_objects: dict[int, dict[str, Any]] = {}
            for term in unique_terms:
                rows = _rows(
                    cursor,
                    """
                    SELECT TOP (200) o.object_id,s.name AS schema_name,o.name AS object_name,
                           o.type,o.type_desc,m.definition
                    FROM sys.objects o
                    JOIN sys.schemas s ON s.schema_id=o.schema_id
                    LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                    WHERE o.is_ms_shipped=0 AND o.name LIKE %s
                      AND o.type IN ('U','V','P','FN','IF','TF','TR')
                    ORDER BY CASE WHEN LOWER(o.name)=LOWER(%s) THEN 0 ELSE 1 END,
                             LEN(o.name),s.name,o.name,o.type
                    """,
                    (f"%{term}%", term),
                )
                persisted = []
                for row in rows[:MAX_CANDIDATES_PER_TERM]:
                    object_id = int(row["object_id"])
                    definition = row.pop("definition") or ""
                    row["type"] = str(row["type"]).strip()
                    record = {
                        "object_id": object_id,
                        "object": f"{row['schema_name']}.{row['object_name']}",
                        "type": row["type"],
                        "type_desc": row["type_desc"],
                        "definition_length": len(definition),
                        "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest() if definition else None,
                        "definition_persisted": False,
                        "match_strength": "EXACT_NORMALIZED_NAME" if _normalized(row["object_name"]) == _normalized(term) else "NAME_CONTAINS_TERM",
                    }
                    all_objects[object_id] = record
                    persisted.append(record)
                matches_by_term[term] = persisted

            object_ids = list(all_objects)
            metadata_by_id: dict[int, dict[str, int]] = {object_id: {"column_count": 0, "parameter_count": 0, "dependency_count": 0, "trigger_count": 0} for object_id in object_ids}
            if object_ids:
                marks = ",".join("%s" for _ in object_ids)
                for row in _rows(cursor, f"SELECT object_id,COUNT(*) AS n FROM sys.columns WHERE object_id IN ({marks}) GROUP BY object_id", tuple(object_ids)):
                    metadata_by_id[int(row["object_id"])]["column_count"] = int(row["n"])
                for row in _rows(cursor, f"SELECT object_id,COUNT(*) AS n FROM sys.parameters WHERE object_id IN ({marks}) GROUP BY object_id", tuple(object_ids)):
                    metadata_by_id[int(row["object_id"])]["parameter_count"] = int(row["n"])
                for row in _rows(cursor, f"SELECT referencing_id AS object_id,COUNT(*) AS n FROM sys.sql_expression_dependencies WHERE referencing_id IN ({marks}) GROUP BY referencing_id", tuple(object_ids)):
                    metadata_by_id[int(row["object_id"])]["dependency_count"] = int(row["n"])
                for row in _rows(cursor, f"SELECT parent_id AS object_id,COUNT(*) AS n FROM sys.triggers WHERE parent_id IN ({marks}) GROUP BY parent_id", tuple(object_ids)):
                    metadata_by_id[int(row["object_id"])]["trigger_count"] = int(row["n"])

    objects = []
    object_by_id = {}
    for object_id, record in sorted(all_objects.items(), key=lambda item: (item[1]["object"], item[1]["type"])):
        merged = {**record, **metadata_by_id[object_id]}
        object_by_id[object_id] = merged
        objects.append({key: value for key, value in merged.items() if key != "object_id"})

    term_coverage = []
    for term in unique_terms:
        matches = matches_by_term[term]
        term_coverage.append(
            {
                "term": term,
                "candidate_count": len(matches),
                "candidate_objects": [row["object"] for row in matches],
                "truncated_at_per_term_cap": len(matches) == MAX_CANDIDATES_PER_TERM,
                "status": "CATALOG_CANDIDATES_FOUND" if matches else "NO_NAME_MATCH",
            }
        )

    reports = []
    for report_type, terms in report_terms.items():
        candidates = sorted({row["object"] for term in terms for row in matches_by_term.get(term, [])})
        reports.append(
            {
                "report_type": report_type,
                "data_access_search_terms": terms,
                "data_access_type_terms": report_type_terms[report_type],
                "called_member_terms": report_member_terms[report_type],
                "candidate_object_count": len(candidates),
                "candidate_objects": candidates,
                "link_status": "NAME_CANDIDATES_ONLY_NOT_EXECUTION_PROOF" if candidates else "NO_NAME_MATCH_REQUIRES_DEEPER_TRACE",
            }
        )

    errors = []
    if graph.get("validation") != "PASS":
        errors.append("report dependency graph not PASS")
    artifact = {
        "artifact": "varanegar_report_clone_sql_catalog_name_candidate_surface",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE", "max_candidates_per_term": MAX_CANDIDATES_PER_TERM},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_METADATA_AND_DEFINITION_FINGERPRINTS_ONLY",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_or_string_literals_persisted": 0,
            "credentials_identity_grants_or_secrets_persisted": 0,
            "procedures_functions_views_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": {
            "report_surface_count": len(reports),
            "data_access_search_term_count": len(unique_terms),
            "term_with_candidate_count": sum(bool(row["candidate_count"]) for row in term_coverage),
            "term_without_candidate_count": sum(not row["candidate_count"] for row in term_coverage),
            "term_truncated_at_cap_count": sum(row["truncated_at_per_term_cap"] for row in term_coverage),
            "unique_candidate_object_count": len(objects),
            "candidate_table_count": sum(row["type"] == "U" for row in objects),
            "candidate_module_count": sum(row["type"] != "U" for row in objects),
            "report_with_candidate_count": sum(bool(row["candidate_object_count"]) for row in reports),
            "report_without_candidate_count": sum(not row["candidate_object_count"] for row in reports),
            "definition_persisted_count": 0,
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "term_coverage": term_coverage,
        "reports": reports,
        "objects": objects,
        "validation_errors": errors,
        "limits": [
            "Object-name matching yields candidates, not a proven DataAccess-to-SQL execution path.",
            "The read-only clone can lag operational Varanegar and contains no proof of report result parity.",
            "Dynamic SQL, report engines, inheritance and caller-provided datasets can hide actual SQL objects.",
            "Candidate lists are capped per search term and cap status remains explicit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
