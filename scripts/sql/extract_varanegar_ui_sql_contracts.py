"""Map selected Varanegar UI commands to SQL contracts in the local clone.

The extractor is pinned to the local read-only ``NeginPakhsh_WebDev`` clone.
It persists object metadata, parameters, dependency names, and definition
fingerprints only. It never executes an application procedure or reads rows
from an operational business table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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


CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "object": "SLE.usp_sdsnet_CreateDist",
        "domain": 9,
        "ui_chain": ["FormDistManagementDataEntry.SaveCommand", "DistHandler.CreateDist"],
        "required": True,
    },
    {
        "object": "dbo.usp_CreateExitVocherByDist",
        "domain": 9,
        "ui_chain": ["FormDistManagementList.SetExitexportation", "DistHandler.CreateExitVocherByDist"],
        "required": True,
    },
    {
        "object": "inv.Usp_InsertGoodsExit_RD",
        "domain": 9,
        "ui_chain": ["FormDistManagementList.SetFreeDistribution", "DistHandler.MergeGoodsExit"],
        "required": True,
    },
    {
        "object": "inv.Usp_RemoveExitFromDist",
        "domain": 9,
        "ui_chain": ["FormDistManagementList.RemoveExitFromDist", "DistHandler.RemoveExitFromDist"],
        "required": True,
    },
    {
        "object": "dbo.GetMaxDistNo",
        "domain": 9,
        "ui_chain": ["FormDistManagementDataEntry.SaveCommand", "DistHandler.GetMaxDistNo"],
        "required": True,
    },
    {
        "object": "dbo.DoRCheque_AddRChequeHistory",
        "domain": 12,
        "ui_chain": ["frmRChequeTracking.DoChangeStatus", "RChequeAdapter.AddRChequeHistory"],
        "required": True,
    },
    {
        "object": "dbo.DoRCheque_DeleteLastRChequeHistory",
        "domain": 12,
        "ui_chain": ["frmRChequeTracking.DoUndo", "RChequeAdapter.DeleteLastRChequeHistory"],
        "required": True,
    },
    {
        "object": "dbo.RchequeWorkFlow_IsValid",
        "domain": 12,
        "ui_chain": ["frmRChequeTracking.DoChangeStatus"],
        "required": True,
    },
    {
        "object": "dbo.DoPCheque_AddPChequeHistory",
        "domain": 14,
        "ui_chain": ["frmPChequeTracking.btnChangeStatus_Click", "PChequeAdapter.AddPChequeHistory"],
        "required": True,
    },
    {
        "object": "dbo.DoPCheque_DeleteLastPChequeHistory",
        "domain": 14,
        "ui_chain": ["frmPChequeTracking.UndoStatus", "PChequeAdapter.DeleteLastPChequeHistory"],
        "required": True,
    },
    {
        "object": "dbo.PChequeWorkFlow_IsValid",
        "domain": 14,
        "ui_chain": ["frmPChequeTracking.btnChangeStatus_Click"],
        "required": True,
    },
    {
        "object": "GNR.vwStockGoods_serverMode",
        "domain": 8,
        "ui_chain": ["FormStockGoods.LoadInitData", "StockGoodsGridServerModeDC"],
        "required": True,
    },
)


def _object_contract(cursor: Any, item: dict[str, Any]) -> dict[str, Any]:
    identity = _rows(
        cursor,
        """
        SELECT o.object_id,s.name AS schema_name,o.name AS object_name,
               o.type_desc,o.create_date,o.modify_date,m.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE o.object_id=OBJECT_ID(%s)
        """,
        (item["object"],),
    )
    if not identity:
        return {**item, "found": False, "parameters": [], "dependencies": []}

    row = identity[0]
    object_id = row.pop("object_id")
    definition = row.pop("definition") or ""
    parameters = _rows(
        cursor,
        """
        SELECT p.parameter_id,p.name AS parameter_name,
               TYPE_NAME(p.user_type_id) AS data_type,p.max_length,
               p.precision,p.scale,p.is_output,p.has_default_value
        FROM sys.parameters p
        WHERE p.object_id=%s
        ORDER BY p.parameter_id
        """,
        (object_id,),
    )
    dependencies = _rows(
        cursor,
        """
        SELECT DISTINCT
               COALESCE(d.referenced_schema_name,OBJECT_SCHEMA_NAME(d.referenced_id)) AS schema_name,
               COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) AS object_name,
               COALESCE(o.type_desc,'UNRESOLVED_OR_COLUMN_REFERENCE') AS type_desc,
               d.is_schema_bound_reference
        FROM sys.sql_expression_dependencies d
        LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
        WHERE d.referencing_id=%s
          AND COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) IS NOT NULL
        ORDER BY schema_name,object_name,type_desc
        """,
        (object_id,),
    )
    return {
        **item,
        "found": True,
        **row,
        "definition_length": len(definition),
        "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
        "parameters": parameters,
        "dependencies": dependencies,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            contracts = [_object_contract(cursor, item) for item in CONTRACTS]

    missing_required = [
        row["object"] for row in contracts if row["required"] and not row["found"]
    ]
    artifact = {
        "artifact": "varanegar_ui_to_sql_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_METADATA",
            "database_updateability": context["updateability"],
            "can_select": context["can_select"],
            "can_view_definition": context["can_view_definition"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "application_procedures_executed": 0,
            "business_rows_read_or_persisted": 0,
            "raw_definitions_persisted": 0,
            "credentials_persisted": 0,
        },
        "summary": {
            "contract_count": len(contracts),
            "found_count": sum(row["found"] for row in contracts),
            "required_count": sum(row["required"] for row in contracts),
            "missing_required": missing_required,
        },
        "contracts": contracts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not missing_required else 1


if __name__ == "__main__":
    raise SystemExit(main())
