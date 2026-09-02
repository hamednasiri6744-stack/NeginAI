"""Extract redacted formulas for the bank-reconciliation Summary procedure.

The procedure definition is read from the local read-only clone and parsed in
memory. No procedure is executed, no business row is selected, and raw SQL or
non-allowlisted string literals are persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_extension_sql_semantics import _mask_comments_and_strings
from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


OBJECT_NAME = "dbo.DoReconcile_GetSummary"
EXPECTED_TYPE_PREDICATES = (
    ("RCHEQUE", 3),
    ("RBANKDARFT", 1),
    ("PCHEQUE", 3),
    ("TRANSFER", None),
    ("PWITHDRAW", None),
    ("RCASHDRAF", None),
)
MATCH_DISCRIMINATORS = {
    "PCHEQUE",
    "PWITHDRAW",
    "RBANKDRAFT",
    "RCASHDRAFT",
    "RCHEQUE",
    "TRANSFER",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _has(masked: str, pattern: str) -> bool:
    return bool(re.search(pattern, masked, re.IGNORECASE | re.DOTALL))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matching-boundary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    matching = _load(args.matching_boundary)
    if matching.get("validation") != "PASS":
        raise ValueError("validated matching boundary is required")

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            identity = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,
                       o.type_desc,OBJECTPROPERTYEX(o.object_id,'IsEncrypted') AS is_encrypted,
                       m.definition
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(%s)
                """,
                (OBJECT_NAME,),
            )
            if not identity:
                raise ValueError(f"required object missing: {OBJECT_NAME}")
            row = identity[0]
            object_id = int(row.pop("object_id"))
            definition = row.pop("definition") or ""
            parameters = _rows(
                cursor,
                """
                SELECT p.parameter_id,p.name AS parameter_name,TYPE_NAME(p.user_type_id) AS data_type,
                       p.max_length,p.precision,p.scale,p.is_output
                FROM sys.parameters p WHERE p.object_id=%s ORDER BY p.parameter_id
                """,
                (object_id,),
            )
            dependencies = _rows(
                cursor,
                """
                SELECT DISTINCT COALESCE(d.referenced_schema_name,OBJECT_SCHEMA_NAME(d.referenced_id)) AS schema_name,
                       COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) AS object_name,
                       COALESCE(o.type_desc,'UNRESOLVED_OR_COLUMN_REFERENCE') AS type_desc
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
                WHERE d.referencing_id=%s
                  AND COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) IS NOT NULL
                ORDER BY schema_name,object_name,type_desc
                """,
                (object_id,),
            )

    masked = _mask_comments_and_strings(definition)
    type_literals = tuple(
        (
            match.group(1).upper(),
            int(status.group(1)) if status else None,
        )
        for match in re.finditer(r"\bType\s*=\s*N?'([^']+)'", definition, re.IGNORECASE)
        for status in [
            re.match(r"\s*AND\s+StatusID\s*=\s*(\d+)", definition[match.end() :], re.IGNORECASE)
        ]
    )

    formula_checks = {
        "remaining_last_reconcile_no_prior": _has(
            masked,
            r"IF\s+NOT\s+EXISTS\s*\(\s*SELECT\s+\*\s+FROM\s+Reconcile\s+WHERE\s+Amount\s+IS\s+NOT\s+NULL\s+AND\s+BankAccountId\s*=\s*@BankAccountId\s*\).*?SELECT\s+TOP\s+1\s+@RemainingLastReconcile\s*=\s*ISNULL\s*\(\s*Balance\s*,\s*0\s*\)\s+FROM\s+BankBill\s+WHERE\s+ReconcileId\s*=\s*@ReconcileId\s+ORDER\s+BY\s+BankBillId\s+ASC",
        ),
        "remaining_last_reconcile_prior": _has(
            masked,
            r"SELECT\s+TOP\s+1\s+@RemainingLastReconcile\s*=\s*ISNULL\s*\(\s*Amount\s*,\s*0\s*\)\s+FROM\s+Reconcile\s+WHERE\s+BankAccountId\s*=\s*@BankAccountId\s+ORDER\s+BY\s+ReconcileDate\s+DESC",
        ),
        "remaining_this_period": _has(
            masked,
            r"@RemainingThisPeriod\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*VocherCredit\s*,\s*0\s*\)\s*\)\s*-\s*SUM\s*\(\s*ISNULL\s*\(\s*VocherDebit\s*,\s*0\s*\)\s*\).*?FROM\s+BankBill\s+WHERE\s+ReconcileId\s*=\s*@ReconcileId\s+AND\s+VocherDate\s*<=\s*@VocherDate",
        ),
        "remaining_bill": _has(
            masked,
            r"SET\s+@RemainingBill\s*=\s*ISNULL\s*\(\s*@RemainingLastReconcile\s*,\s*0\s*\)\s*-\s*ISNULL\s*\(\s*@RemainingThisPeriod\s*,\s*0\s*\)",
        ),
        "remaining_cardex_base": _has(
            masked,
            r"@RemainingCardex\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*Credit\s*,\s*0\s*\)\s*\)\s*-\s*SUM\s*\(\s*ISNULL\s*\(\s*Debit\s*,\s*0\s*\)\s*\)\s+FROM\s+BankAccountCardex.*?BankAccountId\s*=\s*@BankAccountId\s+AND\s+DateOf\s*<=\s*@VocherDate",
        ),
        "remaining_cardex_initial_balance": _has(
            masked,
            r"@InitialBalance\s*=\s*ISNULL\s*\(\s*InitialBalance\s*,\s*0\s*\)\s+FROM\s+(?:dbo\.)?BankAccount\s+WHERE\s+BankAccountId\s*=\s*@BankAccountId.*?SET\s+@RemainingCardex\s*=\s*ISNULL\s*\(\s*@RemainingCardex\s*,\s*0\s*\)\s*\+\s*ISNULL\s*\(\s*@InitialBalance\s*,\s*0\s*\)",
        ),
        "bill_debit_open_items": _has(masked, r"@BillDebitOpenItems\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*VocherDebit\s*,\s*0\s*\)\s*\)\s+FROM\s+FreeBankBill\s+WHERE\s+ReconcileId\s*=\s*@ReconcileId"),
        "bill_credit_open_items": _has(masked, r"@BillCreditOpenItems\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*VocherCredit\s*,\s*0\s*\)\s*\)\s+FROM\s+FreeBankBill\s+WHERE\s+ReconcileId\s*=\s*@ReconcileId"),
        "cardex_debit_open_items": _has(masked, r"@CardexDebitOpenItems\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*Debit\s*,\s*0\s*\)\s*\)\s+FROM\s+FreeBankAccountCardex\s+WHERE\s+BankAccountId\s*=\s*@BankAccountId\s+AND\s+DateOf\s*<=\s*@VocherDate"),
        "cardex_credit_open_items": _has(masked, r"@CardexCreditOpenItems\s*=\s*SUM\s*\(\s*ISNULL\s*\(\s*Credit\s*,\s*0\s*\)\s*\)\s+FROM\s+FreeBankAccountCardex\s+WHERE\s+BankAccountId\s*=\s*@BankAccountId\s+AND\s+DateOf\s*<=\s*@VocherDate"),
        "real_remaining_bill": _has(masked, r"@RealRemainingBill\s*=\s*ISNULL\s*\(\s*@RemainingBill\s*,\s*0\s*\)\s*\+\s*ISNULL\s*\(\s*@CardexDebitOpenItems\s*,\s*0\s*\)\s*-\s*ISNULL\s*\(\s*@CardexCreditOpenItems\s*,\s*0\s*\)"),
        "real_remaining_cardex": _has(masked, r"@RealRemainingCardex\s*=\s*ISNULL\s*\(\s*@RemainingCardex\s*,\s*0\s*\)\s*\+\s*ISNULL\s*\(\s*@BillDebitOpenItems\s*,\s*0\s*\)\s*-\s*ISNULL\s*\(\s*@BillCreditOpenItems\s*,\s*0\s*\)"),
        "reconcile_delta": _has(masked, r"@Reconcile\s*=\s*ISNULL\s*\(\s*@RealRemainingCardex\s*,\s*0\s*\)\s*-\s*ISNULL\s*\(\s*@RealRemainingBill\s*,\s*0\s*\)"),
    }

    formulas = [
        {"metric": "RemainingLastReconcile", "formula": "IF no non-null prior Reconcile.Amount for account THEN first BankBill.Balance in ReconcileId by BankBillId ASC ELSE latest Reconcile.Amount for account by ReconcileDate DESC", "scope": ["ReconcileId", "BankAccountId"]},
        {"metric": "RemainingThisPeriod", "formula": "SUM(BankBill.VocherCredit)-SUM(BankBill.VocherDebit)", "scope": ["ReconcileId", "BankBill.VocherDate<=VocherDate"]},
        {"metric": "RemainingBill", "formula": "RemainingLastReconcile-RemainingThisPeriod", "scope": []},
        {"metric": "RemainingCardex", "formula": "SUM(BankAccountCardex.Credit)-SUM(BankAccountCardex.Debit)+BankAccount.InitialBalance", "scope": ["BankAccountId", "BankAccountCardex.DateOf<=VocherDate", "allowlisted Type/Status predicate"]},
        {"metric": "BillDebitOpenItems", "formula": "SUM(FreeBankBill.VocherDebit)", "scope": ["ReconcileId"]},
        {"metric": "BillCreditOpenItems", "formula": "SUM(FreeBankBill.VocherCredit)", "scope": ["ReconcileId"]},
        {"metric": "CardexDebitOpenItems", "formula": "SUM(FreeBankAccountCardex.Debit)", "scope": ["BankAccountId", "DateOf<=VocherDate"]},
        {"metric": "CardexCreditOpenItems", "formula": "SUM(FreeBankAccountCardex.Credit)", "scope": ["BankAccountId", "DateOf<=VocherDate"]},
        {"metric": "RealRemainingBill", "formula": "RemainingBill+CardexDebitOpenItems-CardexCreditOpenItems", "scope": []},
        {"metric": "RealRemainingCardex", "formula": "RemainingCardex+BillDebitOpenItems-BillCreditOpenItems", "scope": []},
        {"metric": "Reconcile", "formula": "RealRemainingCardex-RealRemainingBill", "scope": []},
    ]

    observed_match_types = {
        row["type_discriminator"] for row in matching["matching_dispatch"]["typed_reference_mappings"]
    }
    summary_types = {name for name, _ in type_literals}
    alias_risks = [
        {"summary_literal": "RBANKDARFT", "matching_discriminator": "RBANKDRAFT", "status_id": 1},
        {"summary_literal": "RCASHDRAF", "matching_discriminator": "RCASHDRAFT", "status_id": None},
    ]
    validation_errors: list[str] = []
    if row["is_encrypted"]:
        validation_errors.append("summary procedure unexpectedly encrypted")
    if not definition:
        validation_errors.append("summary procedure definition unavailable")
    if tuple(type_literals) != EXPECTED_TYPE_PREDICATES:
        validation_errors.append("Type/Status predicate sequence changed")
    if observed_match_types != MATCH_DISCRIMINATORS:
        validation_errors.append("matching discriminator set changed")
    for name, matched in formula_checks.items():
        if not matched:
            validation_errors.append(f"formula pattern not matched: {name}")

    mutation_counts = {
        keyword: len(re.findall(rf"\b{keyword}\b", masked, re.IGNORECASE))
        for keyword in ("INSERT", "UPDATE", "DELETE", "MERGE")
    }
    summary = {
        "catalog_object_count": 1,
        "parameter_count": len(parameters),
        "dependency_count": len(dependencies),
        "output_metric_count": len(formulas),
        "formula_pattern_count": len(formula_checks),
        "matched_formula_pattern_count": sum(formula_checks.values()),
        "cardex_type_predicate_count": len(type_literals),
        "type_literal_alias_risk_count": len(alias_risks),
        "lexical_mutation_keyword_count": sum(mutation_counts.values()),
        "definition_length": len(definition),
        "definition_persisted_count": 0,
        "allowlisted_domain_literal_value_count": len(type_literals),
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_summary_redacted_sql_formula_semantics",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_FORMULA_PARSE",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_persisted": 0,
            "non_allowlisted_string_literals_persisted": 0,
            "procedures_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "catalog_object": {
            **row,
            "definition_length": len(definition),
            "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
            "definition_persisted": False,
        },
        "parameters": parameters,
        "dependencies": dependencies,
        "formula_pattern_checks": formula_checks,
        "formulas": formulas,
        "cardex_type_status_predicates": [
            {"type": name, "required_status_id": status} for name, status in type_literals
        ],
        "type_literal_alias_risks": alias_risks,
        "lexical_mutation_keyword_counts": mutation_counts,
        "target_contract": {
            "static_formula_semantics_confirmed_from_clone_definition": True,
            "raw_sql_definition_is_copied_to_target": False,
            "all_null_aggregates_normalize_to_zero": True,
            "solar_varchar_date_comparison_is_copied_without_typed_date_parity": False,
            "misspelled_type_literals_are_silently_corrected": False,
            "type_aliases_require_fixture_backed_parity": True,
            "initial_balance_branch_requires_explicit_fixture_cases": True,
            "runtime_row_result_parity_confirmed": False,
            "command_pilot_allowed": False,
        },
        "validation_errors": validation_errors,
        "limits": [
            "Static formula semantics come from the current clone definition and can drift.",
            "No procedure was executed and no result or business row was read.",
            "Allowlisted Type literals are domain constants; all other literal values and raw SQL are omitted.",
            "The RBANKDARFT/RBANKDRAFT and RCASHDRAF/RCASHDRAFT differences require real fixture parity, not automatic correction.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
