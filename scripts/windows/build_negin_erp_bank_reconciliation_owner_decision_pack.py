"""Build an owner-decision register for unresolved bank-reconciliation semantics.

The builder is offline and composes validated acceptance obligations.  It does
not approve a policy, connect to Varanegar, or execute source/target commands.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DECISIONS: tuple[dict[str, Any], ...] = (
    {
        "decision_id": "BR-DEC-001",
        "title": "Summary type-literal alias handling",
        "owner_role": "finance_process_owner",
        "case_ids": [
            "summary.alias_risk.rbankdarft",
            "summary.alias_risk.rcashdraf",
        ],
        "required_before_slice": "session_read_model_summary_candidate",
        "options": [
            {
                "option_id": "exact_legacy_literals",
                "effect": "Preserve the observed SQL literals exactly, including their spelling.",
                "risk": "May preserve a legacy omission if runtime data uses the other spelling.",
            },
            {
                "option_id": "explicit_approved_alias_set",
                "effect": "Accept both observed Summary and matching-family spellings through a versioned alias table.",
                "risk": "Changes legacy inclusion and requires redacted row-result parity evidence.",
            },
        ],
        "recommended_safe_default": "exact_legacy_literals",
        "required_evidence": [
            "redacted distinct Type counts for both spellings",
            "legacy/proposed Summary differential output for the same approved fixture",
        ],
    },
    {
        "decision_id": "BR-DEC-002",
        "title": "Statement row with both Debit and Credit nonzero",
        "owner_role": "treasury_process_owner",
        "case_ids": ["parser.amounts.both_nonzero"],
        "required_before_slice": "isolated_statement_parser_staging",
        "options": [
            {
                "option_id": "reject_row",
                "effect": "Reject the row with a stable validation reason and persist nothing.",
                "risk": "Requires an operator correction path for malformed bank files.",
            },
            {
                "option_id": "quarantine_row",
                "effect": "Keep the raw staged row outside the ledger until explicit review.",
                "risk": "Adds a review queue and retention policy.",
            },
        ],
        "recommended_safe_default": "reject_row",
        "required_evidence": ["approved sample of a dual-sided source row if this occurs in practice"],
    },
    {
        "decision_id": "BR-DEC-003",
        "title": "Zero-amount statement row policy",
        "owner_role": "treasury_process_owner",
        "case_ids": ["parser.amounts.both_zero"],
        "required_before_slice": "isolated_statement_parser_staging",
        "options": [
            {
                "option_id": "reject_row",
                "effect": "Reject zero-amount rows before session persistence.",
                "risk": "May exclude informational rows used by a specific bank format.",
            },
            {
                "option_id": "quarantine_informational_row",
                "effect": "Store it only in immutable staging with an informational classification.",
                "risk": "Requires an explicit non-ledger data lifecycle.",
            },
        ],
        "recommended_safe_default": "reject_row",
        "required_evidence": ["approved bank-format fixture showing whether zero rows carry business meaning"],
    },
    {
        "decision_id": "BR-DEC-004",
        "title": "Dormant profile-field activation",
        "owner_role": "integration_product_owner",
        "case_ids": [
            "parser.profile_field.hdr",
            "parser.profile_field.startrow",
            "parser.profile_field.seperator",
            "parser.profile_field.isarabic",
        ],
        "required_before_slice": "isolated_statement_parser_staging",
        "options": [
            {
                "option_id": "remain_inert_until_typed_parser_support",
                "effect": "Do not expose or apply a field until a typed parser implements and tests it.",
                "risk": "Some legacy profile intent may remain unavailable initially.",
            },
            {
                "option_id": "activate_per_profile_version",
                "effect": "Activate only an explicitly approved subset in a versioned parser profile.",
                "risk": "Requires real profile fixtures and per-format acceptance tests.",
            },
        ],
        "recommended_safe_default": "remain_inert_until_typed_parser_support",
        "required_evidence": ["approved redacted real profile rows", "per-format parser output parity"],
    },
    {
        "decision_id": "BR-DEC-005",
        "title": "Already-reconciled instrument conflict",
        "owner_role": "treasury_process_owner",
        "case_ids": ["confirm.already_reconciled"],
        "required_before_slice": "confirm_command",
        "options": [
            {
                "option_id": "reject_conflict",
                "effect": "Reject when the instrument belongs to a different session or state.",
                "risk": "Requires a clear investigation/reversal workflow.",
            },
            {
                "option_id": "idempotent_same_session_only",
                "effect": "Return the prior success only when command identity and session ownership match exactly.",
                "risk": "Requires durable idempotency keys and ownership evidence.",
            },
        ],
        "recommended_safe_default": "reject_conflict",
        "required_evidence": ["owner-approved idempotency and cross-session conflict rules"],
    },
    {
        "decision_id": "BR-DEC-006",
        "title": "Confirmed-session reversal policy",
        "owner_role": "finance_controller",
        "case_ids": [
            "confirm.unmatch_reversal.reversal_all_instruments",
            "confirm.unmatch_reversal.reversal_failure",
        ],
        "required_before_slice": "reverse_confirmed_session_command",
        "options": [
            {
                "option_id": "deny_until_audited_reversal_is_approved",
                "effect": "Confirmed sessions remain immutable until a separate authorized reversal contract exists.",
                "risk": "Operational corrections require an interim controlled procedure.",
            },
            {
                "option_id": "atomic_audited_reversal",
                "effect": "Reverse the session and every linked instrument atomically with reason, actor and version checks.",
                "risk": "Requires finance approval, SoD, failure injection and audit retention.",
            },
        ],
        "recommended_safe_default": "deny_until_audited_reversal_is_approved",
        "required_evidence": ["finance-approved reversal accounting policy", "authenticated SoD UAT", "atomic rollback tests"],
    },
    {
        "decision_id": "BR-DEC-007",
        "title": "Unconfirmed empty-session cancel/archive policy",
        "owner_role": "treasury_process_owner",
        "case_ids": ["confirm.discard_cancel.cancel_empty_header"],
        "required_before_slice": "cancel_session_command",
        "options": [
            {
                "option_id": "archive_with_reason",
                "effect": "Atomically transition the header and rows to a non-active archived state with reason.",
                "risk": "Requires retention and visibility rules for archived imports.",
            },
            {
                "option_id": "hard_delete_unconfirmed_only",
                "effect": "Delete an unconfirmed empty session only under strict version and no-link guards.",
                "risk": "Reduces audit evidence and needs explicit retention approval.",
            },
        ],
        "recommended_safe_default": "archive_with_reason",
        "required_evidence": ["retention policy", "owner-approved distinction between discard and cancel"],
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--differential-acceptance", required=True, type=Path)
    parser.add_argument("--type-alias-aggregates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = _load(args.differential_acceptance)
    if source.get("validation") != "PASS":
        raise ValueError("validated differential-acceptance artifact required")
    alias_evidence = _load(args.type_alias_aggregates)
    if alias_evidence.get("validation") != "PASS":
        raise ValueError("validated type-alias aggregate artifact required")

    owner_cases = {
        row["case_id"] for row in source["cases"] if row.get("owner_decision_required") is True
    }
    mapped = [case_id for decision in DECISIONS for case_id in decision["case_ids"]]
    duplicate_mappings = sorted({case_id for case_id in mapped if mapped.count(case_id) > 1})
    missing_mappings = sorted(owner_cases - set(mapped))
    extra_mappings = sorted(set(mapped) - owner_cases)
    validation_errors = []
    if duplicate_mappings:
        validation_errors.append("duplicate case mappings: " + ", ".join(duplicate_mappings))
    if missing_mappings:
        validation_errors.append("unmapped owner cases: " + ", ".join(missing_mappings))
    if extra_mappings:
        validation_errors.append("unknown mapped cases: " + ", ".join(extra_mappings))

    decisions = []
    for template in DECISIONS:
        row = dict(template)
        row.update(
            {
                "decision_status": "NOT_APPROVED",
                "selected_option_id": None,
                "approver_identity": None,
                "approval_timestamp": None,
                "approval_evidence_reference": None,
                "source_varanegar_mutation_allowed": False,
            }
        )
        if row["decision_id"] == "BR-DEC-001":
            row["available_evidence"] = {
                "evidence_status": "PARTIAL_CLONE_AGGREGATE_AVAILABLE_PARITY_PENDING",
                "artifact": alias_evidence["artifact"],
                "bank_account_cardex_row_count": alias_evidence["summary"]["bank_account_cardex_row_count"],
                "summary_literal_total_count": alias_evidence["summary"]["summary_literal_total_count"],
                "matching_literal_total_count": alias_evidence["summary"]["matching_literal_total_count"],
                "short_literal_catalog_consumer_count": alias_evidence["summary"]["short_literal_catalog_consumer_count"],
                "canonical_literal_catalog_consumer_count": alias_evidence["summary"]["canonical_literal_catalog_consumer_count"],
                "alias_family_with_short_summary_outlier_count": alias_evidence["summary"]["alias_family_with_short_summary_outlier_count"],
                "owner_approval_inferred": False,
                "runtime_result_parity_proven": False,
                "production_frequency_proven": False,
            }
        decisions.append(row)

    payload = {
        "artifact": "negin_erp_bank_reconciliation_owner_decision_register",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "status": "DECISION_INPUT_READY_NOT_OWNER_APPROVED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ACCEPTANCE_OBLIGATION_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_values_read": 0,
            "owner_approvals_inferred": 0,
        },
        "source_evidence": {
            "artifact": source["artifact"],
            "validation": source["validation"],
            "owner_decision_case_count": len(owner_cases),
            "supporting_alias_aggregate_artifact": alias_evidence["artifact"],
            "supporting_alias_aggregate_validation": alias_evidence["validation"],
        },
        "summary": {
            "owner_decision_case_count": len(owner_cases),
            "decision_register_count": len(decisions),
            "mapped_case_count": len(set(mapped) & owner_cases),
            "recommended_safe_default_count": sum(bool(row["recommended_safe_default"]) for row in decisions),
            "decision_with_partial_clone_evidence_count": sum("available_evidence" in row for row in decisions),
            "approved_decision_count": 0,
            "unapproved_decision_count": len(decisions),
            "database_connection_count": 0,
            "source_or_target_command_execution_count": 0,
            "validation_error_count": len(validation_errors),
        },
        "decisions": decisions,
        "execution_rule": {
            "recommendation_is_not_approval": True,
            "selected_option_requires_named_owner_and_evidence_reference": True,
            "command_slice_remains_blocked_until_its_required_decisions_are_approved": True,
            "source_varanegar_remains_read_only": True,
        },
        "validation_errors": validation_errors,
        "limits": [
            "Safe defaults are engineering recommendations, not business approvals.",
            "No individual approver identity is known or persisted in this artifact.",
            "A decision cannot replace redacted parity fixtures or authenticated role UAT.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
