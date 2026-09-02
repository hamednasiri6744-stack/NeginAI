"""Extract the read-only sale -> PreVoucher -> batch -> journal crosswalk."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _json_default, _rows

CREATOR_ID = 31
DATE_FROM = "1405/03/01"
DATE_TO = "1405/05/31"
MODULES = (
    ("dbo", "vwCreatePreVoucher_VN_Sale"),
    ("dbo", "usp_DoPreVoucher"),
    ("dbo", "usp_DoExternalVoucher"),
)


def _module_profiles(cursor: Any) -> list[dict[str, Any]]:
    rows = []
    for schema, name in MODULES:
        found = _rows(cursor, """
          SELECT s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,
                 sm.definition
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          JOIN sys.sql_modules sm ON sm.object_id=o.object_id
          WHERE s.name=%s AND o.name=%s
        """, (schema, name))
        if len(found) != 1:
            raise AssertionError(f"expected one module: {schema}.{name}")
        row, definition = found[0], found[0].pop("definition")
        deps = _rows(cursor, """
          SELECT DISTINCT COALESCE(referenced_schema_name,'') referenced_schema,
                 COALESCE(referenced_entity_name,'') referenced_entity
          FROM sys.sql_expression_dependencies
          WHERE referencing_id=OBJECT_ID(%s)
          ORDER BY referenced_schema,referenced_entity
        """, (f"{schema}.{name}",))
        compact = re.sub(r"\s+", " ", definition or "")
        row.update({
            "qualified_name": f"{schema}.{name}",
            "definition_sha256": hashlib.sha256((definition or "").encode("utf-8")).hexdigest(),
            "definition_character_count": len(definition or ""),
            "dependency_count": len(deps),
            "dependencies": [f"{x['referenced_schema']}.{x['referenced_entity']}".strip(".") for x in deps],
            "begin_transaction_signal_count": len(re.findall(r"(?i)\bbegin\s+tran(?:saction)?\b", compact)),
            "commit_signal_count": len(re.findall(r"(?i)\bcommit(?:\s+tran(?:saction)?)?\b", compact)),
            "rollback_signal_count": len(re.findall(r"(?i)\brollback(?:\s+tran(?:saction)?)?\b", compact)),
            "try_catch_signal": bool(re.search(r"(?i)\bbegin\s+try\b", compact) and re.search(r"(?i)\bbegin\s+catch\b", compact)),
            "uses_nolock_signal": bool(re.search(r"(?i)\b(?:with\s*\()?nolock\b", compact)),
            "references_sale_snapshot_signal": "tblSaleVocherHdr".casefold() in compact.casefold(),
            "references_sale_header_signal": "tblSaleHdr".casefold() in compact.casefold(),
            "references_pre_voucher_signal": "PreVoucher".casefold() in compact.casefold(),
            "filters_non_cancelled_sale_signal": bool(re.search(r"(?i)CancelFlag\s*=\s*0", compact)),
            "requires_numbered_sale_signal": bool(re.search(r"(?i)SaleNo\s+is\s+not\s+null", compact)),
            "filters_non_deleted_sale_item_signal": bool(re.search(r"(?i)IsDeleted\s*=\s*0", compact)),
            "definition_or_literal_values_persisted": False,
        })
        rows.append(row)
    return rows


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        if str(context["updateability"]).upper() != "READ_ONLY" or int(context["can_update"] or 0) != 0:
            raise RuntimeError("analysis database is not safely read-only")
        modules = _module_profiles(cursor)
        shapes = _rows(cursor, f"""
          WITH p AS (
            SELECT ReferenceId sale_id,COUNT_BIG(*) line_count,
                   COUNT(DISTINCT ExternalVoucherHeaderId) batch_count,
                   SUM(DebitAmount) debit,SUM(CreditAmount) credit
            FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID}
            GROUP BY ReferenceId
          )
          SELECT s.Status,s.CancelFlag,CASE WHEN s.SaleNo IS NULL THEN 0 ELSE 1 END has_sale_no,
                 COUNT_BIG(*) sale_count,
                 SUM(CASE WHEN p.sale_id IS NOT NULL THEN 1 ELSE 0 END) with_accounting_source_count,
                 SUM(CASE WHEN p.sale_id IS NULL THEN 1 ELSE 0 END) without_accounting_source_count,
                 SUM(CASE WHEN p.batch_count>1 THEN 1 ELSE 0 END) multi_batch_source_count,
                 SUM(CASE WHEN p.debit<>p.credit THEN 1 ELSE 0 END) unbalanced_source_count,
                 SUM(CASE WHEN p.sale_id IS NOT NULL AND p.debit=s.TotalAmount THEN 1 ELSE 0 END) debit_equals_sale_amount_count,
                 SUM(CASE WHEN p.sale_id IS NOT NULL AND p.debit<>s.TotalAmount THEN 1 ELSE 0 END) debit_differs_sale_amount_count,
                 SUM(CASE WHEN s.SaleDate BETWEEN '{DATE_FROM}' AND '{DATE_TO}' THEN 1 ELSE 0 END) recent_sale_count,
                 SUM(CASE WHEN s.SaleDate BETWEEN '{DATE_FROM}' AND '{DATE_TO}' AND p.sale_id IS NOT NULL THEN 1 ELSE 0 END) recent_with_accounting_source_count
          FROM SLE.tblSaleHdr s LEFT JOIN p ON p.sale_id=s.ID
          GROUP BY s.Status,s.CancelFlag,CASE WHEN s.SaleNo IS NULL THEN 0 ELSE 1 END
          ORDER BY s.CancelFlag,s.Status,has_sale_no
        """)
        source_integrity = _rows(cursor, f"""
          WITH p AS (
            SELECT ReferenceId sale_id,COUNT_BIG(*) line_count,
                   COUNT(DISTINCT ExternalVoucherHeaderId) batch_count,
                   SUM(DebitAmount) debit,SUM(CreditAmount) credit
            FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID}
            GROUP BY ReferenceId
          )
          SELECT COUNT_BIG(*) source_count,SUM(line_count) line_count,
                 SUM(CASE WHEN s.ID IS NULL THEN 1 ELSE 0 END) source_without_current_sale_count,
                 SUM(CASE WHEN s.ID IS NOT NULL THEN 1 ELSE 0 END) source_with_current_sale_count,
                 SUM(CASE WHEN s.CancelFlag=1 THEN 1 ELSE 0 END) cancelled_sale_source_count,
                 SUM(CASE WHEN s.CancelFlag=0 THEN 1 ELSE 0 END) active_sale_source_count,
                 SUM(CASE WHEN batch_count>1 THEN 1 ELSE 0 END) source_with_multiple_batch_count,
                 SUM(CASE WHEN debit<>credit THEN 1 ELSE 0 END) unbalanced_source_count
          FROM p LEFT JOIN SLE.tblSaleHdr s ON s.ID=p.sale_id
        """)[0]
        chain = _rows(cursor, f"""
          WITH source_batch AS (
            SELECT DISTINCT ReferenceId sale_id,ExternalVoucherHeaderId batch_id
            FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID}
          ), journal_count AS (
            SELECT ExternalVoucherHeaderId,COUNT_BIG(*) journal_count,
                   SUM(CASE WHEN IsDeleted=0 THEN 1 ELSE 0 END) active_journal_count
            FROM dbo.Voucher WHERE ExternalVoucherHeaderId IS NOT NULL
            GROUP BY ExternalVoucherHeaderId
          )
          SELECT COUNT_BIG(*) source_batch_links,
                 COUNT(DISTINCT sale_id) source_count,
                 COUNT(DISTINCT batch_id) batch_count,
                 SUM(CASE WHEN h.ExternalVoucherHeaderId IS NULL THEN 1 ELSE 0 END) missing_batch_link_count,
                 SUM(CASE WHEN ISNULL(j.journal_count,0)=0 THEN 1 ELSE 0 END) link_without_journal_count,
                 SUM(CASE WHEN ISNULL(j.journal_count,0)>1 THEN 1 ELSE 0 END) link_with_multiple_journal_count,
                 SUM(CASE WHEN ISNULL(j.active_journal_count,0)=1 THEN 1 ELSE 0 END) link_with_one_active_journal_count
          FROM source_batch x
          LEFT JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=x.batch_id
          LEFT JOIN journal_count j ON j.ExternalVoucherHeaderId=x.batch_id
        """)[0]
        batch_grouping = _rows(cursor, f"""
          WITH x AS (
            SELECT ExternalVoucherHeaderId batch_id,COUNT(DISTINCT ReferenceId) source_count
            FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID}
            GROUP BY ExternalVoucherHeaderId
          )
          SELECT CASE WHEN source_count=1 THEN 'SINGLE_SOURCE' ELSE 'MULTI_SOURCE' END source_shape,
                 COUNT_BIG(*) batch_count,MIN(source_count) minimum_sources,MAX(source_count) maximum_sources,
                 SUM(source_count) source_assignments
          FROM x GROUP BY CASE WHEN source_count=1 THEN 'SINGLE_SOURCE' ELSE 'MULTI_SOURCE' END
          ORDER BY source_shape
        """)
        snapshot_crosswalk = _rows(cursor, f"""
          WITH p AS (SELECT DISTINCT ReferenceId sale_id FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID})
          SELECT COUNT_BIG(*) snapshot_count,
                 SUM(CASE WHEN p.sale_id IS NOT NULL THEN 1 ELSE 0 END) snapshot_with_accounting_source_count,
                 SUM(CASE WHEN p.sale_id IS NULL THEN 1 ELSE 0 END) snapshot_without_accounting_source_count,
                 SUM(CASE WHEN s.CancelFlag=1 AND p.sale_id IS NOT NULL THEN 1 ELSE 0 END) cancelled_snapshot_with_accounting_source_count,
                 SUM(CASE WHEN s.CancelFlag=1 AND p.sale_id IS NULL THEN 1 ELSE 0 END) cancelled_snapshot_without_accounting_source_count
          FROM SLE.tblSaleVocherHdr v
          LEFT JOIN SLE.tblSaleHdr s ON s.ID=v.SaleRef
          LEFT JOIN p ON p.sale_id=v.SaleRef
        """)[0]
        active_quadrants = _rows(cursor, f"""
          WITH p AS (SELECT DISTINCT ReferenceId sale_id FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID}),
          v AS (SELECT DISTINCT SaleRef sale_id FROM SLE.tblSaleVocherHdr)
          SELECT CASE WHEN v.sale_id IS NULL THEN 0 ELSE 1 END has_snapshot,
                 CASE WHEN p.sale_id IS NULL THEN 0 ELSE 1 END has_accounting_source,
                 COUNT_BIG(*) sale_count,
                 SUM(CASE WHEN s.SaleDate BETWEEN '{DATE_FROM}' AND '{DATE_TO}' THEN 1 ELSE 0 END) recent_sale_count
          FROM SLE.tblSaleHdr s
          LEFT JOIN p ON p.sale_id=s.ID LEFT JOIN v ON v.sale_id=s.ID
          WHERE s.Status=1 AND s.CancelFlag=0 AND s.SaleNo IS NOT NULL
          GROUP BY CASE WHEN v.sale_id IS NULL THEN 0 ELSE 1 END,
                   CASE WHEN p.sale_id IS NULL THEN 0 ELSE 1 END
          ORDER BY has_snapshot,has_accounting_source
        """)
        monthly_coverage = _rows(cursor, f"""
          WITH p AS (SELECT DISTINCT ReferenceId sale_id FROM dbo.PreVoucher WHERE VoucherCreatorId={CREATOR_ID})
          SELECT LEFT(s.SaleDate,7) business_month,COUNT_BIG(*) sale_count,
                 SUM(CASE WHEN p.sale_id IS NOT NULL THEN 1 ELSE 0 END) with_accounting_source_count,
                 SUM(CASE WHEN p.sale_id IS NULL THEN 1 ELSE 0 END) without_accounting_source_count
          FROM SLE.tblSaleHdr s LEFT JOIN p ON p.sale_id=s.ID
          WHERE s.Status=1 AND s.CancelFlag=0 AND s.SaleNo IS NOT NULL
          GROUP BY LEFT(s.SaleDate,7)
          ORDER BY business_month
        """)
        c = {x["qualified_name"]: x for x in modules}
        contract = {
            "sale_creator_view_references_sale_header": c["dbo.vwCreatePreVoucher_VN_Sale"]["references_sale_header_signal"],
            "sale_creator_view_does_not_reference_sale_snapshot": not c["dbo.vwCreatePreVoucher_VN_Sale"]["references_sale_snapshot_signal"],
            "sale_creator_view_uses_nolock": c["dbo.vwCreatePreVoucher_VN_Sale"]["uses_nolock_signal"],
            "sale_creator_view_selects_only_non_cancelled_numbered_non_deleted_item_state": c["dbo.vwCreatePreVoucher_VN_Sale"]["filters_non_cancelled_sale_signal"] and c["dbo.vwCreatePreVoucher_VN_Sale"]["requires_numbered_sale_signal"] and c["dbo.vwCreatePreVoucher_VN_Sale"]["filters_non_deleted_sale_item_signal"],
            "pre_voucher_writer_references_staging_without_local_transaction": c["dbo.usp_DoPreVoucher"]["references_pre_voucher_signal"] and c["dbo.usp_DoPreVoucher"]["begin_transaction_signal_count"] == 0,
            "external_orchestrator_references_pre_voucher_without_local_transaction": c["dbo.usp_DoExternalVoucher"]["references_pre_voucher_signal"] and c["dbo.usp_DoExternalVoucher"]["begin_transaction_signal_count"] == 0,
        }
        summary = {
            "selected_sql_module_count": len(modules),
            "sale_accounting_source_count": int(source_integrity["source_count"]),
            "sale_accounting_line_count": int(source_integrity["line_count"]),
            "sale_accounting_source_without_current_sale_count": int(source_integrity["source_without_current_sale_count"]),
            "cancelled_sale_accounting_source_count": int(source_integrity["cancelled_sale_source_count"]),
            "sale_accounting_source_with_multiple_batch_count": int(source_integrity["source_with_multiple_batch_count"]),
            "unbalanced_sale_accounting_source_count": int(source_integrity["unbalanced_source_count"]),
            "accounting_link_without_journal_count": int(chain["link_without_journal_count"]),
            "accounting_link_with_multiple_journal_count": int(chain["link_with_multiple_journal_count"]),
            "snapshot_without_accounting_source_count": int(snapshot_crosswalk["snapshot_without_accounting_source_count"]),
        }
        return {
            "artifact": "varanegar_sale_accounting_crosswalk_boundary",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(contract.values()) else "FAIL",
            "scope": {"server": "127.0.0.1", "database": "NeginPakhsh_WebDev"},
            "safety": {"mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_ACCOUNTING_AGGREGATES", "database_updateability": context["updateability"], "can_select": context["can_select"], "can_view_definition": context["can_view_definition"], "can_update": context["can_update"], "denies_data_writes": 1, "stored_procedure_view_form_or_application_command_executions": 0, "sale_snapshot_accounting_customer_user_host_or_raw_values_persisted": 0, "sql_definitions_comments_account_codes_or_business_identifiers_persisted": 0, "source_or_target_state_changed": 0},
            "summary": summary,
            "sql_module_profiles": modules,
            "static_sale_accounting_contract": contract,
            "sale_state_accounting_shapes": shapes,
            "sale_accounting_source_integrity": source_integrity,
            "sale_batch_journal_chain": chain,
            "sale_batch_source_grouping": batch_grouping,
            "sale_snapshot_accounting_crosswalk": snapshot_crosswalk,
            "active_final_snapshot_accounting_quadrants": active_quadrants,
            "active_final_accounting_coverage_by_business_month": monthly_coverage,
            "evidence_limits": [
                "Balanced source groups and intact links prove current reconciliation, not business correctness of account dimensions or historical rule versions.",
                "Retained accounting for cancelled sales is historical lineage and must not be called an active receivable without a business rule.",
                "Current creator configuration cannot reconstruct the rule or grouping version used by every historical batch.",
                "No procedure, view, form or command was executed and no raw sale, snapshot, journal, customer, account, user, host or error value was persisted.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["static_sale_accounting_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
