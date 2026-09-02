"""Diagnose the NGT mobile-return to SLE return crosswalk, read-only.

Only catalog metadata, definition fingerprints, and anonymous aggregates are
persisted.  No raw UUID, document number, customer, operator, amount, comment,
or source row is written to the artifact and no stored procedure is executed.
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


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _module_contracts(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE m.definition LIKE '%CustomerCallReturn%'
           OR m.definition LIKE '%BackOfficeReturnOrder%'
           OR m.definition LIKE '%BackOfficeReturnInvoice%'
        ORDER BY s.name,o.name
        """,
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        definition = row.pop("definition")
        normalized = re.sub(r"\s+", " ", definition).casefold()
        replication_call_at = normalized.find("exec ngt_replicatetour")
        commit_at = normalized.find("commit", replication_call_at if replication_call_at >= 0 else 0)
        crosswalk_writeback_at = normalized.find(
            "backofficereturnorderuniqueid = result.backofficeuniqueid"
        )
        result.append(
            {
                **row,
                "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                "definition_sha256": _sha256(definition),
                "reads_ngt_return": bool(
                    re.search(r"\b(from|join)\s+(?:\[?ngt\]?\.)?\[?customercallreturn", normalized)
                ),
                "writes_ngt_return": bool(
                    re.search(r"\b(insert\s+into|update|delete\s+from)\s+(?:\[?ngt\]?\.)?\[?customercallreturn", normalized)
                ),
                "writes_sle_return_order": bool(
                    re.search(r"\b(insert\s+into|update)\s+(?:\[?sle\]?\.)?\[?tblretorder", normalized)
                ),
                "writes_sle_return_sale": bool(
                    re.search(r"\b(insert\s+into|update)\s+(?:\[?sle\]?\.)?\[?tblretsale", normalized)
                ),
                "uses_reverse_customer_call_return_id": "customercallreturnid" in normalized,
                "uses_line_backoffice_return_order": "backofficereturnorder" in normalized,
                "uses_line_backoffice_return_invoice": "backofficereturninvoice" in normalized,
                "has_explicit_transaction": bool(re.search(r"\bbegin\s+tran(?:saction)?\b", normalized)),
                "has_try_catch": "begin try" in normalized and "begin catch" in normalized,
                "has_explicit_rollback": bool(re.search(r"\brollback\s+tran(?:saction)?\b", normalized)),
                "calls_ngt_replicate_tour": bool(re.search(r"\bexec(?:ute)?\s+(?:dbo\.)?ngt_replicatetour\b", normalized)),
                "writes_line_order_crosswalk_from_final_result": (
                    "backofficereturnorderuniqueid = result.backofficeuniqueid" in normalized
                    and "backofficereturnorderref = result.backofficeref" in normalized
                ),
                "return_quantity_comes_from_detail": (
                    "customercallreturnlineqtydetails" in normalized
                    and bool(re.search(r"\bd\.qty\b", normalized))
                ),
                "converts_detail_quantity_by_unit_factor": (
                    "customercallreturnlineqtydetails" in normalized
                    and "convertfactor" in normalized
                ),
                "commits_replication_before_ngt_return_crosswalk_writeback": (
                    replication_call_at >= 0
                    and commit_at > replication_call_at
                    and crosswalk_writeback_at > commit_at
                ),
            }
        )
    return result


def _population(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT
          COUNT_BIG(*) header_count,
          SUM(CASE WHEN IsRemoved=0 AND IsCanceled=0 THEN 1 ELSE 0 END) active_header_count,
          SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_header_count,
          SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END) cancelled_header_count,
          MIN(CreatedDate) first_created_at,
          MAX(CreatedDate) last_created_at,
          MAX(LastUpdate) last_updated_at,
          SUM(CASE WHEN OperationDate='19000101' THEN 1 ELSE 0 END) sentinel_operation_date_count,
          SUM(CASE WHEN ReturnEndTime<ReturnStartTime THEN 1 ELSE 0 END) invalid_time_order_count,
          SUM(CASE WHEN ConcurrencyCheckField>0 THEN 1 ELSE 0 END) versioned_header_count,
          SUM(CASE WHEN ReplacementRegistration=1 THEN 1 ELSE 0 END) replacement_registration_count
        FROM NGT.CustomerCallReturns
        """,
    )[0]


def _lineage(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT
          COUNT_BIG(*) line_count,
          SUM(CASE WHEN h.Id IS NULL THEN 1 ELSE 0 END) orphan_parent_count,
          SUM(CASE WHEN l.IsRemoved=0 THEN 1 ELSE 0 END) active_line_count,
          SUM(CASE WHEN q.line_id IS NOT NULL THEN 1 ELSE 0 END) line_with_return_qty_count,
          SUM(CASE WHEN rq.line_id IS NOT NULL THEN 1 ELSE 0 END) line_with_request_qty_count,
          SUM(CASE WHEN l.BackOfficeReturnOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END) order_uuid_present_count,
          SUM(CASE WHEN l.BackOfficeReturnOrderRef IS NOT NULL THEN 1 ELSE 0 END) order_ref_present_count,
          SUM(CASE WHEN NULLIF(LTRIM(RTRIM(l.BackOfficeReturnOrderNo)),'') IS NOT NULL THEN 1 ELSE 0 END) order_no_present_count,
          SUM(CASE WHEN ro_uuid.ID IS NOT NULL THEN 1 ELSE 0 END) order_uuid_exact_match_count,
          SUM(CASE WHEN ro_ref.ID IS NOT NULL THEN 1 ELSE 0 END) order_ref_exact_match_count,
          SUM(CASE WHEN ro_no.match_count=1 THEN 1 ELSE 0 END) order_no_scope_unique_match_count,
          SUM(CASE WHEN ro_no.match_count>1 THEN 1 ELSE 0 END) order_no_scope_ambiguous_match_count,
          SUM(CASE WHEN l.BackOfficeReturnInvoiceUniqueId IS NOT NULL THEN 1 ELSE 0 END) return_uuid_present_count,
          SUM(CASE WHEN l.BackOfficeReturnInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) return_ref_present_count,
          SUM(CASE WHEN NULLIF(LTRIM(RTRIM(l.BackOfficeReturnInvoiceNo)),'') IS NOT NULL THEN 1 ELSE 0 END) return_no_present_count,
          SUM(CASE WHEN rs_uuid.ID IS NOT NULL THEN 1 ELSE 0 END) return_item_uuid_exact_match_count,
          SUM(CASE WHEN rs_ref.ID IS NOT NULL THEN 1 ELSE 0 END) return_item_ref_exact_match_count,
          SUM(CASE WHEN rs_no.match_count=1 THEN 1 ELSE 0 END) return_no_scope_unique_match_count,
          SUM(CASE WHEN rs_no.match_count>1 THEN 1 ELSE 0 END) return_no_scope_ambiguous_match_count,
          SUM(CASE WHEN l.ItemRef IS NOT NULL THEN 1 ELSE 0 END) generic_item_ref_present_count,
          SUM(CASE WHEN sale_item.ID IS NOT NULL THEN 1 ELSE 0 END) generic_item_ref_sale_item_match_count,
          SUM(CASE WHEN ret_item.ID IS NOT NULL THEN 1 ELSE 0 END) generic_item_ref_return_item_match_count
          ,SUM(CASE WHEN th.history_count>0 THEN 1 ELSE 0 END) tour_history_return_result_line_count
          ,SUM(CASE WHEN thr.ref_match_count>0 THEN 1 ELSE 0 END) tour_history_backoffice_ref_exact_match_line_count
          ,SUM(CASE WHEN thu.uuid_match_count>0 THEN 1 ELSE 0 END) tour_history_backoffice_uuid_exact_match_line_count
        FROM NGT.CustomerCallReturnLines l
        LEFT JOIN NGT.CustomerCallReturns h ON h.Id=l.CustomerCallReturnUniqueId
        LEFT JOIN SLE.tblRetOrderHdr ro_uuid ON ro_uuid.UniqueId=l.BackOfficeReturnOrderUniqueId
        LEFT JOIN SLE.tblRetOrderHdr ro_ref ON ro_ref.ID=l.BackOfficeReturnOrderRef
        OUTER APPLY (
          SELECT COUNT_BIG(*) match_count FROM SLE.tblRetOrderHdr x
          WHERE CONVERT(nvarchar(50),x.RetOrderNo)=LTRIM(RTRIM(l.BackOfficeReturnOrderNo))
            AND x.DCRef=h.DcRef AND x.DCSaleOfficeRef=h.SaleOfficeRef
        ) ro_no
        LEFT JOIN SLE.tblRetSaleItm rs_uuid ON rs_uuid.UniqueId=l.BackOfficeReturnInvoiceUniqueId
        LEFT JOIN SLE.tblRetSaleItm rs_ref ON rs_ref.ID=l.BackOfficeReturnInvoiceRef
        OUTER APPLY (
          SELECT COUNT_BIG(*) match_count FROM SLE.tblRetSaleHdr x
          WHERE CONVERT(nvarchar(50),x.RetSaleNo)=LTRIM(RTRIM(l.BackOfficeReturnInvoiceNo))
            AND x.DCRef=h.DcRef AND x.DCSaleOfficeRef=h.SaleOfficeRef
        ) rs_no
        LEFT JOIN SLE.tblSaleItm sale_item ON sale_item.ID=l.ItemRef
        LEFT JOIN SLE.tblRetSaleItm ret_item ON ret_item.ID=l.ItemRef
        LEFT JOIN (
          SELECT CustomerCallReturnLineUniqueId line_id
          FROM NGT.CustomerCallReturnLineQtyDetails
          WHERE IsRemoved=0 GROUP BY CustomerCallReturnLineUniqueId
        ) q ON q.line_id=l.Id
        LEFT JOIN (
          SELECT CustomerCallReturnLineUniqueId line_id
          FROM NGT.CustomerCallReturnLineRequestQtyDetails
          WHERE IsRemoved=0 GROUP BY CustomerCallReturnLineUniqueId
        ) rq ON rq.line_id=l.Id
        OUTER APPLY (
          SELECT COUNT_BIG(*) history_count
          FROM dbo.TourHistory t
          WHERE t.EntityUniqueId=l.Id AND t.Type IN (2,12)
        ) th
        OUTER APPLY (
          SELECT COUNT_BIG(*) ref_match_count
          FROM dbo.TourHistory t
          WHERE t.EntityUniqueId=l.Id AND t.Type IN (2,12)
            AND t.BackOfficeRef=l.BackOfficeReturnOrderRef
        ) thr
        OUTER APPLY (
          SELECT COUNT_BIG(*) uuid_match_count
          FROM dbo.TourHistory t
          WHERE t.EntityUniqueId=l.Id AND t.Type IN (2,12)
            AND t.BackOfficeUniqueId=l.BackOfficeReturnOrderUniqueId
        ) thu
        """,
    )[0]


def _reverse_links(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblRetOrderHdr WHERE CustomerCallReturnId IS NOT NULL) order_reverse_link_present_count,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetOrderHdr ro JOIN FRU.CustomerCallReturns f ON f.Id=ro.CustomerCallReturnId) order_reverse_link_exact_fru_match_count,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleHdr WHERE CustomerCallReturnId IS NOT NULL) return_reverse_link_present_count,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleHdr rs JOIN FRU.CustomerCallReturns f ON f.Id=rs.CustomerCallReturnId) return_reverse_link_exact_fru_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h JOIN FRU.CustomerCallReturns f ON f.Id=h.Number_ID) ngt_number_id_to_fru_exact_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             JOIN FRU.CustomerCallReturns f ON f.Id=h.Number_ID
             JOIN SLE.tblRetOrderHdr ro ON ro.CustomerCallReturnId=f.Id) ngt_to_fru_to_order_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             JOIN FRU.CustomerCallReturns f ON f.Id=h.Number_ID
             JOIN SLE.tblRetSaleHdr rs ON rs.CustomerCallReturnId=f.Id) ngt_to_fru_to_official_return_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             WHERE TRY_CONVERT(int,h.ReturnRequestBackOfficeId) IS NOT NULL) header_request_id_numeric_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             JOIN SLE.tblRetOrderHdr ro ON ro.ID=TRY_CONVERT(int,h.ReturnRequestBackOfficeId)) header_request_id_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             WHERE TRY_CONVERT(int,h.BackOfficeInvoiceId) IS NOT NULL) header_invoice_id_numeric_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             JOIN SLE.tblSaleHdr s ON s.ID=TRY_CONVERT(int,h.BackOfficeInvoiceId)) source_invoice_id_match_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             WHERE TRY_CONVERT(int,h.BackOfficeInvoiceRef) IS NOT NULL) header_invoice_ref_numeric_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns h
             JOIN SLE.tblSaleHdr s ON s.ID=TRY_CONVERT(int,h.BackOfficeInvoiceRef)) source_invoice_ref_match_count
        """,
    )[0]


def _quantity_and_amount_integrity(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH line_rollup AS (
          SELECT CustomerCallReturnUniqueId,
                 SUM(TotalReturnNetAmount) line_net,
                 SUM(TotalRequestNetAmount) line_request_net
          FROM NGT.CustomerCallReturnLines WHERE IsRemoved=0
          GROUP BY CustomerCallReturnUniqueId
        ), qty AS (
          SELECT CustomerCallReturnLineUniqueId,
                 SUM(Qty) qty, SUM(InitQty) init_qty
          FROM NGT.CustomerCallReturnLineQtyDetails WHERE IsRemoved=0
          GROUP BY CustomerCallReturnLineUniqueId
        )
        SELECT
          SUM(CASE WHEN ABS(h.TotalReturnNetAmount-ISNULL(l.line_net,0))>=0.01 THEN 1 ELSE 0 END) header_line_return_net_mismatch_count,
          SUM(CASE WHEN ABS(h.TotalRequestAmount-h.TotalRequestDiscount+h.TotalRequestCharge+h.TotalRequestTax-ISNULL(l.line_request_net,0))>=0.01 THEN 1 ELSE 0 END) header_line_request_candidate_formula_mismatch_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLines x
             LEFT JOIN qty q ON q.CustomerCallReturnLineUniqueId=x.Id
             WHERE x.IsRemoved=0 AND ABS(x.CurrentQty-ISNULL(q.qty,0))>=0.0001) line_return_qty_mismatch_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLineQtyDetails q
             LEFT JOIN NGT.CustomerCallReturnLines x ON x.Id=q.CustomerCallReturnLineUniqueId
             WHERE x.Id IS NULL) orphan_return_qty_detail_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLineRequestQtyDetails q
             LEFT JOIN NGT.CustomerCallReturnLines x ON x.Id=q.CustomerCallReturnLineUniqueId
             WHERE x.Id IS NULL) orphan_request_qty_detail_count
        FROM NGT.CustomerCallReturns h
        LEFT JOIN line_rollup l ON l.CustomerCallReturnUniqueId=h.Id
        """,
    )[0]


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        population = _population(cursor)
        lineage = _lineage(cursor)
        reverse = _reverse_links(cursor)
        integrity = _quantity_and_amount_integrity(cursor)
        modules = _module_contracts(cursor)
    finally:
        connection.close()

    exact_order_links = max(
        int(lineage["order_uuid_exact_match_count"] or 0),
        int(lineage["order_ref_exact_match_count"] or 0),
    )
    exact_return_links = max(
        int(lineage["return_item_uuid_exact_match_count"] or 0),
        int(lineage["return_item_ref_exact_match_count"] or 0),
        int(reverse["ngt_to_fru_to_official_return_match_count"] or 0),
    )
    historical_result_count = int(lineage["tour_history_return_result_line_count"] or 0)
    historical_result_missing_current_order = min(
        historical_result_count,
        max(0, historical_result_count - exact_order_links),
    )
    summary = {
        "active_mobile_return_header_count": int(population["active_header_count"] or 0),
        "active_mobile_return_line_count": int(lineage["active_line_count"] or 0),
        "exact_current_order_crosswalk_count": exact_order_links,
        "exact_current_official_return_crosswalk_count": exact_return_links,
        "without_current_official_return_count": int(population["active_header_count"] or 0) - exact_return_links,
        "historical_return_order_result_line_count": historical_result_count,
        "historical_result_missing_current_order_count": historical_result_missing_current_order,
        "without_historical_return_order_result_line_count": int(lineage["active_line_count"] or 0) - historical_result_count,
        "sql_module_consumer_count": len(modules),
        "header_line_return_net_mismatch_count": int(integrity["header_line_return_net_mismatch_count"] or 0),
        "current_qty_vs_detail_qty_difference_count": int(integrity["line_return_qty_mismatch_count"] or 0),
    }
    if summary["without_current_official_return_count"] < 0:
        raise RuntimeError("NGT return crosswalk counts are internally inconsistent")

    return {
        "artifact": "varanegar_ngt_mobile_return_crosswalk_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_ANONYMOUS_AGGREGATES_AND_CATALOG_FINGERPRINTS",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "live_ui_actions": 0,
            "identities_raw_ids_document_numbers_amounts_or_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "mobile_population": population,
        "line_crosswalk_candidates": lineage,
        "reverse_and_header_crosswalk_candidates": reverse,
        "quantity_and_amount_integrity": integrity,
        "sql_module_contracts": modules,
        "migration_state_contract": {
            "without_any_tour_history_result": "MOBILE_RETURN_PENDING_OR_UNATTEMPTED",
            "with_exact_tour_history_result_but_missing_current_order": "MOBILE_RETURN_HISTORICAL_RESULT_CURRENT_TARGET_MISSING",
            "without_exact_official_return_link": "MOBILE_RETURN_NOT_AN_OFFICIAL_RETURN_IN_CURRENT_SNAPSHOT",
            "must_not_create": ["official sales return", "inventory voucher", "return credit"],
            "preserve": ["mobile header and line identity hashes", "source scope", "operation/creation/version timestamps", "all candidate refs with provenance"],
            "promotion_gate": "one authoritative, non-ambiguous SLE return link plus owner-approved status semantics and amount/quantity reconciliation",
        },
        "quantity_interpretation": {
            "observed_difference": "NGT line CurrentQty differs from the simple SUM(detail.Qty) for both current lines",
            "deployed_replication_input": "dbo.NGT_DoReplicateTour reads CustomerCallReturnLineQtyDetails.Qty into the return-detail staging path",
            "rule": "do not classify CurrentQty-versus-detail difference as corruption until ProductUnit conversion and the exact command branch are resolved; preserve detail quantity as the evidenced replication input",
        },
        "dual_mobile_model_contract": {
            "ngt_identity_type": "NGT.CustomerCallReturns.Id is uniqueidentifier; Number_ID is the integer legacy bridge candidate",
            "fru_identity_type": "FRU.CustomerCallReturns.Id is the integer model referenced by SLE return headers",
            "sle_reverse_link_target": "SLE.tblRetOrderHdr.CustomerCallReturnId and SLE.tblRetSaleHdr.CustomerCallReturnId formally reference FRU.CustomerCallReturns.Id, not NGT.CustomerCallReturns.Id",
            "rule": "never join the SLE integer reverse link directly to the NGT UUID; traverse an evidenced NGT-to-FRU crosswalk such as exact Number_ID-to-Id and preserve both identities",
        },
        "diagnostic_order": [
            "verify NGT header/line/detail integrity and removed/cancelled/version state",
            "check direct SLE reverse CustomerCallReturnId before weaker copied fields",
            "check line UUID and numeric Ref independently for RetOrder and RetSale",
            "treat Number fields as scoped candidates only; never as globally unique crosswalks",
            "reconcile return quantities and net amounts before promotion",
            "keep unresolved rows pending integration; never manufacture a financial or stock document",
        ],
        "evidence_limits": [
            "Current clone state cannot prove whether a copied BackOffice reference once pointed to a deleted or external database row.",
            "Catalog SQL proves reachable database behavior, not the exact mobile/API runtime branch for either historical row.",
            "A current absence of an SLE link cannot distinguish not-yet-processed, rejected, failed, or externally processed without authoritative status/audit evidence.",
            "No raw identifier, document number, customer, operator, amount, stored procedure, application command or mutation was persisted or executed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
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
