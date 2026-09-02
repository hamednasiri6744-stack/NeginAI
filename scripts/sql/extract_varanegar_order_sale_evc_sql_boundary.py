"""Extract the read-only SQL boundary for Discount V2 EVC staging and payment usance persistence."""

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


MODULES = (
    "SLE.usp_sdsnet_CreateSaleByOrder",
    "SLE.usp_CreateSaleByOrder",
    "SLE.usp_CreateSaleByEVC",
    "SLE.usp_FillEVCByOrder",
    "SLE.usp_DoEVC",
)
TOKENS = (
    "@calcfordiscountv2",
    "#saleitempaymentusance",
    "#salesaleitempaymentusance",
    "#tbltempevc",
    "tblsaleitempaymentusance",
    "begin transaction",
    "commit transaction",
    "rollback transaction",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact_strings(line: str) -> str:
    return re.sub(r"N?'(?:''|[^'])*'", "'<STRING>'", " ".join(line.split()), flags=re.I)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        modules: list[dict[str, Any]] = []
        definitions: dict[str, str] = {}
        raw_definitions: dict[str, str] = {}
        for name in MODULES:
            rows = _rows(
                cursor,
                "SELECT m.definition,o.modify_date FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id WHERE m.object_id=OBJECT_ID(%s)",
                (name,),
            )
            if len(rows) != 1:
                raise AssertionError(f"selected SQL module missing or duplicated: {name}")
            definition = rows[0]["definition"] or ""
            executable = _executable_text(definition)
            definitions[name] = executable
            raw_definitions[name] = definition
            selected_lines = []
            for line_number, line in enumerate(executable.splitlines(), start=1):
                lowered = line.casefold()
                matched = [token for token in TOKENS if token in lowered]
                if matched:
                    selected_lines.append(
                        {
                            "line_number": line_number,
                            "matched_tokens": matched,
                            "redacted_line": _redact_strings(line),
                            "line_sha256": _sha(line),
                        }
                    )
            parameters = _rows(
                cursor,
                "SELECT parameter_id,name,TYPE_NAME(user_type_id) data_type,is_output FROM sys.parameters WHERE object_id=OBJECT_ID(%s) ORDER BY parameter_id",
                (name,),
            )
            modules.append(
                {
                    "qualified_name": name,
                    "modify_date": rows[0]["modify_date"],
                    "definition_sha256": _sha(definition),
                    "definition_length": len(definition),
                    "parameters": parameters,
                    "selected_lines": selected_lines,
                }
            )

        single_name_modules = _rows(
            cursor,
            """
            SELECT CONCAT(SCHEMA_NAME(o.schema_id),'.',o.name) qualified_name
            FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE m.definition LIKE %s ORDER BY qualified_name
            """,
            ("%#SaleItemPaymentUsance%",),
        )
        double_name_modules = _rows(
            cursor,
            """
            SELECT CONCAT(SCHEMA_NAME(o.schema_id),'.',o.name) qualified_name
            FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE m.definition LIKE %s ORDER BY qualified_name
            """,
            ("%#SaleSaleItemPaymentUsance%",),
        )
        persistent_count = int(
            _rows(cursor, "SELECT COUNT_BIG(*) row_count FROM SLE.tblSaleItemPaymentUsance")[0]["row_count"]
        )
        discount_v2_config = _rows(
            cursor,
            """
            SELECT COUNT(*) row_count,
                   SUM(CASE WHEN TRY_CONVERT(int,KeyValue)=1 THEN 1 ELSE 0 END) enabled_count
            FROM GNR.tblServerConfig WHERE KeyName=%s
            """,
            ("IsDiscountV2Active",),
        )[0]

        wrapper = " ".join(definitions["SLE.usp_sdsnet_CreateSaleByOrder"].split()).casefold()
        core = " ".join(raw_definitions["SLE.usp_CreateSaleByOrder"].split()).casefold()
        create_by_evc = " ".join(definitions["SLE.usp_CreateSaleByEVC"].split()).casefold()
        flag_parameter = next(
            row
            for row in next(m for m in modules if m["qualified_name"] == "SLE.usp_sdsnet_CreateSaleByOrder")[
                "parameters"
            ]
            if row["name"].casefold() == "@calcfordiscountv2"
        )
        assertions = {
            "all_selected_modules_found": len(modules) == len(MODULES),
            "calc_for_discount_v2_parameter_is_input_int": flag_parameter["data_type"] == "int"
            and not bool(flag_parameter["is_output"]),
            "calc_for_discount_v2_default_is_zero": bool(
                re.search(r"@calcfordiscountv2\s+int\s*=\s*0", wrapper, re.I)
            ),
            "legacy_evc_branch_is_guarded_by_flag_zero": "if (@calcfordiscountv2=0)" in wrapper,
            "legacy_branch_fills_evc_and_builds_single_usance_temp": all(
                token in wrapper
                for token in (
                    "exec @retstat=sle.usp_fillevcbyorder",
                    "into #saleitempaymentusance",
                )
            ),
            "core_creates_single_usance_temp_when_absent": all(
                token in core
                for token in (
                    "object_id('tempdb..#saleitempaymentusance') is null",
                    "create table #saleitempaymentusance",
                )
            ),
            "create_sale_by_evc_reads_single_temp_and_persists_rows": all(
                token in create_by_evc
                for token in (
                    "from #saleitempaymentusance",
                    "insert into sle.tblsaleitempaymentusance",
                )
            ),
            "no_sql_module_references_double_sale_temp_name": len(double_name_modules) == 0,
            "database_is_read_only_and_writer_is_denied": context["updateability"] == "READ_ONLY"
            and context["denies_data_writes"] == 1,
            "current_clone_has_single_disabled_discount_v2_key": (
                int(discount_v2_config["row_count"]) == 1
                and int(discount_v2_config["enabled_count"] or 0) == 0
            ),
        }
        return {
            "artifact": "varanegar_order_sale_evc_sql_boundary",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": context,
            "safety": {
                "mode": "READ_ONLY_CATALOG_AND_AGGREGATE_QUERIES",
                "commands_executed": 0,
                "form_procedures_executed": 0,
                "data_mutations": 0,
                "raw_business_rows_persisted": 0,
            },
            "summary": {
                "selected_module_count": len(modules),
                "single_temp_name_module_count": len(single_name_modules),
                "double_temp_name_module_count": len(double_name_modules),
                "persistent_sale_item_payment_usance_row_count": persistent_count,
                "discount_v2_config_row_count": int(discount_v2_config["row_count"]),
                "discount_v2_enabled_key_count": int(discount_v2_config["enabled_count"] or 0),
            },
            "modules": modules,
            "single_temp_name_modules": [row["qualified_name"] for row in single_name_modules],
            "double_temp_name_modules": [row["qualified_name"] for row in double_name_modules],
            "assertions": assertions,
            "limits": [
                "The clone currently has no persistent sale-item payment-usance rows, so reachability is structural rather than historical-frequency proof.",
                "SQL catalog inspection cannot prove reflection-based assignment of the managed CalcForDiscountV2 property.",
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
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
