"""Build a privacy-safe stock reconciliation diagnostic contract.

The extractor only reads the local READ_ONLY clone.  It does not execute the
legacy repair procedure, any form, or any business command.  Persisted output
contains aggregate counts and static SQL-module semantics; no goods, user,
host, voucher, customer, or server-configuration values are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


ACC_YEAR = 1405
MODULES = (
    "vwHealthyCardex",
    "vwHealthyCardexForCheck",
    "usp_ModifyStockGoods",
    "usp_CheckOnHandQty",
    "trg_tblVocherHdr_UpdateStockGoods",
    "trg_tblVocherItm_UpdateStockGoods",
    "trg_StockGoods_CheckOnHandQty",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _module_contracts(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    quoted = ",".join("N'" + name.replace("'", "''") + "'" for name in MODULES)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ({quoted})
        ORDER BY s.name,o.name
        """,
    )
    public: list[dict[str, Any]] = []
    definitions: dict[str, str] = {}
    for row in rows:
        definition = row.pop("definition")
        qualified = f"{row['schema_name']}.{row['object_name']}"
        definitions[qualified] = definition
        public.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": _sha(definition),
                "has_nolock": "nolock" in definition.casefold(),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
            }
        )
    return public, definitions


def _legacy_naive_reconciliation(cursor: Any) -> dict[str, Any]:
    overview = _rows(
        cursor,
        f"""
        WITH ledger AS(
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) qty
          FROM inv.vwHealthyCardex WHERE AccYear={ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS(
          SELECT s.StockDCRef,s.GoodsRef,ISNULL(s.OnHandQty,0) stored,
                 ISNULL(l.qty,0) ledger_qty
          FROM GNR.tblStockGoods s
          LEFT JOIN ledger l ON l.AccYear=s.AccYear AND l.StockDCRef=s.StockDCRef
                            AND l.GoodsRef=s.GoodsRef
          WHERE s.AccYear={ACC_YEAR}
        )
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored=ledger_qty THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN stored<>ledger_qty THEN 1 ELSE 0 END) mismatch,
               SUM(CASE WHEN stored<ledger_qty THEN 1 ELSE 0 END) ledger_greater,
               SUM(CASE WHEN stored>ledger_qty THEN 1 ELSE 0 END) stored_greater,
               SUM(ABS(stored-ledger_qty)) absolute_difference
        FROM z
        """,
    )[0]
    by_stock = _rows(
        cursor,
        f"""
        WITH ledger AS(
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) qty
          FROM inv.vwHealthyCardex WHERE AccYear={ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS(
          SELECT s.StockDCRef,ISNULL(s.OnHandQty,0) stored,ISNULL(l.qty,0) ledger_qty
          FROM GNR.tblStockGoods s
          LEFT JOIN ledger l ON l.AccYear=s.AccYear AND l.StockDCRef=s.StockDCRef
                            AND l.GoodsRef=s.GoodsRef
          WHERE s.AccYear={ACC_YEAR}
        )
        SELECT StockDCRef,COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored<>ledger_qty THEN 1 ELSE 0 END) mismatch,
               SUM(ABS(stored-ledger_qty)) absolute_difference
        FROM z GROUP BY StockDCRef ORDER BY StockDCRef
        """,
    )
    return {"overview": overview, "by_stock": by_stock}


def _official_formula_cte() -> str:
    # This is a SELECT-only transcription of dbo.usp_ModifyStockGoods's
    # OnHandQty2 branch.  It must never be replaced by EXEC of that procedure:
    # @OnlyCheck=0 is a repair command that updates operational snapshots.
    return f"""
    WITH flags AS(
      SELECT
        ISNULL(MAX(CASE WHEN KeyName='POrder_OnlyInsertOrder'
                       THEN TRY_CONVERT(int,KeyValue) END),0) porder_only_insert,
        ISNULL(MAX(CASE WHEN KeyName='FreeInvoiceDontEffectOnStockGoods'
                       THEN TRY_CONVERT(int,KeyValue) END),0) free_invoice_no_effect
      FROM GNR.tblServerConfig
    ), ledger AS(
      SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) qty
      FROM inv.vwHealthyCardexForCheck WHERE AccYear={ACC_YEAR}
      GROUP BY AccYear,StockDCRef,GoodsRef
    ), component_rows AS(
      SELECT 'sale_without_exit' component,H.StockDCRef,H.AccYear,I.GoodsRef,
             SUM(CONVERT(decimal(38,6),ISNULL(I.TotalQty,0))) qty
      FROM SLE.tblSaleItm I
      JOIN SLE.tblSaleHdr H ON I.HdrRef=H.ID AND H.CancelFlag=0
                           AND H.ExitRef IS NULL AND H.OrderType<>1003
      JOIN SLE.tblOrderHdr O ON O.SaleHdrRef=H.ID
      CROSS JOIN flags f
      WHERE H.AccYear={ACC_YEAR}
        AND ((f.free_invoice_no_effect=0 AND O.FreeInvoiceHdrRef IS NOT NULL)
             OR O.FreeInvoiceHdrRef IS NULL)
      GROUP BY H.StockDCRef,H.AccYear,I.GoodsRef
      UNION ALL
      SELECT 'sale_with_unchanged_exit',H.StockDCRef,H.AccYear,I.GoodsRef,
             SUM(CONVERT(decimal(38,6),ISNULL(I.TotalQty,0)))
      FROM SLE.tblSaleItm I
      JOIN SLE.tblSaleHdr H ON I.HdrRef=H.ID
      JOIN SLE.tblDist D ON H.DistRef=D.ID
      JOIN inv.tblExit E ON E.DistRef=D.ID
      WHERE H.AccYear={ACC_YEAR} AND H.CancelFlag=0 AND H.ExitRef IS NOT NULL
        AND E.UnChangeFlag=0 AND H.OrderType<>1003
      GROUP BY H.StockDCRef,H.AccYear,I.GoodsRef
      UNION ALL
      SELECT 'legacy_purchase_order',I.PStockId,Y.AccYear,I.PGoodsID,
             SUM(CONVERT(decimal(38,6),ISNULL(I.Quantity,0)))
      FROM dbo.POrderLine I
      JOIN dbo.POrder H ON I.POrderId=H.POrderId
      JOIN GNR.tblAccYear Y ON H.OrderDate BETWEEN Y.StartDate AND Y.EndDate
      CROSS JOIN flags f
      WHERE Y.AccYear={ACC_YEAR} AND H.IsCanceled=0 AND f.porder_only_insert=0
        AND NOT EXISTS(SELECT 1 FROM dbo.POrderXBO X WHERE X.POrderId=H.POrderId)
      GROUP BY I.PStockId,Y.AccYear,I.PGoodsID
      UNION ALL
      SELECT 'confirmed_stock_effect_order',H.StockDCRef,H.AccYear,I.GoodsRef,
             SUM(CONVERT(decimal(38,6),ISNULL(I.OrderTotalQty,0)))
      FROM SLE.tblOrderItm I
      JOIN SLE.tblOrderHdr H ON I.HdrRef=H.ID AND H.ConfirmDate IS NOT NULL
      JOIN SLE.tblOrderType T ON T.ID=H.OrderType
      WHERE H.AccYear={ACC_YEAR} AND T.EffectOrderOnStockGoods=1
        AND H.CancelFlag=0 AND H.SaleHdrRef IS NULL
      GROUP BY H.StockDCRef,H.AccYear,I.GoodsRef
      UNION ALL
      SELECT 'legacy_purchase_return',I.PStockId,Y.AccYear,I.PGoodsID,
             -SUM(CONVERT(decimal(38,6),ISNULL(I.Quantity,0)))
      FROM dbo.POrderRetLine I
      JOIN dbo.POrder H ON I.POrderId=H.POrderId
      JOIN GNR.tblAccYear Y ON H.OrderDate BETWEEN Y.StartDate AND Y.EndDate
      WHERE Y.AccYear={ACC_YEAR} AND H.IsCanceled=0 AND I.HealthType=1
        AND NOT EXISTS(SELECT 1 FROM dbo.PRetSaleXBO X WHERE X.POrderId=H.POrderId)
      GROUP BY I.PStockId,Y.AccYear,I.PGoodsID
      UNION ALL
      SELECT 'reserved_prize',StockDCRef,AccYear,GoodsRef,
             SUM(CONVERT(decimal(38,6),ISNULL(Qty,0)))
      FROM SLE.tblReservedPrize WHERE AccYear={ACC_YEAR}
      GROUP BY StockDCRef,AccYear,GoodsRef
    ), obligations AS(
      SELECT StockDCRef,AccYear,GoodsRef,SUM(qty) qty
      FROM component_rows GROUP BY StockDCRef,AccYear,GoodsRef
    ), compared AS(
      SELECT s.StockDCRef,s.GoodsRef,ISNULL(s.OnHandQty,0) stored,
             ISNULL(l.qty,0) ledger_for_check,
             ISNULL(o.qty,0) operational_obligation,
             ISNULL(l.qty,0)-ISNULL(o.qty,0) official_qty
      FROM GNR.tblStockGoods s
      LEFT JOIN ledger l ON l.AccYear=s.AccYear AND l.StockDCRef=s.StockDCRef
                        AND l.GoodsRef=s.GoodsRef
      LEFT JOIN obligations o ON o.AccYear=s.AccYear AND o.StockDCRef=s.StockDCRef
                             AND o.GoodsRef=s.GoodsRef
      WHERE s.AccYear={ACC_YEAR}
    )
    """


def _official_reconciliation(cursor: Any) -> dict[str, Any]:
    cte = _official_formula_cte()
    overview = _rows(
        cursor,
        cte
        + """
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored=official_qty THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN stored<>official_qty THEN 1 ELSE 0 END) mismatch,
               SUM(CASE WHEN stored<official_qty THEN 1 ELSE 0 END) official_greater,
               SUM(CASE WHEN stored>official_qty THEN 1 ELSE 0 END) stored_greater,
               SUM(ABS(stored-official_qty)) absolute_difference,
               SUM(CASE WHEN operational_obligation<>0 THEN 1 ELSE 0 END) obligation_keys,
               SUM(ABS(operational_obligation)) absolute_obligation
        FROM compared
        """,
    )[0]
    by_stock = _rows(
        cursor,
        cte
        + """
        SELECT StockDCRef,COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored<>official_qty THEN 1 ELSE 0 END) mismatch,
               SUM(ABS(stored-official_qty)) absolute_difference,
               SUM(CASE WHEN operational_obligation<>0 THEN 1 ELSE 0 END) obligation_keys,
               SUM(ABS(operational_obligation)) absolute_obligation
        FROM compared GROUP BY StockDCRef ORDER BY StockDCRef
        """,
    )
    components = _rows(
        cursor,
        cte
        + """
        SELECT component,COUNT_BIG(*) component_keys,
               COUNT(DISTINCT StockDCRef) stock_centers,
               SUM(qty) signed_quantity,SUM(ABS(qty)) absolute_quantity
        FROM component_rows GROUP BY component ORDER BY component
        """,
    )
    flags = _rows(
        cursor,
        """
        SELECT
          CASE WHEN ISNULL(MAX(CASE WHEN KeyName='POrder_OnlyInsertOrder'
                    THEN TRY_CONVERT(int,KeyValue) END),0)=0
               THEN 'INCLUDE_LEGACY_PURCHASE_ORDER_COMPONENT'
               ELSE 'EXCLUDE_LEGACY_PURCHASE_ORDER_COMPONENT' END purchase_order_branch,
          CASE WHEN ISNULL(MAX(CASE WHEN KeyName='FreeInvoiceDontEffectOnStockGoods'
                    THEN TRY_CONVERT(int,KeyValue) END),0)=0
               THEN 'INCLUDE_LINKED_FREE_INVOICE_SALES'
               ELSE 'EXCLUDE_LINKED_FREE_INVOICE_SALES' END free_invoice_branch
        FROM GNR.tblServerConfig
        """,
    )[0]
    return {
        "overview": overview,
        "by_stock": by_stock,
        "component_aggregates": components,
        "effective_branch_names_without_raw_values": flags,
    }


def _view_parity(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        f"""
        WITH a AS(
          SELECT StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) qty
          FROM inv.vwHealthyCardex WHERE AccYear={ACC_YEAR}
          GROUP BY StockDCRef,GoodsRef
        ), b AS(
          SELECT StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) qty
          FROM inv.vwHealthyCardexForCheck WHERE AccYear={ACC_YEAR}
          GROUP BY StockDCRef,GoodsRef
        ), keys AS(
          SELECT StockDCRef,GoodsRef FROM a UNION SELECT StockDCRef,GoodsRef FROM b
        )
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN ISNULL(a.qty,0)=ISNULL(b.qty,0) THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN ISNULL(a.qty,0)<>ISNULL(b.qty,0) THEN 1 ELSE 0 END) mismatch,
               SUM(ABS(ISNULL(a.qty,0)-ISNULL(b.qty,0))) absolute_difference
        FROM keys k
        LEFT JOIN a ON a.StockDCRef=k.StockDCRef AND a.GoodsRef=k.GoodsRef
        LEFT JOIN b ON b.StockDCRef=k.StockDCRef AND b.GoodsRef=k.GoodsRef
        """,
    )[0]


def _trigger_state(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT SCHEMA_NAME(o.schema_id) parent_schema,o.name parent_object,
               tr.name trigger_name,tr.is_disabled,tr.is_instead_of_trigger,
               OBJECTPROPERTYEX(tr.object_id,'ExecIsFirstUpdateTrigger') first_update,
               OBJECTPROPERTYEX(tr.object_id,'ExecIsLastUpdateTrigger') last_update
        FROM sys.triggers tr
        JOIN sys.objects o ON o.object_id=tr.parent_id
        WHERE tr.name IN('trg_tblVocherHdr_UpdateStockGoods',
                         'trg_tblVocherItm_UpdateStockGoods',
                         'trg_StockGoods_CheckOnHandQty')
        ORDER BY tr.name
        """,
    )


def _three_month_sale_exit_activity(cursor: Any) -> dict[str, Any]:
    monthly = _rows(
        cursor,
        """
        SELECT CONVERT(char(7),H.CreationDate,120) month_bucket,
               CASE WHEN H.CancelFlag<>0 THEN 'cancelled'
                    WHEN H.ExitRef IS NULL THEN 'active_without_exit'
                    ELSE 'active_with_exit' END current_state,
               COUNT(DISTINCT H.ID) sale_headers,COUNT_BIG(*) sale_lines,
               COUNT(DISTINCT CONCAT(H.StockDCRef,':',I.GoodsRef)) stock_goods_keys,
               SUM(CONVERT(decimal(38,6),ISNULL(I.TotalQty,0))) quantity
        FROM SLE.tblSaleHdr H
        JOIN SLE.tblSaleItm I ON I.HdrRef=H.ID
        WHERE H.CreationDate>=DATEADD(MONTH,-3,SYSDATETIME())
          AND H.OrderType<>1003
        GROUP BY CONVERT(char(7),H.CreationDate,120),
                 CASE WHEN H.CancelFlag<>0 THEN 'cancelled'
                      WHEN H.ExitRef IS NULL THEN 'active_without_exit'
                      ELSE 'active_with_exit' END
        ORDER BY month_bucket,current_state
        """,
    )
    aging = _rows(
        cursor,
        f"""
        SELECT CASE WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<1 THEN 'LT_1_DAY'
                    WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<3 THEN '1_TO_2_DAYS'
                    WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<8 THEN '3_TO_7_DAYS'
                    WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<31 THEN '8_TO_30_DAYS'
                    ELSE 'GT_30_DAYS' END age_bucket,
               COUNT(DISTINCT H.ID) sale_headers,COUNT_BIG(*) sale_lines,
               COUNT(DISTINCT CONCAT(H.StockDCRef,':',I.GoodsRef)) stock_goods_keys,
               SUM(CONVERT(decimal(38,6),ISNULL(I.TotalQty,0))) quantity
        FROM SLE.tblSaleHdr H
        JOIN SLE.tblSaleItm I ON I.HdrRef=H.ID
        JOIN SLE.tblOrderHdr O ON O.SaleHdrRef=H.ID
        CROSS JOIN(
          SELECT ISNULL(MAX(CASE WHEN KeyName='FreeInvoiceDontEffectOnStockGoods'
                         THEN TRY_CONVERT(int,KeyValue) END),0) free_invoice_no_effect
          FROM GNR.tblServerConfig
        ) f
        WHERE H.AccYear={ACC_YEAR} AND H.CancelFlag=0 AND H.ExitRef IS NULL
          AND H.OrderType<>1003
          AND ((f.free_invoice_no_effect=0 AND O.FreeInvoiceHdrRef IS NOT NULL)
               OR O.FreeInvoiceHdrRef IS NULL)
        GROUP BY CASE WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<1 THEN 'LT_1_DAY'
                      WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<3 THEN '1_TO_2_DAYS'
                      WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<8 THEN '3_TO_7_DAYS'
                      WHEN DATEDIFF(DAY,H.CreationDate,SYSDATETIME())<31 THEN '8_TO_30_DAYS'
                      ELSE 'GT_30_DAYS' END
        ORDER BY MIN(DATEDIFF(DAY,H.CreationDate,SYSDATETIME()))
        """,
    )
    return {
        "window_months": 3,
        "monthly_sale_state_counts": monthly,
        "current_stock_obligation_aging": aging,
        "limit": "Monthly rows classify current state by source creation month; they are not a state-transition event log.",
    }


def _findings(definitions: dict[str, str], naive: dict[str, Any], official: dict[str, Any]) -> list[dict[str, Any]]:
    repair = definitions["dbo.usp_ModifyStockGoods"].casefold()
    header = definitions["inv.trg_tblVocherHdr_UpdateStockGoods"].casefold()
    check = definitions["inv.usp_CheckOnHandQty"].casefold()
    naive_count = int(naive["overview"]["mismatch"] or 0)
    official_count = int(official["overview"]["mismatch"] or 0)
    findings = [
        {
            "finding_id": "STK-001",
            "severity": "CRITICAL" if official_count == 0 else "HIGH",
            "title": "Cardex-only comparison is not the legacy authoritative stock formula",
            "confidence": "HIGH_CLONE_RECONCILIATION",
            "evidence": {
                "cardex_only_mismatch": naive_count,
                "official_formula_mismatch": official_count,
                "official_formula": "vwHealthyCardexForCheck minus five operational obligation families plus signed purchase returns",
            },
            "diagnostic_action": "Use the exact read-only formula before classifying a stock row as corrupt; never normalize the snapshot to plain cardex.",
        },
        {
            "finding_id": "STK-002",
            "severity": "CRITICAL",
            "title": "The legacy reconciliation procedure is also a repair command",
            "confidence": "HIGH_STATIC",
            "evidence": ["dbo.usp_ModifyStockGoods has @OnlyCheck branch and an UPDATE branch", "repair branch disables all stock triggers"],
            "diagnostic_action": "Do not EXEC the procedure during diagnosis. Transcribe and version its SELECT formula against a read-only clone.",
        },
        {
            "finding_id": "STK-003",
            "severity": "HIGH",
            "title": "Voucher confirmation trigger deliberately skips specialized voucher paths",
            "confidence": "HIGH_STATIC",
            "evidence": ["voucher types 60,21,64,65 and type 20/health 3 bypass the general confirmation update path"],
            "diagnostic_action": "Trace the specialized creator/exit/distribution path before blaming the voucher trigger.",
        },
        {
            "finding_id": "STK-004",
            "severity": "HIGH",
            "title": "Official repair formula is concurrency-sensitive",
            "confidence": "HIGH_STATIC",
            "evidence": ["dbo.usp_ModifyStockGoods reads multiple ledgers with NOLOCK", "its formula spans inventory, sales, orders, distribution, exit, POS purchase and prize reservation"],
            "diagnostic_action": "Capture a quiescent or snapshot-isolated source checkpoint before accepting residual mismatch counts.",
        },
        {
            "finding_id": "STK-005",
            "severity": "HIGH",
            "title": "Either negative-stock permission flag can bypass pre-check",
            "confidence": "HIGH_STATIC",
            "evidence": ["inv.usp_CheckOnHandQty returns when AllowNegativeOnHandQty=1 OR AllowNegativeCardexQty=1 for most voucher types"],
            "diagnostic_action": "Report both flags and voucher type when investigating an accepted negative movement.",
        },
    ]
    signatures = {
        "repair_updates": "update gnr.tblstockgoods" in repair,
        "repair_disables_triggers": "disable trigger all" in repair,
        "specialized_skips": "in(60,21,64)" in header and "vochertypecode=65" in header,
        "negative_flag_or": "@allownegativeonhandqty=1 or @allownegativecardexqty=1" in check,
    }
    failed = [name for name, value in signatures.items() if not value]
    if failed:
        raise AssertionError(f"stock diagnostic signatures drifted: {failed}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    connection = _connect()
    cursor = connection.cursor()
    _assert_safe_target(cursor)
    safety = _rows(
        cursor,
        """
        SELECT DB_NAME() database_name,DATABASEPROPERTYEX(DB_NAME(),'Updateability') updateability,
               HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','SELECT') can_select,
               HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE') can_update
        """,
    )[0]
    modules, definitions = _module_contracts(cursor)
    naive = _legacy_naive_reconciliation(cursor)
    official = _official_reconciliation(cursor)
    result = {
        "artifact": "varanegar_stock_reconciliation_incident_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {"server": SERVER, "database": DATABASE, "fiscal_year": ACC_YEAR},
        "safety": {
            **safety,
            "database_commands_executed": 0,
            "stored_procedures_executed": 0,
            "application_or_ui_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_rows_changed": 0,
            "raw_goods_vouchers_users_hosts_or_config_values_persisted": 0,
            "mode": "READ_ONLY_CATALOG_AND_ANONYMOUS_AGGREGATES",
        },
        "summary": {
            "cardex_only_mismatch_count": int(naive["overview"]["mismatch"] or 0),
            "official_formula_mismatch_count": int(official["overview"]["mismatch"] or 0),
            "finding_count": 5,
            "critical_finding_count": 2 if int(official["overview"]["mismatch"] or 0) == 0 else 1,
            "high_finding_count": 3 if int(official["overview"]["mismatch"] or 0) == 0 else 4,
            "target_module_count": len(modules),
        },
        "cardex_only_reconciliation": naive,
        "official_legacy_formula_reconciliation": official,
        "healthy_cardex_vs_for_check_view_parity": _view_parity(cursor),
        "three_month_sale_exit_activity": _three_month_sale_exit_activity(cursor),
        "module_contracts": modules,
        "trigger_state": _trigger_state(cursor),
        "findings": _findings(definitions, naive, official),
        "evidence_limits": [
            "The formula is evaluated on a read-only clone, not during a live quiescent checkpoint.",
            "NOLOCK in the legacy formula means a busy production run can observe a mixed-time result.",
            "No goods, voucher, user, host, or raw configuration values are persisted.",
            "No repair procedure or UI command was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
