"""Build provisional, identity-free target ERP role and SoD contracts offline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


TARGET_CAPABILITIES = (
    "session.switch_fiscal_year", "session.switch_distribution_center",
    "master.read", "master.curate", "pricing.read", "pricing.publish",
    "sales.read", "sales.create_edit", "sales.cancel", "returns.create",
    "inventory.stock_goods.read", "inventory.stock_goods.create_edit_delete",
    "distribution.read", "distribution.create_edit", "distribution.follow",
    "distribution.follow_after_voucher", "distribution.reverse_status",
    "distribution.issue_exit", "distribution.remove_exit",
    "distribution.free_or_merge_exit", "received_cheque.read",
    "received_cheque.change_status", "received_cheque.undo",
    "payable_cheque.read", "payable_cheque.change_status", "payable_cheque.undo",
    "accounting.read", "accounting.post", "accounting.reverse",
    "accounting.close_period", "report.read", "report.preview",
    "report.export_file", "document.print", "document.mark_print_completed",
    "configuration.read", "configuration.publish", "authorization.explain",
    "authorization.assign_role", "authorization.grant_scope",
    "migration.capture", "migration.import", "migration.reconcile",
    "migration.resolve_quarantine", "platform.audit.read",
)


ROLE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {"role": "business_reader", "purpose": "scoped read and preview", "allow": ["master.read", "pricing.read", "sales.read", "inventory.stock_goods.read", "distribution.read", "received_cheque.read", "payable_cheque.read", "accounting.read", "report.read", "report.preview"], "deny": ["*.write", "*.publish", "*.undo", "*.reverse", "*.close", "authorization.*", "migration.import"]},
    {"role": "master_data_steward", "purpose": "curate reference data without transactional authority", "allow": ["master.read", "master.curate", "report.read"], "deny": ["sales.*", "distribution.*", "*_cheque.*", "accounting.post", "accounting.reverse", "configuration.publish", "authorization.*"]},
    {"role": "sales_operator", "purpose": "prepare sales and returns", "allow": ["master.read", "pricing.read", "sales.read", "sales.create_edit", "returns.create", "report.read"], "deny": ["pricing.publish", "distribution.issue_exit", "*_cheque.*", "accounting.*", "authorization.*"]},
    {"role": "distribution_planner", "purpose": "create and follow distribution work", "allow": ["sales.read", "inventory.stock_goods.read", "distribution.read", "distribution.create_edit", "distribution.follow", "distribution.follow_after_voucher"], "deny": ["distribution.issue_exit", "distribution.remove_exit", "distribution.reverse_status", "distribution.free_or_merge_exit", "accounting.*"]},
    {"role": "warehouse_exit_operator", "purpose": "issue physical exit after an approved distribution", "allow": ["inventory.stock_goods.read", "distribution.read", "distribution.issue_exit", "document.print"], "deny": ["distribution.create_edit", "distribution.follow", "distribution.remove_exit", "distribution.reverse_status", "accounting.*"]},
    {"role": "distribution_exception_controller", "purpose": "approved reverse/remove/merge exceptions", "allow": ["inventory.stock_goods.read", "distribution.read", "distribution.reverse_status", "distribution.remove_exit", "distribution.free_or_merge_exit", "platform.audit.read"], "deny": ["distribution.create_edit", "distribution.issue_exit", "authorization.*"]},
    {"role": "receivables_operator", "purpose": "received-instrument workflow", "allow": ["sales.read", "received_cheque.read", "received_cheque.change_status", "report.read", "document.print"], "deny": ["received_cheque.undo", "payable_cheque.*", "accounting.post", "authorization.*"]},
    {"role": "payables_operator", "purpose": "payable-instrument workflow", "allow": ["payable_cheque.read", "payable_cheque.change_status", "report.read", "document.print"], "deny": ["payable_cheque.undo", "received_cheque.*", "accounting.post", "authorization.*"]},
    {"role": "treasury_exception_controller", "purpose": "approved last-event undo with independent review", "allow": ["received_cheque.read", "received_cheque.undo", "payable_cheque.read", "payable_cheque.undo", "platform.audit.read"], "deny": ["received_cheque.change_status", "payable_cheque.change_status", "authorization.*"]},
    {"role": "financial_controller", "purpose": "posting, reversal and period control", "allow": ["accounting.read", "accounting.post", "accounting.reverse", "accounting.close_period", "report.read", "report.preview", "platform.audit.read"], "deny": ["sales.create_edit", "distribution.*", "*_cheque.change_status", "authorization.*", "migration.import"]},
    {"role": "report_exporter", "purpose": "approved export and transactional document output", "allow": ["report.read", "report.preview", "report.export_file", "document.print", "document.mark_print_completed"], "deny": ["sales.create_edit", "distribution.*", "*_cheque.*", "accounting.post", "authorization.*"]},
    {"role": "security_administrator", "purpose": "role/scope administration without business execution", "allow": ["authorization.explain", "authorization.assign_role", "authorization.grant_scope", "platform.audit.read"], "deny": ["sales.*", "distribution.*", "*_cheque.*", "accounting.post", "accounting.reverse", "migration.import"]},
    {"role": "configuration_publisher", "purpose": "versioned configuration publication", "allow": ["configuration.read", "configuration.publish", "platform.audit.read"], "deny": ["authorization.*", "sales.*", "distribution.*", "*_cheque.*", "accounting.post"]},
    {"role": "migration_operator", "purpose": "capture/import/reconcile an approved isolated slice", "allow": ["migration.capture", "migration.import", "migration.reconcile", "platform.audit.read"], "deny": ["migration.resolve_quarantine", "authorization.*", "accounting.post", "accounting.close_period"]},
    {"role": "migration_reviewer", "purpose": "review reconciliation and resolve quarantine independently", "allow": ["migration.reconcile", "migration.resolve_quarantine", "platform.audit.read"], "deny": ["migration.capture", "migration.import", "authorization.*"]},
)


SOD_RULES: tuple[dict[str, Any], ...] = (
    {"id": "SOD-01", "left": ["authorization.assign_role", "authorization.grant_scope"], "right": ["any_business_mutation"], "severity": "critical", "control": "hard role exclusion; no self-grant; independent approval"},
    {"id": "SOD-02", "left": ["distribution.create_edit"], "right": ["distribution.issue_exit"], "severity": "high", "control": "maker/checker role separation; time-bound break-glass only"},
    {"id": "SOD-03", "left": ["distribution.issue_exit"], "right": ["distribution.remove_exit", "distribution.reverse_status", "distribution.free_or_merge_exit"], "severity": "critical", "control": "exception controller plus reason, approval and reconciliation"},
    {"id": "SOD-04", "left": ["received_cheque.change_status"], "right": ["received_cheque.undo"], "severity": "high", "control": "independent undo role or dual approval"},
    {"id": "SOD-05", "left": ["payable_cheque.change_status"], "right": ["payable_cheque.undo"], "severity": "high", "control": "independent undo role or dual approval"},
    {"id": "SOD-06", "left": ["received_cheque.change_status"], "right": ["payable_cheque.change_status"], "severity": "high", "control": "separate receivable/payable operators; finance-owner exception review"},
    {"id": "SOD-07", "left": ["accounting.post"], "right": ["accounting.reverse", "accounting.close_period"], "severity": "high", "control": "dual approval and immutable audit; separate controller where staffing allows"},
    {"id": "SOD-08", "left": ["configuration.publish"], "right": ["affected_business_mutation"], "severity": "high", "control": "version approval, effective date and no same-user execution during change window"},
    {"id": "SOD-09", "left": ["migration.capture", "migration.import"], "right": ["migration.resolve_quarantine"], "severity": "critical", "control": "operator/reviewer separation"},
    {"id": "SOD-10", "left": ["report.export_file"], "right": ["unscoped_sensitive_data"], "severity": "high", "control": "field authorization, row scope, export audit, watermark and retention"},
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    capabilities = _load(args.capabilities)
    authorization = _load(args.authorization)
    reports = _load(args.reports)
    blueprint = _load(args.blueprint)
    observed = {row["capability"] for row in capabilities["capabilities"]}
    target = set(TARGET_CAPABILITIES)
    if not observed <= target:
        raise ValueError(f"observed capability missing from target registry: {sorted(observed-target)}")

    artifact = {
        "artifact": "negin_erp_identity_free_role_and_sod_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "PROVISIONAL_TEMPLATES_REQUIRE_BUSINESS_OWNER_SIGNOFF",
        "safety": {
            "mode": "OFFLINE_IDENTITY_FREE_DERIVATION_FROM_AGGREGATE_AUTHORIZATION_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "roles_or_grants_changed": 0,
            "user_or_group_identities_persisted": 0,
            "individual_grants_persisted": 0,
        },
        "evidence": {
            "observed_capability_count": capabilities["summary"]["capability_count"],
            "open_route_count": authorization["summary"]["open_route_count"],
            "authorization_node_count": authorization["summary"]["authorization_node_count"],
            "hidden_command_node_count": authorization["summary"]["hidden_command_node_count"],
            "report_surface_count": reports["summary"]["surface_count"],
            "target_module_count": blueprint["module_count"],
        },
        "decision_model": {
            "formula": "authenticated AND capability_allow AND NOT explicit_deny AND data_scope AND context_open AND feature_config AND domain_guard",
            "deny_precedence": "explicit deny wins at capability and scope layers",
            "namespaces": ["legacy_access_node", "legacy_data_scope", "ngt_rbac", "target_atomic_capability"],
            "required_trace": ["principal", "role_version", "capability", "scope", "context", "config_version", "guard_results", "decision", "reason_codes"],
            "session_rule": "context switch reauthorizes all routes and invalidates dependent query/cache state",
        },
        "atomic_capability_count": len(TARGET_CAPABILITIES),
        "atomic_capabilities": list(TARGET_CAPABILITIES),
        "legacy_observed_capabilities": sorted(observed),
        "role_template_count": len(ROLE_TEMPLATES),
        "role_templates": list(ROLE_TEMPLATES),
        "sod_rule_count": len(SOD_RULES),
        "sod_rules": list(SOD_RULES),
        "approval_contract": {
            "required_for": ["break_glass", "exception_undo", "distribution_reverse_or_remove", "accounting_reverse_or_period_close", "quarantine_resolution", "role_or_scope_grant"],
            "fields": ["approval_id", "requester", "approver", "capability", "aggregate_or_scope", "reason", "evidence_refs", "expires_at", "used_at", "audit_event_id"],
            "rules": ["requester cannot approve own request", "approval is capability/scope/context specific", "single use for material commands", "expiry required", "post-command reconciliation required"],
        },
        "mandatory_negative_tests": [
            "menu visible but command denied",
            "capability allowed but DC/stock/sale-office scope denied",
            "explicit deny overrides group allow",
            "context switch invalidates previous authorization decision",
            "feature disabled blocks allowed role",
            "invalid state/domain guard blocks allowed role",
            "self-grant and self-approval rejected",
            "expired or reused approval rejected",
            "drill-down and export reauthorize row and field scope",
        ],
        "not_inferred_from_aggregate_legacy_evidence": [
            "the role or suitability of any named person",
            "individual current grants",
            "business-owner approval of target templates",
            "production staffing or break-glass assignees",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"atomic_capability_count": artifact["atomic_capability_count"], "role_template_count": artifact["role_template_count"], "sod_rule_count": artifact["sod_rule_count"], "evidence": artifact["evidence"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
