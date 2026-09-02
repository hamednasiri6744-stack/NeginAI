"""Extract the NGT mobile-return replication/crosswalk boundary read-only.

Only catalog fingerprints, safe SQL signal profiles and anonymous aggregates
are persisted. SQL definitions, GUIDs, document identifiers, amounts and raw
business rows remain in memory and are never written to the artifact.
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

from extract_varanegar_ngt_return_crosswalk_diagnostic_contract import (
    collect as collect_diagnostic,
)
from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


PROCEDURES = (
    "dbo.NGT_DoReplicateTour",
    "dbo.NGT_ReplicateTour",
    "dbo.NGT_ReplicateReturnOrderMaster",
    "dbo.NGT_CreateRetSale_ForDistInfo",
)
MUTATION = re.compile(
    r"\b(?P<verb>INSERT(?:\s+INTO)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.I,
)
SQL_OBJECT = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+(?:INTO\s+)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.I,
)
GUID_LITERAL = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])"
)
SIGNALS = (
    "CustomerCallReturns",
    "CustomerCallReturnLines",
    "CustomerCallReturnLineQtyDetails",
    "BackOfficeReturnOrderUniqueId",
    "BackOfficeReturnOrderRef",
    "BackOfficeReturnOrderNo",
    "BackOfficeReturnInvoiceUniqueId",
    "BackOfficeReturnInvoiceRef",
    "BackOfficeReturnInvoiceNo",
    "NGT_ReplicateReturnOrderMaster",
    "NGT_CreateRetSale_ForDistInfo",
    "tblRetOrderHdr",
    "tblRetOrderItm",
    "tblRetSaleHdr",
    "tblRetSaleItm",
    "TourHistory",
    "#FinalResult",
    "BEGIN TRAN",
    "COMMIT",
    "ROLLBACK",
    "NOT EXISTS",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def _position(value: int, length: int) -> float:
    return round(value / max(length, 1), 6)


def _definition(cursor: Any, name: str) -> str:
    rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(%s)",
        (name,),
    )
    if len(rows) != 1 or not rows[0]["definition"]:
        raise RuntimeError(f"Expected one readable definition for {name}")
    return rows[0]["definition"]


def _profile(name: str, definition: str) -> dict[str, Any]:
    folded = re.sub(r"\s+", " ", definition).casefold()
    mutations = []
    for ordinal, match in enumerate(MUTATION.finditer(definition), start=1):
        mutations.append(
            {
                "ordinal": ordinal,
                "verb": re.sub(r"\s+", "_", match.group("verb").upper()),
                "qualified_object": _clean(match.group("object")),
                "normalized_position": _position(match.start(), len(definition)),
            }
        )
    replication_at = folded.find("exec ngt_replicatetour")
    if replication_at < 0:
        replication_at = folded.find("exec dbo.ngt_replicatetour")
    commit_at = folded.find("commit", max(replication_at, 0))
    order_writeback_at = folded.find(
        "backofficereturnorderuniqueid = result.backofficeuniqueid"
    )
    invoice_writeback_at = folded.find(
        "backofficereturninvoiceuniqueid = result.backofficeuniqueid"
    )
    return {
        "qualified_name": name,
        "definition_sha256": _sha(definition),
        "definition_length": len(definition),
        "guid_literal_occurrence_count": len(GUID_LITERAL.findall(definition)),
        "safe_sql_object_references": sorted(
            {_clean(match.group("object")) for match in SQL_OBJECT.finditer(definition)},
            key=str.casefold,
        ),
        "mutation_ledger": mutations,
        "mutation_object_counts": [
            {"qualified_object": key, "mutation_statement_count": count}
            for key, count in sorted(
                Counter(row["qualified_object"] for row in mutations).items(),
                key=lambda item: item[0].casefold(),
            )
        ],
        "signal_profiles": [
            {
                "signal": signal,
                "occurrence_count": len(
                    re.findall(re.escape(signal), definition, re.I)
                ),
            }
            for signal in SIGNALS
        ],
        "has_explicit_transaction": bool(
            re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
        ),
        "has_try_catch": "begin try" in folded and "begin catch" in folded,
        "has_explicit_rollback": bool(
            re.search(r"\brollback(?:\s+tran(?:saction)?)?\b", definition, re.I)
        ),
        "commits_replicate_call_before_return_order_writeback": bool(
            replication_at >= 0
            and commit_at > replication_at
            and order_writeback_at > commit_at
        ),
        "commits_replicate_call_before_return_invoice_writeback": bool(
            replication_at >= 0
            and commit_at > replication_at
            and invoice_writeback_at > commit_at
        ),
    }


def _index_contract(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,i.name index_name,i.is_unique,
               i.is_primary_key,i.is_disabled,i.has_filter,i.filter_definition,ic.key_ordinal,
               ic.is_included_column,c.name column_name
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id=i.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE (s.name='dbo' AND t.name='TourHistory')
           OR (s.name='NGT' AND t.name='CustomerCallReturnLines')
        ORDER BY s.name,t.name,i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )


def _history_population(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH grouped AS (
          SELECT Type,EntityUniqueId,COUNT_BIG(*) history_count
          FROM dbo.TourHistory WHERE Type IN (2,12)
          GROUP BY Type,EntityUniqueId
        )
        SELECT t.Type history_type,COUNT_BIG(*) history_count,
               COUNT(DISTINCT t.EntityUniqueId) distinct_entity_count,
               SUM(CASE WHEN l.Id IS NOT NULL THEN 1 ELSE 0 END) current_ngt_line_match_count,
               SUM(CASE WHEN t.Type=2 AND (ro_u.ID IS NOT NULL OR ro_r.ID IS NOT NULL)
                        THEN 1 WHEN t.Type=12 AND (rs_u.ID IS NOT NULL OR rs_r.ID IS NOT NULL)
                        THEN 1 ELSE 0 END) current_target_match_count,
               SUM(CASE WHEN g.history_count>1 THEN 1 ELSE 0 END) history_in_duplicate_entity_group_count,
               SUM(CASE WHEN g.history_count>1 THEN 1 ELSE 0 END) retry_ambiguity_history_count
        FROM dbo.TourHistory t
        JOIN grouped g ON g.Type=t.Type AND g.EntityUniqueId=t.EntityUniqueId
        LEFT JOIN NGT.CustomerCallReturnLines l ON l.Id=t.EntityUniqueId
        LEFT JOIN SLE.tblRetOrderHdr ro_u ON t.Type=2 AND ro_u.UniqueId=t.BackOfficeUniqueId
        LEFT JOIN SLE.tblRetOrderHdr ro_r ON t.Type=2 AND ro_r.ID=t.BackOfficeRef
        LEFT JOIN SLE.tblRetSaleHdr rs_u ON t.Type=12 AND rs_u.UniqueId=t.BackOfficeUniqueId
        LEFT JOIN SLE.tblRetSaleHdr rs_r ON t.Type=12 AND rs_r.ID=t.BackOfficeRef
        WHERE t.Type IN (2,12)
        GROUP BY t.Type
        ORDER BY t.Type
        """,
    )


def _active_disposition(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) active_line_count,
          SUM(CASE WHEN th.history_count=0 THEN 1 ELSE 0 END) without_history_count,
          SUM(CASE WHEN th.history_count>0 THEN 1 ELSE 0 END) with_history_count,
          SUM(CASE WHEN th.history_count>0 AND ro.ID IS NULL THEN 1 ELSE 0 END)
            historical_result_current_order_missing_count,
          SUM(CASE WHEN ro.ID IS NOT NULL THEN 1 ELSE 0 END) current_order_target_count,
          SUM(CASE WHEN l.BackOfficeReturnOrderUniqueId IS NOT NULL
                    OR l.BackOfficeReturnOrderRef IS NOT NULL
                    OR NULLIF(LTRIM(RTRIM(l.BackOfficeReturnOrderNo)),'') IS NOT NULL
                   THEN 1 ELSE 0 END) order_writeback_present_count,
          SUM(CASE WHEN l.BackOfficeReturnInvoiceUniqueId IS NOT NULL
                    OR l.BackOfficeReturnInvoiceRef IS NOT NULL
                    OR NULLIF(LTRIM(RTRIM(l.BackOfficeReturnInvoiceNo)),'') IS NOT NULL
                   THEN 1 ELSE 0 END) invoice_writeback_present_count
        FROM NGT.CustomerCallReturnLines l
        JOIN NGT.CustomerCallReturns h ON h.Id=l.CustomerCallReturnUniqueId
        OUTER APPLY (
          SELECT COUNT_BIG(*) history_count,MAX(BackOfficeUniqueId) target_uuid
          FROM dbo.TourHistory t WHERE t.EntityUniqueId=l.Id AND t.Type=2
        ) th
        LEFT JOIN SLE.tblRetOrderHdr ro ON ro.UniqueId=th.target_uuid
        WHERE h.IsRemoved=0 AND h.IsCanceled=0 AND l.IsRemoved=0
        """,
    )[0]


def collect() -> dict[str, Any]:
    diagnostic = collect_diagnostic()
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        definitions = {name: _definition(cursor, name) for name in PROCEDURES}
        profiles = [_profile(name, definitions[name]) for name in PROCEDURES]
        indexes = _index_contract(cursor)
        history = _history_population(cursor)
        disposition = _active_disposition(cursor)
    finally:
        connection.close()
    do_replicate = next(
        row for row in profiles if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    tour_history_unique = any(
        row["schema_name"] == "dbo"
        and row["table_name"] == "TourHistory"
        and row["is_unique"]
        and not row["is_disabled"]
        and not row["has_filter"]
        and row["key_ordinal"] == 1
        and row["column_name"] == "EntityUniqueId"
        for row in indexes
    )
    return_line_crosswalk_unique = any(
        row["schema_name"] == "NGT"
        and row["table_name"] == "CustomerCallReturnLines"
        and row["is_unique"]
        and not row["is_disabled"]
        and row["column_name"].startswith("BackOfficeReturn")
        for row in indexes
    )
    contract = {
        "do_replicate_tour_commits_before_return_order_writeback": do_replicate[
            "commits_replicate_call_before_return_order_writeback"
        ],
        "do_replicate_tour_commits_before_return_invoice_writeback": do_replicate[
            "commits_replicate_call_before_return_invoice_writeback"
        ],
        "return_tour_history_entity_unique_index_present": tour_history_unique,
        "return_line_backoffice_crosswalk_unique_constraint_present": return_line_crosswalk_unique,
        "active_return_line_count": int(disposition["active_line_count"] or 0),
        "active_line_without_history_count": int(disposition["without_history_count"] or 0),
        "active_line_with_history_count": int(disposition["with_history_count"] or 0),
        "historical_result_current_order_missing_count": int(
            disposition["historical_result_current_order_missing_count"] or 0
        ),
        "current_order_target_count": int(disposition["current_order_target_count"] or 0),
        "order_writeback_present_count": int(disposition["order_writeback_present_count"] or 0),
        "invoice_writeback_present_count": int(disposition["invoice_writeback_present_count"] or 0),
    }
    return {
        "artifact": "varanegar_ngt_return_replication_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "guid_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "procedure_count": len(profiles),
            "active_mobile_return_header_count": diagnostic["summary"][
                "active_mobile_return_header_count"
            ],
            "active_mobile_return_line_count": contract["active_return_line_count"],
            "line_with_history_count": contract["active_line_with_history_count"],
            "line_without_history_count": contract["active_line_without_history_count"],
            "historical_result_current_target_missing_count": contract[
                "historical_result_current_order_missing_count"
            ],
            "current_order_target_count": contract["current_order_target_count"],
            "history_type_count": len(history),
        },
        "replication_contract": contract,
        "tour_history_population": history,
        "index_contract": indexes,
        "procedure_profiles": profiles,
        "diagnostic_source_summary": diagnostic["summary"],
        "evidence_limits": [
            "Current state cannot distinguish unattempted, rejected and failed replication without durable attempt telemetry.",
            "Definition fingerprints and signal order prove a failure window, not the historical cause of either current row.",
            "No procedure, endpoint or managed assembly was executed and no raw identifier, amount or SQL definition was persisted.",
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
    print(json.dumps(payload["replication_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
