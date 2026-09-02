"""Build synthetic acceptance cases for the target bank-reconciliation aggregate."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SPECIFIC_CASES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "bank_reconciliation.import_statement": (
        ("unsupported_or_spoofed_format", "validation", "file is rejected before parser execution"),
        ("unapproved_query_or_provider_profile", "security", "profile is denied without provider/query execution"),
        ("parser_timeout_or_fault", "failure_injection", "batch is quarantined and no ledger state changes"),
        ("duplicate_file_same_hash", "idempotency", "original import identity and result are returned"),
        ("same_import_key_different_hash", "idempotency", "payload conflict is rejected and audited"),
        ("schema_amount_or_date_invalid", "validation", "invalid rows remain staged or quarantined"),
    ),
    "bank_reconciliation.match_instrument": (
        ("zero_typed_source", "validation", "match is quarantined rather than creating an untyped link"),
        ("multiple_typed_sources", "validation", "ambiguous link is quarantined"),
        ("cross_account_candidate", "scope", "candidate outside bank account scope is denied"),
        ("already_matched_instrument", "concurrency", "competing match does not create a second active link"),
        ("amount_or_date_mismatch", "reconciliation", "blocking mismatch prevents accepted automatic match"),
        ("manual_override_without_capability", "authorization", "override is denied and reason remains auditable"),
    ),
    "bank_reconciliation.unmatch_instrument": (
        ("session_already_confirmed", "workflow", "confirmed session cannot be silently reopened"),
        ("link_not_found", "idempotency", "retry converges without creating a new event"),
        ("cross_account_link", "scope", "out-of-scope link is not disclosed or changed"),
        ("stale_link_version", "concurrency", "stale unlink is rejected"),
        ("dependent_adjustment_exists", "workflow", "dependency blocks unlink until explicit compensation"),
        ("audit_write_fault", "failure_injection", "unlink is not accepted without durable audit outcome"),
    ),
    "bank_reconciliation.confirm": (
        ("bank_cardex_reconciliation_mismatch", "reconciliation", "confirmation remains unaccepted"),
        ("unresolved_or_quarantined_rows", "reconciliation", "session cannot confirm with blocking rows"),
        ("total_debit_credit_mismatch", "reconciliation", "balance mismatch blocks transition"),
        ("closed_operation_date", "context", "closed date blocks confirmation"),
        ("already_confirmed_retry", "idempotency", "original confirmation result is returned"),
        ("cardex_or_outbox_fault", "failure_injection", "transaction rolls back or remains explicitly recoverable"),
    ),
    "bank_reconciliation.cancel": (
        ("already_confirmed_without_reversal", "workflow", "cancel is denied without an explicit reversal command"),
        ("active_matches_require_policy", "workflow", "cancel follows declared unlink/cascade policy"),
        ("already_cancelled_retry", "idempotency", "original cancellation result is returned"),
        ("stale_session_version", "concurrency", "stale cancel is rejected"),
        ("cross_account_session", "scope", "out-of-scope session is not changed"),
        ("cleanup_or_outbox_fault", "failure_injection", "no partial accepted cancellation remains"),
    ),
}

FAILURE_STAGES: dict[str, tuple[str, ...]] = {
    "bank_reconciliation.import_statement": ("upload", "parse", "staging_commit"),
    "bank_reconciliation.match_instrument": ("candidate_validation", "link_write", "audit_outbox"),
    "bank_reconciliation.unmatch_instrument": ("link_load", "unlink_write", "audit_outbox"),
    "bank_reconciliation.confirm": ("state_transition", "bank_cardex_update", "audit_outbox"),
    "bank_reconciliation.cancel": ("state_transition", "staging_cleanup", "audit_outbox"),
}

COMMON_CASES = (
    ("success", "success", "authorized valid command commits once and reconciles"),
    ("authorization_denied", "authorization", "no accepted business mutation occurs"),
    ("scope_denied", "scope", "out-of-scope aggregate is not disclosed or changed"),
    ("stale_expected_version", "concurrency", "stale command is rejected"),
    ("duplicate_command_same_payload", "idempotency", "original result is returned"),
    ("duplicate_command_different_payload", "idempotency", "payload conflict is rejected"),
    ("operation_context_closed", "context", "closed fiscal/date/account context blocks mutation"),
    ("blocking_reconciliation_difference", "reconciliation", "command is not accepted while blocking difference remains"),
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _case_id(command: str, variation: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", f"{command}.{variation}".casefold())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--command-guards", required=True, type=Path)
    parser.add_argument("--import-boundary", required=True, type=Path)
    parser.add_argument("--transaction-boundary", required=True, type=Path)
    parser.add_argument("--cardex-sql-boundary", required=True, type=Path)
    parser.add_argument("--delete-semantics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source_model = _load(args.source_model)
    command_guards = _load(args.command_guards)
    import_boundary = _load(args.import_boundary)
    transaction_boundary = _load(args.transaction_boundary)
    cardex_sql_boundary = _load(args.cardex_sql_boundary)
    delete_semantics = _load(args.delete_semantics)
    for name, payload in (
        ("source model", source_model),
        ("command guards", command_guards),
        ("import boundary", import_boundary),
        ("transaction boundary", transaction_boundary),
        ("cardex SQL boundary", cardex_sql_boundary),
        ("delete semantics", delete_semantics),
    ):
        if payload.get("validation") != "PASS":
            raise ValueError(f"validated {name} artifact is required")

    commands = source_model["target_contract"]["commands"]
    if set(commands) != set(SPECIFIC_CASES) or set(commands) != set(FAILURE_STAGES):
        raise ValueError("bank-reconciliation command set changed without Golden cases")

    cases = []
    for command in commands:
        for variation, kind, expected in COMMON_CASES:
            cases.append(
                {
                    "case_id": _case_id(command, variation),
                    "process_owner_candidate": "P06_COLLECTION_AND_RECEIVED_CHEQUE",
                    "process_owner_signoff_required": True,
                    "command": command,
                    "kind": kind,
                    "fixture": "synthetic_bank_reconciliation_aggregate_with_one_declared_variation",
                    "variation": variation,
                    "expected": expected,
                    "assertions": [
                        "target transaction boundary respected",
                        "stable audit reason recorded",
                        "source Varanegar untouched",
                    ],
                    **(
                        {
                            "legacy_parity_status": delete_semantics["target_contract"]["cancel_session_legacy_parity_status"],
                            "process_owner_decision_required": True,
                        }
                        if command == "bank_reconciliation.cancel"
                        else {}
                    ),
                }
            )
        for stage in FAILURE_STAGES[command]:
            variation = f"fault_after_{stage}"
            cases.append(
                {
                    "case_id": _case_id(command, variation),
                    "process_owner_candidate": "P06_COLLECTION_AND_RECEIVED_CHEQUE",
                    "process_owner_signoff_required": True,
                    "command": command,
                    "kind": "failure_injection",
                    "fixture": "synthetic_valid_command_with_deterministic_fault",
                    "variation": variation,
                    "expected": "no partial accepted result; retry with the same command_id converges",
                    "assertions": [
                        "no duplicate aggregate link audit or outbox event",
                        "reconciliation is zero or explicitly pending and recoverable",
                        "source Varanegar untouched",
                    ],
                }
            )
        for variation, kind, expected in SPECIFIC_CASES[command]:
            cases.append(
                {
                    "case_id": _case_id(command, variation),
                    "process_owner_candidate": "P06_COLLECTION_AND_RECEIVED_CHEQUE",
                    "process_owner_signoff_required": True,
                    "command": command,
                    "kind": kind,
                    "fixture": "synthetic_bank_reconciliation_domain_boundary_fixture",
                    "variation": variation,
                    "expected": expected,
                    "assertions": [
                        "typed-source and account/date scope invariants preserved",
                        "stable audit reason recorded",
                        "source Varanegar untouched",
                    ],
                }
            )
        if command == "bank_reconciliation.confirm":
            parity_objects = sorted(
                row["referenced_object"]
                for row in cardex_sql_boundary["catalog_dependencies"]
                if row["referenced_object"].startswith("dbo.")
            )
            for referenced_object in parity_objects:
                variation = "post_commit_parity_" + referenced_object.split(".", 1)[1].casefold()
                cases.append(
                    {
                        "case_id": _case_id(command, variation),
                        "process_owner_candidate": "P06_COLLECTION_AND_RECEIVED_CHEQUE",
                        "process_owner_signoff_required": True,
                        "command": command,
                        "kind": "post_commit_parity",
                        "fixture": "synthetic_confirm_with_one_typed_legacy_dependency_effect",
                        "variation": variation,
                        "referenced_legacy_object": referenced_object,
                        "expected": "typed effect is accounted for exactly once after successful commit",
                        "assertions": [
                            "effect is absent after rollback and present exactly once after commit",
                            "replay does not duplicate cardex audit or outbox state",
                            "source Varanegar untouched",
                        ],
                    }
                )

    ids = [row["case_id"] for row in cases]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    artifact = {
        "artifact": "negin_erp_bank_reconciliation_synthetic_golden_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not duplicate_ids else "FAIL",
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_used": 0,
            "synthetic_cases_only": 1,
        },
        "summary": {
            "source_command_count": len(commands),
            "case_count": len(cases),
            "common_case_count": len(commands) * len(COMMON_CASES),
            "failure_injection_case_count": sum(len(rows) for rows in FAILURE_STAGES.values()),
            "domain_specific_case_count": sum(len(rows) for rows in SPECIFIC_CASES.values()),
            "post_commit_parity_case_count": sum(row["kind"] == "post_commit_parity" for row in cases),
            "duplicate_case_id_count": len(duplicate_ids),
        },
        "source_evidence": [
            args.source_model.as_posix(),
            args.command_guards.as_posix(),
            args.import_boundary.as_posix(),
            args.transaction_boundary.as_posix(),
            args.cardex_sql_boundary.as_posix(),
            args.delete_semantics.as_posix(),
        ],
        "provisional_command_contracts": {
            "bank_reconciliation.cancel": {
                "legacy_parity_status": delete_semantics["target_contract"]["cancel_session_legacy_parity_status"],
                "process_owner_signoff_required": True,
                "must_not_conflate_with": [
                    "bank_reconciliation.unmatch_instrument",
                    "bank_reconciliation.discard_imported_statement",
                    "bank_reconciliation.reverse_confirmed_session",
                ],
            }
        },
        "execution_policy": {
            "allowed_environment": "isolated target test database with synthetic fixtures only",
            "forbidden_environment": [
                "operational Varanegar",
                "NeginPakhsh_WebDev clone",
                "target production database",
            ],
            "source_mode": "Varanegar remains untouched and disconnected during execution",
        },
        "cases": cases,
        "duplicate_case_ids": duplicate_ids,
        "limits": [
            "Cases are executable acceptance obligations, not evidence that target commands exist.",
            "P06 is a process-owner candidate and requires business signoff before atlas integration.",
            "No source or target command, parser, database or UI action was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": artifact["summary"]}))
    return 0 if not duplicate_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
