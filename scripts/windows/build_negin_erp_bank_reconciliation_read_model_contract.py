"""Build the target bank-reconciliation read-model and Summary contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--matching", required=True, type=Path)
    parser.add_argument("--summary-sql", required=True, type=Path)
    parser.add_argument("--summary-ui", required=True, type=Path)
    parser.add_argument("--owner-decisions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        "source_model": args.source_model,
        "matching": args.matching,
        "summary_sql": args.summary_sql,
        "summary_ui": args.summary_ui,
        "owner_decisions": args.owner_decisions,
    }
    inputs = {name: _load(path) for name, path in paths.items()}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")
    summary_sql = inputs["summary_sql"]
    summary_ui = inputs["summary_ui"]
    matching = inputs["matching"]
    decisions = inputs["owner_decisions"]
    alias_decision = next(row for row in decisions["decisions"] if row["decision_id"] == "BR-DEC-001")
    formulas = summary_sql["formulas"]
    ui_mappings = summary_ui["output_to_ui_mappings"]
    typed_sources = matching["target_contract"]["typed_source_mapping"]

    projections = [
        {
            "projection": "BankReconciliationSessionView",
            "fields": [
                "session_id", "bank_account_id", "reconcile_date", "as_of_date",
                "state", "expected_version", "statement_row_count", "active_link_count",
                "profile_id", "profile_version", "profile_content_sha256",
            ],
        },
        {
            "projection": "BankStatementRowView",
            "fields": [
                "statement_row_id", "session_id", "voucher_date", "description",
                "debit", "credit", "voucher_no", "balance", "match_state", "expected_version",
            ],
        },
        {
            "projection": "BankReconciliationLinkView",
            "fields": [
                "link_id", "statement_row_id", "instrument_type", "instrument_id",
                "instrument_date", "signed_amount", "match_state", "expected_version",
            ],
        },
        {
            "projection": "BankReconciliationSummaryView",
            "fields": ["session_id", "bank_account_id", "as_of_date", "computed_at"]
            + [row["metric"] for row in formulas],
        },
    ]
    queries = [
        {
            "query": "bank_reconciliation.session",
            "required_scope": ["fiscal_year", "dc", "bank_account_id", "session_id"],
            "result": "BankReconciliationSessionView",
        },
        {
            "query": "bank_reconciliation.statement_rows",
            "required_scope": ["fiscal_year", "dc", "bank_account_id", "session_id"],
            "result": "cursor-paged BankStatementRowView ordered by voucher_date, statement_row_id",
        },
        {
            "query": "bank_reconciliation.links",
            "required_scope": ["fiscal_year", "dc", "bank_account_id", "session_id"],
            "result": "cursor-paged BankReconciliationLinkView ordered by statement_row_id, link_id",
        },
        {
            "query": "bank_reconciliation.match_candidates",
            "required_scope": ["fiscal_year", "dc", "bank_account_id", "session_id", "statement_row_id", "as_of_date"],
            "result": "cursor-paged typed candidate references; no command side effect",
        },
        {
            "query": "bank_reconciliation.summary",
            "required_scope": ["fiscal_year", "dc", "bank_account_id", "session_id", "as_of_date"],
            "result": "BankReconciliationSummaryView with 11 signed decimal metrics",
        },
    ]
    acceptance = [
        "every query denies missing capability, feature entitlement or account scope without leaking aggregate existence",
        "fiscal year and DC are server-derived or server-validated",
        "as_of_date is explicit and rows after it are excluded",
        "pagination uses a stable unique tiebreaker and never offset-only ordering",
        "all money metrics are signed fixed-scale decimals and never null",
        "negative values remain negative in the API; parentheses and color are presentation only",
        "accessible sign text does not rely on color",
        "exactly one typed source reference is exposed per valid link",
        "zero or multiple typed references are quarantined and not returned as valid links",
        "candidate queries have zero persistence and cannot trigger grid-event writes",
        "Summary formula output is compared against an approved redacted fixture before pilot",
        "both spelling variants are tested and no alias normalization occurs before BR-DEC-001 approval",
        "session state is explicit and inconsistent legacy confirmer markers map to quarantine",
        "a confirmed marker does not imply all linked instruments are reconciled",
        "response includes profile version/hash provenance without raw profile SQL or path values",
        "no raw legacy procedure name or executable configuration is exposed to the client",
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    formula_names = [row["metric"] for row in formulas]
    mapping_names = [row["output_metric"] for row in ui_mappings]
    if formula_names != mapping_names:
        errors.append("Summary formula and UI mapping order differ")
    if len(formulas) != 11 or len(typed_sources) != 6:
        errors.append("expected 11 Summary metrics and six typed sources")
    if alias_decision["decision_status"] != "NOT_APPROVED":
        errors.append("BR-DEC-001 changed and requires read-model contract review")

    payload = {
        "artifact": "negin_erp_bank_reconciliation_scoped_read_model_and_summary_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "READ_MODEL_CONTRACT_READY_NOT_IMPLEMENTED_OR_RUNTIME_PARITY_APPROVED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_values_read": 0,
            "owner_approvals_inferred": 0,
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "projection_count": len(projections),
            "projection_field_count": sum(len(row["fields"]) for row in projections),
            "query_contract_count": len(queries),
            "summary_metric_count": len(formulas),
            "typed_source_mapping_count": len(typed_sources),
            "acceptance_obligation_count": len(acceptance),
            "runtime_parity_approved_count": 0,
            "query_implementation_execution_count": 0,
            "validation_error_count": len(errors),
        },
        "projections": projections,
        "query_contracts": queries,
        "summary_formula_contracts": formulas,
        "summary_presentation_mappings": ui_mappings,
        "typed_source_mapping": typed_sources,
        "type_status_predicates": summary_sql["cardex_type_status_predicates"],
        "alias_decision_gate": {
            "decision_id": alias_decision["decision_id"],
            "status": alias_decision["decision_status"],
            "silent_normalization_allowed": False,
        },
        "authorization_contract": {
            "capability": "bank_reconciliation.view",
            "decision": "capability AND feature AND fiscal/DC/account scope AND as_of_date/domain validation",
            "deny_overrides_allow": True,
            "neutral_is_not_allow": True,
        },
        "acceptance_obligations": acceptance,
        "validation_errors": errors,
        "limits": [
            "Formulas are static semantic contracts, not approved runtime row-result parity.",
            "The current clone has no bank-reconciliation runtime fixture.",
            "No query endpoint or target database projection is implemented by this artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
