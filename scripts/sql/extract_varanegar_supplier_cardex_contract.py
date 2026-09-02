"""Extract the official multi-source supplier-cardex semantic contract.

Read-only by design. This extractor persists the procedure definition, source
object metadata/counts, and a reviewed branch matrix. It never stores supplier,
customer, cheque, account, document, comment, user, host, or credential rows.
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
    DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows,
)


SOURCE_OBJECTS: tuple[str, ...] = (
    "GNR.tblSupplier", "dbo.Contact", "SLE.TblSaleHdr", "dbo.POrder",
    "dbo.POrderLine", "dbo.POrderRetLine", "dbo.PPayment", "SLE.TblRetSaleHdr",
    "Acc.tblPayments", "Acc.tblPayType", "dbo.Receipt", "dbo.RPReason",
    "Acc.TblBankOrders", "Acc.TblCheque", "dbo.RCash", "dbo.Pay", "dbo.PCash",
    "dbo.PWithdraw", "dbo.PCheque", "dbo.PChequeHistory", "dbo.PayGroup",
    "dbo.Voucher", "dbo.VoucherItem", "ICA.TblSupInvoiceHdr",
    "ICA.TblSupInvoiceItm", "ICA.tblRetSupInvoiceHdr", "ICA.tblRetSupInvoiceItm",
    "Inv.tblVocherHdr", "dbo.RCashDraft", "dbo.Fund", "dbo.FundItem",
    "Acc.tblStatement", "Acc.ManualVoucher",
)


BRANCHES: tuple[dict[str, Any], ...] = (
    {"title_id": 0, "title_fa": "مانده اول دوره", "source": "GNR.tblSupplier", "direction": "PlusMinus=-1 => Bed; PlusMinus=1 => Bes", "date_rule": "opening balance"},
    {"title_id": 1, "title_fa": "فروش", "source": "SLE.TblSaleHdr", "direction": "Bed", "date_rule": "AccYear", "state_rule": "SaleNo present and CancelFlag=0"},
    {"title_id": 2, "title_fa": "فروش مستقیم", "source": "dbo.POrder + POrderLine", "direction": "Bed", "date_rule": "fiscal year containing OrderDate", "state_rule": "SaleId=0, not canceled, type<>6"},
    {"title_id": 3, "title_fa": "برگشت فروش مستقیم", "source": "dbo.POrder + POrderRetLine", "direction": "Bes", "date_rule": "fiscal year containing OrderDate", "state_rule": "SaleId=0 and not canceled"},
    {"title_id": 4, "title_fa": "تسویه فروش مستقیم", "source": "dbo.PPayment + POrder", "direction": "Bes", "date_rule": "fiscal year containing OrderDate", "state_rule": "payment type in 1,2,11,7 and Transfered=0"},
    {"title_id": 5, "title_fa": "برگشت از فروش", "source": "SLE.TblRetSaleHdr", "direction": "Bes", "date_rule": "AccYear", "state_rule": "not canceled; optional confirmed-stock-return gate"},
    {"title_id": 6, "title_fa": "اسناد حسابداری به‌جز چک/حواله", "source": "Acc.vwtblPayments", "direction": "PayTypeGroup=5 => Bed; otherwise Bes", "date_rule": "AccYear", "state_rule": "allowed PayTypeGroup and SL scope"},
    {"title_id": 7, "title_fa": "حواله بانکی", "source": "Acc.vwtblPayments + vwtblBankOrders", "direction": "PayTypeGroup=5 => Bed; otherwise Bes", "date_rule": "OrderDate/PayDate window", "state_rule": "PayTypeGroup in 9,14"},
    {"title_id": 8, "title_fa": "چک تسویه فاکتور", "source": "Acc.vwPayChequeFullStates_New", "direction": "state projection supplies Bed/Bes", "date_rule": "change-state AccYear", "state_rule": "receipt reason and SL scope"},
    {"title_id": 9, "title_fa": "مانده چک", "source": "Acc.vwChequeFullStates_New + tblPayments", "direction": "status 4,5,9 => Bed; else Bes", "date_rule": "change-state AccYear", "state_rule": "remaining cheque amount after allocations"},
    {"title_id": 10, "title_fa": "مانده حواله بانکی", "source": "Acc.vwtblBankOrders + tblPayments", "direction": "Bes", "date_rule": "OrderDate window", "state_rule": "settlement reason only; remaining amount"},
    {"title_id": 11, "title_fa": "مانده نقد", "source": "dbo.RCash + Receipt + tblPayments", "direction": "Bes", "date_rule": "ReceiptDate window/AccYear", "state_rule": "confirmed receipt and settlement reason"},
    {"title_id": 12, "title_fa": "پرداخت نقد", "source": "dbo.Pay + PCash", "direction": "Bed", "date_rule": "reason-sensitive ToDate/AccYear", "state_rule": "PayStatus=2 and PayNo<>0"},
    {"title_id": 13, "title_fa": "پرداخت برداشت", "source": "dbo.Pay + PWithdraw", "direction": "Bed", "date_rule": "reason-sensitive instrument date/AccYear", "state_rule": "PayStatus=2 and PayNo<>0"},
    {"title_id": 14, "title_fa": "پرداخت چک", "source": "dbo.Pay + PCheque + PChequeHistory", "direction": "status 3,5 => Bed; status 2 => Bes", "date_rule": "reason-sensitive history date/AccYear", "state_rule": "non-certified; status/history-specific PayNo rules"},
    {"title_id": 15, "title_fa": "پرداخت چک سایرین", "source": "received cheque history + Pay", "direction": "Bed", "date_rule": "reason-sensitive PayDate/AccYear", "state_rule": "assigned-to-other status 7 and PayStatus=2"},
    {"title_id": 16, "title_fa": "پرداخت برگشت چک سایرین", "source": "received cheque history + Pay", "direction": "Bes", "date_rule": "reason-sensitive return status date/AccYear", "state_rule": "return/safe status after prior status 7"},
    {"title_id": 17, "title_fa": "پرداخت گروهی", "source": "dbo.PayGroup", "direction": "Bed", "date_rule": "PayGroupDate<=ToDate", "state_rule": "PayStatus=2"},
    {"title_id": 18, "title_fa": "سند حسابداری", "source": "dbo.Voucher + VoucherItem", "direction": "DebitAmount=>Bed; CreditAmount=>Bes", "date_rule": "VoucherDate<=ToDate", "state_rule": "posted manual type 59, feature flag, not external"},
    {"title_id": 19, "title_fa": "خرید", "source": "ICA.TblSupInvoiceHdr + Itm", "direction": "Bes", "date_rule": "SupInvoiceDate<=ToDate", "state_rule": "Total - ineffective supplier addition + ineffective supplier discount"},
    {"title_id": 20, "title_fa": "برگشت خرید", "source": "ICA.tblRetSupInvoiceHdr + Itm + inventory voucher", "direction": "Bed", "date_rule": "RetInvoiceDate<=ToDate", "state_rule": "inventory-linked return"},
    {"title_id": 21, "title_fa": "دریافت حواله بانکی", "source": "dbo.RCashDraft + Receipt", "direction": "Bes", "date_rule": "draft date<=ToDate", "state_rule": "non-settlement reason and official receipt number"},
    {"title_id": 22, "title_fa": "دریافت چک متفرقه", "source": "Acc.vwSupplierChequeFullStates + Receipt", "direction": "status 4,5 => Bed; else Bes", "date_rule": "ReceiptDate<=ToDate", "state_rule": "non-settlement reason and status in 1,2,3,7,4,5"},
    {"title_id": 23, "title_fa": "دریافت نقد", "source": "dbo.RCash + Receipt", "direction": "Bes", "date_rule": "ReceiptDate<=ToDate", "state_rule": "non-settlement reason and official receipt number"},
    {"title_id": 24, "title_fa": "سند تنخواه", "source": "dbo.Fund + FundItem", "direction": "Bed", "date_rule": "FundDate<=ToDate", "state_rule": "supplier DL and SL scope"},
    {"title_id": 25, "title_fa": "اعلامیه بدهکار", "source": "Acc.tblStatement", "direction": "Bed", "date_rule": "StatementDate<=ToDate", "state_rule": "customer/supplier crosswalk"},
    {"title_id": 26, "title_fa": "اعلامیه حسابداری - طرف بدهکار", "source": "Acc.ManualVoucher.DebitContactId", "direction": "Bed", "date_rule": "ManualVoucherDate<=ToDate", "state_rule": "DC scope"},
    {"title_id": 26, "title_fa": "اعلامیه حسابداری - طرف بستانکار", "source": "Acc.ManualVoucher.CreditContactId", "direction": "Bed", "date_rule": "ManualVoucherDate<=ToDate", "state_rule": "DC scope; same title id and direction require business confirmation"},
)


def _object_inventory(cursor: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for qualified in SOURCE_OBJECTS:
        schema, name = qualified.split(".", 1)
        rows = _rows(cursor, f"""
          SELECT s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,
                 CASE WHEN o.type='U' THEN (
                   SELECT SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END)
                   FROM sys.partitions p WHERE p.object_id=o.object_id) END row_count
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          WHERE s.name=N'{schema}' AND o.name=N'{name}'
        """)
        result.append(rows[0] if rows else {"schema_name": schema, "object_name": name,
                                            "type_desc": "NOT_FOUND", "row_count": None})
    return result


def _population_summary(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM GNR.tblSupplier) suppliers,
       (SELECT COUNT_BIG(*) FROM SLE.TblSaleHdr) sales,
       (SELECT COUNT_BIG(*) FROM SLE.TblRetSaleHdr) sales_returns,
       (SELECT COUNT_BIG(*) FROM dbo.POrder) legacy_direct_orders,
       (SELECT COUNT_BIG(*) FROM Acc.tblPayments) accounting_payment_allocations,
       (SELECT COUNT_BIG(*) FROM dbo.Receipt) receipt_headers,
       (SELECT COUNT_BIG(*) FROM dbo.RCash) received_cash_rows,
       (SELECT COUNT_BIG(*) FROM dbo.RCashDraft) received_bank_drafts,
       (SELECT COUNT_BIG(*) FROM dbo.Pay) outgoing_pay_headers,
       (SELECT COUNT_BIG(*) FROM dbo.PCash) outgoing_cash_rows,
       (SELECT COUNT_BIG(*) FROM dbo.PWithdraw) outgoing_withdrawals,
       (SELECT COUNT_BIG(*) FROM dbo.PCheque) outgoing_cheques,
       (SELECT COUNT_BIG(*) FROM dbo.PayGroup) pay_groups,
       (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceHdr) supplier_invoices,
       (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceHdr) supplier_returns,
       (SELECT COUNT_BIG(*) FROM dbo.Fund) petty_cash_headers,
       (SELECT COUNT_BIG(*) FROM dbo.FundItem) petty_cash_items,
       (SELECT COUNT_BIG(*) FROM Acc.tblStatement) statements,
       (SELECT COUNT_BIG(*) FROM Acc.ManualVoucher) manual_vouchers
    """)[0]


def _procedure_contract(cursor: Any) -> dict[str, Any]:
    row = _rows(cursor, """
      SELECT OBJECT_DEFINITION(OBJECT_ID(N'Acc.Usp_GetSupplierRemAmount')) definition,
             o.modify_date
      FROM sys.objects o WHERE o.object_id=OBJECT_ID(N'Acc.Usp_GetSupplierRemAmount')
    """)[0]
    definition = row["definition"]
    if not definition:
        raise RuntimeError("Supplier-cardex procedure definition is unavailable.")
    encoded = definition.encode("utf-8")
    detected_title_ids = sorted({int(x) for x in re.findall(r"'',\s*(\d+)\s*(?:\r?\n|$)", definition)})
    expected_ids = list(range(27))
    return {
        "object": "Acc.Usp_GetSupplierRemAmount",
        "modify_date": row["modify_date"],
        "definition_sha256": hashlib.sha256(encoded).hexdigest(),
        "definition_line_count": len(definition.splitlines()),
        "dynamic_sql": "sp_executesql" in definition.lower(),
        "final_balance_formula": "SUM(BedAmount) - SUM(BesAmount)",
        "branch_rows_in_reviewed_matrix": len(BRANCHES),
        "distinct_title_ids_in_reviewed_matrix": sorted({x["title_id"] for x in BRANCHES}),
        "expected_title_ids": expected_ids,
        "title_id_26_is_duplicated": sum(1 for x in BRANCHES if x["title_id"] == 26) == 2,
        "source_definition": definition,
        "limits": [
            "The procedure is dynamic SQL; dependency metadata alone is incomplete.",
            "The reviewed branch matrix is checked against the current definition hash and must be re-reviewed after a hash change.",
            "Both ManualVoucher debit-contact and credit-contact branches currently write BedAmount with TitleId 26; this is preserved as source behavior and requires business confirmation.",
        ],
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        proc = _procedure_contract(cursor)
        if proc["distinct_title_ids_in_reviewed_matrix"] != proc["expected_title_ids"]:
            raise RuntimeError("Reviewed supplier-cardex branch ids are incomplete.")
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "official_supplier_cardex_contract",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only procedure contract and aggregate source inventory",
                      "privacy_policy": "no supplier/customer/document/cheque/account/comment/user/host/credential rows"},
            "safety": {
                "target_is_local": True, "database_name": safety["database_name"],
                "updateability": safety["updateability"], "can_select": safety["can_select"],
                "can_view_definition": safety["can_view_definition"], "can_update": safety["can_update"],
                "denies_data_writes": safety["denies_data_writes"],
            },
            "procedure_contract": proc,
            "reviewed_branch_matrix": list(BRANCHES),
            "source_object_inventory": _object_inventory(cursor),
            "source_population_summary": _population_summary(cursor),
            "procedure_dependencies": _rows(cursor, """
              SELECT referenced_schema_name,referenced_entity_name,referenced_class_desc,
                     is_schema_bound_reference,is_ambiguous
              FROM sys.sql_expression_dependencies
              WHERE referencing_id=OBJECT_ID(N'Acc.Usp_GetSupplierRemAmount')
              ORDER BY referenced_schema_name,referenced_entity_name
            """),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "migration_invariant": (
                "SupplierBalance = sum(BedAmount) - sum(BesAmount) after the same fiscal, "
                "date, DC, sale-office, SL, settlement-reason, state, and feature-flag gates."
            ),
            "evidence_limits": [
                "This artifact captures the official formula and source matrix, not raw supplier balances.",
                "Source table population does not mean every row contributes to a selected supplier/date scope.",
                "Dynamic flags and temporary crosswalks make a naive UNION replacement unsafe.",
                "Exact balance parity still requires a controlled executable replica or golden supplier cases.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(collect(), ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
