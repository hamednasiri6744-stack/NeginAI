"""Extract anonymous current order-to-sale policy configuration profiles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows


FIELDS = (
    "CheckSaleItmStock",
    "SaleAsnLimit",
    "SaleBedLimit",
    "SaleAsnLimitDealer",
    "SaleBedLimitDealer",
    "SaleMaxLimit",
)

CREDIT_MODES = {
    0: "FORCED_BYPASS_CONTROL_DISABLED_CHECKED",
    1: "USER_SELECTABLE_DEFAULT_ENFORCED",
    2: "FORCED_ENFORCEMENT_CONTROL_DISABLED_UNCHECKED",
}
STOCK_MODES = {
    0: "USER_SELECTABLE_DEFAULT_STRICT",
    1: "FORCED_PARTIAL_CONVERSION_CONTROL_DISABLED_CHECKED",
    2: "FORCED_STRICT_CONTROL_DISABLED_UNCHECKED",
}


def _mode(field: str, value: Any) -> str:
    if value is None:
        return "NULL_UNRESOLVED"
    mapping = STOCK_MODES if field == "CheckSaleItmStock" else CREDIT_MODES
    return mapping.get(int(value), "OUT_OF_RECONSTRUCTED_ENUM")


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        object_rows = _rows(
            cursor,
            """
            SELECT o.type_desc,s.name schema_name,o.name object_name,o.modify_date
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            WHERE o.object_id=OBJECT_ID('gnr.SdsNet_serverConfig')
            """,
        )
        if len(object_rows) != 1:
            raise AssertionError("SdsNet server configuration object is absent or duplicated")
        select_fields = ",".join(FIELDS)
        group_fields = ",".join(FIELDS)
        profiles = _rows(
            cursor,
            f"""
            SELECT {select_fields},COUNT_BIG(*) profile_row_count
            FROM gnr.SdsNet_serverConfig
            GROUP BY {group_fields}
            ORDER BY {group_fields}
            """,
        )
        aggregate = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) config_row_count,COUNT_BIG(DISTINCT DcRef) dc_count,
              SUM(CASE WHEN D.ID IS NULL THEN 1 ELSE 0 END) orphan_dc_count
            FROM gnr.SdsNet_serverConfig C
            LEFT JOIN gnr.tblDC D ON D.ID=C.DcRef
            """,
        )[0]
        normalized = []
        for profile in profiles:
            count = int(profile.pop("profile_row_count"))
            normalized.append(
                {
                    "profile_row_count": count,
                    "policy_modes": {
                        field: {
                            "enum_value": profile[field],
                            "mode": _mode(field, profile[field]),
                        }
                        for field in FIELDS
                    },
                }
            )
        invalid_nonnull = sum(
            row["profile_row_count"]
            for row in normalized
            if any(
                value["mode"] == "OUT_OF_RECONSTRUCTED_ENUM"
                for value in row["policy_modes"].values()
            )
        )
        null_profile_rows = sum(
            row["profile_row_count"]
            for row in normalized
            if any(value["mode"] == "NULL_UNRESOLVED" for value in row["policy_modes"].values())
        )
        null_cells = sum(
            row["profile_row_count"]
            * sum(value["mode"] == "NULL_UNRESOLVED" for value in row["policy_modes"].values())
            for row in normalized
        )
        assertions = {
            "read_only_clone_and_denied_writer": context["updateability"] == "READ_ONLY"
            and context["can_update"] == 0
            and context["denies_data_writes"] == 1,
            "all_config_rows_have_current_dc": aggregate["orphan_dc_count"] == 0,
            "all_nonnull_selected_values_are_in_reconstructed_enum": invalid_nonnull == 0,
            "null_values_are_explicitly_classified_not_defaulted": all(
                value["mode"] == "NULL_UNRESOLVED"
                for row in normalized
                for value in row["policy_modes"].values()
                if value["enum_value"] is None
            ),
            "profile_counts_cover_all_config_rows": sum(row["profile_row_count"] for row in normalized)
            == aggregate["config_row_count"],
            "no_operational_command_was_executed": True,
        }
        mode_distribution = {
            field: sorted(
                [
                    {"mode": mode, "config_row_count": count}
                    for mode, count in {
                        candidate: sum(
                            row["profile_row_count"]
                            for row in normalized
                            if row["policy_modes"][field]["mode"] == candidate
                        )
                        for candidate in {
                            row["policy_modes"][field]["mode"] for row in normalized
                        }
                    }.items()
                ],
                key=lambda row: row["mode"],
            )
            for field in FIELDS
        }
        return {
            "artifact": "varanegar_order_sale_policy_config_snapshot",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": {
                "server_class": "LOCAL_READ_ONLY_CLONE",
                "database": context["database_name"],
                "login": context["login_name"],
                "configuration_object": object_rows[0],
            },
            "safety": {
                "connection_readonly": True,
                "operational_stored_procedure_executions": 0,
                "business_row_ids_names_or_dc_ids_persisted": 0,
                "raw_sql_definitions_strings_or_secrets_persisted": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "config_row_count": int(aggregate["config_row_count"]),
                "dc_count": int(aggregate["dc_count"]),
                "orphan_dc_count": int(aggregate["orphan_dc_count"]),
                "distinct_policy_profile_count": len(normalized),
                "invalid_nonnull_policy_row_count": invalid_nonnull,
                "profile_row_with_null_policy_count": null_profile_rows,
                "null_policy_cell_count": null_cells,
            },
            "enum_contract": {
                "credit_and_limit": CREDIT_MODES,
                "stock_shortage": STOCK_MODES,
            },
            "anonymous_policy_profiles": normalized,
            "anonymous_mode_distribution": mode_distribution,
            "null_semantic_boundary": {
                "entity_getters_return_cli_int32_not_nullable": "PROVEN_BY_SEPARATE_HASH_PINNED_UI_IL_ARTIFACT",
                "database_columns_can_be_null": True,
                "ui_materializer_null_to_int32_behavior": "NOT_PROVEN",
                "sql_customer_or_dealer_pair_reloaded_as_both_null": "INNER_IN_OR_CONDITION_EVALUATES_UNKNOWN_SO_VALIDATOR_BRANCH_IS_NOT_ENTERED",
                "target_requirement": "REJECT_OR_RESOLVE_NULL_EXPLICITLY_BEFORE_POLICY_DECISION",
            },
            "assertions": assertions,
            "limits": [
                "The clone snapshot establishes current anonymous configuration, not historical effective values at each conversion attempt.",
                "No DC identity is persisted, so profile ownership and production parity are intentionally not attributed.",
                "NULL is not coerced to enum zero; UI materialization and SQL three-valued logic must be reconciled before target policy mapping.",
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
