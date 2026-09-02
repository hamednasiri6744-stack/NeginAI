"""Extract a privacy-safe diagnostic contract for Varanegar operation/final dates.

The database side is read-only and limited to catalog definitions, anonymous
authorization aggregates, state counts, and bounded replication-log counts.
The binary side parses PE metadata/IL without loading or executing assemblies.
No business date values, identities, configuration values, raw log scripts, or
credentials are persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _analyze_assembly,
    _full_type_name,
)


TARGET_MODULE_NAMES = (
    "CheckValidationFinalDateManagement",
    "UpdateFinalDateManagement",
    "USP_SDSNET_CheckValidationBuyDateManagement",
    "USP_SDSNET_CheckValidationMaliDateManagement",
    "USP_SDSNET_CheckValidationTankhahDateManagement",
    "USP_SDSNET_UpdateBuyDateManagement",
    "USP_SDSNET_UpdateMaliDateManagement",
    "USP_SDSNET_UpdateTankhahDateManagement",
    "TRG_VN_FinalDateManagement",
    "trg_tblOprDate_Ignore",
    "Trg_DeleteStatement",
    "trg_tblOprDate_IsClosed_0_RetDist_1",
    "usp_tblDist_BackupBeforeRD",
    "DoOprDate_Close",
    "DoOprDate_Open",
    "DoPOrder_UpdateOprDate",
    "usp_sdsnet_OperationDate_Save",
    "usp_UpdateOprDateByPOS",
)

IL_TARGETS = {
    "VN.SDS.Setting.UI.dll": {
        "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementBuy",
        "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementMali",
        "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementTankhah",
    },
    "VN.SDS.Setting.Business.dll": {
        "VN.SDS.Setting.Business.FinalDateManagemen.FinalDateManagementValidator",
        "VN.SDS.Setting.Business.FinalDateManagement.FinalDateManagementHandler",
    },
    "VN.SDS.Setting.DataAccess.dll": {
        "VN.SDS.Setting.DataAccess.DataAdapter.FinalDateManagement.FinalDateManagementAdapter",
    },
}

ADAPTER_TYPE = (
    "VN.SDS.Setting.DataAccess.DataAdapter.FinalDateManagement."
    "FinalDateManagementAdapter"
)


def _normalize(definition: str) -> str:
    return re.sub(r"\s+", " ", definition).casefold()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _module_catalog(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    quoted = ",".join("N'" + name.replace("'", "''") + "'" for name in TARGET_MODULE_NAMES)
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
    public_rows = []
    definitions: dict[str, str] = {}
    for row in rows:
        qualified = f"{row['schema_name']}.{row['object_name']}"
        definition = row.pop("definition")
        definitions[qualified] = definition
        public_rows.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": _sha256_text(definition),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
            }
        )
    return public_rows, definitions


def _finding(
    finding_id: str,
    title: str,
    severity: str,
    evidence: list[str],
    symptom: str,
    diagnostic_action: str,
    *,
    confidence: str = "HIGH_STATIC",
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence,
        "likely_symptom": symptom,
        "diagnostic_action": diagnostic_action,
    }


def _static_findings(definitions: dict[str, str]) -> list[dict[str, Any]]:
    get = lambda name: _normalize(definitions.get(name, ""))
    update_all = get("GNR.UpdateFinalDateManagement")
    validate_buy = get("GNR.USP_SDSNET_CheckValidationBuyDateManagement")
    validate_mali = get("GNR.USP_SDSNET_CheckValidationMaliDateManagement")
    update_mali = get("GNR.USP_SDSNET_UpdateMaliDateManagement")
    update_tankhah = get("GNR.USP_SDSNET_UpdateTankhahDateManagement")
    delete_statement = get("GNR.Trg_DeleteStatement")
    dist_trigger = get("GNR.trg_tblOprDate_IsClosed_0_RetDist_1")
    dist_proc = get("SLE.usp_tblDist_BackupBeforeRD")
    final_trigger = get("GNR.TRG_VN_FinalDateManagement")

    missing_userref = []
    insert_pattern = re.compile(r"insert\s+into\s+(?:gnr\.)?tbloprdate\s*\(([^)]*)\)")
    for qualified, definition in definitions.items():
        normalized = _normalize(definition)
        for match in insert_pattern.finditer(normalized):
            if "userref" not in match.group(1):
                missing_userref.append(qualified)
                break

    target_updates = [
        name
        for name in (
            "GNR.UpdateFinalDateManagement",
            "GNR.USP_SDSNET_UpdateBuyDateManagement",
            "GNR.USP_SDSNET_UpdateMaliDateManagement",
            "GNR.USP_SDSNET_UpdateTankhahDateManagement",
        )
        if "begin tran" not in get(name) and "begin transaction" not in get(name)
    ]

    findings = [
        _finding(
            "FD-001",
            "Several first-create paths omit mandatory UserRef",
            "CRITICAL",
            sorted(missing_userref),
            "Opening or saving a date for a missing DC/fiscal-year/system row can fail while editing an existing row succeeds.",
            "Check whether GNR.tblOprDate already has the exact DCRef+AccYear+SysRef row before debugging UI validation.",
        ),
        _finding(
            "FD-002",
            "Combined updater guards petty-cash creation with sales fields",
            "HIGH",
            ["GNR.UpdateFinalDateManagement: SysRef=7 NOT EXISTS branch tests ForoshLastDate/ForoshLicenseDate"],
            "Petty-cash final-date save may update an existing row but fail to create a missing one when sales fields are blank.",
            "Compare presence of SysRef=7 with the sales fields submitted by the legacy form.",
        ),
        _finding(
            "FD-003",
            "Buy and financial validators contain unreachable predicates",
            "HIGH",
            [
                "GNR.USP_SDSNET_CheckValidationBuyDateManagement: @BuyDate < @BuyDate",
                "GNR.USP_SDSNET_CheckValidationMaliDateManagement: same variable must be blank and nonblank",
            ],
            "A head-office restriction or clear-date restriction expected by operators may never fire.",
            "Do not treat a successful validation response as proof that those two business rules were evaluated.",
        ),
        _finding(
            "FD-004",
            "Financial and petty-cash LicenseDate CASE assignments have no ELSE",
            "HIGH",
            [
                "GNR.USP_SDSNET_UpdateMaliDateManagement",
                "GNR.USP_SDSNET_UpdateTankhahDateManagement",
            ],
            "LicenseDate can become NULL for the login DC while LastDate is changed, producing branch-dependent state.",
            "Inspect LastDate and LicenseDate independently; never infer one from the other.",
        ),
        _finding(
            "FD-005",
            "Final-date update procedures do not own an explicit transaction",
            "HIGH",
            target_updates,
            "A later statement or trigger failure can leave an earlier statement committed unless the caller supplied an ambient transaction.",
            "Correlate every incident with all SysRef rows before and after the save; a single success message is insufficient.",
        ),
        _finding(
            "FD-006",
            "Financial reopen delete is not fiscal-year scoped",
            "CRITICAL",
            ["GNR.Trg_DeleteStatement deletes Acc.tblStatement by StatementTypeRef and DCRef without AccYear"],
            "Reopening one financial year can delete opening-balance statements for other years in the same DC.",
            "Before any approved reopen, count StatementTypeRef=1005 by DC and fiscal year and require a restore plan.",
        ),
        _finding(
            "FD-007",
            "Sales reopen distribution rewrite is not fiscal-year scoped",
            "CRITICAL",
            [
                "GNR.trg_tblOprDate_IsClosed_0_RetDist_1 invokes SLE.usp_tblDist_BackupBeforeRD",
                "SLE.usp_tblDist_BackupBeforeRD updates all status 4/7 rows for DC; AccYear filter is commented",
                "SLE.tblDist_BeforeRD is cleared without DC scope",
            ],
            "Reopening sales can change old-year distribution states or erase another DC's temporary backup set.",
            "Calculate both status-4 and status-7 blast radii across all years before approving reopen.",
        ),
        _finding(
            "FD-008",
            "Sales reopen trigger ignores the distribution procedure output error",
            "HIGH",
            ["GNR.trg_tblOprDate_IsClosed_0_RetDist_1 receives @ErrMsg but never checks or raises it"],
            "The year/date row can reopen even when distribution preconditions asked the caller to stop.",
            "Verify distribution states separately after reopen; do not rely on the date-row result.",
        ),
        _finding(
            "FD-009",
            "Final-date triggers assume single-row inserted/deleted sets",
            "HIGH",
            [
                "GNR.TRG_VN_FinalDateManagement uses TOP 1/scalar reads from inserted/deleted",
                "GNR.trg_tblOprDate_Ignore assigns scalar SysRef/DCRef/AccYear from inserted",
            ],
            "Bulk maintenance or replication batches can validate/log one arbitrary row and apply incomplete companion behavior.",
            "Treat bulk updates as unsupported until row-by-row parity is proven on an isolated target.",
        ),
    ]

    checks = {
        "FD-002": "sysref=7" in update_all and "@foroshlastdate<>'' or @foroshlicensedate<>''" in update_all,
        "FD-003-buy": "@buydate<@buydate" in validate_buy,
        "FD-003-mali": "@malidate='' and @malidate<>''" in validate_mali,
        "FD-004-mali": "licensedate=case when" in update_mali and "else" not in update_mali.split("licensedate=case when", 1)[1].split("end", 1)[0],
        "FD-004-tankhah": "licensedate=case when" in update_tankhah and "else" not in update_tankhah.split("licensedate=case when", 1)[1].split("end", 1)[0],
        "FD-006": "delete from acc.tblstatement" in delete_statement and "accyear" not in delete_statement.split("delete from acc.tblstatement", 1)[1],
        "FD-008": "@errmsg output" in dist_trigger and "raiserror" not in dist_trigger,
        "FD-009": "top 1" in final_trigger or "select @oprdcref" in final_trigger,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"static finding signatures drifted: {failed}")
    return findings


def _table_contract(cursor: Any) -> dict[str, Any]:
    columns = _rows(
        cursor,
        """
        SELECT c.column_id,c.name column_name,TYPE_NAME(c.user_type_id) data_type,
               c.max_length,c.is_nullable,dc.definition default_definition
        FROM sys.columns c
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE c.object_id=OBJECT_ID(N'GNR.tblOprDate')
        ORDER BY c.column_id
        """,
    )
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_primary_key,
               STRING_AGG(c.name,',') WITHIN GROUP(ORDER BY ic.key_ordinal) columns
        FROM sys.indexes i
        JOIN sys.index_columns ic
          ON ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.key_ordinal>0
        JOIN sys.columns c
          ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'GNR.tblOprDate')
        GROUP BY i.name,i.is_unique,i.is_primary_key
        ORDER BY i.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT tr.name,tr.is_instead_of_trigger,tr.is_disabled,
               te.type_desc event_type,
               OBJECTPROPERTYEX(tr.object_id,'ExecIsFirstUpdateTrigger') first_update,
               OBJECTPROPERTYEX(tr.object_id,'ExecIsLastUpdateTrigger') last_update
        FROM sys.triggers tr
        LEFT JOIN sys.trigger_events te ON te.object_id=tr.object_id
        WHERE tr.parent_id=OBJECT_ID(N'GNR.tblOprDate')
        ORDER BY tr.name,te.type_desc
        """,
    )
    return {"columns": columns, "indexes": indexes, "triggers": triggers}


def _population(cursor: Any) -> dict[str, Any]:
    by_sysref = _rows(
        cursor,
        """
        SELECT SysRef,COUNT_BIG(*) row_count,COUNT(DISTINCT DCRef) dc_count,
               COUNT(DISTINCT AccYear) fiscal_year_count,
               SUM(CASE WHEN LastDate='' THEN 1 ELSE 0 END) blank_last_date,
               SUM(CASE WHEN OprDate IS NULL OR OprDate='' THEN 1 ELSE 0 END) blank_opr_date,
               SUM(CASE WHEN LicenseDate IS NULL OR LicenseDate='' THEN 1 ELSE 0 END) blank_license_date,
               SUM(CASE WHEN IsClosed=1 THEN 1 ELSE 0 END) closed_count,
               SUM(CASE WHEN ModifiedDate>=DATEADD(MONTH,-3,SYSDATETIME()) THEN 1 ELSE 0 END) modified_last_3_months
        FROM GNR.tblOprDate GROUP BY SysRef ORDER BY SysRef
        """,
    )
    latest_coverage = _rows(
        cursor,
        """
        WITH y AS(SELECT MAX(AccYear) AccYear FROM GNR.tblAccYear),
        d AS(SELECT ID DCRef FROM GNR.tblDC),
        s AS(SELECT v SysRef FROM(VALUES(1),(2),(3),(5),(7))x(v))
        SELECT s.SysRef,COUNT_BIG(*) configured_dc_count,
               SUM(CASE WHEN o.ID IS NOT NULL THEN 1 ELSE 0 END) row_present_count,
               SUM(CASE WHEN o.ID IS NULL THEN 1 ELSE 0 END) missing_count,
               SUM(CASE WHEN o.ID IS NOT NULL AND o.LastDate='' THEN 1 ELSE 0 END) present_blank_last_date_count
        FROM d CROSS JOIN y CROSS JOIN s
        LEFT JOIN GNR.tblOprDate o
          ON o.DCRef=d.DCRef AND o.AccYear=y.AccYear AND o.SysRef=s.SysRef
        GROUP BY s.SysRef ORDER BY s.SysRef
        """,
    )
    overview = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,COUNT(DISTINCT DCRef) dcs,
               COUNT(DISTINCT AccYear) fiscal_years,
               SUM(CASE WHEN AccYear IS NULL THEN 1 ELSE 0 END) null_fiscal_year,
               SUM(CASE WHEN LEN(LastDate) NOT IN(0,10) THEN 1 ELSE 0 END) malformed_last_date_length,
               SUM(CASE WHEN OprDate IS NOT NULL AND LEN(OprDate) NOT IN(0,10) THEN 1 ELSE 0 END) malformed_opr_date_length,
               SUM(CASE WHEN LicenseDate IS NOT NULL AND LEN(LicenseDate) NOT IN(0,10) THEN 1 ELSE 0 END) malformed_license_date_length
        FROM GNR.tblOprDate
        """,
    )[0]
    return {
        "overview_without_date_values": overview,
        "by_system_reference_without_date_values": by_sysref,
        "latest_fiscal_year_coverage_without_year_value": latest_coverage,
    }


def _authorization(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH selected_nodes AS (
          SELECT AccessNodeId,AccessNodeKey FROM dbo.AccessNode
          WHERE AccessNodeId IN(432,923,926,927,928)
        ), active_users AS (
          SELECT AppUserId,IsAdmin FROM dbo.AppUser
          WHERE IsActive=1 AND ISNULL(IsDeleted,0)=0
        ), evaluated AS (
          SELECT n.AccessNodeId,n.AccessNodeKey,u.AppUserId,u.IsAdmin,
                 MAX(CASE WHEN d.AccessValue=1 THEN 1 ELSE 0 END) direct_allow,
                 MAX(CASE WHEN d.AccessValue=2 THEN 1 ELSE 0 END) direct_deny,
                 MAX(CASE WHEN g.AccessValue=1 THEN 1 ELSE 0 END) group_allow,
                 MAX(CASE WHEN g.AccessValue=2 THEN 1 ELSE 0 END) group_deny
          FROM selected_nodes n CROSS JOIN active_users u
          LEFT JOIN dbo.UserRights d
            ON d.AccessNodeId=n.AccessNodeId AND d.AppUserId=u.AppUserId
          LEFT JOIN dbo.UserGroupXAppUser m ON m.AppUserId=u.AppUserId
          LEFT JOIN dbo.UserGroupRights g
            ON g.AccessNodeId=n.AccessNodeId AND g.UserGroupId=m.UserGroupId
          GROUP BY n.AccessNodeId,n.AccessNodeKey,u.AppUserId,u.IsAdmin
        )
        SELECT AccessNodeId,AccessNodeKey,COUNT_BIG(*) active_users,
               SUM(CASE WHEN IsAdmin=1 THEN 1 ELSE 0 END) admin_bypass,
               SUM(CASE WHEN IsAdmin=1 OR
                    ((direct_allow=1 OR group_allow=1) AND direct_deny=0 AND group_deny=0)
                    THEN 1 ELSE 0 END) effective_allow,
               SUM(CASE WHEN IsAdmin=0 AND (direct_deny=1 OR group_deny=1)
                    THEN 1 ELSE 0 END) explicit_deny,
               SUM(CASE WHEN IsAdmin=0 AND direct_deny=0 AND group_deny=0
                         AND direct_allow=0 AND group_allow=0
                    THEN 1 ELSE 0 END) neutral_no_allow
        FROM evaluated GROUP BY AccessNodeId,AccessNodeKey ORDER BY AccessNodeId
        """,
    )


def _impact_aggregates(cursor: Any) -> dict[str, Any]:
    opening = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) statement_type_1005_rows,
               COUNT(DISTINCT AccYear) fiscal_years,COUNT(DISTINCT DCRef) dcs
        FROM Acc.tblStatement WHERE StatementTypeRef=1005
        """,
    )[0]
    distribution = _rows(
        cursor,
        """
        SELECT Status,COUNT_BIG(*) row_count,COUNT(DISTINCT AccYear) fiscal_years,
               COUNT(DISTINCT DCRef) dcs
        FROM SLE.tblDist WHERE Status IN(4,7)
        GROUP BY Status ORDER BY Status
        """,
    )
    backup = _rows(
        cursor,
        """
        SELECT (SELECT COUNT_BIG(*) FROM SLE.tblDist_BeforeRD) backup_rows,
               COUNT_BIG(*) trigger_count,
               SUM(CASE WHEN is_disabled=1 THEN 1 ELSE 0 END) disabled_trigger_count
        FROM sys.triggers WHERE parent_id=OBJECT_ID(N'SLE.tblDist')
        """,
    )[0]
    return {
        "financial_reopen_opening_statement_blast_radius": opening,
        "sales_reopen_distribution_branch_blast_radius": distribution,
        "distribution_backup_and_trigger_state": backup,
    }


def _consumer_surface(cursor: Any) -> dict[str, Any]:
    summary = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.type_desc,COUNT_BIG(*) module_count
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE m.definition LIKE '%tblOprDate%'
        GROUP BY s.name,o.type_desc ORDER BY s.name,o.type_desc
        """,
    )
    dependency = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) dependency_rows,
               COUNT(DISTINCT referencing_id) dependency_consumers
        FROM sys.sql_expression_dependencies
        WHERE referenced_id=OBJECT_ID(N'GNR.tblOprDate')
        """,
    )[0]
    return {
        "text_consumer_count": sum(int(row["module_count"]) for row in summary),
        "text_consumers_by_schema_and_type": summary,
        "catalog_dependency_summary": dependency,
    }


def _three_month_log(cursor: Any) -> dict[str, Any]:
    clock = _rows(
        cursor,
        "SELECT DATEADD(MONTH,-3,SYSDATETIME()) target_from,SYSDATETIME() captured_at",
    )[0]
    maximum = int(_rows(cursor, "SELECT MAX(ID) max_id FROM GNR.tblLog")[0]["max_id"] or 0)
    target = clock["target_from"]
    low, high = 0, maximum
    while low < high:
        middle = (low + high) // 2
        row = _rows(
            cursor,
            f"SELECT TOP 1 ID,TransDate FROM GNR.tblLog WITH(INDEX(PK_tblLog)) WHERE ID>={middle} ORDER BY ID",
        )
        if not row:
            high = middle
        elif row[0]["TransDate"] < target:
            low = int(row[0]["ID"]) + 1
        else:
            high = int(row[0]["ID"])
    threshold = low
    aggregate = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) row_count,
               SUM(CASE WHEN Script LIKE 'UPDATE GNR.tblOprDate%' THEN 1 ELSE 0 END) update_scripts,
               SUM(CASE WHEN Script LIKE '%INSERT INTO  GNR.tblOprDate%' THEN 1 ELSE 0 END) insert_scripts,
               SUM(CASE WHEN Script LIKE 'Delete from gnr.tblOprDate%' THEN 1 ELSE 0 END) delete_scripts
        FROM GNR.tblLog WITH(INDEX(PK_tblLog))
        WHERE ID>={threshold} AND Script LIKE '%tblOprDate%'
        """,
    )[0]
    monthly = _rows(
        cursor,
        f"""
        SELECT CONVERT(char(7),TransDate,120) month_bucket,Direction,
               COUNT_BIG(*) row_count,
               SUM(CASE WHEN Script LIKE 'UPDATE GNR.tblOprDate%' THEN 1 ELSE 0 END) update_scripts,
               SUM(CASE WHEN Script LIKE '%INSERT INTO  GNR.tblOprDate%' THEN 1 ELSE 0 END) insert_scripts,
               SUM(CASE WHEN Script LIKE 'Delete from gnr.tblOprDate%' THEN 1 ELSE 0 END) delete_scripts
        FROM GNR.tblLog WITH(INDEX(PK_tblLog))
        WHERE ID>={threshold} AND Script LIKE '%tblOprDate%'
        GROUP BY CONVERT(char(7),TransDate,120),Direction
        ORDER BY month_bucket,Direction
        """,
    )
    return {
        "window_months": 3,
        "captured_at": clock["captured_at"],
        "threshold_method": "binary_search_over_monotonic_log_identity_then_bounded_script_scan",
        "threshold_id_persisted": False,
        "aggregate_without_raw_scripts": aggregate,
        "monthly_direction_counts_without_raw_scripts": monthly,
        "limit": "TransDate is assumed to be monotonic with the clustered identity for threshold selection.",
    }


def _raw_adapter_templates(path: Path) -> list[dict[str, Any]]:
    pe = dnfile.dnPE(str(path))
    type_row = next(
        row
        for row in pe.net.mdtables.TypeDef.rows
        if _full_type_name(row) == ADAPTER_TYPE
    )
    templates = []
    for method_index in type_row.MethodList or []:
        method = method_index.row
        if method is None or not method.Rva:
            continue
        body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
        for instruction in body.instructions:
            if not isinstance(instruction.operand, StringToken):
                continue
            item = pe.net.user_strings.get(instruction.operand.rid)
            value = "" if item is None else str(item)
            command = re.search(r"\bGNR\.[A-Za-z0-9_]+", value, re.I)
            if command is None:
                continue
            templates.append(
                {
                    "method": str(method.Name),
                    "sql_command": command.group(0),
                    "template_sha256": _sha256_text(value),
                    "template_length": len(value),
                    "construction": "System.String.Format",
                    "data_context_parameter_count": 0,
                    "parameterization": "TEXT_INTERPOLATION_NOT_DB_PARAMETERS",
                }
            )
    return sorted(templates, key=lambda row: row["method"])


def _il_contract(source_directory: Path) -> dict[str, Any]:
    assemblies = []
    for file_name, target_types in IL_TARGETS.items():
        path = source_directory / file_name
        row = _analyze_assembly(path, target_types)
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        assemblies.append(row)
    templates = _raw_adapter_templates(source_directory / "VN.SDS.Setting.DataAccess.dll")
    return {
        "assemblies": assemblies,
        "adapter_sql_templates_without_values": templates,
        "summary": {
            "assembly_count": len(assemblies),
            "target_type_count": sum(len(row.get("target_types", [])) for row in assemblies),
            "found_type_count": sum(
                sum(bool(item.get("found")) for item in row.get("target_types", []))
                for row in assemblies
            ),
            "adapter_sql_template_count": len(templates),
            "parameterized_adapter_template_count": sum(
                row["parameterization"] == "DB_PARAMETERS" for row in templates
            ),
        },
    }


def collect(source_directory: Path) -> dict[str, Any]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            safety = _assert_safe_target(cursor)
            modules, definitions = _module_catalog(cursor)
            table_contract = _table_contract(cursor)
            population = _population(cursor)
            authorization = _authorization(cursor)
            impacts = _impact_aggregates(cursor)
            consumers = _consumer_surface(cursor)
            three_month_log = _three_month_log(cursor)

    il = _il_contract(source_directory)
    findings = _static_findings(definitions)
    findings.append(
        _finding(
            "FD-010",
            "DataAccess builds final-date commands with text interpolation",
            "HIGH",
            [row["method"] for row in il["adapter_sql_templates_without_values"]],
            "Malformed or unexpectedly quoted date text can fail as SQL syntax; client validation is the only observed value barrier.",
            "Capture the submitted field shape and exact adapter method; target ERP must use typed database parameters.",
        )
    )
    findings.append(
        _finding(
            "FD-011",
            "Final-date access is page-level in the captured legacy tree",
            "MEDIUM",
            [f"AccessNodeId={row['AccessNodeId']}" for row in authorization],
            "A user who can open the page may reach save behavior without a separately modeled command grant.",
            "Evaluate page access, DC scope, fiscal context and save capability as separate target checks.",
            confidence="MEDIUM_STATIC_AND_ANONYMOUS_AGGREGATE",
        )
    )

    severities = Counter(row["severity"] for row in findings)
    summary = {
        "finding_count": len(findings),
        "finding_severity_counts": dict(sorted(severities.items())),
        "critical_finding_count": severities["CRITICAL"],
        "target_module_count": len(modules),
        "operation_date_consumer_count": consumers["text_consumer_count"],
        "active_final_date_access_node_count": len(authorization),
        "current_operation_date_row_count": population["overview_without_date_values"]["row_count"],
        "three_month_logged_operation_count": three_month_log["aggregate_without_raw_scripts"]["row_count"],
        "raw_business_date_value_count": 0,
        "identity_count": 0,
        "command_execution_count": 0,
        "validation_error_count": 0,
    }
    return {
        "artifact": "varanegar_final_and_operation_date_incident_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {
            "server": SERVER,
            "database": DATABASE,
            "binary_source_kind": "READ_ONLY_DEPLOYED_PACKAGE",
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_NONEXECUTING_IL_PARSE",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_log_scripts_persisted": 0,
            "business_date_values_persisted": 0,
            "configuration_values_persisted": 0,
            "identities_or_individual_grants_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "semantic_model": {
            "OprDate": "current operational date used for day-level processing",
            "LastDate": "closed/final boundary checked by operational consumers",
            "LicenseDate": "head-office permission boundary replicated toward operational scope",
            "IsClosed": "fiscal/system closure state with cross-domain trigger effects",
            "scope_key": ["DCRef", "AccYear", "SysRef"],
            "system_reference_map": {
                "1": "sales",
                "2": "financial_or_treasury",
                "3": "branch_expense",
                "5": "purchase",
                "7": "petty_cash",
            },
        },
        "incident_findings": findings,
        "diagnostic_order": [
            "identify exact symptom and adapter/form path",
            "resolve DCRef, fiscal year and SysRef without collapsing headquarters and branch semantics",
            "check exact GNR.tblOprDate row presence before interpreting a save failure",
            "compare OprDate, LastDate, LicenseDate and IsClosed independently",
            "evaluate page authorization separately from data scope and command eligibility",
            "inspect validation branch, site type and replication mode",
            "for reopen, calculate accounting and distribution blast radii before any approved command",
            "verify all affected SysRef/domain rows after save because legacy atomicity is not proven",
        ],
        "table_contract": table_contract,
        "module_contracts": modules,
        "consumer_surface": consumers,
        "population_without_business_date_values": population,
        "anonymous_authorization": authorization,
        "reopen_impact_aggregates": impacts,
        "three_month_activity_without_raw_scripts": three_month_log,
        "il_contract": il,
        "evidence_limits": [
            "Static definitions prove reachable code shapes, not which runtime branch a real user executed.",
            "Anonymous authorization aggregates do not reveal the effective permission of the current operator.",
            "No validation or mutation procedure was executed; command result and transaction parity remain unproven.",
            "The clone may drift from production and contains no business date values in this artifact.",
            "Three-month log threshold selection assumes TransDate is monotonic with clustered log identity.",
            "Cached procedure execution counts were unavailable because VIEW SERVER STATE is denied.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
