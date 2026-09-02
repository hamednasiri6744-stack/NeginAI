"""Extract the NGT payment-to-BackOffice replication boundary safely.

The extractor reads only catalog metadata, anonymous aggregates, and the text
of dbo.NGT_DoReplicateTour in memory.  It persists hashes, token/statement
profiles, safe database object identifiers, and anonymous state counts only.
It never executes a stored procedure or application command and never stores
SQL definitions, GUID literals, customer/payment rows, credentials, or config
values.
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


PROC_NAMES = (
    "dbo.NGT_DoReplicateTour",
    "dbo.NGT_ReplicateTour",
    "dbo.NGT_CreateReceipt_ForDistInfo",
    "dbo.NGT_CreateSettlement_Merge",
)
TABLES = (
    ("dbo", "TourHistory"),
    ("NGT", "CustomerCallPayments"),
    ("NGT", "CustomerCallPaymentDetails"),
    ("dbo", "Receipt"),
    ("dbo", "RCash"),
    ("Acc", "TblCheque"),
    ("Acc", "TblBankOrders"),
    ("Acc", "tblPayments"),
)

GUID_LITERAL = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])"
)
SQL_OBJECT = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+(?:INTO\s+)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))"
    r"\.\[[A-Za-z_][A-Za-z0-9_]*\]|(?:dbo|NGT|FRU|SLE|GNR|ACC)\."
    r"[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
MUTATION = re.compile(
    r"\b(?P<verb>INSERT(?:\s+INTO)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.IGNORECASE,
)
EXEC_CALL = re.compile(
    r"\bEXEC(?:UTE)?\s+(?:@[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))\.)?"
    r"\[?[A-Za-z_][A-Za-z0-9_]*\]?)",
    re.IGNORECASE,
)

SIGNALS = (
    "CustomerCallPayments",
    "CustomerCallPaymentDetails",
    "BackOfficeReceiptUniqueId",
    "BackOfficeReceiptRef",
    "BackOfficeReceiptNo",
    "TourHistory",
    "Receipt",
    "RCash",
    "TblCheque",
    "TblBankOrders",
    "tblPayments",
    "SettlementTypeId",
    "PaymentApproved",
    "ReceiptRef",
    "Cheque",
    "Pos",
    "PaidAmount",
    "Amount",
    "BEGIN TRAN",
    "COMMIT",
    "ROLLBACK",
    "TRY",
    "CATCH",
    "NGT_CreateReceipt_ForDistInfo",
    "NGT_CreateReceipt_ForHotSale",
    "NGT_CreateReceipt",
    "GetMaxPayNo",
    "#FinalResult",
    "#Payment",
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_object(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def _catalog(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    return _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.max_length,c.precision,c.scale,c.is_nullable
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        WHERE {predicates}
        ORDER BY s.name,t.name,c.column_id
        """,
    )


def _table_counts(cursor: Any) -> list[dict[str, Any]]:
    result = []
    for schema, table in TABLES:
        row = _rows(
            cursor,
            f"SELECT COUNT_BIG(*) row_count FROM [{schema}].[{table}]",
        )[0]
        result.append({"qualified_name": f"{schema}.{table}", **row})
    return result


def _procedure_definition(cursor: Any, qualified_name: str) -> str:
    rows = _rows(
        cursor,
        """
        SELECT sm.definition
        FROM sys.sql_modules sm
        WHERE sm.object_id=OBJECT_ID(%s)
        """,
        (qualified_name,),
    )
    if len(rows) != 1 or not rows[0]["definition"]:
        raise RuntimeError(f"Expected one readable {qualified_name} definition")
    return rows[0]["definition"]


def _position_ratio(position: int, length: int) -> float:
    return round(position / max(length, 1), 6)


def _procedure_profile(qualified_name: str, definition: str) -> dict[str, Any]:
    folded = definition.casefold()
    refs = sorted(
        {_clean_object(m.group("object")) for m in SQL_OBJECT.finditer(definition)},
        key=str.casefold,
    )
    mutations = []
    for ordinal, match in enumerate(MUTATION.finditer(definition), start=1):
        verb = re.sub(r"\s+", "_", match.group("verb").strip().upper())
        mutations.append(
            {
                "ordinal": ordinal,
                "verb": verb,
                "qualified_object": _clean_object(match.group("object")),
                "normalized_position": _position_ratio(match.start(), len(definition)),
            }
        )
    calls = []
    for ordinal, match in enumerate(EXEC_CALL.finditer(definition), start=1):
        value = _clean_object(match.group("object"))
        if value.startswith("@"):
            continue
        calls.append(
            {
                "ordinal": ordinal,
                "qualified_or_local_name": value,
                "normalized_position": _position_ratio(match.start(), len(definition)),
            }
        )
    signal_profiles = []
    for signal in SIGNALS:
        positions = [m.start() for m in re.finditer(re.escape(signal), definition, re.I)]
        signal_profiles.append(
            {
                "signal": signal,
                "occurrence_count": len(positions),
                "first_normalized_position": None
                if not positions
                else _position_ratio(positions[0], len(definition)),
                "last_normalized_position": None
                if not positions
                else _position_ratio(positions[-1], len(definition)),
            }
        )
    return {
        "qualified_name": qualified_name,
        "definition_sha256": _sha256(definition),
        "definition_length": len(definition),
        "guid_literal_occurrence_count": len(GUID_LITERAL.findall(definition)),
        "distinct_guid_literal_count": len({m.group(0).casefold() for m in GUID_LITERAL.finditer(definition)}),
        "safe_sql_object_references": refs,
        "mutation_ledger": mutations,
        "mutation_object_counts": [
            {"qualified_object": name, "mutation_statement_count": count}
            for name, count in sorted(
                Counter(row["qualified_object"] for row in mutations).items(),
                key=lambda item: item[0].casefold(),
            )
        ],
        "exec_call_ledger": calls,
        "signal_profiles": signal_profiles,
        "has_explicit_begin_transaction": bool(re.search(r"\bbegin\s+tran(?:saction)?\b", folded, re.I)),
        "has_explicit_commit": bool(re.search(r"\bcommit(?:\s+tran(?:saction)?)?\b", folded, re.I)),
        "has_explicit_rollback": bool(re.search(r"\brollback(?:\s+tran(?:saction)?)?\b", folded, re.I)),
        "has_try_catch": "begin try" in folded and "begin catch" in folded,
        "throw_or_raiserror_count": len(re.findall(r"\b(?:throw|raiserror)\b", folded, re.I)),
    }


def _dependency_contract(cursor: Any, qualified_name: str) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT referenced_schema_name,referenced_entity_name,referenced_class_desc,
               is_caller_dependent,is_ambiguous
        FROM sys.sql_expression_dependencies
        WHERE referencing_id=OBJECT_ID(%s)
        ORDER BY referenced_schema_name,referenced_entity_name
        """,
        (qualified_name,),
    )
    return [
        {
            **row,
            "is_caller_dependent": bool(row["is_caller_dependent"]),
            "is_ambiguous": bool(row["is_ambiguous"]),
        }
        for row in rows
    ]


def _settlement_guid_contract(
    cursor: Any, definitions: dict[str, str]
) -> dict[str, Any]:
    occurrences: dict[str, dict[str, Any]] = {}
    for procedure, definition in definitions.items():
        for match in GUID_LITERAL.finditer(definition):
            key = match.group(0).casefold()
            item = occurrences.setdefault(key, {"by_procedure": Counter()})
            item["by_procedure"][procedure] += 1
    matched = []
    resolved_non_settlement_count = 0
    unresolved_count = 0
    for guid, occurrence in occurrences.items():
        rows = _rows(
            cursor,
            """
            SELECT b.BaseValueName,bt.BaseTypeName
            FROM NGT.BaseValues b
            LEFT JOIN NGT.BaseTypes bt ON bt.Id=b.BaseTypeId
            WHERE b.Id=CONVERT(uniqueidentifier,%s)
            """,
            (guid,),
        )
        if not rows:
            unresolved_count += 1
            continue
        row = rows[0]
        if row["BaseTypeName"] != "SettlementType":
            resolved_non_settlement_count += 1
            continue
        matched.append(
            {
                "settlement_type": row["BaseValueName"],
                "base_type": row["BaseTypeName"],
                "occurrence_count": sum(occurrence["by_procedure"].values()),
                "procedure_occurrences": [
                    {"qualified_name": name, "occurrence_count": count}
                    for name, count in sorted(
                        occurrence["by_procedure"].items(), key=lambda item: item[0]
                    )
                ],
            }
        )
    return {
        "distinct_guid_literal_count": len(occurrences),
        "matched_settlement_type_count": len(matched),
        "resolved_non_settlement_guid_count": resolved_non_settlement_count,
        "unresolved_guid_count": unresolved_count,
        "settlement_type_profiles": sorted(
            matched, key=lambda row: row["settlement_type"]
        ),
        "guid_literals_persisted": 0,
    }


def _tour_history_catalog_contract(cursor: Any) -> dict[str, Any]:
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_primary_key,i.has_filter,i.filter_definition,
               ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'dbo.TourHistory') AND i.index_id>0
        ORDER BY i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT tr.name trigger_name,tr.is_disabled,tr.is_instead_of_trigger
        FROM sys.triggers tr WHERE tr.parent_id=OBJECT_ID(N'dbo.TourHistory')
        ORDER BY tr.name
        """,
    )
    foreign_keys = _rows(
        cursor,
        """
        SELECT fk.name constraint_name,fk.is_disabled,fk.is_not_trusted,
               pc.name parent_column,rs.name referenced_schema,rt.name referenced_table,
               rc.name referenced_column
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id=OBJECT_ID(N'dbo.TourHistory')
        ORDER BY fk.name,fkc.constraint_column_id
        """,
    )
    return {
        "indexes": [
            {
                **{key: value for key, value in row.items() if key != "filter_definition"},
                "is_unique": bool(row["is_unique"]),
                "is_primary_key": bool(row["is_primary_key"]),
                "has_filter": bool(row["has_filter"]),
                "filter_definition_sha256": None
                if row["filter_definition"] is None
                else _sha256(row["filter_definition"]),
                "filter_targets_type_1": bool(
                    row["filter_definition"]
                    and re.search(
                        r"\[?Type\]?\s*=\s*\(?\s*1\s*\)?",
                        row["filter_definition"],
                        re.I,
                    )
                ),
                "filter_targets_type_10": bool(
                    row["filter_definition"]
                    and re.search(
                        r"\[?Type\]?\s*=\s*\(?\s*10\s*\)?",
                        row["filter_definition"],
                        re.I,
                    )
                ),
                "is_included_column": bool(row["is_included_column"]),
            }
            for row in indexes
        ],
        "triggers": [
            {
                **row,
                "is_disabled": bool(row["is_disabled"]),
                "is_instead_of_trigger": bool(row["is_instead_of_trigger"]),
            }
            for row in triggers
        ],
        "foreign_keys": [
            {
                **row,
                "is_disabled": bool(row["is_disabled"]),
                "is_not_trusted": bool(row["is_not_trusted"]),
            }
            for row in foreign_keys
        ],
    }


def _tour_history_contract(cursor: Any) -> dict[str, Any]:
    return {
        "type_population": _rows(
            cursor,
            """
            SELECT Type history_type,COUNT_BIG(*) history_count,
                   COUNT(DISTINCT EntityUniqueId) distinct_entity_count,
                   SUM(CASE WHEN BackOfficeUniqueId IS NOT NULL THEN 1 ELSE 0 END) with_backoffice_uuid,
                   SUM(CASE WHEN BackOfficeRef IS NOT NULL THEN 1 ELSE 0 END) with_backoffice_ref,
                   SUM(CASE WHEN BackOfficeNo IS NOT NULL THEN 1 ELSE 0 END) with_backoffice_no
            FROM dbo.TourHistory
            GROUP BY Type
            ORDER BY Type
            """,
        ),
        "payment_type_10_crosswalk": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) type_10_history_count,
                   COUNT(DISTINCT h.EntityUniqueId) distinct_entity_count,
                   SUM(CASE WHEN p.Id IS NULL THEN 1 ELSE 0 END) entity_not_current_payment_count,
                   SUM(CASE WHEN p.Id IS NOT NULL THEN 1 ELSE 0 END) entity_is_payment_count,
                   SUM(CASE WHEN p.Id IS NOT NULL AND p.IsRemoved=0 THEN 1 ELSE 0 END) entity_is_active_payment_count,
                   SUM(CASE WHEN r.ReceiptId IS NOT NULL THEN 1 ELSE 0 END) history_uuid_resolves_receipt_count,
                   SUM(CASE WHEN rr.ReceiptId IS NOT NULL THEN 1 ELSE 0 END) history_ref_resolves_receipt_count,
                   SUM(CASE WHEN r.ReceiptId IS NOT NULL AND rr.ReceiptId=r.ReceiptId THEN 1 ELSE 0 END) history_uuid_ref_agree_count,
                   SUM(CASE WHEN r.ReceiptId IS NOT NULL AND rr.ReceiptId=r.ReceiptId
                                  AND h.BackOfficeNo=r.ReceiptNo THEN 1 ELSE 0 END) history_uuid_ref_no_agree_count,
                   SUM(CASE WHEN p.Id IS NOT NULL AND p.BackOfficeReceiptUniqueId=h.BackOfficeUniqueId
                                  AND TRY_CONVERT(int,p.BackOfficeReceiptRef)=h.BackOfficeRef
                                  AND TRY_CONVERT(int,p.BackOfficeReceiptNo)=h.BackOfficeNo THEN 1 ELSE 0 END)
                       payment_and_history_crosswalk_agree_count
            FROM dbo.TourHistory h
            LEFT JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId
            LEFT JOIN dbo.Receipt r ON r.UniqueId=h.BackOfficeUniqueId
            LEFT JOIN dbo.Receipt rr ON rr.ReceiptId=h.BackOfficeRef
            WHERE h.Type=10
            """,
        )[0],
        "payment_perspective": _rows(
            cursor,
            """
            WITH any_history AS (
              SELECT EntityUniqueId,CAST(1 AS int) has_history
              FROM dbo.TourHistory WHERE Type=10 GROUP BY EntityUniqueId
            ), exact_history AS (
              SELECT h.EntityUniqueId,CAST(1 AS int) has_exact_history
              FROM dbo.TourHistory h
              JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId
               AND h.BackOfficeUniqueId=p.BackOfficeReceiptUniqueId
               AND h.BackOfficeRef=TRY_CONVERT(int,p.BackOfficeReceiptRef)
               AND h.BackOfficeNo=TRY_CONVERT(int,p.BackOfficeReceiptNo)
              WHERE h.Type=10 GROUP BY h.EntityUniqueId
            )
            SELECT COUNT_BIG(*) active_payment_count,
                   SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END) with_receipt_uuid_count,
                   SUM(CASE WHEN ah.has_history=1 THEN 1 ELSE 0 END)
                       with_type_10_history_count,
                   SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL
                                  AND ah.has_history IS NULL THEN 1 ELSE 0 END)
                       receipt_crosswalk_without_type_10_history_count,
                   SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NULL
                                  AND ah.has_history=1 THEN 1 ELSE 0 END)
                       type_10_history_without_current_receipt_crosswalk_count,
                   SUM(CASE WHEN eh.has_exact_history=1 THEN 1 ELSE 0 END)
                       exact_type_10_crosswalk_count
            FROM NGT.CustomerCallPayments p
            LEFT JOIN any_history ah ON ah.EntityUniqueId=p.Id
            LEFT JOIN exact_history eh ON eh.EntityUniqueId=p.Id
            WHERE p.IsRemoved=0
            """,
        )[0],
        "type_10_duplicate_entity_groups": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) duplicate_entity_group_count,
                   COALESCE(SUM(history_count),0) histories_in_duplicate_groups,
                   COALESCE(MAX(history_count),0) maximum_histories_per_entity
            FROM (
              SELECT EntityUniqueId,COUNT_BIG(*) history_count
              FROM dbo.TourHistory WHERE Type=10
              GROUP BY EntityUniqueId HAVING COUNT_BIG(*)>1
            ) d
            """,
        )[0],
        "type_10_entity_shape": _rows(
            cursor,
            """
            WITH per_entity AS (
              SELECT h.EntityUniqueId,COUNT_BIG(*) history_count,
                     COUNT(DISTINCT h.BackOfficeUniqueId) distinct_target_uuid_count,
                     SUM(CASE WHEN r.ReceiptId IS NOT NULL THEN 1 ELSE 0 END) existing_target_history_count,
                     COUNT(DISTINCT CASE WHEN r.ReceiptId IS NOT NULL THEN h.BackOfficeUniqueId END)
                         distinct_existing_target_count,
                     MAX(CASE WHEN p.BackOfficeReceiptUniqueId=h.BackOfficeUniqueId
                                   AND TRY_CONVERT(int,p.BackOfficeReceiptRef)=h.BackOfficeRef
                                   AND TRY_CONVERT(int,p.BackOfficeReceiptNo)=h.BackOfficeNo THEN 1 ELSE 0 END)
                         has_exact_current_crosswalk
              FROM dbo.TourHistory h
              JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId AND p.IsRemoved=0
              LEFT JOIN dbo.Receipt r ON r.UniqueId=h.BackOfficeUniqueId
              WHERE h.Type=10
              GROUP BY h.EntityUniqueId
            )
            SELECT CASE WHEN history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END history_multiplicity,
                   CASE WHEN distinct_target_uuid_count=1 THEN 'ONE_TARGET' ELSE 'MULTIPLE_TARGETS' END target_multiplicity,
                   CASE WHEN has_exact_current_crosswalk=1 THEN 'CURRENT_EXACT' ELSE 'NO_CURRENT_EXACT' END current_crosswalk_state,
                   COUNT_BIG(*) payment_count,
                   SUM(history_count) history_count,
                   SUM(existing_target_history_count) existing_target_history_count,
                   SUM(distinct_existing_target_count) distinct_existing_target_count,
                   MAX(history_count) maximum_histories_per_payment,
                   MAX(distinct_target_uuid_count) maximum_targets_per_payment
            FROM per_entity
            GROUP BY CASE WHEN history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END,
                     CASE WHEN distinct_target_uuid_count=1 THEN 'ONE_TARGET' ELSE 'MULTIPLE_TARGETS' END,
                     CASE WHEN has_exact_current_crosswalk=1 THEN 'CURRENT_EXACT' ELSE 'NO_CURRENT_EXACT' END
            ORDER BY history_multiplicity,target_multiplicity,current_crosswalk_state
            """,
        ),
        "type_10_by_settlement_type": _rows(
            cursor,
            """
            WITH h AS (
              SELECT EntityUniqueId,COUNT_BIG(*) history_count,
                     COUNT(DISTINCT BackOfficeUniqueId) distinct_target_count,
                     MAX(CASE WHEN r.ReceiptId IS NOT NULL THEN 1 ELSE 0 END) has_existing_receipt
              FROM dbo.TourHistory th
              LEFT JOIN dbo.Receipt r ON r.UniqueId=th.BackOfficeUniqueId
              WHERE th.Type=10 GROUP BY EntityUniqueId
            )
            SELECT b.BaseValueName settlement_type,COUNT_BIG(*) payment_count,
                   SUM(h.history_count) history_count,
                   SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END) current_crosswalk_count,
                   SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NULL THEN 1 ELSE 0 END) missing_current_crosswalk_count,
                   SUM(CASE WHEN h.distinct_target_count>1 THEN 1 ELSE 0 END) multiple_target_payment_count,
                   SUM(CASE WHEN h.has_existing_receipt=0 THEN 1 ELSE 0 END) no_existing_history_target_count
            FROM h
            JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId AND p.IsRemoved=0
            LEFT JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
            GROUP BY b.BaseValueName
            ORDER BY settlement_type
            """,
        ),
        "type_10_receipt_status": _rows(
            cursor,
            """
            SELECT CASE WHEN r.ReceiptId IS NULL THEN 'TARGET_MISSING'
                        ELSE CONCAT('STATUS_',CONVERT(varchar(12),r.ReceiptStatusId)) END receipt_state,
                   COUNT_BIG(*) history_count,COUNT(DISTINCT h.EntityUniqueId) payment_count,
                   COUNT(DISTINCT h.BackOfficeUniqueId) distinct_target_count
            FROM dbo.TourHistory h
            LEFT JOIN dbo.Receipt r ON r.UniqueId=h.BackOfficeUniqueId
            WHERE h.Type=10
            GROUP BY CASE WHEN r.ReceiptId IS NULL THEN 'TARGET_MISSING'
                          ELSE CONCAT('STATUS_',CONVERT(varchar(12),r.ReceiptStatusId)) END
            ORDER BY receipt_state
            """,
        ),
        "type_10_field_presence": _rows(
            cursor,
            """
            WITH h AS (
              SELECT EntityUniqueId,COUNT_BIG(*) history_count
              FROM dbo.TourHistory WHERE Type=10 GROUP BY EntityUniqueId
            )
            SELECT CASE WHEN h.history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END history_multiplicity,
                   CASE WHEN p.BackOfficeReceiptUniqueId IS NULL THEN 0 ELSE 1 END has_current_uuid,
                   CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NULL THEN 0 ELSE 1 END has_current_ref,
                   CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptNo)),'') IS NULL THEN 0 ELSE 1 END has_current_no,
                   COUNT_BIG(*) payment_count,SUM(h.history_count) history_count
            FROM h JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId AND p.IsRemoved=0
            GROUP BY CASE WHEN h.history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END,
                     CASE WHEN p.BackOfficeReceiptUniqueId IS NULL THEN 0 ELSE 1 END,
                     CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NULL THEN 0 ELSE 1 END,
                     CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptNo)),'') IS NULL THEN 0 ELSE 1 END
            ORDER BY history_multiplicity,has_current_uuid,has_current_ref,has_current_no
            """,
        ),
        "type_10_timeline_by_current_crosswalk": _rows(
            cursor,
            """
            WITH h AS (
              SELECT EntityUniqueId,COUNT_BIG(*) history_count,MIN(CreatedDate) first_created,
                     MAX(CreatedDate) last_created
              FROM dbo.TourHistory WHERE Type=10 GROUP BY EntityUniqueId
            )
            SELECT CONVERT(char(7),h.first_created,120) first_history_month,
                   CASE WHEN h.history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END history_multiplicity,
                   CASE WHEN p.BackOfficeReceiptUniqueId IS NULL THEN 'NO_CURRENT_UUID' ELSE 'CURRENT_UUID' END current_uuid_state,
                   COUNT_BIG(*) payment_count,SUM(h.history_count) history_count
            FROM h JOIN NGT.CustomerCallPayments p ON p.Id=h.EntityUniqueId AND p.IsRemoved=0
            GROUP BY CONVERT(char(7),h.first_created,120),
                     CASE WHEN h.history_count=1 THEN 'ONE_HISTORY' ELSE 'MULTIPLE_HISTORIES' END,
                     CASE WHEN p.BackOfficeReceiptUniqueId IS NULL THEN 'NO_CURRENT_UUID' ELSE 'CURRENT_UUID' END
            ORDER BY first_history_month,history_multiplicity,current_uuid_state
            """,
        ),
        "type_10_exact_duplicate_groups": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) exact_duplicate_group_count,
                   COALESCE(SUM(history_count),0) histories_in_exact_duplicate_groups,
                   COALESCE(MAX(history_count),0) maximum_exact_duplicate_count
            FROM (
              SELECT EntityUniqueId,BackOfficeUniqueId,BackOfficeRef,BackOfficeNo,COUNT_BIG(*) history_count
              FROM dbo.TourHistory WHERE Type=10
              GROUP BY EntityUniqueId,BackOfficeUniqueId,BackOfficeRef,BackOfficeNo
              HAVING COUNT_BIG(*)>1
            ) d
            """,
        )[0],
        "type_10_created_months": _rows(
            cursor,
            """
            SELECT CONVERT(char(7),CreatedDate,120) month_bucket,COUNT_BIG(*) history_count
            FROM dbo.TourHistory
            WHERE Type=10 AND CreatedDate IS NOT NULL
            GROUP BY CONVERT(char(7),CreatedDate,120)
            ORDER BY month_bucket
            """,
        ),
    }


def _sanitize_line(line: str) -> str:
    value = GUID_LITERAL.sub("<GUID>", line)
    value = re.sub(r"N?'(?:''|[^'])*'", "<STRING>", value)
    value = re.sub(r"\b\d{5,}\b", "<NUMBER>", value)
    return value.strip()


def _sanitized_payment_lines(qualified_name: str, definition: str) -> list[str]:
    patterns = (
        "payment",
        "receipt",
        "cheque",
        "cash",
        "bankorder",
        "finalresult",
        "tourhistory",
        "begin tran",
        "commit",
        "rollback",
    )
    lines = definition.splitlines()
    selected: set[int] = set()
    for index, line in enumerate(lines):
        if any(pattern in line.casefold() for pattern in patterns):
            selected.update(range(max(0, index - 8), min(len(lines), index + 9)))
    result = []
    for index in sorted(selected):
        result.append(
            f"{qualified_name}:{index + 1}: {_sanitize_line(lines[index])}"
        )
    return result


def collect() -> dict[str, Any]:
    with _connect() as connection:
        cursor = connection.cursor()
        _assert_safe_target(cursor)
        state = _rows(
            cursor,
            """
            SELECT CONVERT(varchar(30),DATABASEPROPERTYEX(DB_NAME(),'Updateability')) updateability,
                   HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE') can_update
            """,
        )[0]
        catalog = _catalog(cursor)
        counts = _table_counts(cursor)
        definitions = {
            name: _procedure_definition(cursor, name) for name in PROC_NAMES
        }
        procedures = [
            _procedure_profile(name, definitions[name]) for name in PROC_NAMES
        ]
        dependencies = {
            name: _dependency_contract(cursor, name) for name in PROC_NAMES
        }
        settlement_guids = _settlement_guid_contract(cursor, definitions)
        history_catalog = _tour_history_catalog_contract(cursor)
        history = _tour_history_contract(cursor)

    payload = {
        "artifact": "varanegar_ngt_payment_replication_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {"server": SERVER, "database": DATABASE, "approved_target": True},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": state["updateability"],
            "can_update": state["can_update"],
            "denies_data_writes": 1 if state["can_update"] == 0 else 0,
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "guid_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "target_table_count": len(TABLES),
            "catalog_column_count": len(catalog),
            "procedure_count": len(procedures),
            "procedure_definition_length": sum(row["definition_length"] for row in procedures),
            "procedure_mutation_statement_count": sum(len(row["mutation_ledger"]) for row in procedures),
            "procedure_mutation_object_count": len({item["qualified_object"].casefold() for row in procedures for item in row["mutation_ledger"]}),
            "procedure_exec_call_count": sum(len(row["exec_call_ledger"]) for row in procedures),
            "procedure_dependency_count": sum(len(rows) for rows in dependencies.values()),
            "tour_history_type_count": len(history["type_population"]),
            "payment_type_10_history_count": history["payment_type_10_crosswalk"]["type_10_history_count"],
            "settlement_type_literal_count": settlement_guids["matched_settlement_type_count"],
        },
        "target_catalog_columns": catalog,
        "target_table_counts": counts,
        "replication_procedure_profiles": procedures,
        "replication_dependency_contract": dependencies,
        "settlement_type_literal_contract": settlement_guids,
        "tour_history_catalog_contract": history_catalog,
        "tour_history_contract": history,
        "evidence_limits": [
            "Static SQL text proves deployed control-flow shape, not successful runtime execution.",
            "Anonymous current-state aggregates cannot reconstruct the exact chronological attempt history.",
            "Mutation order in source text does not alone prove which conditional branch ran for a specific tour.",
            "GUID literals are counted in memory but never persisted; semantic mapping is a later focused step.",
        ],
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--print-sanitized-payment-lines", action="store_true")
    args = parser.parse_args()
    payload = collect()
    if args.print_sanitized_payment_lines:
        with _connect() as connection:
            cursor = connection.cursor()
            _assert_safe_target(cursor)
            for name in PROC_NAMES:
                for line in _sanitized_payment_lines(
                    name, _procedure_definition(cursor, name)
                ):
                    print(line)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
