"""Extract Varanegar/NGT configuration structure and rule-use evidence.

Read-only by design. Persists key/column names, aggregate coverage, history
counts, and module consumers. Never persists configuration values, old values,
credentials, URLs, paths, host/application identities, device-owner rows, or
raw change-history records.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "GNR.tblGeneralConfig", "role": "global_key_value_configuration"},
    {"object": "GNR.tblGeneralConfig_History", "role": "global_configuration_change_history"},
    {"object": "GNR.tblServerConfig", "role": "server_key_value_configuration"},
    {"object": "GNR.tblServerConfig_History", "role": "server_configuration_change_history"},
    {"object": "GNR.tblServerConfigDC", "role": "dc_operational_feature_configuration"},
    {"object": "GNR.tblCustConfig", "role": "customer_field_configuration"},
    {"object": "GNR.tblCustConfigDC", "role": "dc_customer_default_configuration"},
    {"object": "NGT.BaseValues", "role": "ngt_base_value_catalog"},
    {"object": "NGT.PublicValues", "role": "ngt_public_value_catalog"},
    {"object": "NGT.DeviceSettings", "role": "ngt_device_behavior_configuration"},
    {"object": "NGT.DeviceSettingKeyTypes", "role": "ngt_device_setting_key_type"},
    {"object": "NGT.AppSettings", "role": "ngt_application_behavior_configuration"},
    {"object": "dbo.ApplicationSetting", "role": "backoffice_application_version_setting"},
    {"object": "dbo.ApplicationSettingData", "role": "backoffice_data_version_setting"},
)

REVIEWED_RULE_KEYS: tuple[str, ...] = (
    "ControlStockRetSale_ShowCardex", "EffectVocherWithOutConfirm",
    "CheckSaleItmStock", "AutoGenRetSaleVocher", "OrderRowLimit",
    "RChequePayControl", "DiscountControl", "Ngt_InsertReceiptForSaleOffice",
    "SettlementPreviousDebtId", "MaxLimitOfOrderConvertToSale", "AutoOrderConfirm",
    "AllowFreeReason", "CreateExitWithConfirmStockMan", "NGT_CreatePOrder",
    "MatchRetSaleVchNo", "RefRetOrder", "MaxDay4OpenSale", "ValidPeriodOfSales",
    "ValidPeriodOfFinancial", "PayDateControl", "MinOrderAmount", "MaxOrderAmount",
)


def _ids() -> str:
    return ",".join(f"OBJECT_ID(N'{x['object']}', 'U')" for x in DOMAIN_TABLES)


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sensitive_fragments = (
        "password", "pass", "username", "user_name", "url", "path", "email",
        "website", "latitude", "longitude", "token", "secret", "keyvalue",
        "hostname", "applicationname", "apikey",
    )
    result = dict(metadata)
    result["columns"] = [
        c for c in metadata.get("columns", [])
        if not any(x in str(c.get("column_name", "")).lower() for x in sensitive_fragments)
    ]
    result["redacted_column_count"] = len(metadata.get("columns", [])) - len(result["columns"])
    return result


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT fk.name constraint_name,
             OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
             OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
             OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
             OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
             fk.delete_referential_action_desc on_delete,
             fk.update_referential_action_desc on_update,fk.is_disabled,fk.is_not_trusted
      FROM sys.foreign_keys fk
      JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
      JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
      JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
      WHERE fk.parent_object_id IN ({ids}) OR fk.referenced_object_id IN ({ids})
      ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,fk.name,fkc.constraint_column_id
    """)


def _consumers(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
             OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
             OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
             OBJECT_NAME(d.referenced_id) source_table,d.is_schema_bound_reference,
             o.modify_date consumer_modify_date
      FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id=d.referencing_id
      WHERE d.referenced_id IN ({ids})
      ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _key_value_profile(cursor: Any) -> dict[str, Any]:
    general = _rows(cursor, """
      SELECT COUNT_BIG(*) current_rows,COUNT(DISTINCT KeyName) distinct_keys,
             SUM(CASE WHEN NULLIF(LTRIM(RTRIM(KeyName)),'') IS NULL THEN 1 ELSE 0 END) blank_keys,
             SUM(CASE WHEN KeyValue IS NULL THEN 1 ELSE 0 END) null_values,
             (SELECT COUNT_BIG(*) FROM (SELECT KeyName FROM GNR.tblGeneralConfig GROUP BY KeyName HAVING COUNT_BIG(*)>1)x) duplicate_key_groups
      FROM GNR.tblGeneralConfig
    """)[0]
    server = _rows(cursor, """
      SELECT COUNT_BIG(*) current_rows,COUNT(DISTINCT KeyName) distinct_keys,
             SUM(CASE WHEN NULLIF(LTRIM(RTRIM(KeyName)),'') IS NULL THEN 1 ELSE 0 END) blank_keys,
             SUM(CASE WHEN KeyValue IS NULL THEN 1 ELSE 0 END) null_values,
             (SELECT COUNT_BIG(*) FROM (SELECT KeyName FROM GNR.tblServerConfig GROUP BY KeyName HAVING COUNT_BIG(*)>1)x) duplicate_key_groups
      FROM GNR.tblServerConfig
    """)[0]
    histories = _rows(cursor, """
      SELECT 'general' config_type,COUNT_BIG(*) history_rows,COUNT(DISTINCT KeyName) keys,
             MIN(ChangeDate) minimum_change_date,MAX(ChangeDate) maximum_change_date,
             SUM(CASE WHEN KeyValue=KeyValueOld OR (KeyValue IS NULL AND KeyValueOld IS NULL) THEN 1 ELSE 0 END) no_value_change_rows
      FROM GNR.tblGeneralConfig_History
      UNION ALL
      SELECT 'server',COUNT_BIG(*),COUNT(DISTINCT KeyName),MIN(ChangeDate),MAX(ChangeDate),
             SUM(CASE WHEN KeyValue=KeyValueOld OR (KeyValue IS NULL AND KeyValueOld IS NULL) THEN 1 ELSE 0 END)
      FROM GNR.tblServerConfig_History
    """)
    history_key_integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM (SELECT DISTINCT h.KeyName FROM GNR.tblGeneralConfig_History h LEFT JOIN GNR.tblGeneralConfig c ON c.KeyName=h.KeyName WHERE c.KeyName IS NULL)x) general_history_only_keys,
       (SELECT COUNT_BIG(*) FROM (SELECT DISTINCT h.KeyName FROM GNR.tblServerConfig_History h LEFT JOIN GNR.tblServerConfig c ON c.KeyName=h.KeyName WHERE c.KeyName IS NULL)x) server_history_only_keys
    """)[0]
    keys = _rows(cursor, """
      SELECT 'general' config_type,KeyName key_name,
             CASE WHEN KeyValue IS NULL THEN 'null'
                  WHEN LOWER(LTRIM(RTRIM(KeyValue))) IN ('0','1','true','false') THEN 'boolean_like'
                  WHEN TRY_CONVERT(decimal(38,10),KeyValue) IS NOT NULL THEN 'numeric_like'
                  ELSE 'text_like' END value_shape
      FROM GNR.tblGeneralConfig
      UNION ALL
      SELECT 'server',KeyName,
             CASE WHEN KeyValue IS NULL THEN 'null'
                  WHEN LOWER(LTRIM(RTRIM(KeyValue))) IN ('0','1','true','false') THEN 'boolean_like'
                  WHEN TRY_CONVERT(decimal(38,10),KeyValue) IS NOT NULL THEN 'numeric_like'
                  ELSE 'text_like' END
      FROM GNR.tblServerConfig
      ORDER BY config_type,key_name
    """)
    return {"general_config_without_values": general, "server_config_without_values": server,
            "history_without_values_or_hosts": histories,
            "history_key_integrity": history_key_integrity,
            "key_catalog_with_value_shape_only": keys}


def _dc_and_customer_config(cursor: Any) -> dict[str, Any]:
    dc = _rows(cursor, """
      SELECT COUNT_BIG(*) rows,COUNT(DISTINCT DcRef) dcs,
             SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) orphan_dc
      FROM GNR.tblServerConfigDC c LEFT JOIN GNR.tblDC d ON d.ID=c.DcRef
    """)[0]
    customer = _rows(cursor, """
      SELECT COUNT_BIG(*) rows,COUNT(DISTINCT DCRef) dcs,COUNT(DISTINCT CustFieldRef) fields,
             SUM(CASE WHEN IsNecessary=1 THEN 1 ELSE 0 END) necessary,
             SUM(CASE WHEN DCRef IS NOT NULL AND d.ID IS NULL THEN 1 ELSE 0 END) orphan_dc
      FROM GNR.tblCustConfig c LEFT JOIN GNR.tblDC d ON d.ID=c.DCRef
    """)[0]
    customer_dc = _rows(cursor, """
      SELECT COUNT_BIG(*) rows,COUNT(DISTINCT DcRef) dcs,
             SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) orphan_dc
      FROM GNR.tblCustConfigDC c LEFT JOIN GNR.tblDC d ON d.ID=c.DcRef
    """)[0]
    safe_columns = _rows(cursor, """
      SELECT c.column_id,c.name column_name,TYPE_NAME(c.user_type_id) data_type,c.is_nullable
      FROM sys.columns c WHERE c.object_id=OBJECT_ID(N'GNR.tblServerConfigDC')
        AND LOWER(c.name) NOT LIKE '%password%' AND LOWER(c.name) NOT LIKE '%pass%'
        AND LOWER(c.name) NOT LIKE '%user%' AND LOWER(c.name) NOT LIKE '%url%'
        AND LOWER(c.name) NOT LIKE '%path%' AND LOWER(c.name) NOT LIKE '%latitude%'
        AND LOWER(c.name) NOT LIKE '%longitude%'
      ORDER BY c.column_id
    """)
    return {"dc_config_population": dc, "customer_field_config": customer,
            "customer_dc_defaults": customer_dc,
            "dc_operational_setting_schema_without_sensitive_fields": safe_columns}


def _ngt_profile(cursor: Any) -> dict[str, Any]:
    catalogs = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM NGT.BaseValues) base_values,
       (SELECT COUNT_BIG(*) FROM NGT.BaseValues WHERE IsRemoved=1) removed_base_values,
       (SELECT COUNT_BIG(*) FROM NGT.PublicValues) public_values,
       (SELECT COUNT_BIG(*) FROM NGT.DeviceSettingKeyTypes) device_setting_key_types,
       (SELECT COUNT_BIG(*) FROM NGT.DeviceSettings) device_settings,
       (SELECT COUNT_BIG(*) FROM NGT.DeviceSettings WHERE IsRemoved=1) removed_device_settings,
       (SELECT COUNT_BIG(*) FROM NGT.AppSettings) app_settings,
       (SELECT COUNT_BIG(*) FROM NGT.AppSettings WHERE IsRemoved=1) removed_app_settings
    """)[0]
    policy_coverage = _rows(cursor, """
      SELECT COUNT_BIG(*) device_settings,
             SUM(CASE WHEN EnableGPS IS NOT NULL THEN 1 ELSE 0 END) gps_policy_present,
             SUM(CASE WHEN CheckDistance IS NOT NULL THEN 1 ELSE 0 END) distance_check_present,
             SUM(CASE WHEN MaxDistance IS NOT NULL THEN 1 ELSE 0 END) max_distance_present,
             SUM(CASE WHEN ShowStockLevel IS NOT NULL THEN 1 ELSE 0 END) stock_visibility_present,
             SUM(CASE WHEN AllowReturnWithRef IS NOT NULL THEN 1 ELSE 0 END) return_with_ref_policy_present,
             SUM(CASE WHEN AllowReturnWithoutRef IS NOT NULL THEN 1 ELSE 0 END) return_without_ref_policy_present,
             SUM(CASE WHEN InventoryControl IS NOT NULL THEN 1 ELSE 0 END) inventory_control_present,
             SUM(CASE WHEN SayadCheckMandatory IS NOT NULL THEN 1 ELSE 0 END) sayad_policy_present,
             SUM(CASE WHEN MandatoryCustomerVisit IS NOT NULL THEN 1 ELSE 0 END) mandatory_visit_policy_present
      FROM NGT.DeviceSettings
    """)[0]
    return {"catalog_and_setting_population": catalogs,
            "safe_policy_field_coverage_without_values": policy_coverage,
            "boundary": "Base/Public values are semantic catalogs; Device/App settings are scoped behavior. Names/IDs need crosswalks, while secret-bearing fields remain outside artifacts and logs."}


def _reviewed_rule_usage(cursor: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in REVIEWED_RULE_KEYS:
        escaped = key.replace("'", "''")
        rows = _rows(cursor, f"""
          SELECT COUNT_BIG(*) module_count,
                 SUM(CASE WHEN o.type IN ('P','PC') THEN 1 ELSE 0 END) procedure_count,
                 SUM(CASE WHEN o.type IN ('V') THEN 1 ELSE 0 END) view_count,
                 SUM(CASE WHEN o.type IN ('FN','IF','TF') THEN 1 ELSE 0 END) function_count,
                 SUM(CASE WHEN o.type IN ('TR') THEN 1 ELSE 0 END) trigger_count
          FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
          WHERE m.definition LIKE '%{escaped}%'
        """)[0]
        result.append({"rule_key": key, **rows})
    return result


def _sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
      SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
             DATALENGTH(m.definition) definition_bytes
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      JOIN sys.sql_modules m ON m.object_id=o.object_id
      WHERE o.name IN ('Usp_GetSupplierRemAmount','usp_Prepare_OpenInvoice',
        'usp_ApplySupInvoice','usp_ValidateSupInvoiceAmount',
        'usp_sdsnet_RetSale_BeforeSave','usp_sdsnet_PChequeChangeStatus_Save',
        'usp_sdsnet_RChequeChangeStatus_Save')
      ORDER BY s.name,o.name
    """)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "configuration_and_rule_flags",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only configuration schema, key names, aggregate coverage, and module-use evidence",
                      "privacy_policy": "no config/old values, credentials, URLs, paths, hosts/apps, device-owner rows, or raw history"},
            "safety": {"target_is_local": True, "database_name": safety["database_name"],
                       "updateability": safety["updateability"], "can_select": safety["can_select"],
                       "can_view_definition": safety["can_view_definition"], "can_update": safety["can_update"],
                       "denies_data_writes": safety["denies_data_writes"]},
            "tables": [_public_metadata(_table_metadata(cursor, x["object"], x["role"])) for x in DOMAIN_TABLES],
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _consumers(cursor),
            "key_value_configs": _key_value_profile(cursor),
            "dc_and_customer_configs": _dc_and_customer_config(cursor),
            "ngt_configuration": _ngt_profile(cursor),
            "reviewed_rule_key_usage": _reviewed_rule_usage(cursor),
            "semantic_contract_sources": _sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "migration_contract": (
                "Every business-rule decision must record configuration scope, effective version, "
                "and non-secret value hash; secret-bearing settings stay in a secret store."
            ),
            "evidence_limits": [
                "No configuration value or old value is persisted; value_shape is only null/boolean-like/numeric-like/text-like.",
                "No credential, URL, path, host/application identity, device-owner row, or raw history is persisted.",
                "Module text matches prove a key is referenced, not the full runtime precedence among general/server/DC/device/app scopes.",
                "History-only keys may be retired or renamed; they are not automatically active settings.",
                "Client applications may consume settings outside SQL dependency metadata.",
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
