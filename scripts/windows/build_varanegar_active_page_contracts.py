"""Build active-page field/filter/validation contracts from redacted evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PAGE_SPECS: dict[str, dict[str, Any]] = {
    "received_cheque_tracking": {
        "route_node": 42,
        "active_type": "TreasuryOld.Forms.frmRChequeTracking",
        "types": (
            "TreasuryOld.Forms.frmRChequeTracking",
            "TreasuryOld.DataLayer.RChequeAdapter",
        ),
        "sql_objects": (
            "dbo.DoRCheque_AddRChequeHistory",
            "dbo.DoRCheque_DeleteLastRChequeHistory",
            "dbo.RchequeWorkFlow_IsValid",
        ),
        "capability_prefix": "received_cheque.",
        "work_queue": "RChequeStatusId in (1,2,4,8,9), then receipt/DC/sale-office filters",
        "write_boundary": "ChangeStatus appends history and advances current state; Undo removes only the permitted last history transition.",
    },
    "payable_cheque_tracking": {
        "route_node": 43,
        "active_type": "TreasuryOld.Forms.frmPChequeTracking",
        "types": (
            "TreasuryOld.Forms.frmPChequeTracking",
            "TreasuryOld.DataLayer.PChequeAdapter",
        ),
        "sql_objects": (
            "dbo.DoPCheque_AddPChequeHistory",
            "dbo.DoPCheque_DeleteLastPChequeHistory",
            "dbo.PChequeWorkFlow_IsValid",
        ),
        "capability_prefix": "payable_cheque.",
        "work_queue": "PChequeStatusId in (1,5), then DC/sale-office filters",
        "write_boundary": "ChangeStatus appends history and advances current state; Undo validates leaf/pay/balance/current-pointer constraints.",
    },
    "stock_goods": {
        "route_node": 109,
        "active_type": "VN.SDS.Stock.UI.StockGoods.FormStockGoods",
        "types": (
            "VN.SDS.Stock.UI.StockGoods.FormStockGoods",
            "VN.SDS.Stock.UI.StockGoods.FormStockGoodsDataEntry",
            "VN.SDS.Stock.UI.StockGoods.FormStockGoodsEdit",
            "VN.SDS.Stock.Business.StockGoods.StockGoodsHandler",
            "VN.SDS.Stock.Business.StockGoods.StockGoodsValidator",
            "VN.SDS.Stock.DataAccess.DataAdapter.StockGoods.StockGoodsAdapter",
        ),
        "sql_objects": ("GNR.vwStockGoods_serverMode",),
        "capability_prefix": "inventory.stock_goods.",
        "work_queue": "Server-mode stock-goods projection scoped by AccYear/DC/StockDCRef",
        "write_boundary": "Stock assignment/edit/delete is guarded by goods status, batch mode, open order/sale/flow and stock-use validation.",
    },
    "distribution_management": {
        "route_node": 412,
        "active_type": "VN.SDS.Sales.UI.DistManagement.FormDistManagementList",
        "types": (
            "VN.SDS.Sales.UI.DistManagement.FormDistManagementList",
            "VN.SDS.Sales.UI.DistManagement.FormDistManagementDataEntry",
            "VN.SDS.Sales.UI.DistManagement.FormFactorSelection",
            "VN.SDS.Sales.UI.DistManagement.FormFollowDist",
            "VN.SDS.Sales.UI.DistManagement.FormOrderToDist",
            "VN.SDS.Sales.UI.DistManagement.FormExitExportationDataEntry",
            "VN.SDS.Sales.UI.DistManagement.FormRemoveExitFromDistReason",
            "VN.SDS.Sales.UI.DistManagement.FormChangeBatchNo",
            "VN.SDS.Sales.Business.Dist.DistHandler",
            "VN.SDS.Sales.Business.Dist.DistValidator",
            "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter",
        ),
        "sql_objects": (
            "SLE.usp_sdsnet_CreateDist",
            "dbo.usp_CreateExitVocherByDist",
            "inv.Usp_InsertGoodsExit_RD",
            "inv.Usp_RemoveExitFromDist",
            "dbo.GetMaxDistNo",
        ),
        "capability_prefix": "distribution.",
        "work_queue": "Master distribution list with status/where/sort plus detail SaleS; scoped by AccYear/DC/user context",
        "write_boundary": "Create, follow, reverse, exit, remove-exit and free/merge are separate stateful operations with distinct guards.",
    },
}


FRAMEWORK_PROPERTIES = {
    "Appearance", "AutoScaleDimensions", "AutoScaleMode", "BackColor", "Caption",
    "Checked", "ClientSize", "Columns", "Controls", "Count", "Current", "Data",
    "DataObject", "DataSource", "DialogResult", "Dock", "EditValue", "Enabled",
    "Errors", "ErrorMessage", "FetchReason", "FocusedRowHandle", "Font", "FormTitle",
    "HasValue", "ID", "IsClosed", "IsValid", "Item", "Items", "Location", "Message",
    "Name", "NullText", "OpenType", "Options", "Panel1", "Panel2", "Properties",
    "Rows", "RowCount", "Size", "Status", "TabIndex", "Text", "Value", "Visible",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _targets(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        target["type"]: target
        for assembly in payload["assemblies"]
        for target in assembly["target_types"]
    }


def _safe_literals(method: dict[str, Any]) -> list[str]:
    return [
        row["safe_literal"]
        for row in method["string_literals"]
        if "safe_literal" in row
    ]


def _entity_property(call: str) -> str | None:
    if ".Entity." not in call:
        return None
    match = re.search(r"\.(?:get|set)_([A-Za-z][A-Za-z0-9_]*)$", call)
    if not match or match.group(1) in FRAMEWORK_PROPERTIES:
        return None
    return match.group(1)


def _query_call(call: str) -> bool:
    return bool(
        ("Adapter." in call or "Handler." in call or "UIHelper." in call)
        and re.search(r"\.(Get|Load|Refresh|Fill|Check|BeValid|Is|Have)[A-Za-z0-9_]*$", call)
    )


def _validation_method(name: str) -> bool:
    lowered = name.casefold()
    return any(token in lowered for token in ("valid", "check", "cando", "canchange"))


def _screen_literal(value: str) -> bool:
    return bool(
        re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,80}", value)
        and not value.startswith(("Form", "ItemFor", "layout", "emptySpace", "vnGrid"))
        and value not in {"MaskManagerType"}
    )


def _page_contract(
    page_id: str,
    spec: dict[str, Any],
    targets: dict[str, dict[str, Any]],
    capability_payload: dict[str, Any],
    sql_payload: dict[str, Any],
    auth_payload: dict[str, Any],
) -> dict[str, Any]:
    missing = [name for name in spec["types"] if name not in targets]
    selected = [targets[name] for name in spec["types"] if name in targets]
    entity_fields: Counter[str] = Counter()
    screen_fields: set[str] = set()
    grid_columns: list[str] = []
    filters: set[str] = set()
    query_calls: set[str] = set()
    validations: list[dict[str, Any]] = []

    for target in selected:
        for method in target["methods"]:
            literals = _safe_literals(method)
            if method["method"] == "AddColumns" and target["type"] == spec["active_type"]:
                grid_columns.extend(
                    value for value in literals
                    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,80}", value)
                )
            if method["method"] == "InitializeComponent":
                screen_fields.update(value for value in literals if _screen_literal(value))
            if method["method"] in {"LoadData", "ApplyingFilter"}:
                filters.update(
                    value for value in literals
                    if any(token in value.casefold() for token in ("statusid", "exists(select", "receiptstatusid", "order by"))
                )
            for call in method["calls"]:
                field = _entity_property(call)
                if field:
                    entity_fields[field] += 1
                if _query_call(call):
                    query_calls.add(call)
            if _validation_method(method["method"]):
                validation_calls = sorted(
                    call for call in method["calls"]
                    if any(token in call for token in ("Validator", "Validation", "Check", "BeValid", "IsValid", "GetBalance", "History", "Transfer"))
                )
                validations.append(
                    {
                        "type": target["type"],
                        "method": method["method"],
                        "instruction_count": method["instruction_count"],
                        "validation_calls": validation_calls,
                        "referenced_fields": sorted(
                            {value.rsplit(".", 1)[-1] for value in method["referenced_fields"]}
                        ),
                    }
                )

    capabilities = [
        row for row in capability_payload["capabilities"]
        if row["capability"].startswith(spec["capability_prefix"])
    ]
    sql_by_name = {row["object"]: row for row in sql_payload["contracts"]}
    sql_contracts = [
        {
            "object": name,
            "found": sql_by_name[name]["found"],
            "type_desc": sql_by_name[name]["type_desc"],
            "modify_date": sql_by_name[name]["modify_date"],
            "definition_sha256": sql_by_name[name]["definition_sha256"],
            "parameters": sql_by_name[name]["parameters"],
            "dependency_count": len(sql_by_name[name]["dependencies"]),
        }
        for name in spec["sql_objects"]
    ]
    auth_nodes = [
        row for row in auth_payload["nodes"]
        if row["root_access_node_id"] == spec["route_node"]
    ]
    return {
        "page_id": page_id,
        "active_type": spec["active_type"],
        "route_access_node_id": spec["route_node"],
        "related_types": list(spec["types"]),
        "missing_types": missing,
        "work_queue_contract": spec["work_queue"],
        "grid_columns": list(dict.fromkeys(grid_columns)),
        "screen_field_candidates": sorted(screen_fields),
        "entity_field_candidates": [
            {"field": field, "reference_count": count}
            for field, count in sorted(entity_fields.items())
        ],
        "filter_literals": sorted(filters),
        "query_and_guard_calls": sorted(query_calls),
        "validation_methods": validations,
        "capabilities": capabilities,
        "authorization_nodes": [
            {
                "access_node_id": row["access_node_id"],
                "parent_id": row["parent_id"],
                "depth": row["depth"],
                "access_node_key": row["access_node_key"],
                "is_show": row["is_show"],
            }
            for row in auth_nodes
        ],
        "sql_contracts": sql_contracts,
        "write_intent_boundary": spec["write_boundary"],
        "erp_api_rule": (
            "Read model and command model must be separate. A command request must carry "
            "expected version/current state, operational date and scope context; the server "
            "must re-evaluate authorization and domain guards and append an audit event."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--il", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--sql-contracts", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    il_payload = _load(args.il)
    capability_payload = _load(args.capabilities)
    sql_payload = _load(args.sql_contracts)
    auth_payload = _load(args.authorization)
    targets = _targets(il_payload)
    pages = [
        _page_contract(page_id, spec, targets, capability_payload, sql_payload, auth_payload)
        for page_id, spec in PAGE_SPECS.items()
    ]
    artifact = {
        "artifact": "varanegar_active_page_field_filter_validation_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {
            "targeted_il": args.il.as_posix(),
            "capability_matrix": args.capabilities.as_posix(),
            "ui_sql_contracts": args.sql_contracts.as_posix(),
            "route_authorization": args.authorization.as_posix(),
        },
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_rows_or_bound_values_read_or_persisted": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "page_count": len(pages),
            "related_type_count": sum(len(row["related_types"]) for row in pages),
            "missing_type_count": sum(len(row["missing_types"]) for row in pages),
            "grid_column_count": sum(len(row["grid_columns"]) for row in pages),
            "entity_field_candidate_count": sum(len(row["entity_field_candidates"]) for row in pages),
            "validation_method_count": sum(len(row["validation_methods"]) for row in pages),
            "sql_contract_count": sum(len(row["sql_contracts"]) for row in pages),
            "authorization_node_count": sum(len(row["authorization_nodes"]) for row in pages),
        },
        "confidence": {
            "route_and_active_type": "high",
            "cheque_grid_columns": "high_from_AddColumns_IL",
            "entity_field_candidates": "medium_to_high_from_domain_property_calls",
            "screen_field_candidates": "medium_from_InitializeComponent_static_identifiers",
            "validation_contract": "high_for_call_presence_not_branch_semantics",
            "runtime_values": "not_observed_by_design",
        },
        "limits": [
            "Field candidates are contracts referenced by code, not proof that every field is visible or editable in the current session.",
            "Static call presence does not prove every branch executes for every state.",
            "Status numbers retain source semantics until a separately evidenced status dictionary is crosswalked.",
            "No command was executed; write boundaries are intent contracts only.",
        ],
        "pages": pages,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
