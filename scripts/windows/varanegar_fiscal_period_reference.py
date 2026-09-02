"""Pure synthetic fiscal-period decision evaluator; it performs no ERP operation."""
from __future__ import annotations

FIELDS = {
    "scope_current", "period_state", "requested_action", "expected_period_version", "current_period_version",
    "all_posting_paths_guarded", "subledger_dependency_receipts_current", "control_totals_reconciled",
    "numbering_rollover_atomic", "adjustment_class_current", "adjustment_balanced", "reversal_policy_current",
    "reopen_reason_current", "reopen_impact_scope_current", "reopen_authorization_current", "sod_separated",
    "token_current_single_use", "break_glass", "incident_and_independent_review_current",
    "reclose_dependencies_rerun", "supersession_lineage_current", "blocking_unknown",
}
BOOL_FIELDS = FIELDS - {"period_state", "requested_action", "expected_period_version", "current_period_version"}
STATES = {"OPEN", "SOFT_CLOSED", "HARD_CLOSED", "REOPENED", "PERMANENTLY_SEALED"}
ACTIONS = {"CLOSE_SOFT", "CLOSE_HARD", "POST_ADJUSTMENT", "REOPEN", "RECLOSE"}
ALLOWED_STATE = {
    "CLOSE_SOFT": "OPEN", "CLOSE_HARD": "SOFT_CLOSED", "POST_ADJUSTMENT": "HARD_CLOSED",
    "REOPEN": "HARD_CLOSED", "RECLOSE": "REOPENED",
}


def evaluate(evidence):
    if not isinstance(evidence, dict) or set(evidence) != FIELDS:
        return "SCHEMA_INVALID"
    if any(type(evidence[name]) is not bool for name in BOOL_FIELDS):
        return "SCHEMA_INVALID"
    if any(type(evidence[name]) is not int or evidence[name] < 0 for name in ("expected_period_version", "current_period_version")):
        return "SCHEMA_INVALID"
    if evidence["period_state"] not in STATES or evidence["requested_action"] not in ACTIONS:
        return "SCHEMA_INVALID"
    if not evidence["scope_current"]:
        return "FISCAL_ACTION_REJECTED_SCOPE"
    if evidence["expected_period_version"] != evidence["current_period_version"]:
        return "FISCAL_ACTION_REJECTED_VERSION"
    action = evidence["requested_action"]
    if evidence["period_state"] != ALLOWED_STATE[action]:
        return "FISCAL_ACTION_REJECTED_STATE"
    if not evidence["all_posting_paths_guarded"]:
        return "FISCAL_ACTION_REJECTED_LOCK_BYPASS"
    if evidence["blocking_unknown"]:
        return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
    if action in {"CLOSE_SOFT", "CLOSE_HARD"}:
        if not evidence["subledger_dependency_receipts_current"] or not evidence["control_totals_reconciled"]:
            return "CLOSE_REJECTED_DEPENDENCY_OR_RECONCILIATION"
        if action == "CLOSE_HARD" and not evidence["numbering_rollover_atomic"]:
            return "CLOSE_REJECTED_NUMBERING_ROLLOVER_ATOMICITY"
        return "SOFT_CLOSE_ACCEPTED_RESTRICTED_POSTING" if action == "CLOSE_SOFT" else "HARD_CLOSE_ACCEPTED_ALL_DEPENDENCIES_RECONCILED"
    if action == "POST_ADJUSTMENT":
        if not evidence["adjustment_class_current"] or not evidence["adjustment_balanced"] or not evidence["reopen_authorization_current"]:
            return "ADJUSTMENT_REJECTED_CLASS_AUTHORIZATION_OR_BALANCE"
        if not evidence["reversal_policy_current"]:
            return "ADJUSTMENT_REJECTED_REVERSAL_POLICY"
        return "ADJUSTMENT_ACCEPTED_SCOPED_AND_REVERSIBLE"
    if action == "REOPEN":
        if not all(evidence[name] for name in ("reopen_reason_current", "reopen_impact_scope_current", "reopen_authorization_current", "token_current_single_use")):
            return "REOPEN_REJECTED_REASON_SCOPE_IMPACT_OR_EXPIRY"
        if not evidence["sod_separated"]:
            return "REOPEN_REJECTED_SEGREGATION_OF_DUTIES"
        if evidence["break_glass"] and not evidence["incident_and_independent_review_current"]:
            return "BREAK_GLASS_REJECTED_INCIDENT_OR_REVIEW"
        return "REOPEN_ACCEPTED_SCOPED_EXPIRING_AND_SEPARATED"
    if not evidence["reclose_dependencies_rerun"] or not evidence["control_totals_reconciled"] or not evidence["supersession_lineage_current"]:
        return "RECLOSE_REJECTED_DEPENDENCY_OR_LINEAGE"
    return "RECLOSE_ACCEPTED_RECONCILED_AND_SUPERSEDED"


def baseline():
    return {
        "scope_current": True, "period_state": "SOFT_CLOSED", "requested_action": "CLOSE_HARD",
        "expected_period_version": 7, "current_period_version": 7, "all_posting_paths_guarded": True,
        "subledger_dependency_receipts_current": True, "control_totals_reconciled": True,
        "numbering_rollover_atomic": True, "adjustment_class_current": True, "adjustment_balanced": True,
        "reversal_policy_current": True, "reopen_reason_current": True, "reopen_impact_scope_current": True,
        "reopen_authorization_current": True, "sod_separated": True, "token_current_single_use": True,
        "break_glass": False, "incident_and_independent_review_current": True,
        "reclose_dependencies_rerun": True, "supersession_lineage_current": True, "blocking_unknown": False,
    }
