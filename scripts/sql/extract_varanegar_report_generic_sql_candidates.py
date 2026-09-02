"""Find read-only clone SQL name candidates for generic report bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


MAX_CANDIDATES_PER_TERM = 50


def _normalized(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _type_terms(type_name: str) -> set[str]:
    short = type_name.rsplit(".", 1)[-1]
    terms = {short}
    for suffix in ("EntityHelper", "Handler", "Validator"):
        if short.endswith(suffix):
            terms.add(short[: -len(suffix)])
    if short.endswith("ViewEntityHelper"):
        terms.add(short[: -len("ViewEntityHelper")])
        terms.add(short[: -len("EntityHelper")])
    if short.startswith("ChartReport") and len(short) > len("ChartReport") + 3:
        terms.add(short[len("ChartReport"):])
    return {term for term in terms if len(term) >= 5}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generic-bindings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    bindings = json.loads(args.generic_bindings.read_text(encoding="utf-8-sig"))

    report_terms: dict[str, list[str]] = {}
    caller_by_shell = {row["report_shell_type"]: row["caller_types"] for row in bindings["reports"]}
    caller_contracts = {row["caller_type"]: row for row in bindings["caller_contracts"]}
    for report in bindings["reports"]:
        terms: set[str] = set()
        for type_name in report["entity_helper_types"] + report["business_handler_types"] + caller_by_shell[report["report_shell_type"]]:
            terms.update(_type_terms(type_name))
        report_terms[report["report_shell_type"]] = sorted(terms)
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
                    record = {
                        "object_id": object_id,
                        "object": f"{row['schema_name']}.{row['object_name']}",
                        "type": str(row["type"]).strip(),
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
            metadata_by_id: dict[int, dict[str, int]] = {
                object_id: {"column_count": 0, "parameter_count": 0, "dependency_count": 0, "trigger_count": 0}
                for object_id in object_ids
            }
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
    for object_id, record in sorted(all_objects.items(), key=lambda item: (item[1]["object"], item[1]["type"])):
        objects.append({key: value for key, value in {**record, **metadata_by_id[object_id]}.items() if key != "object_id"})
    term_coverage = [
        {
            "term": term,
            "candidate_count": len(matches_by_term[term]),
            "candidate_objects": [row["object"] for row in matches_by_term[term]],
            "truncated_at_per_term_cap": len(matches_by_term[term]) == MAX_CANDIDATES_PER_TERM,
            "status": "CATALOG_CANDIDATES_FOUND" if matches_by_term[term] else "NO_NAME_MATCH",
        }
        for term in unique_terms
    ]
    reports = []
    for report_type, terms in report_terms.items():
        candidates = sorted({row["object"] for term in terms for row in matches_by_term[term]})
        reports.append({
            "report_shell_type": report_type,
            "generic_binding_search_terms": terms,
            "candidate_object_count": len(candidates),
            "candidate_objects": candidates,
            "link_status": "GENERIC_BINDING_NAME_CANDIDATES_ONLY" if candidates else "NO_GENERIC_BINDING_NAME_MATCH",
            "sql_identity_or_execution_proven": False,
        })
    errors = []
    if bindings.get("validation") != "PASS":
        errors.append("generic bindings input is not PASS")
    artifact = {
        "artifact": "varanegar_generic_report_binding_clone_sql_name_candidates",
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
            "report_shell_count": len(reports),
            "generic_binding_search_term_count": len(unique_terms),
            "term_with_candidate_count": sum(bool(row["candidate_count"]) for row in term_coverage),
            "term_without_candidate_count": sum(not row["candidate_count"] for row in term_coverage),
            "term_truncated_at_cap_count": sum(row["truncated_at_per_term_cap"] for row in term_coverage),
            "unique_candidate_object_count": len(objects),
            "candidate_table_count": sum(row["type"] == "U" for row in objects),
            "candidate_module_count": sum(row["type"] != "U" for row in objects),
            "report_shell_with_candidate_count": sum(bool(row["candidate_object_count"]) for row in reports),
            "report_shell_without_candidate_count": sum(not row["candidate_object_count"] for row in reports),
            "definition_persisted_count": 0,
            "sql_identity_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "term_coverage": term_coverage,
        "reports": reports,
        "objects": objects,
        "validation_errors": errors,
        "limits": [
            "Entity-helper, handler and caller-name matching produces candidates only.",
            "Generic dispatch still hides concrete adapter and parameter binding.",
            "Candidate lists are capped per term; no SQL module or report was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
