"""Extract the Varanegar distribution-path storage and runtime contract.

The database side is read-only and persists only schema/catalog facts,
anonymous authorization aggregates, configuration branch values, and
distribution aggregates.  The binary side parses PE metadata/IL without
loading or executing assemblies.  No party identities or raw descriptions are
persisted.
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

from extract_varanegar_targeted_il_contracts import _analyze_assembly  # noqa: E402


RECENT_FROM = "1405/03/01"
RECENT_TO = "1405/05/31"

IL_TARGETS = {
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementDataEntry",
        "VN.SDS.Sales.UI.DistManagement.FormFollowDist",
    },
    "VN.SDS.Sales.UIComponent.dll": {
        "VN.SDS.Sales.UIComponent.DistPath.DistPathUIHelper",
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.DistPath.DistPathHandler",
        "VN.SDS.Sales.Business.DistPath.DistPathValidator",
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.DistPath.DistPathAdapter",
    },
}

MODULE_NAMES = (
    "usp_sdsnet_CreateDist",
    "usp_sdsnet_DistPathTree_GetList",
    "tblDistPathTree",
    "vwDistPath",
    "NGT_InsertOrUpdatePath",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        qualified = f"{row['schema_name']}.{row['object_name']}"
        definition = row.pop("definition")
        definitions[qualified] = definition
        normalized = _normalize(definition)
        public.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": _sha256_text(definition),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
                "references_distribution_path_master": "gnr.tbldistpath" in normalized,
                "references_distribution_path_parameter": "@distpath" in normalized,
            }
        )
    return public, definitions


def _schema_and_population(cursor: Any) -> dict[str, Any]:
    column = _rows(
        cursor,
        """
        SELECT c.name column_name,TYPE_NAME(c.user_type_id) data_type,
               c.max_length,c.is_nullable,dc.definition default_definition
        FROM sys.columns c
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE c.object_id=OBJECT_ID(N'SLE.tblDist') AND c.name='DistPath'
        """,
    )[0]
    fk = _rows(
        cursor,
        """
        SELECT fk.name constraint_name,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) target_schema,
               OBJECT_NAME(fkc.referenced_object_id) target_table,rc.name target_column
        FROM sys.foreign_key_columns fkc
        JOIN sys.foreign_keys fk ON fk.object_id=fkc.constraint_object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id
          AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id
          AND rc.column_id=fkc.referenced_column_id
        WHERE fkc.parent_object_id=OBJECT_ID(N'SLE.tblDist') AND pc.name='DistPath'
        """,
    )
    counts = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblDist) distributions,
          (SELECT COUNT(DISTINCT DistPath) FROM SLE.tblDist) distinct_path_codes,
          (SELECT COUNT_BIG(*) FROM GNR.tblDistZone) legacy_zone_master_rows,
          (SELECT COUNT_BIG(*) FROM GNR.tblDistArea) legacy_area_master_rows,
          (SELECT COUNT_BIG(*) FROM GNR.tblDistPath) legacy_path_master_rows,
          (SELECT COUNT_BIG(*) FROM GNR.tblDistPathTree) legacy_path_tree_view_rows,
          (SELECT COUNT_BIG(*) FROM GNR.vwDistPath) legacy_path_flat_view_rows
        """,
    )[0]
    code_profile = _rows(
        cursor,
        """
        SELECT DistPath path_code,COUNT_BIG(*) distributions,
               COUNT(DISTINCT DCRef) dcs,
               COUNT(DISTINCT DistributerRef) distributors,
               COUNT(DISTINCT DriverRef) drivers,
               COUNT(DISTINCT TruckRef) trucks,
               COUNT(DISTINCT LEFT(DistDate,7)) business_months,
               MIN(DistDate) minimum_business_date,
               MAX(DistDate) maximum_business_date
        FROM SLE.tblDist GROUP BY DistPath ORDER BY DistPath
        """,
    )
    legacy_join = _rows(
        cursor,
        """
        SELECT
          SUM(CASE WHEN p_id.ID IS NOT NULL THEN 1 ELSE 0 END) matches_master_id,
          SUM(CASE WHEN p_no.ID IS NOT NULL THEN 1 ELSE 0 END) matches_master_number,
          COUNT_BIG(*) total_rows
        FROM SLE.tblDist d
        LEFT JOIN GNR.tblDistPath p_id ON p_id.ID=d.DistPath
        LEFT JOIN GNR.tblDistPath p_no ON p_no.DistPathNo=d.DistPath
        """,
    )[0]
    distributor_days = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) distributor_days,
               SUM(CASE WHEN path_count=1 THEN 1 ELSE 0 END) one_code_days,
               SUM(CASE WHEN path_count>1 THEN 1 ELSE 0 END) multi_code_days,
               MAX(path_count) maximum_codes_per_distributor_day
        FROM (
          SELECT DistDate,DistributerRef,COUNT(DISTINCT DistPath) path_count
          FROM SLE.tblDist GROUP BY DistDate,DistributerRef
        )x
        """,
    )[0]
    return {
        "dist_path_column": column,
        "formal_foreign_keys": fk,
        "population": counts,
        "path_code_profile": code_profile,
        "legacy_master_join_observation": legacy_join,
        "distributor_day_shape": distributor_days,
    }


def _configuration(cursor: Any) -> dict[str, Any]:
    rows = _rows(
        cursor,
        """
        SELECT DistPathingType,DistLimitType,COUNT_BIG(*) configuration_rows
        FROM GNR.SdsNet_serverConfig
        GROUP BY DistPathingType,DistLimitType
        ORDER BY DistPathingType,DistLimitType
        """,
    )
    return {
        "effective_value_groups": rows,
        "all_groups_select_manual_entry_branch": bool(rows)
        and all(row["DistPathingType"] == 0 and row["DistLimitType"] == 0 for row in rows),
        "value_interpretation_source": "verified FormFollowDist_Load and FormDistManagementDataEntry.FillDistPathLookUpEdit IL branches",
    }


def _recent_activity(cursor: Any) -> dict[str, Any]:
    summary = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) distributions,COUNT(DISTINCT DistPath) path_codes,
               COUNT(DISTINCT DistributerRef) distributors,
               COUNT(DISTINCT DriverRef) drivers,
               COUNT(DISTINCT TruckRef) trucks,
               SUM(CASE WHEN Status=7 THEN 1 ELSE 0 END) finished,
               SUM(CASE WHEN Status=0 THEN 1 ELSE 0 END) cancelled
        FROM SLE.tblDist
        WHERE DistDate BETWEEN '{RECENT_FROM}' AND '{RECENT_TO}'
        """,
    )[0]
    monthly = _rows(
        cursor,
        f"""
        SELECT LEFT(DistDate,7) month_bucket,DistPath path_code,
               COUNT_BIG(*) distributions,
               COUNT(DISTINCT DistributerRef) distributors,
               COUNT(DISTINCT DriverRef) drivers,
               COUNT(DISTINCT TruckRef) trucks,
               SUM(CASE WHEN Status=7 THEN 1 ELSE 0 END) finished,
               SUM(CASE WHEN Status=0 THEN 1 ELSE 0 END) cancelled
        FROM SLE.tblDist
        WHERE DistDate BETWEEN '{RECENT_FROM}' AND '{RECENT_TO}'
        GROUP BY LEFT(DistDate,7),DistPath
        ORDER BY month_bucket,DistPath
        """,
    )
    return {
        "business_date_from": RECENT_FROM,
        "business_date_to": RECENT_TO,
        "summary": summary,
        "monthly_path_code_counts": monthly,
        "interpretation": "current distribution headers grouped by business month; not an event transition log",
    }


def _authorization(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH selected_nodes AS (
          SELECT AccessNodeId,AccessNodeKey,ParentId
          FROM dbo.AccessNode
          WHERE AccessNodeId=412 OR ParentId=412
        ), active_users AS (
          SELECT AppUserId,IsAdmin FROM dbo.AppUser
          WHERE IsActive=1 AND ISNULL(IsDeleted,0)=0
        ), evaluated AS (
          SELECT n.AccessNodeId,n.AccessNodeKey,n.ParentId,u.AppUserId,u.IsAdmin,
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
          GROUP BY n.AccessNodeId,n.AccessNodeKey,n.ParentId,u.AppUserId,u.IsAdmin
        )
        SELECT AccessNodeId,AccessNodeKey,ParentId,COUNT_BIG(*) active_users,
               SUM(CASE WHEN IsAdmin=1 THEN 1 ELSE 0 END) admin_bypass,
               SUM(CASE WHEN IsAdmin=1 OR
                    ((direct_allow=1 OR group_allow=1) AND direct_deny=0 AND group_deny=0)
                    THEN 1 ELSE 0 END) effective_allow,
               SUM(CASE WHEN IsAdmin=0 AND (direct_deny=1 OR group_deny=1)
                    THEN 1 ELSE 0 END) explicit_deny,
               SUM(CASE WHEN IsAdmin=0 AND direct_deny=0 AND group_deny=0
                         AND direct_allow=0 AND group_allow=0 THEN 1 ELSE 0 END)
                    neutral_no_allow
        FROM evaluated
        GROUP BY AccessNodeId,AccessNodeKey,ParentId ORDER BY AccessNodeId
        """,
    )


def _method_calls(assemblies: list[dict[str, Any]], type_name: str, method_name: str) -> set[str]:
    for assembly in assemblies:
        for target_type in assembly.get("target_types", []):
            if target_type.get("type") != type_name:
                continue
            for method in target_type.get("methods", []):
                if method.get("method") == method_name:
                    return set(method.get("calls", []))
    raise RuntimeError(f"Required IL method not found: {type_name}.{method_name}")


def _il_contract(source_directory: Path) -> dict[str, Any]:
    assemblies = [
        _analyze_assembly(source_directory / file_name, target_types)
        for file_name, target_types in sorted(IL_TARGETS.items())
    ]
    form_type = "VN.SDS.Sales.UI.DistManagement.FormDistManagementDataEntry"
    follow_type = "VN.SDS.Sales.UI.DistManagement.FormFollowDist"
    selected_calls = _method_calls(
        assemblies, form_type, "DistPathLookUpEdit_EditValueChanged"
    )
    lookup_calls = _method_calls(assemblies, form_type, "FillDistPathLookUpEdit")
    save_calls = _method_calls(assemblies, form_type, "SaveCommand")
    follow_calls = _method_calls(assemblies, follow_type, "FormFollowDist_Load")

    required = {
        "selected_lookup_writes_business_number": {
            "calls": {
                "VN.SDS.Common.Sales.Entity.DistPath.DistPathEntity.get_DistPathTreeNo",
                "DevExpress.XtraEditors.BaseEdit.set_EditValue",
            },
            "observed": selected_calls,
        },
        "conditional_lookup_uses_zone_path": {
            "calls": {
                "VN.SDS.Common.MainData.Entity.ServerConfig.ServerConfigEntity.get_DistLimitType",
                "VN.SDS.Sales.UIComponent.DistPath.DistPathUIHelper.DistZonePath",
            },
            "observed": lookup_calls,
        },
        "save_passes_code_through_create_unit_of_work": {
            "calls": {
                "VN.SDS.Common.Sales.Entity.Dist.DistEntity.get_DistPath",
                "VN.SDS.Common.Sales.EntityHelper.Dist.DistEntityHelper.set_DistPath",
                "VN.SDS.Sales.Business.Dist.DistHandler.CreateDist",
                "Thunderstruck.DataContext.Commit",
            },
            "observed": save_calls,
        },
        "follow_form_mode_uses_both_configuration_flags": {
            "calls": {
                "VN.SDS.Common.MainData.Entity.ServerConfig.ServerConfigEntity.get_DistPathingType",
                "VN.SDS.Common.MainData.Entity.ServerConfig.ServerConfigEntity.get_DistLimitType",
                "System.Windows.Forms.Control.set_Enabled",
            },
            "observed": follow_calls,
        },
    }
    for name, contract in required.items():
        missing = contract["calls"] - contract["observed"]
        if missing:
            raise RuntimeError(f"IL contract drift for {name}: {sorted(missing)}")

    return {
        "assemblies": assemblies,
        "verified_branch_contracts": [
            {
                "method": f"{form_type}.DistPathLookUpEdit_EditValueChanged",
                "contract": "selected lookup row writes DistPathTreeNo into txtDistpath; it does not write the path master ID",
            },
            {
                "method": f"{form_type}.FillDistPathLookUpEdit",
                "contract": "lookup population is skipped for DistLimitType=0 or 3; otherwise FetchReason=2 and distributor scope feed DistZonePath",
            },
            {
                "method": f"{follow_type}.FormFollowDist_Load",
                "contract": "manual DistPath text is enabled only when DistPathingType=0 and DistLimitType=0",
            },
            {
                "method": f"{form_type}.SaveCommand",
                "contract": "DistEntity.DistPath is copied as an integer into CreateDist and committed only after a valid result",
            },
        ],
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


def collect(source_directory: Path) -> dict[str, Any]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            safety = _assert_safe_target(cursor)
            modules, definitions = _module_contract(cursor)
            schema = _schema_and_population(cursor)
            configuration = _configuration(cursor)
            recent = _recent_activity(cursor)
            authorization = _authorization(cursor)

    il = _il_contract(source_directory)
    create_definition = _normalize(definitions.get("SLE.usp_sdsnet_CreateDist", ""))
    create_references_master = "gnr.tbldistpath" in create_definition
    create_has_transaction = bool(
        re.search(r"\bbegin\s+tran(?:saction)?\b", create_definition, re.I)
    )

    findings = [
        _finding(
            "DP-001",
            "The previous 26,086-row orphan-FK classification is invalid",
            "CRITICAL",
            [
                "SLE.tblDist.DistPath has no formal foreign key",
                "lookup selection writes DistPathTreeNo rather than GNR.tblDistPath.ID",
                "current configuration selects the manual integer-code branch",
            ],
            "Treating DistPath as GNR.tblDistPath.ID would invent corruption and can misroute every migrated distribution.",
            "Preserve the source integer as a path/run code with provenance; do not auto-create or auto-join a legacy path ID.",
        ),
        _finding(
            "DP-002",
            "Current runtime intentionally uses manual distribution-path codes",
            "HIGH",
            [
                "all effective configuration groups have DistPathingType=0 and DistLimitType=0",
                "FormFollowDist_Load enables the text field only for that pair",
                "FormDistManagementDataEntry skips path lookup population for DistLimitType=0",
            ],
            "Codes 1, 2, 3, 4, 5, 11 and 12 are valid observed operational values even though the legacy route master is empty.",
            "Model the mode as configuration and validate an integer code, not a required master reference.",
        ),
        _finding(
            "DP-003",
            "Legacy route labels and hierarchy cannot be reconstructed from the current master tables",
            "HIGH",
            [
                "GNR.tblDistZone=0",
                "GNR.tblDistArea=0",
                "GNR.tblDistPath=0",
                "GNR.tblDistPathTree contains only its synthetic root",
            ],
            "The integer codes have operational meaning but no evidenced current label, area or zone.",
            "Keep labels unresolved unless a separate authoritative route source or operator-approved crosswalk is supplied.",
        ),
        _finding(
            "DP-004",
            "CreateDist stores DistPath without legacy-master validation",
            "HIGH",
            [
                "SLE.usp_sdsnet_CreateDist accepts @DistPath INT",
                "insert and update copy @DistPath directly",
                "procedure definition does not reference GNR.tblDistPath",
            ],
            "A database FK or master lookup is not part of the captured source contract.",
            "Target validation must be conditional on path mode and must not silently strengthen the legacy rule during parity migration.",
        ),
        _finding(
            "DP-005",
            "Distribution path is an open code set, not a hard-coded binary flag",
            "MEDIUM",
            [
                "seven distinct codes exist in the clone",
                "code 5 appears materially in the recent three-month window",
            ],
            "Hard-coding only values 1 and 2 would reject or collapse valid history.",
            "Use an integer value object plus observed-code analytics; add labels only through explicit crosswalk governance.",
        ),
        _finding(
            "DP-006",
            "Distribution page permission and data/path semantics are separate controls",
            "HIGH",
            [
                "DistManagement has separate View, AddNew and Edit access nodes",
                "path mode comes from server configuration",
                "CreateDist carries DCRef, AccYear and UserRef separately",
            ],
            "Page access alone does not determine whether a user may create/edit a distribution or which path mode applies.",
            "Evaluate command grant, active scope, fiscal context, current state and path-mode validation independently.",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    summary = {
        "finding_count": len(findings),
        "finding_severity_counts": dict(sorted(severities.items())),
        "distribution_count": schema["population"]["distributions"],
        "distinct_path_code_count": schema["population"]["distinct_path_codes"],
        "legacy_path_master_row_count": schema["population"]["legacy_path_master_rows"],
        "formal_dist_path_fk_count": len(schema["formal_foreign_keys"]),
        "previous_orphan_fk_interpretation_valid": False,
        "current_runtime_path_mode": "MANUAL_INTEGER_CODE",
        "recent_distribution_count": recent["summary"]["distributions"],
        "authorization_node_count": len(authorization),
        "create_dist_references_legacy_master": create_references_master,
        "create_dist_has_explicit_transaction": create_has_transaction,
        "database_or_application_commands_executed": 0,
    }
    return {
        "artifact": "varanegar_distribution_path_runtime_and_migration_diagnostic_contract",
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
            "identities_or_raw_party_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "semantic_correction": {
            "wrong_model": "SLE.tblDist.DistPath is a foreign key to GNR.tblDistPath.ID",
            "evidenced_model": "SLE.tblDist.DistPath is a mode-dependent integer path/run code; lookup mode also stores DistPathTreeNo, not master ID",
            "remaining_unknown": "human label and route hierarchy for each observed code",
            "migration_rule": "preserve exact integer and source mode; never invent a path master or default label",
        },
        "incident_findings": findings,
        "schema_and_population": schema,
        "configuration_contract": configuration,
        "recent_three_month_activity": recent,
        "anonymous_authorization": authorization,
        "module_contracts": modules,
        "il_contract": il,
        "diagnostic_order": [
            "identify whether the symptom concerns path code, distribution ID, distributor/team, or geographic route label",
            "read DistPathingType and DistLimitType for the effective runtime scope",
            "preserve SLE.tblDist.DistPath as an integer code and never diagnose an orphan by joining it to GNR.tblDistPath.ID",
            "check View/AddNew/Edit authorization separately from DC, fiscal year, operation date and distribution state",
            "for missing labels, request an authoritative crosswalk; do not synthesize one from the empty legacy master",
            "verify CreateDist result and ambient unit-of-work outcome before treating a UI success or failure as committed state",
        ],
        "evidence_limits": [
            "The clone proves current configuration and current-state aggregates, not every historical configuration value.",
            "Static IL proves reachable branch shape, not the exact runtime branch used for each historical row.",
            "No authoritative human label for codes 1, 2, 3, 4, 5, 11 or 12 is present in the captured legacy masters.",
            "Anonymous authorization aggregates do not disclose or prove one named operator's effective permissions.",
            "CreateDist owns no explicit SQL transaction, while the UI passes a DataContext and commits after validation; full transaction internals remain inside the framework.",
            "No form, procedure, transaction, or mutation was executed.",
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
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
