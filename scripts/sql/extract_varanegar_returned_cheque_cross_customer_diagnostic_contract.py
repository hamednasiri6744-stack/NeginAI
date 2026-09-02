"""Prove the cross-customer returned-cheque settlement contract safely.

Only catalog definitions and anonymous aggregates are read from the read-only
clone.  Existing non-executing IL evidence is consumed for the UI boundary.
No identifiers, party names, cheque numbers, comments, or raw rows are emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
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


MODULE_NAMES = (
    "Usp_CreatePaymentsFromOthersCust",
    "trg_Settlement_tblPayments",
    "Usp_CheckRemRetChequeRef",
    "USP_SDSNet_RetChequeForSettlement_GetList",
    "UspPaymentInsertIsValid_Settlement",
    "UspPaymentInsert_Settlement",
    "UspPaymentParentCustomerInsert_Settlement",
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold()


def _module_contract(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    quoted = ",".join("N'" + name.replace("'", "''") + "'" for name in MODULE_NAMES)
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
        normalized = _normalize(definition)
        public.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "references_ret_cheque": "retchequeref" in normalized,
                "references_parent_customer": "parentcustomer" in normalized,
                "references_other_customer_sale": "salerefforothercust" in normalized,
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
            }
        )
    return public, definitions


def _schema_contract(cursor: Any) -> dict[str, Any]:
    return {
        "columns": _rows(
            cursor,
            """
            SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
                   TYPE_NAME(c.user_type_id) data_type,c.is_nullable
            FROM sys.columns c
            JOIN sys.tables t ON t.object_id=c.object_id
            JOIN sys.schemas s ON s.schema_id=t.schema_id
            WHERE c.object_id IN (OBJECT_ID(N'Acc.TblCheque'),
                                  OBJECT_ID(N'Acc.tblPayments'),
                                  OBJECT_ID(N'GNR.tblCust'))
              AND c.name IN ('CustRef','ManualCustRef','ChqRef','RetChequeRef',
                             'SaleRef','SaleRefForOtherCust','PaymentRef','ReferenceId',
                             'ParentCustomerId','IsParent','CustGroupRef',
                             'AccountingCustGroupRef','Amount','PayTypeRef','PayDate')
            ORDER BY s.name,t.name,c.column_id
            """,
        ),
        "payment_types": _rows(
            cursor,
            """
            SELECT ID,Code,Name,PlusMinus,IsDisabled,RefToInvoice,UseInSettlement,
                   IsAutomatic,FactorRef,ProcessTypeId
            FROM Acc.tblPayType
            WHERE ID IN (2,11,14,1006,1008)
            ORDER BY ID
            """,
        ),
    }


def _aggregate_contract(cursor: Any) -> dict[str, Any]:
    by_pay_type = _rows(
        cursor,
        """
        WITH m AS (
          SELECT p.*,c.CustRef cheque_cust,c.ManualCustRef
          FROM Acc.tblPayments p
          JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
          WHERE p.CustRef<>c.CustRef
        )
        SELECT PayTypeRef,COUNT_BIG(*) rows,COUNT(DISTINCT RetChequeRef) cheques,
               SUM(Amount) amount,
               SUM(CASE WHEN SaleRef IS NOT NULL THEN 1 ELSE 0 END) sale_linked,
               SUM(CASE WHEN SaleRefForOtherCust IS NOT NULL THEN 1 ELSE 0 END)
                    other_sale_linked,
               SUM(CASE WHEN ReferenceId IS NOT NULL THEN 1 ELSE 0 END)
                    reference_linked,
               SUM(CASE WHEN PaymentRef IS NOT NULL THEN 1 ELSE 0 END)
                    payment_linked
        FROM m GROUP BY PayTypeRef ORDER BY rows DESC
        """,
    )
    relationships = _rows(
        cursor,
        """
        WITH m AS (
          SELECT p.*,c.CustRef cheque_cust,c.ManualCustRef
          FROM Acc.tblPayments p
          JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
          WHERE p.CustRef<>c.CustRef
        )
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT RetChequeRef) cheques,
               SUM(CASE WHEN sh.CustRef=m.CustRef THEN 1 ELSE 0 END)
                    sale_matches_payment_customer,
               SUM(CASE WHEN sh.CustRef=m.cheque_cust THEN 1 ELSE 0 END)
                    sale_matches_cheque_customer,
               SUM(CASE WHEN sh.CustRef=m.ManualCustRef THEN 1 ELSE 0 END)
                    sale_matches_manual_customer,
               SUM(CASE WHEN pc.ParentCustomerId=m.cheque_cust THEN 1 ELSE 0 END)
                    payment_customer_child_of_cheque_customer,
               SUM(CASE WHEN cc.ParentCustomerId=m.CustRef THEN 1 ELSE 0 END)
                    cheque_customer_child_of_payment_customer,
               SUM(CASE WHEN pc.ParentCustomerId IS NOT NULL
                         AND pc.ParentCustomerId=cc.ParentCustomerId THEN 1 ELSE 0 END)
                    same_parent,
               SUM(CASE WHEN ISNULL(pc.IsParent,0)=1 THEN 1 ELSE 0 END)
                    payment_customer_is_parent,
               SUM(CASE WHEN ISNULL(cc.IsParent,0)=1 THEN 1 ELSE 0 END)
                    cheque_customer_is_parent
        FROM m
        LEFT JOIN SLE.tblSaleHdr sh ON sh.ID=m.SaleRef
        LEFT JOIN GNR.tblCust pc ON pc.ID=m.CustRef
        LEFT JOIN GNR.tblCust cc ON cc.ID=m.cheque_cust
        """,
    )[0]
    allocation_explanation = _rows(
        cursor,
        """
        WITH m AS (
          SELECT p.*,c.CustRef cheque_cust
          FROM Acc.tblPayments p
          JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
          WHERE p.CustRef<>c.CustRef
        ),a AS (
          SELECT ChqRef,SaleRef,CustRef,SUM(Amount) allocated_amount,
                 COUNT_BIG(*) allocated_rows
          FROM Acc.tblPayments WHERE ChqRef IS NOT NULL
          GROUP BY ChqRef,SaleRef,CustRef
        )
        SELECT COUNT_BIG(*) mismatch_rows,
               SUM(CASE WHEN a.ChqRef IS NOT NULL THEN 1 ELSE 0 END)
                    exact_cheque_sale_customer_allocation_match,
               SUM(CASE WHEN a.ChqRef IS NULL THEN 1 ELSE 0 END) unexplained_rows,
               SUM(CASE WHEN m.SaleRef IS NULL THEN 1 ELSE 0 END) null_sale_rows
        FROM m LEFT JOIN a
          ON a.ChqRef=m.RetChequeRef
         AND ISNULL(a.SaleRef,0)=ISNULL(m.SaleRef,0)
         AND a.CustRef=m.CustRef
        """,
    )[0]
    pair_reconciliation = _rows(
        cursor,
        """
        WITH a AS (
          SELECT ChqRef,SaleRef,CustRef,SUM(Amount) allocated_amount
          FROM Acc.tblPayments WHERE ChqRef IS NOT NULL
          GROUP BY ChqRef,SaleRef,CustRef
        ),s AS (
          SELECT RetChequeRef,SaleRef,CustRef,SUM(Amount) settled_amount,
                 COUNT_BIG(*) settlement_rows
          FROM Acc.tblPayments WHERE RetChequeRef IS NOT NULL
          GROUP BY RetChequeRef,SaleRef,CustRef
        ),x AS (
          SELECT s.*,a.allocated_amount
          FROM s JOIN Acc.TblCheque c ON c.ID=s.RetChequeRef
          LEFT JOIN a ON a.ChqRef=s.RetChequeRef
                     AND ISNULL(a.SaleRef,0)=ISNULL(s.SaleRef,0)
                     AND a.CustRef=s.CustRef
          WHERE s.CustRef<>c.CustRef
        )
        SELECT COUNT_BIG(*) pairs,SUM(settlement_rows) rows,
               SUM(CASE WHEN allocated_amount IS NULL THEN 1 ELSE 0 END)
                    pairs_without_exact_allocation,
               SUM(CASE WHEN allocated_amount IS NOT NULL
                         AND settled_amount>allocated_amount THEN 1 ELSE 0 END)
                    over_settled_pairs,
               SUM(CASE WHEN allocated_amount=settled_amount THEN 1 ELSE 0 END)
                    fully_settled_pairs,
               SUM(CASE WHEN allocated_amount>settled_amount THEN 1 ELSE 0 END)
                    partially_settled_pairs,
               MAX(CASE WHEN allocated_amount IS NOT NULL
                        THEN ABS(allocated_amount-settled_amount) END)
                    maximum_pair_remaining
        FROM x
        """,
    )[0]
    by_month = _rows(
        cursor,
        """
        WITH m AS (
          SELECT p.*,c.CustRef cheque_cust
          FROM Acc.tblPayments p
          JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
          WHERE p.CustRef<>c.CustRef
        )
        SELECT AccYear,LEFT(PayDate,7) month_bucket,COUNT_BIG(*) rows,
               COUNT(DISTINCT RetChequeRef) cheques,SUM(Amount) amount
        FROM m GROUP BY AccYear,LEFT(PayDate,7)
        ORDER BY AccYear,month_bucket
        """,
    )
    by_current_state = _rows(
        cursor,
        """
        WITH m AS (
          SELECT p.*,c.CustRef cheque_cust
          FROM Acc.tblPayments p
          JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
          WHERE p.CustRef<>c.CustRef
        )
        SELECT h.StatRef,COUNT_BIG(*) rows,COUNT(DISTINCT m.RetChequeRef) cheques,
               SUM(m.Amount) amount
        FROM m LEFT JOIN Acc.tblChqHist h
          ON h.ChqRef=m.RetChequeRef AND h.IsLast=1
        GROUP BY h.StatRef ORDER BY h.StatRef
        """,
    )
    return {
        "by_payment_type": by_pay_type,
        "relationship_profile": relationships,
        "source_allocation_explanation": allocation_explanation,
        "cheque_sale_customer_pair_reconciliation": pair_reconciliation,
        "by_business_month": by_month,
        "by_current_cheque_state": by_current_state,
    }


def _ui_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    forms = payload.get("forms", payload.get("form_contracts", []))
    target = next(
        (row for row in forms if row.get("type") == "TreasuryOld.Forms.frmSettlementByCustomer"),
        None,
    )
    if target is None:
        # Current evidence nests the entries below a top-level contract list.
        candidates: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                if value.get("type") == "TreasuryOld.Forms.frmSettlementByCustomer":
                    candidates.append(value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)
        target = candidates[0] if candidates else None
    if target is None:
        raise RuntimeError("frmSettlementByCustomer missing from static form evidence")
    contract = target.get("contract", {})
    calls = set(contract.get("external_calls", [])) | set(
        contract.get("first_party_external_calls", [])
    )
    required = {
        "TreasuryOld.DataLayer.RChequeAdapter.GetRetRChequesForSettlement",
        "TreasuryOld.DataLayer.Settlement.set_RetChequeRef",
        "TreasuryOld.DataLayer.Transaction.Commit",
        "TreasuryOld.DataLayer.Transaction.RollBack",
    }
    missing = sorted(required - calls)
    if missing:
        raise RuntimeError(f"Settlement UI contract drift: {missing}")
    return {
        "source_path": str(path),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "form_type": target["type"],
        "page_shape": target.get("page_shape"),
        "write_like_methods": contract.get("write_like_methods", []),
        "verified_calls": sorted(required),
        "interpretation": "the settlement form selects returned-cheque candidates, carries RetChequeRef and has explicit commit/rollback signals",
    }


def _finding(
    finding_id: str,
    title: str,
    severity: str,
    evidence: list[str],
    implication: str,
    action: str,
    confidence: str = "HIGH_STATIC_AND_AGGREGATE",
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence,
        "implication": implication,
        "diagnostic_or_migration_action": action,
    }


def collect(form_contracts: Path) -> dict[str, Any]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            safety = _assert_safe_target(cursor)
            modules, definitions = _module_contract(cursor)
            schema = _schema_contract(cursor)
            aggregates = _aggregate_contract(cursor)
    ui = _ui_contract(form_contracts)
    normalized = {name: _normalize(value) for name, value in definitions.items()}
    checks = {
        "other_customer_payment_path_is_explicit": (
            "salerefforothercust" in normalized.get("Acc.Usp_CreatePaymentsFromOthersCust", "")
        ),
        "validation_is_per_cheque_and_sale": all(
            token in normalized.get("dbo.Usp_CheckRemRetChequeRef", "")
            for token in ("chqref=@retchequeref", "saleref", "retchequeref=@retchequeref")
        ),
        "selection_remaining_is_per_cheque_and_sale": all(
            token in normalized.get("dbo.USP_SDSNet_RetChequeForSettlement_GetList", "")
            for token in ("p.retchequeref=c.id", "p.saleref=t.saleref")
        ),
        "parent_customer_path_preserves_ret_cheque": (
            normalized.get("dbo.UspPaymentParentCustomerInsert_Settlement", "").count("@retchequeref") >= 5
        ),
        "generic_insert_preserves_ret_cheque": (
            "@retsaleref, @retchequeref" in normalized.get("dbo.UspPaymentInsert_Settlement", "")
        ),
    }
    explanation = aggregates["source_allocation_explanation"]
    pairs = aggregates["cheque_sale_customer_pair_reconciliation"]
    relationships = aggregates["relationship_profile"]
    if not (
        all(checks.values())
        and explanation["mismatch_rows"] == 49
        and explanation["exact_cheque_sale_customer_allocation_match"] == 49
        and explanation["unexplained_rows"] == 0
        and pairs["pairs_without_exact_allocation"] == 0
        and pairs["over_settled_pairs"] == 0
        and relationships["sale_matches_payment_customer"] == 48
    ):
        raise RuntimeError("Cross-customer returned-cheque contract drift")

    findings = [
        _finding(
            "RCX-001",
            "The 49 cross-customer rows are explained allocations, not customer corruption",
            "CRITICAL",
            [
                "49 of 49 rows match an original allocation on cheque, sale and payment customer",
                "unexplained rows=0",
                "48 sale-linked rows match the invoice customer and zero match the cheque owner",
            ],
            "Reassigning these rows to TblCheque.CustRef would move valid invoice settlement to the cheque owner and corrupt customer balances.",
            "Preserve cheque owner, allocation customer and sale/customer relationship as distinct roles; never normalize them to one CustRef.",
        ),
        _finding(
            "RCX-002",
            "Returned-cheque remaining amount is controlled per cheque and sale allocation",
            "HIGH",
            [
                "Usp_CheckRemRetChequeRef filters both ChqRef/RetChequeRef and SaleRef",
                "USP_SDSNet_RetChequeForSettlement_GetList subtracts settlements for the same cheque and sale",
                "31 anonymous cheque-sale-customer pairs have zero over-settlement",
            ],
            "A cheque-only balance is insufficient for allocating returned-cheque debt back to invoices.",
            "Model an immutable ChequeSaleAllocation and settle against that key transactionally.",
        ),
        _finding(
            "RCX-003",
            "Cross-party invoice settlement is an explicit Varanegar feature",
            "HIGH",
            [
                "Acc.Usp_CreatePaymentsFromOthersCust writes SaleRefForOtherCust",
                "the parent-customer procedure emits linked accounting legs and preserves RetChequeRef",
                "the settlement form carries RetChequeRef through an explicit transaction boundary",
            ],
            "Flattening linked payment legs can preserve totals while losing counterparty and audit provenance.",
            "Migrate linked legs, reference provenance and role labels; validate net-zero transfer plus invoice effect.",
        ),
        _finding(
            "RCX-004",
            "ManualCustRef is not the authoritative allocation customer",
            "HIGH",
            [
                "only 2 of 49 rows match ManualCustRef",
                "all 49 match the original payment allocation customer",
                "official checks operate on payment SaleRef rather than ManualCustRef",
            ],
            "Using ManualCustRef as a repair key would silently misassign most cross-party settlements.",
            "Keep ManualCustRef as source metadata only; use the original cheque-sale-payment allocation as authority.",
        ),
        _finding(
            "RCX-005",
            "Current aggregate proof does not identify the operator's business reason",
            "MEDIUM",
            [
                "the rows are anonymous and historical",
                "static code proves supported branches, not the exact operator intent for each document",
                "the latest observed row bucket is 1404/12",
            ],
            "Technical validity does not replace an auditable business label for migration or support screens.",
            "Expose allocation provenance and reason/linked-document context; request review only when that provenance is missing or inconsistent.",
            confidence="MEDIUM_STATIC_AND_CURRENT_STATE_AGGREGATE",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    return {
        "artifact": "varanegar_returned_cheque_cross_customer_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_EXISTING_NONEXECUTING_IL_EVIDENCE",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "identities_or_raw_business_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "finding_count": len(findings),
            "finding_severity_counts": dict(sorted(severities.items())),
            "cross_customer_rows": explanation["mismatch_rows"],
            "cross_customer_cheques": relationships["cheques"],
            "exact_original_allocation_matches": explanation[
                "exact_cheque_sale_customer_allocation_match"
            ],
            "unexplained_rows": explanation["unexplained_rows"],
            "allocation_pairs": pairs["pairs"],
            "over_settled_pairs": pairs["over_settled_pairs"],
            "previous_anomaly_interpretation_valid": False,
            "official_authority_key": "RetChequeRef + SaleRef + allocation CustRef",
            "stored_procedure_or_application_commands_executed": 0,
        },
        "semantic_correction": {
            "wrong_model": "tblPayments.CustRef must always equal TblCheque.CustRef for RetChequeRef settlements",
            "evidenced_model": "the cheque owner and invoice allocation customer are distinct roles; returned-cheque settlement follows the original cheque+sale+customer allocation",
            "previous_false_positive": "49 payment rows across 17 cheques",
            "migration_rule": "preserve cross-party allocation provenance; do not quarantine or reassign solely because payment customer differs from cheque owner",
            "review_trigger": "missing original allocation, sale/customer inconsistency, over-settlement, broken linked leg or missing provenance",
        },
        "incident_findings": findings,
        "schema_contract": schema,
        "aggregate_contract": aggregates,
        "sql_module_contracts": modules,
        "verified_sql_contracts": checks,
        "ui_contract": ui,
        "diagnostic_order": [
            "separate cheque owner, manual source customer, allocation customer and invoice customer",
            "find the original ChqRef allocation for the same cheque, sale and customer",
            "reconcile allocation minus all RetChequeRef settlements at the same key",
            "verify invoice customer, payment type, current cheque state and linked accounting legs",
            "classify as defect only when provenance is missing, inconsistent or over-settled",
        ],
        "evidence_limits": [
            "Current-state aggregates do not retain every historical edit or operator explanation.",
            "Static SQL and IL evidence proves supported code paths, not the exact runtime branch of each old record.",
            "Party identities, cheque numbers, sale IDs, comments and raw payment rows are intentionally excluded.",
            "No form, stored procedure, transaction, assembly or mutation was executed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.form_contracts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
