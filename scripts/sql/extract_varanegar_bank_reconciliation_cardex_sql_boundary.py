"""Extract the catalog and IL boundary for reconciliation cardex posting.

The extractor deliberately persists only an allowlisted stored-command name,
parameter names/types, and SQL Server catalog dependencies. It never reads a
module definition, business row, connection-string value, or executes the
legacy command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_targeted_il_contracts import _full_type_name  # noqa: E402
from extract_varanegar_org_domain import (  # noqa: E402
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


ASSEMBLY = "TreasuryOld.DataAccess.dll"
ADAPTER_TYPE = "TreasuryOld.DataLayer.ReconcileAdapter"
INITIALIZER = "InitCommandCollection"
COMMAND = "DoReconcile_UpdateBankAccountCardex"
COMMAND_PATTERN = re.compile(r"^(?:dbo\.)?DoReconcile_UpdateBankAccountCardex$", re.I)
PARAMETER_PATTERN = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{0,127}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _allowlisted_il_boundary(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    type_row = next(
        row
        for row in pe.net.mdtables.TypeDef.rows
        if _full_type_name(row) == ADAPTER_TYPE
    )
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None
        and index.row.Rva
        and str(index.row.Name) == INITIALIZER
    )
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
    command_names: set[str] = set()
    parameter_names: set[str] = set()
    omitted_literal_count = 0
    for instruction in body.instructions:
        if not isinstance(instruction.operand, StringToken):
            continue
        item = pe.net.user_strings.get(instruction.operand.rid)
        value = "" if item is None else str(item)
        if COMMAND_PATTERN.fullmatch(value):
            command_names.add(value)
        elif PARAMETER_PATTERN.fullmatch(value):
            parameter_names.add(value)
        else:
            omitted_literal_count += 1
    return {
        "assembly": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "type": ADAPTER_TYPE,
        "method": INITIALIZER,
        "instruction_count": len(body.instructions),
        "allowlisted_command_names": sorted(command_names),
        "allowlisted_parameter_name_count": len(parameter_names),
        "target_parameter_name_observed": "@ReconcileId" in parameter_names,
        "non_allowlisted_literal_value_count": omitted_literal_count,
        "non_allowlisted_literal_values_persisted_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    expected_hash = {row["name"]: row["sha256"] for row in inventory["files"]}
    assembly_path = args.source_directory / ASSEMBLY
    il_boundary = _allowlisted_il_boundary(assembly_path)
    hash_mismatch = il_boundary["sha256"] != expected_hash.get(ASSEMBLY)

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            objects = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name,o.type,o.type_desc,
                       o.create_date,o.modify_date
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                """,
                ("dbo", COMMAND),
            )
            object_id = int(objects[0]["object_id"]) if objects else -1
            parameters = [] if object_id < 0 else _rows(
                cursor,
                """
                SELECT parameter_id,name,TYPE_NAME(user_type_id) AS data_type,
                       max_length,precision,scale,is_output
                FROM sys.parameters
                WHERE object_id=%s
                ORDER BY parameter_id
                """,
                (object_id,),
            )
            dependencies = [] if object_id < 0 else _rows(
                cursor,
                """
                SELECT DISTINCT
                       COALESCE(rs.name+'.','')+COALESCE(ro.name,d.referenced_entity_name)
                           AS referenced_object,
                       ro.type_desc AS referenced_type_desc,
                       d.is_ambiguous
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects ro ON ro.object_id=d.referenced_id
                LEFT JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
                WHERE d.referencing_id=%s
                ORDER BY referenced_object
                """,
                (object_id,),
            )

    object_rows = [
        {
            "object": f"{row['schema_name']}.{row['name']}",
            "object_type": str(row["type"]).strip(),
            "object_type_desc": row["type_desc"],
            "create_date": row["create_date"],
            "modify_date": row["modify_date"],
        }
        for row in objects
    ]
    parameter_rows = [
        {
            "ordinal": int(row["parameter_id"]),
            "name": row["name"],
            "data_type": row["data_type"],
            "max_length": int(row["max_length"]),
            "precision": int(row["precision"]),
            "scale": int(row["scale"]),
            "is_output": bool(row["is_output"]),
        }
        for row in parameters
    ]
    dependency_rows = [
        {
            "referenced_object": row["referenced_object"],
            "referenced_type_desc": row["referenced_type_desc"],
            "is_ambiguous": bool(row["is_ambiguous"]),
        }
        for row in dependencies
    ]

    errors: list[str] = []
    if hash_mismatch:
        errors.append("source package hash mismatch")
    if il_boundary["allowlisted_command_names"] != [COMMAND]:
        errors.append("target command literal missing or changed")
    if not il_boundary["target_parameter_name_observed"]:
        errors.append("target ReconcileId parameter name not observed")
    if len(object_rows) != 1 or object_rows[0]["object_type"] not in {"P", "PC"}:
        errors.append("target catalog procedure missing or changed")
    if not any(row["name"] == "@ReconcileId" for row in parameter_rows):
        errors.append("catalog ReconcileId parameter missing")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_cardex_sql_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_ALLOWLISTED_IL_LITERAL_AND_SQL_SYSTEM_CATALOG_METADATA",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "module_definitions_read_or_persisted": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "connection_string_values_read_or_persisted": 0,
            "procedures_functions_triggers_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "allowlisted_il_command_count": len(il_boundary["allowlisted_command_names"]),
            "catalog_object_count": len(object_rows),
            "catalog_parameter_count": len(parameter_rows),
            "catalog_dependency_count": len(dependency_rows),
            "source_hash_mismatch_count": int(hash_mismatch),
            "validation_error_count": len(errors),
        },
        "il_boundary": il_boundary,
        "catalog_objects": object_rows,
        "catalog_parameters": parameter_rows,
        "catalog_dependencies": dependency_rows,
        "target_contract": {
            "legacy_command": "dbo.DoReconcile_UpdateBankAccountCardex",
            "target_command": "bank_reconciliation.confirm",
            "direct_web_execution_of_legacy_procedure_allowed": False,
            "application_service_owns_transaction": True,
            "repository_accepts_typed_reconcile_id_only": True,
            "procedure_text_or_dynamic_sql_exposed_to_client": False,
            "dependency_effects_require_post_commit_parity_checks": True,
        },
        "validation_errors": errors,
        "limits": [
            "Catalog dependencies show declared references, not every dynamic runtime branch.",
            "Module definitions and business rows were intentionally not read.",
            "No legacy procedure, command, application form, or transaction was executed.",
            "Clone metadata does not prove parity with the live operational database.",
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
