"""Select evidence-backed SQL anchor contracts for material extensions."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ANCHORS: dict[str, tuple[str, ...]] = {
    "authorization.stock_accounting_access": (
        "GNR.tblStockUserAndGroupAccess",
        "GNR.tblUserDCAccess",
        "GNR.tblUserDistAccess",
        "GNR.tblUserSaleAccess",
        "dbo.USP_SDSNET_UserDcAccess_GetList",
        "dbo.USP_SDSNET_UserSaleAccess_GetList",
        "dbo.usp_sdsnet_UserDCAccessRights_BeforeSave",
        "dbo.usp_sdsnet_UserDCAccessRights_Save",
    ),
    "configuration.accounting_article_template": (
        "dbo.ArticleTemplate",
        "dbo.BeforeArticleTemplate",
        "dbo.USP_SDSNET_ArticleTemplate_GetList",
    ),
    "configuration.general": (
        "GNR.tblGeneralConfig",
        "GNR.tblGeneralConfig_History",
        "dbo.usp_GetGeneralConfigValue",
        "dbo.usp_SDSNet_GeneralConfig_getList",
    ),
    "configuration.web_service": ("dbo.usp_sdsnet_WebConfigSetting_Save",),
    "pos.charge_device": (
        "dbo.BaseChargeDevice",
        "dbo.usp_GetNextBaseChargeDeviceNo",
        "dbo.usp_sdsnet_BaseChargeDevice_GetList",
        "dbo.usp_sdsnet_ConfirmBaseChargeDevice",
    ),
    "pos.instalment_method": (
        "dbo.InstalmentMethod",
        "dbo.InstalmentMethodThirdParty",
        "dbo.usp_sdsnet_InstalmentMethod_GetList",
        "dbo.usp_sdsnet_InstalmentMethodThirdParty_GetList",
    ),
    "pos.linear_discount": (
        "dbo.POSLineDiscount",
        "SLE.USP_SDSNET_POSLineDiscountValidation",
        "dbo.usp_GetPOSLineDiscount",
        "dbo.usp_sdsnet_POSLineDiscount_GetList",
    ),
    "pos.safe": (
        "dbo.POSSafe",
        "dbo.usp_GetOpenPosSafeforuser",
        "dbo.usp_sdsnet_POSSafe_GetList",
    ),
    "pos.session": ("dbo.usp_ReplicateSalesReceipt",),
    "pos.subscriber": (
        "dbo.Subscriber",
        "dbo.SubscriberGroup",
        "dbo.usp_GetNextSubscriberCode",
        "dbo.usp_GetSubscriberCredit",
        "dbo.usp_sdsnet_Subscriber_GetList",
    ),
    "tablet.dealer_day_path": (
        "dbo.USP_SDSNET_DealersDayPathList_SAVE",
        "dbo.USP_SDSNET_DealersDayPath_GetList",
        "dbo.USP_SDSNET_DealersDayPath_SAVE",
    ),
    "tablet.visit_template": (
        "NGT.VisitTemplates",
        "NGT.VisitTemplatePaths",
        "NGT.VisitTemplatePathPoints",
        "NGT.VisitTemplatePathCustomers",
        "dbo.USP_NGT_GetDealerVisitTemplatePathes",
        "dbo.USP_NGT_UpdateDealerVisitTemplatePathes",
        "dbo.USP_NGT_VisitTemplate_GetList",
        "dbo.USP_SDSNET_VisitTemplate_Save",
    ),
}


PROVENANCE: dict[str, str] = {
    "dbo.POSLineDiscount": "EXACT_ALLOWLISTED_IL_SQL_LITERAL_AND_CLONE_CATALOG",
    "dbo.usp_ReplicateSalesReceipt": "EXACT_ALLOWLISTED_IL_COMMAND_LITERAL_AND_CLONE_CATALOG",
    "dbo.USP_SDSNET_DealersDayPathList_SAVE": "CHILD_FORM_ENTITY_FAMILY_AND_CLONE_CATALOG_NAME_CANDIDATE",
    "dbo.USP_SDSNET_DealersDayPath_GetList": "CHILD_FORM_ENTITY_FAMILY_AND_CLONE_CATALOG_NAME_CANDIDATE",
    "dbo.USP_SDSNET_DealersDayPath_SAVE": "CHILD_FORM_ENTITY_FAMILY_AND_CLONE_CATALOG_NAME_CANDIDATE",
}


GATES: dict[str, tuple[str, ...]] = {
    "authorization.stock_accounting_access": ("identity-free role UAT", "deny-by-default scope matrix", "SoD and delegated-scope review"),
    "configuration.accounting_article_template": ("posting rule versioning", "historical consumer crosswalk", "balanced-entry golden cases"),
    "configuration.general": ("typed allowlist", "current/history reconciliation", "consumer impact matrix"),
    "configuration.web_service": ("vault-only secret references", "egress allowlist", "credential rotation and non-mutating health check"),
    "pos.charge_device": ("device/cashier/safe crosswalk", "open-session retirement guard", "provider/device UAT"),
    "pos.instalment_method": ("schedule calculation fixtures", "effective-period overlap guard", "historical version pinning"),
    "pos.linear_discount": ("replace MAX(Id)+1", "rule overlap/priority specification", "pricing trace reconciliation"),
    "pos.safe": ("server-side scope", "sensitive balance capability", "projection cutoff/watermark"),
    "pos.session": ("replication idempotency", "per-receipt quarantine", "source-target count/amount reconciliation"),
    "pos.subscriber": ("PII minimization", "duplicate/merge policy", "stable source-target identity crosswalk"),
    "tablet.dealer_day_path": ("prove base-save procedure path", "effective dealer/day conflict rule", "offline version/ack contract"),
    "tablet.visit_template": ("template/path version model", "customer/point cardinality reconciliation", "offline client adoption watermark"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-surface", required=True, type=Path)
    parser.add_argument("--gap-paths", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sql = _load(args.sql_surface)
    gaps = _load(args.gap_paths)
    errors: list[str] = []
    if sql.get("validation") != "PASS" or gaps.get("validation") != "PASS":
        errors.append("source evidence is not PASS")

    objects = {f"{row['schema_name']}.{row['object_name']}".casefold(): row for row in sql["objects"]}
    contracts = []
    for capability, names in ANCHORS.items():
        selected = []
        for name in names:
            row = objects.get(name.casefold())
            if row is None:
                errors.append(f"missing required SQL anchor: {name}")
                continue
            selected.append(
                {
                    "object": f"{row['schema_name']}.{row['object_name']}",
                    "type": row["type"],
                    "type_desc": row["type_desc"],
                    "provenance": PROVENANCE.get(name, "CAPABILITY_NAME_AND_CLONE_CATALOG_CANDIDATE"),
                    "row_count_metadata": row["row_count_metadata"],
                    "columns": row["columns"],
                    "parameters": row["parameters"],
                    "foreign_keys": row["foreign_keys"],
                    "triggers": row["triggers"],
                    "dependencies": row["dependencies"],
                    "definition_length": row["definition_length"],
                    "definition_sha256": row["definition_sha256"],
                    "runtime_execution_proven": name in {"dbo.POSLineDiscount", "dbo.usp_ReplicateSalesReceipt"},
                }
            )
        contracts.append(
            {
                "capability": capability,
                "anchor_count": len(selected),
                "anchors": selected,
                "target_gates": list(GATES[capability]),
                "readiness": "EVIDENCE_CONTRACT_NOT_IMPLEMENTATION_OR_MIGRATION_APPROVAL",
            }
        )

    all_anchors = [anchor for contract in contracts for anchor in contract["anchors"]]
    type_counts = Counter(anchor["type_desc"] for anchor in all_anchors)
    summary = {
        "capability_count": len(contracts),
        "anchor_count": len(all_anchors),
        "anchor_type_counts": dict(sorted(type_counts.items())),
        "table_column_count": sum(len(anchor["columns"]) for anchor in all_anchors if anchor["type"] == "U"),
        "module_parameter_count": sum(len(anchor["parameters"]) for anchor in all_anchors if anchor["type"] != "U"),
        "foreign_key_count": sum(len(anchor["foreign_keys"]) for anchor in all_anchors),
        "trigger_count": sum(len(anchor["triggers"]) for anchor in all_anchors),
        "dependency_count": sum(len(anchor["dependencies"]) for anchor in all_anchors),
        "runtime_execution_proven_anchor_count": sum(anchor["runtime_execution_proven"] for anchor in all_anchors),
        "candidate_only_anchor_count": sum(not anchor["runtime_execution_proven"] for anchor in all_anchors),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_material_extension_selected_sql_anchor_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_SELECTION_FROM_REDACTED_IL_AND_READ_ONLY_CLONE_CATALOG_METADATA",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "procedures_functions_or_triggers_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "module_definitions_or_credentials_persisted": 0,
        },
        "summary": summary,
        "contracts": contracts,
        "validation_errors": errors,
        "limits": [
            "Only POSLineDiscount and usp_ReplicateSalesReceipt have exact allowlisted IL literals linking runtime code to the SQL name.",
            "Other anchors remain catalog/name/dependency candidates until adapter, ORM or runtime trace proves execution.",
            "Clone metadata can lag operational Varanegar and row_count_metadata is not a migration watermark.",
            "No module, trigger, function, view or application command was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
