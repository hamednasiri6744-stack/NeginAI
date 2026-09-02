"""Diagnose received-cheque Pay projection and legal-routing semantics safely."""

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
    "DoRCheque_AddRChequeHistory",
    "DoRCheque_CessionToOther",
    "Pay2",
    "USP_SDSNET_PayRCheque_GetList",
    "usp_sdsnet_RChequeChangeStatus_BeforeSave",
    "usp_sdsnet_RChequeChangeStatus_Save",
    "LegalTypeModel",
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold()


def _modules(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
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
        public.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "references_master_pay_id": "tblcheque" in definition.casefold()
                and "payid" in definition.casefold(),
                "references_history_pay_id": "payid2" in definition.casefold(),
                "references_legal_type": "legaltype" in definition.casefold(),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
            }
        )
    return public, definitions


def _schema(cursor: Any) -> dict[str, Any]:
    return {
        "relevant_columns": _rows(
            cursor,
            """
            SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
                   TYPE_NAME(c.user_type_id) data_type,c.is_nullable
            FROM sys.columns c
            JOIN sys.tables t ON t.object_id=c.object_id
            JOIN sys.schemas s ON s.schema_id=t.schema_id
            WHERE c.object_id IN (OBJECT_ID(N'Acc.TblCheque'),
                                  OBJECT_ID(N'Acc.tblChqHist'),
                                  OBJECT_ID(N'Acc.tblChqChangeStatus'))
              AND c.name IN ('PayId','PayId2','StatRef','PreviousStatRef','IsLast',
                             'ChangeDate','TransitionId','PersonnelId','LegalType',
                             'ChqChangeStatusRef','RChequeWorkflowId','ConfirmedDate')
            ORDER BY s.name,t.name,c.column_id
            """,
        ),
        "legal_type_reference": _rows(
            cursor, "SELECT * FROM FRU.LegalTypeModel ORDER BY LegalType"
        ),
        "legal_workflows": _rows(
            cursor,
            """
            SELECT RChequeAllWorkflowId,OldStatusId,NewStatusId,IsActiveInForm,
                   RChequeAllWorkflowCode,ProcessTypeId
            FROM dbo.RChequeAllWorkflow
            WHERE NewStatusId=9 OR OldStatusId=9
            ORDER BY OldStatusId,NewStatusId,RChequeAllWorkflowId
            """,
        ),
    }


def _aggregates(cursor: Any) -> dict[str, Any]:
    status7 = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) cheques,
               SUM(CASE WHEN c.PayId=h.PayId2 THEN 1 ELSE 0 END)
                    master_matches_history,
               SUM(CASE WHEN c.PayId IS NULL AND h.PayId2 IS NOT NULL THEN 1 ELSE 0 END)
                    master_missing_history_present,
               SUM(CASE WHEN c.PayId IS NOT NULL AND h.PayId2 IS NULL THEN 1 ELSE 0 END)
                    master_present_history_missing,
               SUM(CASE WHEN c.PayId IS NOT NULL AND h.PayId2 IS NOT NULL
                         AND c.PayId<>h.PayId2 THEN 1 ELSE 0 END) conflicting_links,
               SUM(CASE WHEN ph.PayId IS NULL THEN 1 ELSE 0 END) history_orphan,
               SUM(CASE WHEN pc.PayId IS NULL AND c.PayId IS NOT NULL THEN 1 ELSE 0 END)
                    master_orphan
        FROM Acc.TblCheque c
        JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        LEFT JOIN dbo.Pay ph ON ph.PayId=h.PayId2
        LEFT JOIN dbo.Pay pc ON pc.PayId=c.PayId
        WHERE h.StatRef=7
        """,
    )[0]
    missing_master = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) cheques,
               SUM(CASE WHEN p.PayId IS NOT NULL THEN 1 ELSE 0 END)
                    valid_history_pay_links,
               SUM(CASE WHEN p.PayStatusId=1 THEN 1 ELSE 0 END) draft_pay_links,
               SUM(CASE WHEN p.PayStatusId=2 THEN 1 ELSE 0 END) approved_pay_links,
               MIN(h.ChangeDate) minimum_change_date,
               MAX(h.ChangeDate) maximum_change_date
        FROM Acc.TblCheque c
        JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        LEFT JOIN dbo.Pay p ON p.PayId=h.PayId2
        WHERE h.StatRef=7 AND c.PayId IS NULL
        """,
    )[0]
    missing_sequences = _rows(
        cursor,
        """
        WITH target AS (
          SELECT c.ID
          FROM Acc.TblCheque c
          JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
          WHERE h.StatRef=7 AND c.PayId IS NULL
        ),seq AS (
          SELECT t.ID,
                 STRING_AGG(CONVERT(varchar(10),h.StatRef),',')
                   WITHIN GROUP (ORDER BY h.ID) state_sequence,
                 STRING_AGG(CASE WHEN h.PayId2 IS NULL THEN '0' ELSE '1' END,',')
                   WITHIN GROUP (ORDER BY h.ID) history_pay_presence_sequence,
                 COUNT_BIG(*) history_count
          FROM target t JOIN Acc.tblChqHist h ON h.ChqRef=t.ID
          GROUP BY t.ID
        )
        SELECT state_sequence,history_pay_presence_sequence,history_count,
               COUNT_BIG(*) cheques
        FROM seq
        GROUP BY state_sequence,history_pay_presence_sequence,history_count
        ORDER BY cheques DESC
        """,
    )
    legal = _rows(
        cursor,
        """
        SELECT ISNULL(h.LegalType,-1) legal_type,COUNT_BIG(*) cheques,
               SUM(CASE WHEN h.PersonnelId IS NOT NULL THEN 1 ELSE 0 END)
                    personnel_present,
               SUM(CASE WHEN h.ChqChangeStatusRef IS NOT NULL THEN 1 ELSE 0 END)
                    change_status_ref_present,
               SUM(CASE WHEN h.TransitionId IS NOT NULL THEN 1 ELSE 0 END)
                    transition_present,
               MIN(h.ChangeDate) minimum_change_date,
               MAX(h.ChangeDate) maximum_change_date
        FROM Acc.tblChqHist h
        WHERE h.IsLast=1 AND h.StatRef=9
        GROUP BY ISNULL(h.LegalType,-1)
        ORDER BY legal_type
        """,
    )
    legal_by_month = _rows(
        cursor,
        """
        SELECT LEFT(h.ChangeDate,7) month_bucket,ISNULL(h.LegalType,-1) legal_type,
               COUNT_BIG(*) cheques,
               SUM(CASE WHEN h.PersonnelId IS NOT NULL THEN 1 ELSE 0 END)
                    personnel_present
        FROM Acc.tblChqHist h
        WHERE h.IsLast=1 AND h.StatRef=9
        GROUP BY LEFT(h.ChangeDate,7),ISNULL(h.LegalType,-1)
        ORDER BY month_bucket,legal_type
        """,
    )
    return {
        "current_status7_pay_projection": status7,
        "status7_rows_with_missing_master_projection": missing_master,
        "missing_master_projection_state_sequences": missing_sequences,
        "current_status9_legal_type_profile": legal,
        "legal_type_by_business_month": legal_by_month,
    }


def _contracts(definitions: dict[str, str]) -> dict[str, bool]:
    n = {name: _normalize(value) for name, value in definitions.items()}
    pay2 = n["dbo.Pay2"]
    list_proc = n["dbo.USP_SDSNET_PayRCheque_GetList"]
    add_hist = n["dbo.DoRCheque_AddRChequeHistory"]
    cession = n["dbo.DoRCheque_CessionToOther"]
    before = n["dbo.usp_sdsnet_RChequeChangeStatus_BeforeSave"]
    save_raw = definitions["dbo.usp_sdsnet_RChequeChangeStatus_Save"]
    save = n["dbo.usp_sdsnet_RChequeChangeStatus_Save"]
    call = re.search(
        r"exec\s+DoRCheque_AddRChequeHistory(?P<body>.*?)(?:\r?\n\s*\r?\n|select\s+top|fetch\s+next)",
        save_raw,
        re.I | re.S,
    )
    if call is None:
        raise RuntimeError("RCheque change-status confirmation call not found")
    call_body = _normalize(call.group("body"))
    return {
        "draft_pay_uses_tblcheque_projection": all(
            token in pay2
            for token in ("rc.payid = pay.payid", "pay.paystatusid=1")
        ),
        "approved_pay_uses_history_payid2": all(
            token in pay2
            for token in ("rch.payid2 = pay.payid", "pay.paystatusid=2")
        ),
        "approved_list_filters_history_payid2": (
            "payid2 ='+ltrim(@payid)" in list_proc
        ),
        "unapproved_list_filters_tblcheque_payid": (
            "c.payid ='+ltrim(@payid)" in list_proc
        ),
        "cession_copies_pay_to_master_and_history": all(
            token in cession
            for token in ("set payid = @payid", "dorcheque_addrchequehistory", "@appuserid,@payid")
        ),
        "leaving_cession_clears_master_projection": all(
            token in add_hist
            for token in ("@oldrchequestatusid = 7", "set payid = null")
        ),
        "zero_legal_type_is_normalized_to_null": all(
            token in add_hist
            for token in ("if (@legaltype = 0)", "set @legaltype = null")
        ),
        "legal_type_is_not_globally_required_by_validator": (
            "isnull(@legaltype,0) =1" in before
            and "isnull(@personnelid,0)=0" in before
            and not bool(re.search(r"legaltype[^.]{0,80}(cannot|empty|خالی|الزام)", before, re.I))
        ),
        "change_status_parent_persists_legal_type": (
            "custref, legaltype," in save and "from #parententity" in save
        ),
        "confirmation_call_forgets_legal_type": (
            "@chqchangestatusref" in call_body and "@legaltype" not in call_body
        ),
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


def collect() -> dict[str, Any]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            safety = _assert_safe_target(cursor)
            modules, definitions = _modules(cursor)
            schema = _schema(cursor)
            aggregates = _aggregates(cursor)
    contracts = _contracts(definitions)
    status7 = aggregates["current_status7_pay_projection"]
    missing = aggregates["status7_rows_with_missing_master_projection"]
    legal = {row["legal_type"]: row for row in aggregates["current_status9_legal_type_profile"]}
    if not (
        all(contracts.values())
        and status7["cheques"] == 12635
        and status7["master_missing_history_present"] == 8
        and status7["history_orphan"] == 0
        and status7["conflicting_links"] == 0
        and missing["valid_history_pay_links"] == 8
        and missing["approved_pay_links"] == 8
        and legal[-1]["cheques"] == 35
        and legal[2]["cheques"] == 18
    ):
        raise RuntimeError("Received-cheque projection/legal contract drift")

    findings = [
        _finding(
            "RCL-001",
            "The eight status-7 cheques do not have missing operational Pay links",
            "CRITICAL",
            [
                "all eight have a valid current-history PayId2",
                "all eight linked Pay documents are approved",
                "history orphan and conflicting-link counts are zero",
            ],
            "Quarantining or synthesizing a Pay link would duplicate or replace an already authoritative approved linkage.",
            "Treat TblCheque.PayId as a draft projection and tblChqHist.PayId2 as approved durable authority; never repair from the master column alone.",
        ),
        _finding(
            "RCL-002",
            "Official read models switch Pay authority at approval",
            "HIGH",
            [
                "Pay2 uses TblCheque.PayId for PayStatusId=1",
                "Pay2 uses tblChqHist.PayId2 for PayStatusId=2",
                "USP_SDSNET_PayRCheque_GetList makes the same IsApproved branch",
            ],
            "A single foreign key on ReceivedCheque cannot reproduce both draft selection and approved historical custody.",
            "Model draft selection separately from immutable cession event/reference and rebuild the current projection.",
        ),
        _finding(
            "RCL-003",
            "Null LegalType is an observed unspecified state and cannot be imputed",
            "HIGH",
            [
                "35 current legal cheques have null LegalType and all have PersonnelId",
                "the validator requires PersonnelId only when LegalType=1 but does not require LegalType globally",
                "LegalType=0 is explicitly normalized to null",
                "all 35 null records are concentrated in 1404/05/25..1404/05/27",
            ],
            "PersonnelId does not distinguish type 1 from type 2 because every current type-2 row also has PersonnelId.",
            "Preserve legal routing as UNKNOWN_UNSPECIFIED; do not guess assigned-to-personnel or legal-department.",
        ),
        _finding(
            "RCL-004",
            "The deployed bulk confirmation path does not forward LegalType into history",
            "CRITICAL",
            [
                "usp_sdsnet_RChequeChangeStatus_Save persists LegalType on its parent record",
                "its confirmation call passes ChqChangeStatusRef and PersonnelId but omits the optional @LegalType argument",
                "DoRCheque_AddRChequeHistory therefore receives the default null LegalType",
            ],
            "If this reachable path is used, the authoritative history can lose whether custody went to personnel or the legal department even though the draft parent captured it.",
            "In the target command, require and atomically persist a typed legal-routing value on the immutable event; add a source-version regression test and reconcile parent versus history before migration.",
            confidence="HIGH_STATIC_REACHABLE_PATH_RUNTIME_FREQUENCY_UNPROVEN",
        ),
        _finding(
            "RCL-005",
            "Current rows prove semantics, not exact historical operator intent",
            "MEDIUM",
            [
                "the 35 null rows predate the first current type-2 bucket by several months",
                "current change-status parent tables contain no rows to recover the missing value",
                "no raw identities, comments or document identifiers were inspected or persisted",
            ],
            "The original legal destination for those historical rows remains unknowable from approved aggregate evidence.",
            "Retain unknown provenance and route only source inconsistencies—not all nulls—to owner review.",
            confidence="MEDIUM_CURRENT_STATE_AND_STATIC_CODE",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    return {
        "artifact": "varanegar_received_cheque_projection_and_legal_type_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
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
            "current_status7_cheques": status7["cheques"],
            "master_pay_projection_missing_rows": status7[
                "master_missing_history_present"
            ],
            "valid_approved_history_pay_links_for_all_missing_master_rows": missing[
                "valid_history_pay_links"
            ],
            "history_pay_orphans": status7["history_orphan"],
            "conflicting_pay_links": status7["conflicting_links"],
            "current_status9_unspecified_legal_type_rows": legal[-1]["cheques"],
            "current_status9_explicit_legal_department_rows": legal[2]["cheques"],
            "previous_missing_pay_link_interpretation_valid": False,
            "legal_type_null_is_safe_to_impute": False,
            "bulk_confirmation_forwards_legal_type": False,
            "stored_procedure_or_application_commands_executed": 0,
        },
        "semantic_correction": {
            "wrong_pay_model": "current status-7 requires non-null TblCheque.PayId",
            "evidenced_pay_model": "draft/unapproved selection uses TblCheque.PayId; approved cession authority uses current-history PayId2",
            "previous_false_positive": "eight current status-7 cheques",
            "legal_type_model": "1=assigned to personnel, 2=assigned to legal department, null=unspecified legacy/source state",
            "migration_rule": "preserve approved history authority and unknown legal routing; never synthesize from master PayId or PersonnelId",
        },
        "incident_findings": findings,
        "schema_contract": schema,
        "aggregate_contract": aggregates,
        "sql_module_contracts": modules,
        "verified_contracts": contracts,
        "diagnostic_order": [
            "read current cheque state only from the IsLast history event",
            "branch Pay authority by Pay status: draft master projection versus approved history link",
            "verify history PayId2 exists and resolves before classifying a missing link",
            "preserve null LegalType as unknown unless authoritative source provenance exists",
            "compare change-status draft parent fields with the confirmed immutable history event",
        ],
        "evidence_limits": [
            "Static SQL proves the deployed reachable path and omission, not its runtime frequency.",
            "Current-state aggregates do not reconstruct every edit or deleted/archived parent document.",
            "No operator identity, cheque number, Pay number, comment or raw business row was persisted.",
            "No form, stored procedure, transaction or mutation was executed.",
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
