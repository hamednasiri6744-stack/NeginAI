"""Extract read-only SQL authorization and resource-scope boundaries for order-to-sale."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text


COMMANDS = (
    "SLE.usp_sdsnet_CreateSaleByOrder",
    "SLE.usp_CreateSaleByOrder",
    "SLE.usp_sdsnet_CreateSaleByOrder_CheckAreaAccess",
    "SLE.usp_sdsnet_Order_OrderTypePermission",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        definitions = {}
        raw_definitions = {}
        modules = []
        for command in COMMANDS:
            rows = _rows(
                cursor,
                """
                SELECT m.definition,o.modify_date,o.type_desc
                FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
                WHERE m.object_id=OBJECT_ID(%s)
                """,
                (command,),
            )
            if len(rows) != 1:
                raise AssertionError(f"authorization command absent or duplicated: {command}")
            definition = rows[0]["definition"] or ""
            raw_definitions[command] = definition
            definitions[command] = " ".join(_executable_text(definition).replace("[", "").replace("]", "").split()).casefold()
            parameters = _rows(
                cursor,
                """
                SELECT parameter_id,name parameter_name,TYPE_NAME(user_type_id) data_type,is_output
                FROM sys.parameters WHERE object_id=OBJECT_ID(%s) ORDER BY parameter_id
                """,
                (command,),
            )
            dependencies = _rows(
                cursor,
                """
                SELECT DISTINCT COALESCE(referenced_schema_name,'?') referenced_schema,
                  referenced_entity_name
                FROM sys.sql_expression_dependencies
                WHERE referencing_id=OBJECT_ID(%s) AND referenced_entity_name IS NOT NULL
                ORDER BY referenced_schema,referenced_entity_name
                """,
                (command,),
            )
            executable = definitions[command]
            modules.append(
                {
                    "qualified_command": command,
                    "type_desc": rows[0]["type_desc"],
                    "modify_date": rows[0]["modify_date"],
                    "definition_sha256": _sha(definition),
                    "definition_character_count": len(definition),
                    "parameters": parameters,
                    "authorization_term_count": len(
                        re.findall(r"\b(permission|persmission|authori[sz]|access|acsses|right|role)\w*\b", executable, re.I)
                    ),
                    "authorization_dependencies": [
                        f"{row['referenced_schema']}.{row['referenced_entity_name']}"
                        for row in dependencies
                        if re.search(r"(?i)(user|group|right|access|area|permission|role)", row["referenced_entity_name"])
                    ],
                }
            )

        wrapper = definitions[COMMANDS[0]]
        core = definitions[COMMANDS[1]]
        area = definitions[COMMANDS[2]]
        raw_area = raw_definitions[COMMANDS[2]]
        order_type = definitions[COMMANDS[3]]
        current = {
            "global_area_access_enabled_key_count": int(
                _rows(
                    cursor,
                    "SELECT COUNT_BIG(*) value FROM GNR.tblServerConfig WHERE KeyName='AreaAccess' AND KeyValue=1",
                )[0]["value"]
            ),
            "general_config_row_count": int(
                _rows(cursor, "SELECT COUNT_BIG(*) value FROM GNR.SdsNet_generalConfig")[0]["value"]
            ),
            "general_config_area_access_true_count": int(
                _rows(cursor, "SELECT COUNT_BIG(*) value FROM GNR.SdsNet_generalConfig WHERE AreaAccess=1")[0]["value"]
            ),
            "sale_user_access_projection_row_count": int(
                _rows(cursor, "SELECT COUNT_BIG(*) value FROM GNR.vwSaleUserAccess")[0]["value"]
            ),
            "direct_order_type_user_right_row_count": int(
                _rows(cursor, "SELECT COUNT_BIG(*) value FROM SLE.tblOrderTypeUserRight")[0]["value"]
            ),
            "group_order_type_right_row_count": int(
                _rows(cursor, "SELECT COUNT_BIG(*) value FROM SLE.tblOrderTypeUserGroupRight")[0]["value"]
            ),
        }
        semantic_assertions = {
            "wrapper_calls_conditional_area_access_before_core": (
                wrapper.find("usp_sdsnet_createsalebyorder_checkareaaccess") >= 0
                and wrapper.find("usp_createsalebyorder_checkareaaccess")
                < wrapper.find("sle.usp_createsalebyorder")
            ),
            "area_access_is_enabled_only_by_global_key_value_one": (
                "tblserverconfig" in area
                and re.search(r"(?i)keyname\s*=\s*N?'AreaAccess'", raw_area) is not None
                and "keyvalue = 1" in area
            ),
            "area_access_scopes_customer_sale_area_to_user_projection": (
                "vwsaleuseraccess" in area and "userref=@userref" in area and "cc.id=@custref" in area
            ),
            "area_access_allows_customer_without_sale_area": "or sa.id is null" in area,
            "core_accepts_actor_but_has_no_access_or_right_dependency": (
                "@userref" in core
                and not re.search(r"(?i)(permission|persmission|authori[sz]|access|acsses|userright|groupright)", core)
            ),
            "order_type_permission_has_no_convert_action": (
                "@actiontype" in order_type
                and "power (2, @actiontype)" in order_type
                and not re.search(r"(?i)(convert|create\s*sale|order\s*to\s*sale)", order_type)
            ),
            "order_type_permission_supports_admin_direct_and_group_rights": all(
                token in order_type
                for token in ("isadmin=1", "tblordertypeuserright", "tblordertypeusergroupright")
            ),
            "current_clone_global_and_general_area_access_are_disabled": (
                current["global_area_access_enabled_key_count"] == 0
                and current["general_config_area_access_true_count"] == 0
            ),
        }
        assertions = {
            "read_only_clone_and_denied_writer": context["updateability"] == "READ_ONLY"
            and context["can_update"] == 0
            and context["denies_data_writes"] == 1,
            "all_selected_modules_found": len(modules) == len(COMMANDS),
            "all_semantic_assertions_pass": all(semantic_assertions.values()),
            "no_operational_command_executed": True,
        }
        return {
            "artifact": "varanegar_order_sale_authorization_sql",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": {
                "server_class": "LOCAL_READ_ONLY_CLONE",
                "database": context["database_name"],
                "login": context["login_name"],
            },
            "safety": {
                "connection_readonly": True,
                "operational_stored_procedure_executions": 0,
                "raw_sql_definitions_messages_string_literals_or_identities_persisted": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "selected_sql_module_count": len(modules),
                **current,
            },
            "modules": modules,
            "contract": {
                "server_resource_scope_gate": "CONDITIONAL_CUSTOMER_SALE_AREA_ACCESS",
                "server_resource_scope_gate_enablement": "GNR_TBLSERVERCONFIG_AREAACCESS_EQUALS_ONE",
                "server_action_authorization_for_convert_order_to_sale": "NOT_PROVEN_IN_SELECTED_COMMANDS",
                "order_type_right_actions": ["VIEW", "NEW", "EDIT", "DELETE", "CANCEL", "CONFIRM", "UNCONFIRM"],
                "order_type_right_has_convert_action": False,
                "target_requirement": "DISTINCT_SERVER_SIDE_CONVERT_ORDER_TO_SALE_ACTION_PLUS_DC_SALE_OFFICE_CUSTOMER_AREA_ORDER_SCOPE",
            },
            "semantic_assertions": semantic_assertions,
            "assertions": assertions,
            "limits": [
                "Static SQL absence does not prove absence of menu, endpoint, proxy, database-role or outer middleware authorization.",
                "Current clone configuration is not proof of production configuration or historical enablement.",
                "Retained right rows do not prove the effective rights of any current identity.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
