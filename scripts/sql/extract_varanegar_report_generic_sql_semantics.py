"""Extract redacted metadata semantics for unique generic-report SQL candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


OPERATION_PATTERNS = {
    "select": re.compile(r"\bselect\b", re.IGNORECASE),
    "insert": re.compile(r"\binsert\b", re.IGNORECASE),
    "update": re.compile(r"\bupdate\b", re.IGNORECASE),
    "delete": re.compile(r"\bdelete\b", re.IGNORECASE),
    "merge": re.compile(r"\bmerge\b", re.IGNORECASE),
    "execute": re.compile(r"\bexec(?:ute)?\b", re.IGNORECASE),
    "dynamic_sql": re.compile(r"\bsp_executesql\b|\bexec\s*\(", re.IGNORECASE),
    "transaction": re.compile(r"\bbegin\s+tran(?:saction)?\b|\bcommit\b|\brollback\b", re.IGNORECASE),
}
IDENTIFIER = r"(?:[#@]\w+|\[[^\]]+\]|\w+)(?:\.(?:\[[^\]]+\]|\w+)){0,2}"
MUTATION_TARGET_PATTERNS = {
    "insert": re.compile(rf"\binsert\s+(?:into\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "update": re.compile(rf"\bupdate\s+(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "delete": re.compile(rf"\bdelete\s+(?:from\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "merge": re.compile(rf"\bmerge\s+(?:into\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
}


def _clean_identifier(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generic-candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    candidates = _load(args.generic_candidates)
    unique_terms = [row for row in candidates["term_coverage"] if row["candidate_count"] == 1 and not row["truncated_at_per_term_cap"]]
    selected_objects = sorted({row["candidate_objects"][0] for row in unique_terms})
    terms_by_object: dict[str, list[str]] = defaultdict(list)
    for row in unique_terms:
        terms_by_object[row["candidate_objects"][0]].append(row["term"])

    modules = []
    lookup_failures: list[str] = []
    result_shape_failures: list[dict[str, str]] = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for full_name in selected_objects:
                schema_name, object_name = full_name.split(".", 1)
                rows = _rows(
                    cursor,
                    """
                    SELECT o.object_id,o.type,o.type_desc,m.definition
                    FROM sys.objects o
                    JOIN sys.schemas s ON s.schema_id=o.schema_id
                    LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                    WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                    """,
                    (schema_name, object_name),
                )
                if len(rows) != 1:
                    lookup_failures.append(full_name)
                    continue
                row = rows[0]
                object_id = int(row["object_id"])
                definition = row["definition"] or ""
                operation_counts = {name: len(pattern.findall(definition)) for name, pattern in OPERATION_PATTERNS.items()}
                mutation_target_classes = Counter()
                durable_mutation_targets: set[str] = set()
                for pattern in MUTATION_TARGET_PATTERNS.values():
                    for match in pattern.finditer(definition):
                        raw_target = _clean_identifier(match.group("target"))
                        if raw_target.startswith(("#", "@")):
                            mutation_target_classes["TEMP_OR_TABLE_VARIABLE"] += 1
                            continue
                        resolved = _rows(
                            cursor,
                            """
                            SELECT OBJECT_SCHEMA_NAME(OBJECT_ID(%s)) AS schema_name,
                                   OBJECT_NAME(OBJECT_ID(%s)) AS object_name
                            """,
                            (raw_target, raw_target),
                        )[0]
                        if resolved["schema_name"] and resolved["object_name"]:
                            mutation_target_classes["CATALOG_RESOLVED_DURABLE"] += 1
                            durable_mutation_targets.add(f"{resolved['schema_name']}.{resolved['object_name']}")
                        else:
                            mutation_target_classes["UNRESOLVED_IDENTIFIER_OR_ALIAS"] += 1
                parameters = _rows(
                    cursor,
                    """
                    SELECT p.parameter_id,p.name,TYPE_NAME(p.user_type_id) AS data_type,
                           p.max_length,p.precision,p.scale,p.is_output
                    FROM sys.parameters p WHERE p.object_id=%s ORDER BY p.parameter_id
                    """,
                    (object_id,),
                )
                dependencies = _rows(
                    cursor,
                    """
                    SELECT DISTINCT COALESCE(d.referenced_schema_name,'?') AS schema_name,
                           COALESCE(d.referenced_entity_name,'?') AS entity_name,
                           d.referenced_class_desc
                    FROM sys.sql_expression_dependencies d
                    WHERE d.referencing_id=%s
                    ORDER BY schema_name,entity_name,referenced_class_desc
                    """,
                    (object_id,),
                )
                result_columns: list[dict[str, Any]] = []
                result_shape_status = "NO_DESCRIBED_RESULT_COLUMNS"
                try:
                    described = _rows(
                        cursor,
                        """
                        SELECT column_ordinal,name,system_type_name,is_nullable,error_type_desc
                        FROM sys.dm_exec_describe_first_result_set_for_object(%s,0)
                        ORDER BY column_ordinal
                        """,
                        (object_id,),
                    )
                    error_types = sorted({str(item["error_type_desc"]) for item in described if item.get("error_type_desc")})
                    result_columns = [
                        {
                            "ordinal": int(item["column_ordinal"]),
                            "name": item["name"],
                            "system_type_name": item["system_type_name"],
                            "is_nullable": None if item["is_nullable"] is None else bool(item["is_nullable"]),
                        }
                        for item in described
                        if item.get("column_ordinal") is not None and not item.get("error_type_desc")
                    ]
                    result_shape_status = "DESCRIBED" if result_columns else "METADATA_ERROR_TYPE" if error_types else result_shape_status
                    if error_types:
                        result_shape_failures.append({"object": full_name, "error_class": ",".join(error_types)})
                except Exception as exc:
                    result_shape_status = "METADATA_QUERY_EXCEPTION"
                    result_shape_failures.append({"object": full_name, "error_class": type(exc).__name__})

                report_shells = sorted(
                    report["report_shell_type"]
                    for report in candidates["reports"]
                    if full_name in report["candidate_objects"]
                )
                modules.append({
                    "object": full_name,
                    "type": str(row["type"]).strip(),
                    "type_desc": row["type_desc"],
                    "candidate_terms": sorted(terms_by_object[full_name]),
                    "candidate_report_shells": report_shells,
                    "definition_length": len(definition),
                    "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest() if definition else None,
                    "definition_persisted": False,
                    "operation_token_counts": operation_counts,
                    "mutation_token_count": sum(operation_counts[name] for name in ("insert", "update", "delete", "merge")),
                    "mutation_target_class_counts": dict(sorted(mutation_target_classes.items())),
                    "durable_mutation_targets": sorted(durable_mutation_targets),
                    "parameters": [
                        {
                            "ordinal": int(item["parameter_id"]),
                            "name": item["name"],
                            "data_type": item["data_type"],
                            "max_length": int(item["max_length"]),
                            "precision": int(item["precision"]),
                            "scale": int(item["scale"]),
                            "is_output": bool(item["is_output"]),
                        }
                        for item in parameters
                    ],
                    "dependencies": [
                        {
                            "object": f"{item['schema_name']}.{item['entity_name']}",
                            "referenced_class_desc": item["referenced_class_desc"],
                        }
                        for item in dependencies
                    ],
                    "result_shape_status": result_shape_status,
                    "result_columns": result_columns,
                    "execution_or_result_parity_proven": False,
                })

    errors = []
    if candidates.get("validation") != "PASS":
        errors.append("generic candidate input is not PASS")
    if lookup_failures:
        errors.append("selected catalog candidates could not be resolved uniquely")
    operation_totals = Counter()
    for module in modules:
        operation_totals.update(module["operation_token_counts"])
    artifact = {
        "artifact": "varanegar_unique_generic_report_sql_redacted_semantic_footprints",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_AND_RESULT_METADATA_WITH_TRANSIENT_DEFINITION_SCAN",
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
            "unique_single_candidate_term_count": len(unique_terms),
            "selected_module_count": len(modules),
            "stored_procedure_count": sum(row["type"] == "P" for row in modules),
            "view_count": sum(row["type"] == "V" for row in modules),
            "parameter_count": sum(len(row["parameters"]) for row in modules),
            "dependency_count": sum(len(row["dependencies"]) for row in modules),
            "described_result_column_count": sum(len(row["result_columns"]) for row in modules),
            "module_with_described_result_count": sum(row["result_shape_status"] == "DESCRIBED" for row in modules),
            "result_shape_metadata_failure_count": len(result_shape_failures),
            "operation_token_counts": dict(sorted(operation_totals.items())),
            "module_with_mutation_token_count": sum(row["mutation_token_count"] > 0 for row in modules),
            "module_with_catalog_resolved_durable_mutation_target_count": sum(bool(row["durable_mutation_targets"]) for row in modules),
            "catalog_resolved_durable_mutation_target_count": len({target for row in modules for target in row["durable_mutation_targets"]}),
            "definition_persisted_count": 0,
            "execution_or_result_parity_proven_count": 0,
            "lookup_failure_count": len(lookup_failures),
            "validation_error_count": len(errors),
        },
        "modules": modules,
        "result_shape_failures": result_shape_failures,
        "lookup_failures": lookup_failures,
        "validation_errors": errors,
        "limits": [
            "Unique name correspondence is still a candidate link, not runtime execution proof.",
            "Token counts are lexical and can include dead branches, comments or dynamic SQL fragments.",
            "Result metadata describes compilable first-result shape only and does not prove values or parity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
