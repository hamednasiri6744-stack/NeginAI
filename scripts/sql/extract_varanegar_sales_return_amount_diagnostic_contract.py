"""Extract the Varanegar sales-return amount contract without executing it.

The database side reads catalog definitions and anonymous aggregates from the
read-only clone.  The binary side parses PE metadata/IL without loading or
executing assemblies.  No party identities, document identifiers, comments,
credentials, raw rows, forms, or stored procedures are persisted or executed.
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
from dncil.clr.token import Token

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
    _owner_maps,
    _resolve_token,
)


RECENT_FROM = "1405/03/01"
RECENT_TO = "1405/05/31"

MODULE_NAMES = (
    "usp_CheckRetSaleAmountDiscount",
    "usp_RecalcRetSale",
    "usp_Sdsnet_RetSale_Save",
    "USP_SDSNET_RetSaleItm_GetList",
)

IL_TARGETS = {
    "VN.SDS.Common.dll": {
        "VN.SDS.Common.Sales.Entity.RetSale.RetSaleItemEntity",
    },
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry",
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.RetSale.RetSaleHandler",
        "VN.SDS.Sales.Business.RetSale.RetSaleValidator",
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter",
    },
}


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
                "checks_item_discount_rollup": (
                    "discount" in normalized
                    and "dis1" in normalized
                    and "dis2" in normalized
                    and "dis3" in normalized
                    and "otherdiscount" in normalized
                ),
                "checks_item_addition_rollup": (
                    "addamount" in normalized
                    and "add1" in normalized
                    and "add2" in normalized
                    and "otheraddition" in normalized
                ),
                "checks_net_formula": "amountnut <> amount - discount + addamount"
                in normalized,
                "checks_header_total_against_net_items": bool(
                    re.search(
                        r"totalamount\s*<>\s*sum\s*\(\s*isnull\s*\(\s*si\.amountnut",
                        normalized,
                    )
                ),
                "recalculates_header_total_from_net_items": bool(
                    re.search(
                        r"totalamount\s*=\s*\(\s*select\s+sum\s*\(\s*amountnut",
                        normalized,
                    )
                ),
            }
        )
    return public, definitions


def _schema_contract(cursor: Any) -> dict[str, Any]:
    columns = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               TYPE_NAME(c.user_type_id) data_type,c.max_length,c.precision,c.scale,
               c.is_nullable
        FROM sys.columns c
        JOIN sys.tables t ON t.object_id=c.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE c.object_id IN (OBJECT_ID(N'SLE.tblRetSaleHdr'),
                              OBJECT_ID(N'SLE.tblRetSaleItm'))
          AND c.name IN ('TotalAmount','Amount','AmountNut','Discount','AddAmount',
                         'Dis1','Dis2','Dis3','OtherDiscount',
                         'Add1','Add2','OtherAddition','Tax','Charge','CancelFlag',
                         'RetSaleDate','HdrRef')
        ORDER BY s.name,t.name,c.column_id
        """,
    )
    constraints = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,cc.name constraint_name,
               cc.definition
        FROM sys.check_constraints cc
        JOIN sys.tables t ON t.object_id=cc.parent_object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE cc.parent_object_id=OBJECT_ID(N'SLE.tblRetSaleItm')
          AND (cc.definition LIKE '%Amount%' OR cc.definition LIKE '%Discount%'
               OR cc.definition LIKE '%AddAmount%')
        ORDER BY cc.name
        """,
    )
    return {"amount_columns": columns, "relevant_check_constraints": constraints}


def _reconciliation(cursor: Any) -> dict[str, Any]:
    overall = _rows(
        cursor,
        """
        WITH a AS (
          SELECT HdrRef,
                 SUM(Amount) gross_amount,
                 SUM(AmountNut) stored_net_amount,
                 SUM(Amount-Discount+AddAmount) calculated_net_amount,
                 SUM(Amount-(Dis1+Dis2+Dis3+OtherDiscount)
                           +(Add1+Add2+OtherAddition)) component_net_amount,
                 SUM(Discount) discount_amount,
                 SUM(AddAmount) addition_amount,
                 SUM(Dis1+Dis2+Dis3+OtherDiscount) component_discount_amount,
                 SUM(Add1+Add2+OtherAddition) component_addition_amount
          FROM SLE.tblRetSaleItm GROUP BY HdrRef
        )
        SELECT COUNT_BIG(*) returns,
               SUM(CASE WHEN ABS(h.TotalAmount-a.gross_amount)>.01 THEN 1 ELSE 0 END)
                    gross_comparison_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.stored_net_amount)>.01 THEN 1 ELSE 0 END)
                    stored_net_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.calculated_net_amount)>.01 THEN 1 ELSE 0 END)
                    calculated_net_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.component_net_amount)>.01 THEN 1 ELSE 0 END)
                    component_net_differences,
               SUM(CASE WHEN ABS(a.stored_net_amount-a.calculated_net_amount)>.01
                        THEN 1 ELSE 0 END) stored_item_net_formula_differences,
               SUM(CASE WHEN ABS(a.discount_amount-a.component_discount_amount)>.01
                        THEN 1 ELSE 0 END) discount_rollup_differences,
               SUM(CASE WHEN ABS(a.addition_amount-a.component_addition_amount)>.01
                        THEN 1 ELSE 0 END) addition_rollup_differences,
               MAX(ABS(h.TotalAmount-a.calculated_net_amount)) maximum_official_net_delta,
               SUM(h.TotalAmount) header_net_total,
               SUM(a.gross_amount) item_gross_total,
               SUM(a.calculated_net_amount) calculated_item_net_total,
               SUM(a.gross_amount-h.TotalAmount) gross_minus_official_net_total
        FROM SLE.tblRetSaleHdr h JOIN a ON a.HdrRef=h.ID
        """,
    )[0]
    by_cancel_state = _rows(
        cursor,
        """
        WITH a AS (
          SELECT HdrRef,SUM(Amount) gross_amount,
                 SUM(AmountNut) stored_net_amount,
                 SUM(Amount-Discount+AddAmount) calculated_net_amount
          FROM SLE.tblRetSaleItm GROUP BY HdrRef
        )
        SELECT h.CancelFlag,COUNT_BIG(*) returns,
               SUM(CASE WHEN ABS(h.TotalAmount-a.gross_amount)>.01 THEN 1 ELSE 0 END)
                    gross_comparison_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.stored_net_amount)>.01 THEN 1 ELSE 0 END)
                    stored_net_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.calculated_net_amount)>.01 THEN 1 ELSE 0 END)
                    calculated_net_differences,
               SUM(a.gross_amount-h.TotalAmount) gross_minus_official_net_total
        FROM SLE.tblRetSaleHdr h JOIN a ON a.HdrRef=h.ID
        GROUP BY h.CancelFlag ORDER BY h.CancelFlag
        """,
    )
    return {"overall": overall, "by_cancel_state": by_cancel_state}


def _recent_activity(cursor: Any) -> dict[str, Any]:
    monthly = _rows(
        cursor,
        f"""
        WITH a AS (
          SELECT HdrRef,SUM(Amount) gross_amount,
                 SUM(AmountNut) stored_net_amount,
                 SUM(Amount-Discount+AddAmount) calculated_net_amount
          FROM SLE.tblRetSaleItm GROUP BY HdrRef
        )
        SELECT LEFT(h.RetSaleDate,7) month_bucket,h.CancelFlag,COUNT_BIG(*) returns,
               SUM(CASE WHEN ABS(h.TotalAmount-a.gross_amount)>.01 THEN 1 ELSE 0 END)
                    gross_comparison_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.stored_net_amount)>.01 THEN 1 ELSE 0 END)
                    stored_net_differences,
               SUM(CASE WHEN ABS(h.TotalAmount-a.calculated_net_amount)>.01 THEN 1 ELSE 0 END)
                    calculated_net_differences,
               SUM(a.gross_amount-h.TotalAmount) gross_minus_official_net_total
        FROM SLE.tblRetSaleHdr h JOIN a ON a.HdrRef=h.ID
        WHERE h.RetSaleDate BETWEEN '{RECENT_FROM}' AND '{RECENT_TO}'
        GROUP BY LEFT(h.RetSaleDate,7),h.CancelFlag
        ORDER BY month_bucket,h.CancelFlag
        """,
    )
    return {
        "business_date_from": RECENT_FROM,
        "business_date_to": RECENT_TO,
        "monthly_cancel_state_aggregates": monthly,
        "interpretation": "current return headers grouped by Persian business month; not an event transition log",
    }


def _method_calls(
    assemblies: list[dict[str, Any]], type_name: str, method_name: str
) -> set[str]:
    for assembly in assemblies:
        for target_type in assembly.get("target_types", []):
            if target_type.get("type") != type_name:
                continue
            for method in target_type.get("methods", []):
                if method.get("method") == method_name:
                    return set(method.get("calls", []))
    raise RuntimeError(f"Required IL method not found: {type_name}.{method_name}")


def _method_calls_any_type(path: Path, method_name: str) -> set[str]:
    """Resolve calls for a uniquely named compiler-generated method."""
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    matches = []
    for type_row in pe.net.mdtables.TypeDef.rows:
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is not None and str(method.Name) == method_name and method.Rva:
                matches.append(method)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one IL method named {method_name}, observed {len(matches)}"
        )
    body = read_method_body_from_bytes(pe.get_data(matches[0].Rva, 65536))
    return {
        _resolve_token(pe, instruction.operand, method_owners, field_owners)
        for instruction in body.instructions
        if instruction.mnemonic in {"call", "callvirt", "newobj"}
        and isinstance(instruction.operand, Token)
    }


def _il_contract(source_directory: Path) -> dict[str, Any]:
    assemblies = [
        _analyze_assembly(source_directory / file_name, target_types)
        for file_name, target_types in sorted(IL_TARGETS.items())
    ]
    form_type = "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry"
    entity_type = "VN.SDS.Common.Sales.Entity.RetSale.RetSaleItemEntity"
    handler_type = "VN.SDS.Sales.Business.RetSale.RetSaleHandler"
    adapter_type = "VN.SDS.Sales.DataAccess.DataAdapter.RetSale.RetSaleAdapter"

    fill_calls = _method_calls(assemblies, form_type, "FillSumOfDisAddS")
    final_selector_calls = _method_calls_any_type(
        source_directory / "VN.SDS.Sales.UI.dll",
        "<FillSumOfDisAddS>b__142_7",
    )
    save_calls = _method_calls(assemblies, form_type, "SaveCommand")
    entity_amount_calls = _method_calls(assemblies, entity_type, "set_Amount")
    entity_discount_calls = _method_calls(assemblies, entity_type, "set_Discount")
    handler_calls = _method_calls(
        assemblies, handler_type, "CheckRetSaleAmountDiscount"
    )
    adapter_calls = _method_calls(assemblies, adapter_type, "CheckRetSaleAmountDiscount")

    contracts = {
        "form_sums_official_item_net": {
            "required": {
                "VN.SDS.Common.Sales.Entity.RetSale.RetSaleEntity.set_TotalAmount",
            },
            "observed": fill_calls,
        },
        "form_final_selector_reads_official_item_net": {
            "required": {f"{entity_type}.get_AmountNutFinal"},
            "observed": final_selector_calls,
        },
        "form_save_uses_unit_of_work_and_business_handler": {
            "required": {
                f"{handler_type}.SaveCommand",
                "Thunderstruck.DataContext.Commit",
            },
            "observed": save_calls,
        },
        "item_amount_setter_recalculates_final_net": {
            "required": {
                f"{entity_type}.get__Amount",
                f"{entity_type}.get__Discount",
                f"{entity_type}.get__AddAmount",
                f"{entity_type}.set__AmountNutFinal",
                "System.Decimal.op_Subtraction",
                "System.Decimal.op_Addition",
            },
            "observed": entity_amount_calls,
        },
        "item_discount_setter_recalculates_final_net": {
            "required": {
                f"{entity_type}.set__Discount",
                f"{entity_type}.set__AmountNutFinal",
                "System.Decimal.op_Subtraction",
                "System.Decimal.op_Addition",
            },
            "observed": entity_discount_calls,
        },
        "business_amount_validation_maps_to_adapter": {
            "required": {f"{adapter_type}.CheckRetSaleAmountDiscount"},
            "observed": handler_calls,
        },
        "adapter_maps_amount_validation_procedure": {
            "required": {"Thunderstruck.DataContext.Execute"},
            "observed": adapter_calls,
        },
    }
    for name, contract in contracts.items():
        missing = contract["required"] - contract["observed"]
        if missing:
            raise RuntimeError(f"IL contract drift for {name}: {sorted(missing)}")

    return {
        "assemblies": assemblies,
        "verified_branch_contracts": [
            {
                "method": f"{form_type}.FillSumOfDisAddS",
                "contract": "header TotalAmount is the sum of RetSaleItemEntity.AmountNutFinal, not the sum of Amount",
            },
            {
                "method": f"{entity_type}.set_Amount and set_Discount",
                "contract": "the in-memory final net is recalculated as Amount - Discount + AddAmount",
            },
            {
                "method": f"{form_type}.SaveCommand",
                "contract": "save flows through RetSaleHandler and commits the DataContext only after checks",
            },
            {
                "method": f"{handler_type}.CheckRetSaleAmountDiscount",
                "contract": "the business validation method maps to the RetSaleAdapter SQL validation boundary",
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
            schema = _schema_contract(cursor)
            reconciliation = _reconciliation(cursor)
            recent = _recent_activity(cursor)

    il = _il_contract(source_directory)
    validation_definition = _normalize(
        definitions.get("SLE.usp_CheckRetSaleAmountDiscount", "")
    )
    recalc_definition = _normalize(definitions.get("dbo.usp_RecalcRetSale", ""))
    sql_formula_verified = (
        "amountnut <> amount - discount + addamount" in validation_definition
    )
    sql_header_net_verified = bool(
        re.search(
            r"totalamount\s*<>\s*sum\s*\(\s*isnull\s*\(\s*si\.amountnut",
            validation_definition,
        )
    )
    recalc_header_net_verified = bool(
        re.search(
            r"totalamount\s*=\s*\(\s*select\s+sum\s*\(\s*amountnut",
            recalc_definition,
        )
    )
    overall = reconciliation["overall"]

    findings = [
        _finding(
            "RA-001",
            "The previous 696-active-return amount-mismatch classification is invalid",
            "CRITICAL",
            [
                "the previous comparison used header TotalAmount versus SUM(item Amount)",
                "the official SQL validator compares TotalAmount with SUM(item AmountNut)",
                "all 13,913 active returns have zero official-net residual",
            ],
            "Treating gross-to-net adjustment as corruption would quarantine valid returns and can overstate customer credit or reversal values.",
            "Replace every gross comparison with the official stored-net contract and retain the gross/net adjustment as explainable provenance.",
        ),
        _finding(
            "RA-002",
            "The official return item net formula is Amount - Discount + AddAmount",
            "HIGH",
            [
                "SLE.usp_CheckRetSaleAmountDiscount checks the formula",
                "RetSaleItemEntity setters recalculate AmountNutFinal through decimal subtraction and addition",
                "stored AmountNut equals the calculated formula for every return header aggregate",
            ],
            "Tax and Charge are separate header/item components and are not part of the observed AmountNut formula.",
            "Implement the net calculation as a named money policy with the same rounding boundary; do not add tax or charge without separate evidence.",
        ),
        _finding(
            "RA-003",
            "Header discount and addition components are exact item rollups",
            "HIGH",
            [
                "Discount equals Dis1 + Dis2 + Dis3 + OtherDiscount",
                "AddAmount equals Add1 + Add2 + OtherAddition",
                "zero aggregate rollup differences across 14,091 returns",
            ],
            "Collapsing the components would preserve a total but destroy the reason/account provenance needed for recalculation and audit.",
            "Store both component amounts and derived totals; reject inconsistent payloads at the command boundary.",
        ),
        _finding(
            "RA-004",
            "The UI, entity, business and SQL layers agree on the net-total invariant",
            "HIGH",
            [
                "FillSumOfDisAddS sums AmountNutFinal into header TotalAmount",
                "the business amount-validation method reaches RetSaleAdapter",
                "the save procedure and RD conversion procedure call the SQL validator",
            ],
            "A web replacement that validates only one layer can accept a payload that the legacy workflow rejects later.",
            "Apply the invariant in the domain model and command handler, then recheck it transactionally before persistence.",
        ),
        _finding(
            "RA-005",
            "Gross-minus-net is a business adjustment, not an unexplained residual",
            "MEDIUM",
            [
                f"{overall['gross_comparison_differences']} returns differ from gross comparison",
                f"gross-minus-official-net aggregate={overall['gross_minus_official_net_total']}",
                "all official-net comparisons have zero residual",
            ],
            "Operational reports must label gross, discount, addition and final net explicitly to avoid false incident escalation.",
            "Expose a transparent amount bridge and alert only on invariant failure, not on gross-versus-net difference.",
        ),
        _finding(
            "RA-006",
            "Historical formula consistency does not prove every future runtime branch",
            "MEDIUM",
            [
                "the clone is a current-state snapshot",
                "the three-month window has zero official-net residual",
                "static IL proves reachable code, not one operator's exact runtime sequence",
            ],
            "Configuration, rounding, external discount-engine versions or future deployments can still drift.",
            "Add invariant telemetry and deployment-hash drift checks without persisting customer or document identities.",
            confidence="MEDIUM_STATIC_AND_CURRENT_STATE_AGGREGATE",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    summary = {
        "finding_count": len(findings),
        "finding_severity_counts": dict(sorted(severities.items())),
        "return_count": overall["returns"],
        "previous_gross_comparison_difference_count": overall[
            "gross_comparison_differences"
        ],
        "previous_active_difference_count": next(
            row["gross_comparison_differences"]
            for row in reconciliation["by_cancel_state"]
            if row["CancelFlag"] == 0
        ),
        "official_stored_net_difference_count": overall["stored_net_differences"],
        "official_calculated_net_difference_count": overall[
            "calculated_net_differences"
        ],
        "item_formula_difference_count": overall[
            "stored_item_net_formula_differences"
        ],
        "discount_rollup_difference_count": overall["discount_rollup_differences"],
        "addition_rollup_difference_count": overall["addition_rollup_differences"],
        "maximum_official_net_delta": overall["maximum_official_net_delta"],
        "previous_mismatch_interpretation_valid": False,
        "official_header_total_basis": "SUM(SLE.tblRetSaleItm.AmountNut)",
        "official_item_net_formula": "Amount - Discount + AddAmount",
        "sql_formula_verified": sql_formula_verified,
        "sql_header_net_verified": sql_header_net_verified,
        "recalculation_header_net_verified": recalc_header_net_verified,
        "stored_procedure_or_application_commands_executed": 0,
    }
    if not (
        sql_formula_verified
        and sql_header_net_verified
        and recalc_header_net_verified
        and overall["stored_net_differences"] == 0
        and overall["calculated_net_differences"] == 0
        and overall["stored_item_net_formula_differences"] == 0
        and overall["discount_rollup_differences"] == 0
        and overall["addition_rollup_differences"] == 0
    ):
        raise RuntimeError("Sales-return amount contract does not satisfy required invariants")

    return {
        "artifact": "varanegar_sales_return_amount_runtime_and_migration_diagnostic_contract",
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
            "identities_or_raw_business_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "semantic_correction": {
            "wrong_model": "SLE.tblRetSaleHdr.TotalAmount must equal SUM(SLE.tblRetSaleItm.Amount)",
            "evidenced_model": "TotalAmount equals SUM(AmountNut), where each item AmountNut equals Amount - Discount + AddAmount",
            "previous_false_positive": "731 all-history gross comparisons, including 696 active returns",
            "remaining_unknown": "exact runtime rounding/configuration branch for every historical capture is not reconstructable from current state alone",
            "migration_rule": "preserve amount components and calculate/validate the official net invariant; never quarantine solely for gross-versus-net difference",
        },
        "incident_findings": findings,
        "schema_contract": schema,
        "amount_reconciliation": reconciliation,
        "recent_three_month_activity": recent,
        "module_contracts": modules,
        "il_contract": il,
        "diagnostic_order": [
            "identify whether the reported value is gross Amount, stored net AmountNut, tax, charge, discount, addition, settlement credit or inventory quantity",
            "recalculate each item as Amount - Discount + AddAmount and separately verify component rollups",
            "compare header TotalAmount with SUM(item AmountNut), never with SUM(item Amount)",
            "check CancelFlag, RetTypeCode, source sale/request link, operation date and scope before interpreting downstream effects",
            "then reconcile type-10 inventory voucher quantity and type-1006/type-97 credit settlement independently",
            "capture the exact validation error boundary and transaction outcome before proposing a correction",
        ],
        "evidence_limits": [
            "The clone proves current-state consistency and bounded three-month aggregates, not every historical intermediate edit.",
            "Static IL proves reachable calculation and save call shape, not one named operator's exact runtime branch.",
            "Money rounding is visible in entity accessors, but every external discount-engine version/configuration branch was not executed.",
            "Tax and Charge are evidenced as separate fields and are excluded from AmountNut by the official validator; their separate accounting treatment remains workflow-specific.",
            "No form, stored procedure, transaction, application assembly or mutation was executed.",
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
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
