"""Build the first non-final evidence baseline for the active 24-hour continuation."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "artifacts/varanegar_analysis"
FIXED = {
    "prior_baseline": "varanegar_25h_final_baseline_bundle_20260829.json",
    "gap": "varanegar_24h_continuation_gap_map_20260829.json",
    "inventory": "varanegar_accounting_command_inventory_correction_20260829.json",
    "generic_save": "varanegar_manual_voucher_generic_save_20260829.json",
    "readiness": "varanegar_command_readiness_delta_20260829.json",
    "accounting_golden": "varanegar_accounting_golden_uat_cases_20260829.json",
    "report_golden": "varanegar_report_golden_fixture_design_20260829.json",
    "playbook": "varanegar_accounting_expert_playbook_contract_20260829.json",
    "trace_delta": "varanegar_continuation_traceability_delta_20260829.json",
    "risk": "ui/negin_erp_risk_register_20260829.json",
    "trace": "ui/negin_erp_requirements_traceability_20260829.json",
}
DOCS = [
    "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "docs/varanegar_reconstruction/README_FA.md",
    "docs/varanegar_reconstruction/VARANEGAR_24H_CONTINUATION_WAVE01_20260829_FA.md",
]
POST_WAVE01_CHECKPOINTS = {
    "varanegar_treasury_command_outcome_checkpoint_20260829.json",
    "varanegar_treasury_command_readiness_checkpoint_20260829.json",
    "varanegar_treasury_golden_uat_checkpoint_20260829.json",
    "varanegar_treasury_expert_playbook_checkpoint_20260829.json",
    "varanegar_treasury_traceability_delta_checkpoint_20260829.json",
    "varanegar_distribution_command_outcome_checkpoint_20260829.json",
    "varanegar_distribution_command_readiness_checkpoint_20260829.json",
    "varanegar_distribution_golden_uat_checkpoint_20260829.json",
    "varanegar_distribution_expert_playbook_checkpoint_20260829.json",
    "varanegar_distribution_traceability_delta_checkpoint_20260829.json",
    "varanegar_cross_module_reconciliation_checkpoint_20260829.json",
    "varanegar_cross_module_reconciliation_golden_checkpoint_20260829.json",
    "varanegar_cross_module_reconciliation_playbook_checkpoint_20260829.json",
    "varanegar_cross_module_reconciliation_traceability_delta_checkpoint_20260829.json",
    "varanegar_24h_continuation_gap_refresh_checkpoint_20260829.json",
    "varanegar_reporting_output_outcome_checkpoint_20260829.json",
    "varanegar_reporting_output_readiness_checkpoint_20260829.json",
    "varanegar_reporting_output_golden_uat_checkpoint_20260829.json",
    "varanegar_reporting_output_expert_playbook_checkpoint_20260829.json",
    "varanegar_reporting_output_traceability_delta_checkpoint_20260829.json",
    "varanegar_pricing_rule_outcome_checkpoint_20260829.json",
    "varanegar_pricing_rule_readiness_checkpoint_20260829.json",
    "varanegar_pricing_rule_golden_uat_checkpoint_20260829.json",
    "varanegar_pricing_rule_expert_playbook_checkpoint_20260829.json",
    "varanegar_pricing_rule_traceability_delta_checkpoint_20260829.json",
    "varanegar_integration_migration_outcome_checkpoint_20260829.json",
    "varanegar_integration_migration_readiness_checkpoint_20260829.json",
    "varanegar_integration_migration_golden_uat_checkpoint_20260829.json",
    "varanegar_integration_migration_expert_playbook_checkpoint_20260829.json",
    "varanegar_integration_migration_traceability_delta_checkpoint_20260829.json",
    "varanegar_configuration_outcome_checkpoint_20260829.json",
    "varanegar_configuration_readiness_checkpoint_20260829.json",
    "varanegar_configuration_golden_uat_checkpoint_20260829.json",
    "varanegar_configuration_expert_playbook_checkpoint_20260829.json",
    "varanegar_configuration_traceability_delta_checkpoint_20260829.json",
    "varanegar_identity_authorization_outcome_checkpoint_20260829.json",
    "varanegar_identity_authorization_readiness_checkpoint_20260829.json",
    "varanegar_identity_authorization_golden_uat_checkpoint_20260829.json",
    "varanegar_identity_authorization_expert_playbook_checkpoint_20260829.json",
    "varanegar_identity_authorization_traceability_delta_checkpoint_20260829.json",
    "varanegar_organization_context_outcome_checkpoint_20260829.json",
    "varanegar_organization_context_readiness_checkpoint_20260829.json",
    "varanegar_organization_context_golden_uat_checkpoint_20260829.json",
    "varanegar_organization_context_expert_playbook_checkpoint_20260829.json",
    "varanegar_organization_context_traceability_delta_checkpoint_20260829.json",
    "varanegar_master_data_outcome_checkpoint_20260829.json",
    "varanegar_master_data_readiness_checkpoint_20260829.json",
    "varanegar_master_data_golden_uat_checkpoint_20260829.json",
    "varanegar_master_data_expert_playbook_checkpoint_20260829.json",
    "varanegar_master_data_traceability_delta_checkpoint_20260829.json",
    "varanegar_platform_outcome_checkpoint_20260829.json",
    "varanegar_platform_readiness_checkpoint_20260829.json",
    "varanegar_platform_golden_uat_checkpoint_20260829.json",
    "varanegar_platform_expert_playbook_checkpoint_20260829.json",
    "varanegar_platform_traceability_delta_checkpoint_20260829.json",
    "varanegar_24h_continuation_consolidated_checkpoint_20260829.json",
    "varanegar_identity_integration_transaction_mutation_checkpoint_20260829.json",
    "varanegar_external_evidence_gate_priority_checkpoint_20260829.json",
    "varanegar_platform_decision_evidence_intake_checkpoint_20260829.json",
    "varanegar_report_parity_evidence_intake_checkpoint_20260829.json",
    "varanegar_authorization_runtime_evidence_intake_checkpoint_20260829.json",
    "varanegar_atomicity_fault_evidence_intake_checkpoint_20260829.json",
    "varanegar_effect_parity_evidence_intake_checkpoint_20260829.json",
    "varanegar_terminal_owner_uat_evidence_intake_checkpoint_20260829.json",
    "varanegar_external_gate_handoff_acceptance_checkpoint_20260829.json",
    "varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.json",
    "varanegar_report_formula_grain_policy_checkpoint_20260829.json",
    "varanegar_identity_authorization_gap_triage_checkpoint_20260829.json",
    "varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint_20260829.json",
    "varanegar_golden_uat_design_delta_audit_checkpoint_20260829.json",
    "varanegar_cross_gate_golden_uat_refinement_checkpoint_20260829.json",
    "varanegar_golden_uat_crosswalk_feasibility_checkpoint_20260829.json",
    "varanegar_distribution_treasury_semantic_alias_candidate_checkpoint_20260829.json",
    "varanegar_unmatched_golden_case_alias_work_queue_checkpoint_20260829.json",
    "varanegar_five_case_kind_multiplicity_disposition_checkpoint_20260829.json",
    "varanegar_action_alias_owner_evidence_packet_checkpoint_20260829.json",
    "varanegar_action_alias_handoff_priority_checkpoint_20260829.json",
    "varanegar_p0_alias_baseline_candidate_checkpoint_20260829.json",
    "varanegar_p0_alias_semantic_evidence_checkpoint_20260829.json",
    "varanegar_p0_failure_injection_adjudication_checkpoint_20260829.json",
    "varanegar_p0_control_outcome_vocabulary_checkpoint_20260829.json",
    "varanegar_p0_assertion_effect_family_gap_checkpoint_20260829.json",
    "varanegar_p0_final_evidence_gap_status_checkpoint_20260829.json",
    "varanegar_p1_alias_baseline_candidate_checkpoint_20260829.json",
    "varanegar_p1_alias_semantic_evidence_checkpoint_20260829.json",
    "varanegar_p1_failure_injection_adjudication_checkpoint_20260829.json",
    "varanegar_p1_control_outcome_vocabulary_checkpoint_20260829.json",
    "varanegar_p1_assertion_effect_family_gap_checkpoint_20260829.json",
    "varanegar_p1_final_evidence_gap_status_checkpoint_20260829.json",
    "varanegar_p2_alias_baseline_candidate_checkpoint_20260829.json",
    "varanegar_p2_alias_semantic_evidence_checkpoint_20260829.json",
    "varanegar_p2_failure_injection_adjudication_checkpoint_20260829.json",
    "varanegar_p2_control_outcome_vocabulary_checkpoint_20260829.json",
    "varanegar_p2_assertion_effect_family_gap_checkpoint_20260829.json",
    "varanegar_p2_final_evidence_gap_status_checkpoint_20260829.json",
    "varanegar_p3_alias_baseline_candidate_checkpoint_20260829.json",
    "varanegar_p3_alias_semantic_evidence_checkpoint_20260829.json",
    "varanegar_p3_failure_injection_adjudication_checkpoint_20260829.json",
    "varanegar_p3_control_outcome_vocabulary_checkpoint_20260829.json",
    "varanegar_p3_assertion_effect_family_gap_checkpoint_20260829.json",
    "varanegar_p3_final_evidence_gap_status_checkpoint_20260829.json",
    "varanegar_p4_alias_baseline_candidate_checkpoint_20260829.json",
    "varanegar_p4_alias_semantic_evidence_checkpoint_20260829.json",
    "varanegar_p4_failure_injection_adjudication_checkpoint_20260829.json",
    "varanegar_p4_control_outcome_vocabulary_checkpoint_20260829.json",
    "varanegar_p4_assertion_effect_family_gap_checkpoint_20260829.json",
    "varanegar_p4_final_evidence_gap_status_checkpoint_20260829.json",
    "varanegar_alias_cross_lane_closure_route_checkpoint_20260829.json",
    "varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829.json",
    "varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829.json",
    "varanegar_alias_cross_lane_role_handoff_checkpoint_20260829.json",
    "varanegar_p0_external_evidence_collection_activation_checkpoint_20260829.json",
    "varanegar_p1_p4_external_evidence_activation_sequence_checkpoint_20260829.json",
    "varanegar_p3_p4_cg05_result_parity_receipt_checkpoint_20260829.json",
    "varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.json",
    "varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.json",
    "varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.json",
    "varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.json",
    "varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.json",
    "varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint_20260829.json",
    "varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint_20260829.json",
    "varanegar_p3_p4_isolated_capture_authorization_redaction_gate_checkpoint_20260829.json",
    "varanegar_p3_p4_capture_to_comparison_evidence_handoff_checkpoint_20260829.json",
    "varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint_20260829.json",
    "varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint_20260829.json",
    "varanegar_p3_p4_evidence_freshness_clock_policy_reference_checkpoint_20260829.json",
    "varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint_20260829.json",
    "varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint_20260829.json",
    "varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829.json",
    "varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.json",
    "varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829.json",
    "varanegar_target_erp_evidence_logging_redaction_retention_checkpoint_20260829.json",
    "varanegar_target_erp_evidence_redaction_synthetic_reference_validator_checkpoint_20260829.json",
    "varanegar_target_erp_migration_cutover_snapshot_delta_reconciliation_checkpoint_20260829.json",
    "varanegar_target_erp_environment_isolation_write_fence_execution_token_checkpoint_20260829.json",
    "varanegar_target_erp_release_promotion_change_rollback_evidence_checkpoint_20260829.json",
    "varanegar_target_erp_observability_slo_incident_evidence_checkpoint_20260829.json",
    "varanegar_target_erp_configuration_policy_immutability_change_audit_checkpoint_20260829.json",
    "varanegar_target_erp_data_provenance_read_model_rebuild_checkpoint_20260829.json",
    "varanegar_target_erp_release_promotion_rollback_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_monetary_quantity_temporal_semantics_checkpoint_20260829.json",
    "varanegar_target_erp_monetary_temporal_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_optimistic_concurrency_version_fencing_checkpoint_20260829.json",
    "varanegar_target_erp_concurrency_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_master_data_identity_dedup_merge_supersession_checkpoint_20260829.json",
    "varanegar_target_erp_capacity_timeout_backpressure_degradation_checkpoint_20260829.json",
    "varanegar_target_erp_capacity_budget_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_document_numbering_series_void_rollover_checkpoint_20260829.json",
    "varanegar_target_erp_numbering_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_file_attachment_import_export_integrity_checkpoint_20260829.json",
    "varanegar_target_erp_file_metadata_synthetic_reference_validator_checkpoint_20260829.json",
    "varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_checkpoint_20260829.json",
    "varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_integration_webhook_message_authenticity_replay_deadletter_checkpoint_20260829.json",
    "varanegar_target_erp_integration_message_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_output_print_pdf_label_barcode_rendering_integrity_checkpoint_20260829.json",
    "varanegar_target_erp_output_rendering_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_privacy_consent_legal_basis_data_subject_rights_checkpoint_20260829.json",
    "varanegar_target_erp_privacy_rights_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_approval_delegation_escalation_sod_breakglass_checkpoint_20260829.json",
    "varanegar_target_erp_approval_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_tax_fiscalization_einvoice_clearance_checkpoint_20260829.json",
    "varanegar_target_erp_tax_fiscalization_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_inventory_lot_serial_expiry_costing_valuation_checkpoint_20260829.json",
    "varanegar_target_erp_inventory_synthetic_reference_evaluator_checkpoint_20260829.json",
    "varanegar_target_erp_procure_to_pay_three_way_match_checkpoint_20260901.json",
    "varanegar_target_erp_procure_to_pay_synthetic_reference_evaluator_checkpoint_20260901.json",
    "varanegar_target_erp_order_to_cash_credit_collections_checkpoint_20260901.json",
    "varanegar_target_erp_order_to_cash_synthetic_reference_evaluator_checkpoint_20260901.json",
    "varanegar_target_erp_workforce_time_payroll_checkpoint_20260901.json",
    "varanegar_target_erp_payroll_synthetic_reference_evaluator_checkpoint_20260901.json",
    "varanegar_10h_continuation_handoff_checkpoint_20260901.json",
    "varanegar_target_erp_fixed_asset_lifecycle_depreciation_checkpoint_20260901.json",
    "varanegar_target_erp_fixed_asset_synthetic_reference_evaluator_checkpoint_20260901.json",
    "varanegar_target_erp_domain_coverage_gap_checkpoint_20260901.json",
    "varanegar_target_erp_contract_portfolio_invariant_audit_checkpoint_20260901.json",
    "varanegar_target_erp_manufacturing_mrp_shopfloor_quality_checkpoint_20260901.json",
    "varanegar_target_erp_manufacturing_synthetic_reference_evaluator_checkpoint_20260901.json",
    "varanegar_target_erp_project_job_costing_revenue_billing_checkpoint_20260901.json",
    "varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_checkpoint_20260901.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def checkpoint_stale(document: dict) -> bool:
    for source in document.get("source_manifest", []):
        path = ROOT / source["path"]
        if not path.is_file() or path.stat().st_size != source["size_bytes"] or sha256(path) != source["sha256"]:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    test_path = args.test_result if args.test_result.is_absolute() else ROOT / args.test_result
    sources = {name: load(ANALYSIS / value) for name, value in FIXED.items()}
    test_result = load(test_path)
    own_checkpoint_name = "varanegar_24h_continuation_wave01_checkpoint_20260829.json"
    checkpoint_paths = sorted(
        path
        for path in ANALYSIS.glob("varanegar_*checkpoint_*.json")
        if path.name != own_checkpoint_name and path.name not in POST_WAVE01_CHECKPOINTS
    )
    checkpoint_documents = [load(path) for path in checkpoint_paths]
    passing = sum(document.get("validation") == "PASS" for document in checkpoint_documents)
    stale = sum(checkpoint_stale(document) for document in checkpoint_documents)
    accounting = sources["accounting_golden"]["summary"]
    reports = sources["report_golden"]["summary"]
    playbook = sources["playbook"]["summary"]
    delta = sources["trace_delta"]["summary"]
    checks = {
        "all_fixed_inputs_pass": all(source["validation"] == "PASS" for source in sources.values()),
        "all_checkpoints_pass": passing == len(checkpoint_documents),
        "checkpoint_manifests_current": stale == 0,
        "full_test_suite_pass": test_result["validation"] == "PASS" and test_result["runner"]["exit_code"] == 0,
        "accounting_inventory_corrected": sources["inventory"]["summary"]["corrected_command_count"] == 6,
        "accounting_golden_boundary_honest": accounting["case_count"] == 42 and accounting["executed_case_count"] == 0,
        "report_golden_boundary_honest": reports["case_count"] == 88 and reports["executed_case_count"] == 0,
        "expert_contract_complete": playbook["playbook_count"] == 5 and playbook["target_contract_section_count"] == 9,
        "trace_delta_additive": delta["continuation_evidence_count"] == 7 and delta["new_risk_count"] == 0,
        "base_risk_trace_stable": sources["risk"]["summary"]["risk_count"] == 84
        and sources["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
        "runtime_readiness_zero": sources["readiness"]["summary"]["command_ready_module_count"] == 0
        and sources["readiness"]["summary"]["pilot_ready_module_count"] == 0,
        "required_docs_present": all((ROOT / path).is_file() for path in DOCS),
    }
    failed = sorted(name for name, value in checks.items() if not value)
    requirements = [
        {"requirement": "continue_from_25h_baseline_without_restart", "status": "PROVEN", "evidence": FIXED["gap"]},
        {"requirement": "accounting_command_semantic_correction", "status": "PROVEN_STATIC", "evidence": FIXED["inventory"]},
        {"requirement": "manual_voucher_generic_transaction_boundary", "status": "PROVEN_STATIC_RUNTIME_BRANCH_OPEN", "evidence": FIXED["generic_save"]},
        {"requirement": "accounting_outcome_retry_target_contract", "status": "PROVEN_DESIGN_NOT_RUNTIME", "evidence": FIXED["readiness"]},
        {"requirement": "accounting_golden_uat_design", "status": "PROVEN_DESIGN_NOT_EXECUTION", "evidence": FIXED["accounting_golden"]},
        {"requirement": "report_golden_fixture_design", "status": "PROVEN_DESIGN_NOT_RESULT_PARITY", "evidence": FIXED["report_golden"]},
        {"requirement": "accounting_expert_playbooks_and_target_contract", "status": "PROVEN_DESIGN", "evidence": FIXED["playbook"]},
        {"requirement": "knowledge_risk_traceability_continuation_delta", "status": "PROVEN_ADDITIVE", "evidence": FIXED["trace_delta"]},
    ]
    paths = checkpoint_paths + [ANALYSIS / value for value in FIXED.values()] + [
        test_path,
        Path(__file__).resolve(),
        ROOT / "scripts/windows/run_varanegar_24h_continuation_tests.py",
        ROOT / "tests/test_varanegar_24h_continuation_wave01_bundle.py",
        *[ROOT / path for path in DOCS],
    ]
    seen: set[str] = set()
    unique_paths = []
    for path in paths:
        resolved = str(path.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(path)
    output = {
        "artifact": "varanegar_24h_continuation_wave01_bundle_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "READ_ONLY_DOCUMENTED_REPRODUCIBLE_CONTINUATION", "wave": 1, "continuation_complete": False},
        "baseline": {
            "checkpoint_count": len(checkpoint_paths),
            "passing_checkpoint_count": passing,
            "stale_checkpoint_manifest_count": stale,
            "offline_test_file_count": test_result["runner"]["test_file_count"],
            "offline_test_passed_count": test_result["runner"]["passed_test_count"],
            "warning_count": test_result["runner"]["warning_count"],
            "risk_count": 84,
            "mapped_risk_assignment_count": 343,
            "command_ready_module_count": 0,
            "pilot_ready_module_count": 0,
            "corrected_accounting_command_count": 6,
            "accounting_golden_design_count": 42,
            "accounting_golden_executed_count": 0,
            "report_golden_design_count": 88,
            "report_result_parity_proven_count": 0,
            "accounting_expert_playbook_count": 5,
            "target_contract_section_count": 9,
            "continuation_trace_evidence_count": 7,
        },
        "requirement_audit": requirements,
        "checks": checks,
        "failed_checks": failed,
        "safety": {
            "operational_forms_reports_or_procedures_executed": 0,
            "varanegar_or_ngt_data_mutations": 0,
            "write_access_created": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_credentials_pii_rules_or_business_values_persisted": 0,
        },
        "manifest": [manifest(path) for path in unique_paths],
        "next_wave_priorities": [
            "treasury command outcome and retry envelope",
            "distribution command outcome and retry envelope",
            "cross-module reconciliation fixture schema",
            "owner/UAT evidence remains an external gate",
        ],
        "confidence": {"static_and_design_scope": "HIGH", "runtime_result_parity": "NOT_PROVEN", "owner_acceptance": "NOT_OBSERVED"},
        "limits": [
            "Wave 01 is an intermediate continuation checkpoint, not completion of the active 24-hour goal.",
            "No command-ready or pilot-ready module is claimed.",
            "Production-only behavior requires separately authorized isolated UAT and owner evidence.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(output["baseline"], ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
