"""Build unexecuted differential acceptance obligations for bank reconciliation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _id(*parts: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", ".".join(parts).casefold())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-sql", required=True, type=Path)
    parser.add_argument("--summary-ui", required=True, type=Path)
    parser.add_argument("--parser-row", required=True, type=Path)
    parser.add_argument("--confirm-cardex", required=True, type=Path)
    parser.add_argument("--confirm-orchestration", required=True, type=Path)
    parser.add_argument("--unmatch-sql", required=True, type=Path)
    parser.add_argument("--discard-cancel", required=True, type=Path)
    parser.add_argument("--role-uat", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {
        "summary_sql": args.summary_sql,
        "summary_ui": args.summary_ui,
        "parser_row": args.parser_row,
        "confirm_cardex": args.confirm_cardex,
        "confirm_orchestration": args.confirm_orchestration,
        "unmatch_sql": args.unmatch_sql,
        "discard_cancel": args.discard_cancel,
        "role_uat": args.role_uat,
    }
    inputs = {name: _load(path) for name, path in paths.items()}
    invalid_inputs = sorted(name for name, payload in inputs.items() if payload.get("validation") != "PASS")
    if invalid_inputs:
        raise ValueError("validated inputs required: " + ", ".join(invalid_inputs))

    cases: list[dict[str, Any]] = []

    def add(group: str, name: str, fixture: dict[str, Any], expected: str, **extra: Any) -> None:
        cases.append(
            {
                "case_id": _id(group, name),
                "group": group,
                "fixture": fixture,
                "expected": expected,
                "source_varanegar_mutation_allowed": False,
                "execution_status": "NOT_EXECUTED",
                **extra,
            }
        )

    summary_sql = inputs["summary_sql"]
    for formula in summary_sql["formulas"]:
        add(
            "summary",
            f"formula_baseline.{formula['metric']}",
            {"metric": formula["metric"], "non_null_small_signed_values": True, "scope": formula["scope"]},
            formula["formula"],
            requires_legacy_redacted_fixture=True,
        )
        add(
            "summary",
            f"null_normalization.{formula['metric']}",
            {"metric": formula["metric"], "all_nullable_inputs": None},
            "NULL aggregate or operand is normalized according to the static ISNULL formula and returns a decimal, never null",
            requires_legacy_redacted_fixture=True,
        )
    add("summary", "initial_balance.no_prior_reconcile", {"prior_non_null_reconcile_amount_exists": False}, "first BankBill Balance by BankBillId ASC is the base", requires_legacy_redacted_fixture=True)
    add("summary", "initial_balance.with_prior_reconcile", {"prior_non_null_reconcile_amount_exists": True}, "latest Reconcile Amount by ReconcileDate DESC is the base", requires_legacy_redacted_fixture=True)
    for relation in ("before", "equal", "after"):
        expected = "included" if relation in {"before", "equal"} else "excluded"
        add("summary", f"as_of_date.{relation}", {"row_date_relation_to_as_of": relation}, expected, requires_legacy_redacted_fixture=True)
    for predicate in summary_sql["cardex_type_status_predicates"]:
        add(
            "summary",
            f"type_status.{predicate['type']}",
            predicate,
            "included only when the exact observed Type and required StatusID predicate match",
            requires_legacy_redacted_fixture=True,
        )
    for alias in summary_sql["type_literal_alias_risks"]:
        add(
            "summary",
            f"alias_risk.{alias['summary_literal']}",
            alias,
            "compare exact legacy and proposed alias behavior; do not silently normalize",
            requires_legacy_redacted_fixture=True,
            owner_decision_required=True,
        )
    for sign in ("negative", "zero", "positive"):
        add(
            "summary",
            f"presentation.{sign}",
            {"signed_decimal": sign},
            "machine-readable sign is preserved and accessible text does not rely on red/dark-blue color",
            requires_legacy_redacted_fixture=False,
        )

    parser_row = inputs["parser_row"]
    for format_name in ("dbf", "txt", "xls", "default"):
        expected = (
            "reject unsupported default format before session creation"
            if format_name == "default"
            else "use typed server-owned parser profile without raw SQL, Office automation or arbitrary path execution"
        )
        add("parser", f"format.{format_name}", {"format": format_name}, expected, requires_legacy_redacted_fixture=format_name != "default")
    for column in parser_row["target_contract"]["canonical_columns_are_schema_validated_before_commit"]:
        add("parser", f"missing_column.{column}", {"missing_column": column}, "stable schema error and zero persistence", requires_legacy_redacted_fixture=False)
    add("parser", "amounts.both_nonzero", {"debit": "nonzero", "credit": "nonzero"}, "reject or apply recorded owner policy; never silently discard Credit", owner_decision_required=True)
    add("parser", "amounts.both_zero", {"debit": 0, "credit": 0}, "reject or quarantine unless owner explicitly permits zero-amount statement rows", owner_decision_required=True)
    for name, fixture, expected in (
        ("same_row_replay", {"same_account": True, "same_profile_version": True, "same_row_fingerprint": True}, "idempotent original result"),
        ("different_account", {"same_row_fingerprint": True, "same_account": False}, "not suppressed by another account"),
        ("different_profile", {"same_row_fingerprint": True, "same_profile_version": False}, "profile version is part of identity or conflict reason"),
        ("query_metacharacters", {"voucher_no_contains_query_metacharacters": True}, "treated as data through bound typed parameters; no predicate injection"),
    ):
        add("parser", f"dedup.{name}", fixture, expected, requires_legacy_redacted_fixture=name != "query_metacharacters")
    for name, expected in (
        ("parser_failure", "zero header and row persistence"),
        ("schema_validation_failure", "zero header and row persistence"),
        ("mid_batch_failure", "all header and prior rows roll back"),
        ("retry_after_failure", "one complete session or the same stable failure, never duplicates"),
    ):
        add("parser", f"atomicity.{name}", {"failure_point": name}, expected, failure_injection_required=True)
    for field in ("HDR", "StartRow", "Seperator", "IsArabic"):
        add(
            "parser",
            f"profile_field.{field}",
            {"field": field, "profile_value_changed": True},
            "field has no effect until a typed target parser explicitly implements and tests it; legacy column presence alone is not activation",
            owner_decision_required=True,
        )

    cardex = inputs["confirm_cardex"]
    type_names = [row["target_table"] for row in cardex["mutation_contracts"]]
    for type_name in type_names:
        add("confirm", f"single_link.{type_name}", {"typed_links": [type_name]}, "session marker and the one instrument update commit atomically")
    for index, type_name in enumerate(type_names):
        other = type_names[(index + 1) % len(type_names)]
        add(
            "confirm",
            f"multi_link.{type_name}.{other}",
            {"typed_links": [type_name, other]},
            "both instruments and session marker commit; regression fails if only the first unordered link changes",
        )
    add("confirm", "all_six_types", {"typed_links": type_names}, "all six instruments and marker commit atomically")
    add("confirm", "invalid.zero_typed_references", {"typed_reference_count_per_link": 0}, "stable validation error before mutation")
    add("confirm", "invalid.multiple_typed_references", {"typed_reference_count_per_link": 2}, "stable validation error before mutation")
    for type_name in type_names:
        add("confirm", f"missing_target.{type_name}", {"typed_link": type_name, "target_exists": False}, "stable domain error and complete rollback")
    for failure_point in (
        "reconcile_state_write",
        "instrument_update",
        "audit_append",
        "outbox_append",
        "physical_commit_before_response",
    ):
        add("confirm", f"failure.{failure_point}", {"failure_after": failure_point}, "no partial committed state; retry is safe", failure_injection_required=True)
    add("confirm", "authorization.denied", {"capability_allow": False}, "deny with zero mutation", authenticated_uat_required=True)
    add("confirm", "operation_date.closed", {"operation_date_open": False}, "deny with zero mutation", authenticated_uat_required=True)
    add("confirm", "expected_version.stale", {"expected_version": "stale"}, "conflict with zero mutation")
    add("confirm", "replay.same_idempotency_key", {"same_idempotency_key": True}, "return original result with no duplicate effects")
    add("confirm", "regression.legacy_one_link_early_return", {"typed_link_count": 2}, "target updates two; test explicitly fails if maximum affected instruments is one")
    add("confirm", "already_reconciled", {"instrument_already_reconciled": True}, "owner-approved conflict or idempotent policy is applied consistently", owner_decision_required=True)
    for name, fixture, expected in (
        ("unmatch_unconfirmed", {"state": "IMPORTED_UNCONFIRMED", "active_link_count": 1}, "delete the named link atomically and refresh summary"),
        ("unmatch_multiple_links_same_bill", {"state": "IMPORTED_UNCONFIRMED", "active_link_count": 2}, "reject invariant violation; never silently delete all links by BankBillId"),
        ("unmatch_confirmed", {"state": "CONFIRMED"}, "deny unmatch and require owner-approved reversal"),
        ("unmatch_not_found", {"state": "IMPORTED_UNCONFIRMED", "link_exists": False}, "stable not-found result with zero mutation"),
        ("unmatch_stale_version", {"state": "IMPORTED_UNCONFIRMED", "expected_version": "stale"}, "conflict with zero mutation"),
        ("unmatch_replay", {"same_idempotency_key": True}, "return original result without additional deletion"),
        ("reversal_all_instruments", {"state": "CONFIRMED", "typed_link_count": 6}, "session and all six instruments reverse atomically"),
        ("reversal_failure", {"state": "CONFIRMED", "failure_after": "instrument_reset"}, "all instrument and session changes roll back"),
    ):
        add("confirm", f"unmatch_reversal.{name}", fixture, expected, owner_decision_required=name.startswith("reversal"))
    for name, fixture, expected, auth_required, fault_required in (
        ("reversal_authorization_denied", {"reverse_capability_allow": False}, "deny with zero mutation", True, False),
        ("reversal_sod_same_confirmer", {"same_actor_confirmed_session": True}, "deny pending an owner-approved exception policy", True, False),
        ("reversal_operation_date_closed", {"operation_date_open": False}, "deny with zero mutation", True, False),
        ("reversal_unconfirmed", {"state": "IMPORTED_UNCONFIRMED"}, "deny because reversal is distinct from cancel/unmatch", False, False),
        ("reversal_stale_version", {"state": "CONFIRMED", "expected_version": "stale"}, "conflict with zero mutation", False, False),
        ("reversal_replay", {"state": "CONFIRMED", "same_idempotency_key": True}, "return original reversal result without duplicate effects", False, False),
        ("reversal_audit_failure", {"state": "CONFIRMED", "failure_after": "audit_append"}, "all instrument, session and audit changes roll back", False, True),
        ("reversal_outbox_failure", {"state": "CONFIRMED", "failure_after": "outbox_append"}, "all instrument, session, audit and outbox changes roll back", False, True),
    ):
        add(
            "confirm",
            f"unmatch_reversal.{name}",
            fixture,
            expected,
            authenticated_uat_required=auth_required,
            failure_injection_required=fault_required,
        )
    for name, fixture, expected, owner_required in (
        ("discard_unconfirmed_no_links", {"state": "IMPORTED_UNCONFIRMED", "active_link_count": 0}, "discard staged rows and transition or archive the header atomically", False),
        ("discard_with_links", {"state": "IMPORTED_UNCONFIRMED", "active_link_count": 1}, "deny discard with zero mutation", False),
        ("discard_confirmed", {"state": "CONFIRMED"}, "deny physical discard and require reversal", False),
        ("cancel_empty_header", {"state": "IMPORTED_UNCONFIRMED", "statement_row_count": 0}, "apply owner-approved cancel/archive policy so no active orphan remains", True),
        ("cancel_stale_version", {"state": "IMPORTED_UNCONFIRMED", "expected_version": "stale"}, "conflict with zero mutation", False),
        ("cancel_replay", {"same_idempotency_key": True}, "return the original cancel result without repeated effects", False),
    ):
        add("confirm", f"discard_cancel.{name}", fixture, expected, owner_decision_required=owner_required)

    ids = [row["case_id"] for row in cases]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    counts = Counter(row["group"] for row in cases)
    errors: list[str] = []
    if dict(counts) != {"summary": 38, "parser": 24, "confirm": 54}:
        errors.append(f"case group count changed: {dict(counts)}")
    if duplicate_ids:
        errors.append("duplicate case ids")
    summary = {
        "source_artifact_count": len(inputs),
        "summary_case_count": counts["summary"],
        "parser_case_count": counts["parser"],
        "confirm_case_count": counts["confirm"],
        "differential_acceptance_case_count": len(cases),
        "legacy_redacted_fixture_case_count": sum(row.get("requires_legacy_redacted_fixture", False) for row in cases),
        "owner_decision_case_count": sum(row.get("owner_decision_required", False) for row in cases),
        "failure_injection_case_count": sum(row.get("failure_injection_required", False) for row in cases),
        "authenticated_uat_case_count": sum(row.get("authenticated_uat_required", False) for row in cases),
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "duplicate_case_id_count": len(duplicate_ids),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "negin_erp_bank_reconciliation_differential_acceptance_obligations",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "DESIGN_ONLY_NOT_EXECUTED_OR_OWNER_APPROVED",
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_DIFFERENTIAL_ACCEPTANCE_DESIGN",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_row_or_identity_values_used": 0,
            "synthetic_cases_only": 1,
        },
        "summary": summary,
        "execution_policy": {
            "source_varanegar_is_read_only": True,
            "legacy_side_uses_redacted_owner_approved_fixtures_or_aggregate_queries_only": True,
            "target_side_uses_isolated_test_database": True,
            "authenticated_uat_is_separate_and_required_where_marked": True,
            "these_cases_are_not_added_to_the_970_module_golden_mapping": True,
            "pilot_requires_all_non_owner_pending_cases_pass_and_owner_pending_cases_be_decided": True,
        },
        "cases": cases,
        "source_evidence": [
            {"name": name, "artifact": payload["artifact"], "path": str(paths[name]).replace("\\", "/")}
            for name, payload in inputs.items()
        ],
        "duplicate_case_ids": duplicate_ids,
        "validation_errors": errors,
        "limits": [
            "All 108 cases are obligations only; none was executed.",
            "No production identity, profile row, statement row or reconciliation result is included.",
            "Owner-decision cases remain unresolved and cannot be auto-approved by static evidence.",
            "Differential parity must not reproduce known unsafe SQL, partial commits or the one-link confirm defect.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
