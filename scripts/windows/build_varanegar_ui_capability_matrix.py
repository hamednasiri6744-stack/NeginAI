"""Build a capability matrix from redacted Varanegar UI/IL/SQL evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _types(il: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["type"]: row
        for assembly in il["assemblies"]
        for row in assembly["target_types"]
        if row["found"]
    }


def _method(types: dict[str, dict[str, Any]], type_name: str, method: str) -> dict[str, Any]:
    return next(row for row in types[type_name]["methods"] if row["method"] == method)


def _safe_literals(method: dict[str, Any]) -> set[str]:
    return {
        row["safe_literal"]
        for row in method["string_literals"]
        if "safe_literal" in row
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", required=True, type=Path)
    parser.add_argument("--il", required=True, type=Path)
    parser.add_argument("--sql", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    ui = _load(args.ui)
    il = _load(args.il)
    sql = _load(args.sql)
    types = _types(il)

    fill_permissions = _method(types, "VN.SDS.Container.Program", "FillUserPermissionS")
    build_menu = _method(types, "VN.SDS.Container.MainForm", "BuildMenu")
    switch_dc = _method(types, "VN.SDS.Container.MainForm", "DcLookUp_EditValueChanged")
    stock_permissions = _method(
        types, "VN.SDS.Stock.UI.StockGoods.FormStockGoods", "ApplyUserPermission"
    )
    stock_load = _method(
        types, "VN.SDS.Stock.UI.StockGoods.FormStockGoods", "LoadInitData"
    )
    dist_permissions = _method(
        types,
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementList",
        "ApplyUserPermission",
    )
    received_permissions = _method(
        types, "TreasuryOld.Forms.frmRChequeTrackingNew", "SetFormPermission"
    )
    payable_permissions = _method(
        types, "TreasuryOld.Forms.frmPChequeTrackingNew", "SetFormPermission"
    )

    assert (
        "VN.SDS.Setting.Business.AccessNodeInfo.AccessNodeInfoHandler.GetInstance"
        in fill_permissions["calls"]
    )
    assert "Application.BaseData.UserSessionInfo.get_UserPermissionS" in build_menu["calls"]
    assert "VN.SDS.Container.MainForm.BuildMenu" in switch_dc["calls"]
    assert "Application.BaseData.UserSessionInfo.HasPersmission" in stock_permissions["calls"]
    assert (
        "VN.SDS.Stock.UIComponent.StockGoods.StockGoodsUIHelper.StockGoodsGridServerModeDC"
        in stock_load["calls"]
    )
    assert "Application.BaseData.UserSessionInfo.HasPersmission" in dist_permissions["calls"]
    assert "RchequeTracking.get_ChangeStatus" in received_permissions["calls"]
    assert "RchequeTracking.get_Undo" in received_permissions["calls"]
    assert "PChequeTracking.get_ChangeStatus" in payable_permissions["calls"]
    assert "PChequeTracking.get_Undo" in payable_permissions["calls"]

    dist_keys = _safe_literals(dist_permissions)
    required_dist_keys = {
        "DistAfterVch2Sale",
        "FreeDist",
        "ApprovalDist",
        "BackToOldStatus",
        "RemoveExitFromDist",
    }
    assert required_dist_keys <= dist_keys

    change_status_controls = [
        row
        for row in ui["safe_named_controls"]
        if row["safe_label"] == "تغيير وضعيت"
    ]
    assert len(change_status_controls) == 2
    assert all(row["is_enabled"] is False for row in change_status_controls)

    sql_objects = {row["object"].casefold() for row in sql["contracts"] if row["found"]}
    required_sql = {
        "sle.usp_sdsnet_createdist",
        "dbo.usp_createexitvocherbydist",
        "dbo.dorcheque_addrchequehistory",
        "dbo.dopcheque_addpchequehistory",
        "gnr.vwstockgoods_servermode",
    }
    assert required_sql <= sql_objects

    capabilities = [
        {
            "capability": "session.switch_fiscal_year",
            "page": "container",
            "permission_source": "session",
            "context_guards": ["AccYear", "operational_dates"],
            "data_partition": ["AccYear"],
            "command_contract": "rebuild operational context and close dependent forms",
        },
        {
            "capability": "session.switch_distribution_center",
            "page": "container",
            "permission_source": "UserPermissionS + MenuConfig + feature locks",
            "context_guards": ["DCRef", "SalesOfficeRef", "SiteType"],
            "data_partition": ["DCRef", "SalesOfficeRef"],
            "command_contract": "rebuild menu and operational context",
        },
        {
            "capability": "inventory.stock_goods.read",
            "page": "اقلام انبار",
            "permission_source": "menu node + page permission",
            "context_guards": ["AccYear", "DCRef", "StockDCRef"],
            "data_partition": ["AccYear", "StockDCRef"],
            "command_contract": "GNR.vwStockGoods_serverMode projection",
        },
        {
            "capability": "inventory.stock_goods.create_edit_delete",
            "page": "اقلام انبار",
            "permission_source": "HasPersmission per New/Edit/Delete command",
            "context_guards": ["stock validator", "goods status", "open order/sale/flow"],
            "data_partition": ["AccYear", "DCRef", "StockDCRef"],
            "command_contract": "separate commands; not part of read projection",
        },
        {
            "capability": "distribution.read",
            "page": "مديريت توزيع",
            "permission_source": "menu node",
            "context_guards": ["CheckStatus", "WhereStatement", "SortField"],
            "data_partition": ["AccYear", "DCRef", "user context"],
            "command_contract": "DistHandler.GetAllView + Sale detail by DistRef",
        },
        {
            "capability": "distribution.create_edit",
            "page": "مديريت توزيع",
            "permission_source": "MenuButtonNew / MenuButtonEdit",
            "context_guards": ["operation date", "sales unassigned", "team/truck", "validator"],
            "data_partition": ["AccYear", "DCRef"],
            "command_contract": "SLE.usp_sdsnet_CreateDist",
        },
        {
            "capability": "distribution.follow",
            "page": "مديريت توزيع",
            "permission_source": "ApprovalDist",
            "context_guards": ["current status"],
            "data_partition": ["AccYear", "DCRef"],
            "command_contract": "SetFollowDist",
        },
        {
            "capability": "distribution.follow_after_voucher",
            "page": "مديريت توزيع",
            "permission_source": "DistAfterVch2Sale",
            "context_guards": ["CanFollowDistAfterVch2Sale feature flag", "current status"],
            "data_partition": ["AccYear", "DCRef"],
            "command_contract": "SetanFollowDistAfterVch2Sale",
        },
        {
            "capability": "distribution.reverse_status",
            "page": "مديريت توزيع",
            "permission_source": "BackToOldStatus",
            "context_guards": ["current status", "return-system mode", "sale/return existence"],
            "data_partition": ["AccYear", "DCRef"],
            "command_contract": "SetBackTopreviousStatus",
        },
        {
            "capability": "distribution.issue_exit",
            "page": "مديريت توزيع",
            "permission_source": "page command + feature configuration",
            "context_guards": ["CreateExitWithConfirmStockMan", "stock/cardex", "operation date", "lock owner/host"],
            "data_partition": ["AccYear", "DCRef", "StockDCRef"],
            "command_contract": "dbo.usp_CreateExitVocherByDist",
        },
        {
            "capability": "distribution.remove_exit",
            "page": "مديريت توزيع",
            "permission_source": "RemoveExitFromDist",
            "context_guards": ["reason required", "last closed date", "current status"],
            "data_partition": ["AccYear", "DCRef"],
            "command_contract": "inv.Usp_RemoveExitFromDist",
        },
        {
            "capability": "distribution.free_or_merge_exit",
            "page": "مديريت توزيع",
            "permission_source": "FreeDist",
            "context_guards": ["lock owner/host", "goods/batch validation"],
            "data_partition": ["DCRef", "StockDCRef"],
            "command_contract": "inv.Usp_InsertGoodsExit_RD",
        },
        {
            "capability": "received_cheque.change_status",
            "page": "پيگيري چکهاي دريافتني",
            "permission_source": "RchequeTracking.ChangeStatus",
            "context_guards": ["row selection", "operation date open", "workflow", "reconciliation", "status context"],
            "data_partition": ["DCFilter", "sale office availability"],
            "command_contract": "RchequeWorkFlow_IsValid + DoRCheque_AddRChequeHistory",
        },
        {
            "capability": "received_cheque.undo",
            "page": "پيگيري چکهاي دريافتني",
            "permission_source": "RchequeTracking.Undo",
            "context_guards": ["operation date open", "last history", "transfer/cession/balance"],
            "data_partition": ["DCFilter"],
            "command_contract": "DoRCheque_DeleteLastRChequeHistory",
        },
        {
            "capability": "payable_cheque.change_status",
            "page": "پيگيري چکهاي پرداختني",
            "permission_source": "PChequeTracking.ChangeStatus",
            "context_guards": ["row selection", "operation date open", "workflow", "cheque leaf", "pay/balance"],
            "data_partition": ["DCFilter", "sale office availability"],
            "command_contract": "PChequeWorkFlow_IsValid + DoPCheque_AddPChequeHistory",
        },
        {
            "capability": "payable_cheque.undo",
            "page": "پيگيري چکهاي پرداختني",
            "permission_source": "PChequeTracking.Undo",
            "context_guards": ["operation date open", "last history", "current pointer"],
            "data_partition": ["DCFilter"],
            "command_contract": "DoPCheque_DeleteLastPChequeHistory",
        },
    ]

    artifact = {
        "artifact": "varanegar_ui_capability_matrix",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "DERIVED_FROM_READ_ONLY_REDACTED_EVIDENCE",
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "database_queries_executed_by_builder": 0,
            "raw_business_values_persisted": 0,
        },
        "summary": {
            "capability_count": len(capabilities),
            "page_count": len({row["page"] for row in capabilities}),
            "all_evidence_assertions_passed": True,
            "selection_guard_observed_for_both_cheque_forms": True,
        },
        "capabilities": capabilities,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
