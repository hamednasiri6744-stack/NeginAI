"""Build the evidence-backed implementation readiness contract for bank reconciliation.

This builder is deliberately offline. It combines previously validated static and
clone-catalog artifacts; it does not connect to Varanegar or execute any command.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


INPUT_NAMES = (
    "source_model",
    "command_guards",
    "permission_catalog",
    "delete_semantics",
    "unmatch_sql_semantics",
    "discard_cancel_boundary",
    "integrity_aggregates",
    "type_alias_aggregates",
    "import_boundary",
    "parser_row_contract",
    "persistence_boundary",
    "golden_cases",
    "transaction_boundary",
    "cardex_boundary",
    "confirm_cardex_semantics",
    "confirm_orchestration",
    "differential_acceptance",
    "owner_decision_pack",
    "profile_target_contract",
    "read_model_target_contract",
    "staging_target_contract",
    "state_machine_target_contract",
    "command_envelope_target_contract",
    "authenticated_uat_runbook",
    "matching_boundary",
    "summary_ui_boundary",
    "summary_sql_semantics",
    "profile_state_boundary",
    "role_uat",
    "root_closure",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in INPUT_NAMES:
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {name: getattr(args, name) for name in INPUT_NAMES}
    inputs = {name: _load(path) for name, path in paths.items()}
    invalid_inputs = sorted(
        name for name, payload in inputs.items() if payload.get("validation") != "PASS"
    )

    summaries = {name: payload["summary"] for name, payload in inputs.items()}
    validation_errors: list[str] = []
    expected_facts = {
        "source_table_count": (summaries["source_model"]["found_table_count"], 15),
        "typed_match_mapping_count": (
            summaries["matching_boundary"]["typed_reference_mapping_count"],
            6,
        ),
        "summary_parameter_count": (
            summaries["matching_boundary"]["summary_parameter_count"],
            14,
        ),
        "summary_output_to_ui_mapping_count": (
            summaries["summary_ui_boundary"]["output_to_label_mapping_count"],
            11,
        ),
        "summary_static_formula_metric_count": (
            summaries["summary_sql_semantics"]["output_metric_count"],
            11,
        ),
        "profile_row_snapshot_count": (
            summaries["profile_state_boundary"]["profile_table_row_count_snapshot"],
            0,
        ),
        "parser_canonical_input_column_count": (
            summaries["parser_row_contract"]["canonical_input_column_count"],
            6,
        ),
        "legacy_confirm_maximum_typed_link_updates": (
            summaries["confirm_cardex_semantics"]["maximum_typed_link_updates_per_execution"],
            1,
        ),
        "confirm_permission_or_operation_date_call_count": (
            summaries["confirm_orchestration"]["confirm_permission_or_operation_date_call_count"],
            0,
        ),
        "differential_acceptance_case_count": (
            summaries["differential_acceptance"]["differential_acceptance_case_count"],
            116,
        ),
        "owner_decision_register_count": (
            summaries["owner_decision_pack"]["decision_register_count"],
            7,
        ),
        "approved_owner_decision_count": (
            summaries["owner_decision_pack"]["approved_decision_count"],
            0,
        ),
        "profile_target_entity_count": (
            summaries["profile_target_contract"]["entity_count"],
            3,
        ),
        "read_model_target_projection_count": (
            summaries["read_model_target_contract"]["projection_count"],
            4,
        ),
        "staging_target_entity_count": (
            summaries["staging_target_contract"]["entity_count"],
            4,
        ),
        "state_machine_target_state_count": (
            summaries["state_machine_target_contract"]["lifecycle_state_count"],
            5,
        ),
        "command_envelope_target_command_count": (
            summaries["command_envelope_target_contract"]["command_contract_count"],
            5,
        ),
        "authenticated_uat_runbook_case_count": (
            summaries["authenticated_uat_runbook"]["covered_uat_case_count"],
            100,
        ),
        "discard_reconcile_header_mutation_call_count": (
            summaries["discard_cancel_boundary"]["discard_reconcile_header_mutation_call_count"],
            0,
        ),
        "runtime_fixture_available_count": (
            summaries["integrity_aggregates"]["runtime_fixture_available_count"],
            0,
        ),
        "type_alias_pair_with_observed_count_difference_count": (
            summaries["type_alias_aggregates"]["pair_with_observed_count_difference_count"],
            1,
        ),
        "unmatch_link_id_scope_column_count": (
            summaries["unmatch_sql_semantics"]["link_id_scope_column_count"],
            0,
        ),
        "synthetic_golden_case_count": (summaries["golden_cases"]["case_count"], 93),
        "identity_free_uat_case_count": (
            summaries["role_uat"]["synthetic_uat_case_count"],
            100,
        ),
        "authenticated_uat_execution_count": (
            summaries["role_uat"]["authenticated_uat_execution_count"],
            0,
        ),
        "resolved_root_count": (
            summaries["root_closure"]["resolved_by_static_evidence_count"],
            0,
        ),
    }
    for name, (actual, expected) in expected_facts.items():
        if actual != expected:
            validation_errors.append(f"{name}: expected {expected}, got {actual}")
    if invalid_inputs:
        validation_errors.append("invalid input artifacts: " + ", ".join(invalid_inputs))

    dimensions = [
        {
            "id": "legacy_source_and_read_model",
            "status": "TARGET_READ_MODEL_CONTRACT_READY_RUNTIME_PARITY_PENDING",
            "proven": [
                "15 required clone catalog tables are present",
                "keys, typed links, columns and dependencies are cataloged without business values",
                "4 target projections, 5 scoped query contracts and 16 acceptance obligations are defined",
            ],
            "not_proven": ["runtime row-result parity for the target read model"],
        },
        {
            "id": "statement_import_and_staging",
            "status": "TARGET_STAGING_CONTRACT_READY_IMPLEMENTATION_PENDING",
            "proven": [
                "legacy DBF/TXT/XLS dispatch and parser boundary are statically mapped",
                "header/detail persistence and optional hook presence are cataloged",
                "six canonical columns, row mapping, unsafe dedup and partial-commit control flow are mapped",
                "4 target staging entities, 8 pipeline stages and atomic commit invariants are defined",
            ],
            "not_proven": ["real approved profile row parity", "safe target parser implementation"],
        },
        {
            "id": "profile_versioning",
            "status": "TARGET_PROFILE_CONTRACT_READY_REAL_PARITY_PENDING",
            "proven": [
                "runtime profile projection and dispatch fields are known",
                "3 target entities, immutable versions, approval lifecycle and typed mappings are defined",
            ],
            "not_proven": [
                "any real profile row: clone snapshot contains zero rows",
                "owner-approved real values for version, effective-date, active and approval semantics",
            ],
        },
        {
            "id": "session_summary",
            "status": "TARGET_READ_MODEL_FORMULA_CONTRACT_READY_RUNTIME_PARITY_PENDING",
            "proven": [
                "summary procedure signature has 3 inputs and 11 money outputs",
                "all 11 signed outputs are mapped to exact UI labels and presentation behavior",
                "all 11 formulas and six Type/Status predicates are parsed from the redacted clone definition",
                "clone aggregate counts show RCASHDRAFT rows while the Summary spelling RCASHDRAF has none",
                "signed-decimal API and presentation separation are defined in the target read model",
            ],
            "not_proven": ["target row-result parity and two misspelled Type alias behaviors"],
        },
        {
            "id": "match_and_unmatch",
            "status": "COMMAND_ENVELOPE_READY_EXECUTION_BLOCKED",
            "proven": [
                "6 explicit typed source-to-link mappings are known",
                "unmatch procedure signature and dependency are cataloged",
                "legacy unmatch deletes all links by BankBillId and resets no instrument flag",
                "target Match and Unmatch have distinct capabilities, states, request fields and atomic envelopes",
            ],
            "not_proven": ["owner-approved amount tolerance", "idempotent target command behavior"],
        },
        {
            "id": "confirm_transaction_and_cardex",
            "status": "COMMAND_ENVELOPE_READY_IMPLEMENTATION_AND_FAILURE_INJECTION_PENDING",
            "proven": [
                "legacy nested transaction behavior is statically bounded",
                "cardex procedure signature and dependencies are cataloged",
                "confirmation markers are ConfirmerId and ConfirmDate",
                "current cardex procedure returns after at most one unordered typed link update",
                "outer DoAccept commits markers when that first update returns ErrorNo zero",
                "target Confirm envelope requires all-link prevalidation and one transaction with audit/outbox",
            ],
            "not_proven": [
                "target transaction owner implementation",
                "rollback and concurrency behavior",
                "a computed reconciliation amount: legacy confirmation sets Amount to zero",
            ],
        },
        {
            "id": "authorization_and_sod",
            "status": "DESIGN_ONLY_AUTHENTICATED_UAT_PENDING",
            "proven": ["7 target capabilities, 6 synthetic roles and 100 identity-free cases exist, including a distinct confirmed-session reversal capability"],
            "not_proven": ["any authenticated allow or deny decision", "process-owner role approval"],
        },
        {
            "id": "cancel_or_reverse",
            "status": "STATE_AND_COMMAND_CONTRACT_READY_OWNER_SEMANTICS_BLOCKED",
            "proven": [
                "no legacy session-cancel command was observed",
                "target Cancel and Reverse have separate states, capabilities, SoD and decision gates",
            ],
            "not_proven": ["cancel versus reverse policy", "confirmed-session recovery transition"],
        },
        {
            "id": "unresolved_entrypoints",
            "status": "RUNTIME_OR_OWNER_EVIDENCE_REQUIRED",
            "proven": ["all 3 roots have explicit non-inference classifications"],
            "not_proven": ["launcher for setup", "queue semantics", "SpecialOptionsDistrict purpose"],
        },
    ]

    slices = [
        {
            "order": 1,
            "id": "profile_catalog_and_read_only_queries",
            "allowed_now": True,
            "exit_gate": "approved profile fixtures plus scoped row-result parity",
        },
        {
            "order": 2,
            "id": "isolated_upload_parser_and_staging",
            "allowed_now": True,
            "exit_gate": "typed parser, content validation, no raw SQL/path/provider execution",
        },
        {
            "order": 3,
            "id": "session_read_model_and_summary",
            "allowed_now": True,
            "exit_gate": "11-output formula and row-result parity approved",
        },
        {
            "order": 4,
            "id": "idempotent_match_and_unmatch",
            "allowed_now": False,
            "exit_gate": "amount tolerance, expected-version and replay tests approved",
        },
        {
            "order": 5,
            "id": "confirm_transaction_and_cardex",
            "allowed_now": False,
            "exit_gate": "single target transaction owner and failure-injection suite pass",
        },
        {
            "order": 6,
            "id": "cancel_or_compensating_reversal",
            "allowed_now": False,
            "exit_gate": "process owner approves semantics, states and audit obligations",
        },
    ]

    hard_pilot_gates = [
        "real versioned and approved bank profile fixtures exist",
        "statement row and diagnostic parity is approved",
        "runtime row-result parity for all 11 static formulas is approved",
        "amount comparison tolerance is owner approved",
        "authenticated allow and deny UAT passes for each capability",
        "transaction failure injection proves zero partial persistence",
        "cancel or compensating reversal semantics are owner approved",
        "three unresolved roots receive runtime or owner evidence without identity/business-value capture",
    ]
    definition_of_done = [
        "every command is server-authorized by capability, feature, fiscal/DC/account scope, operation date, state and domain validation",
        "all mutations require expected version and idempotency key",
        "import parsing runs in isolated staging and cannot execute profile-supplied SQL, provider or path",
        "confirm owns one target transaction and rolls back header, links and cardex together",
        "audit records command, aggregate, reason, before/after state and correlation without credentials or raw business payloads",
        "golden, negative, replay, concurrency and failure-injection cases pass",
        "authenticated UAT and process-owner signoff are recorded before pilot",
        "source Varanegar remains read-only throughout discovery and parity comparison",
    ]

    static_method_contract_count = sum(
        summaries[name].get("selected_method_contract_count", 0)
        for name in (
            "command_guards",
            "import_boundary",
            "persistence_boundary",
            "transaction_boundary",
            "matching_boundary",
            "profile_state_boundary",
        )
    )
    static_method_contract_count += summaries["summary_ui_boundary"]["selected_method_count"]
    summary = {
        "input_artifact_count": len(inputs),
        "validated_input_artifact_count": len(inputs) - len(invalid_inputs),
        "readiness_dimension_count": len(dimensions),
        "static_method_contract_count": static_method_contract_count,
        "source_contract_table_count": summaries["source_model"]["found_table_count"],
        "typed_match_reference_mapping_count": summaries["matching_boundary"]["typed_reference_mapping_count"],
        "summary_parameter_count": summaries["matching_boundary"]["summary_parameter_count"],
        "summary_output_to_ui_mapping_count": summaries["summary_ui_boundary"]["output_to_label_mapping_count"],
        "summary_static_formula_metric_count": summaries["summary_sql_semantics"]["output_metric_count"],
        "summary_type_literal_alias_risk_count": summaries["summary_sql_semantics"]["type_literal_alias_risk_count"],
        "clone_type_alias_pair_with_observed_count_difference_count": summaries["type_alias_aggregates"]["pair_with_observed_count_difference_count"],
        "clone_alias_summary_literal_total_count": summaries["type_alias_aggregates"]["summary_literal_total_count"],
        "clone_alias_matching_literal_total_count": summaries["type_alias_aggregates"]["matching_literal_total_count"],
        "clone_short_literal_catalog_consumer_count": summaries["type_alias_aggregates"]["short_literal_catalog_consumer_count"],
        "clone_canonical_literal_catalog_consumer_count": summaries["type_alias_aggregates"]["canonical_literal_catalog_consumer_count"],
        "clone_alias_family_with_short_summary_outlier_count": summaries["type_alias_aggregates"]["alias_family_with_short_summary_outlier_count"],
        "parser_canonical_input_column_count": summaries["parser_row_contract"]["canonical_input_column_count"],
        "legacy_profile_sqlstatement_executing_parser_count": summaries["parser_row_contract"]["profile_sqlstatement_executing_parser_count"],
        "legacy_parser_consuming_hdr_argument_count": summaries["parser_row_contract"]["parser_consuming_hdr_argument_count"],
        "legacy_confirm_maximum_typed_link_updates_per_execution": summaries["confirm_cardex_semantics"]["maximum_typed_link_updates_per_execution"],
        "legacy_confirm_unordered_cursor_count": summaries["confirm_cardex_semantics"]["unordered_cursor_count"],
        "legacy_confirm_permission_or_operation_date_call_count": summaries["confirm_orchestration"]["confirm_permission_or_operation_date_call_count"],
        "differential_acceptance_case_count": summaries["differential_acceptance"]["differential_acceptance_case_count"],
        "executed_differential_acceptance_case_count": summaries["differential_acceptance"]["executed_case_count"],
        "owner_decision_register_count": summaries["owner_decision_pack"]["decision_register_count"],
        "approved_owner_decision_count": summaries["owner_decision_pack"]["approved_decision_count"],
        "profile_target_entity_count": summaries["profile_target_contract"]["entity_count"],
        "profile_target_command_contract_count": summaries["profile_target_contract"]["command_contract_count"],
        "read_model_target_projection_count": summaries["read_model_target_contract"]["projection_count"],
        "read_model_target_query_contract_count": summaries["read_model_target_contract"]["query_contract_count"],
        "staging_target_entity_count": summaries["staging_target_contract"]["entity_count"],
        "staging_target_pipeline_stage_count": summaries["staging_target_contract"]["pipeline_stage_count"],
        "state_machine_target_state_count": summaries["state_machine_target_contract"]["lifecycle_state_count"],
        "state_machine_target_transition_count": summaries["state_machine_target_contract"]["transition_contract_count"],
        "command_envelope_target_command_count": summaries["command_envelope_target_contract"]["command_contract_count"],
        "command_envelope_stable_error_count": summaries["command_envelope_target_contract"]["stable_error_code_count"],
        "authenticated_uat_runbook_case_count": summaries["authenticated_uat_runbook"]["covered_uat_case_count"],
        "provisioned_uat_test_account_count": summaries["authenticated_uat_runbook"]["provisioned_test_account_count"],
        "legacy_unmatch_link_id_scope_column_count": summaries["unmatch_sql_semantics"]["link_id_scope_column_count"],
        "legacy_unmatch_instrument_update_statement_count": summaries["unmatch_sql_semantics"]["instrument_update_statement_count"],
        "legacy_discard_reconcile_header_mutation_call_count": summaries["discard_cancel_boundary"]["discard_reconcile_header_mutation_call_count"],
        "current_clone_runtime_fixture_available_count": summaries["integrity_aggregates"]["runtime_fixture_available_count"],
        "synthetic_golden_case_count": summaries["golden_cases"]["case_count"],
        "identity_free_uat_case_count": summaries["role_uat"]["synthetic_uat_case_count"],
        "real_profile_row_snapshot_count": summaries["profile_state_boundary"]["profile_table_row_count_snapshot"],
        "authenticated_uat_execution_count": summaries["role_uat"]["authenticated_uat_execution_count"],
        "owner_approved_case_count": summaries["role_uat"]["owner_approved_case_count"],
        "resolved_root_count": summaries["root_closure"]["resolved_by_static_evidence_count"],
        "target_command_execution_count": 0,
        "implementation_slice_count": len(slices),
        "currently_allowed_implementation_slice_count": sum(row["allowed_now"] for row in slices),
        "hard_pilot_gate_count": len(hard_pilot_gates),
        "validation_error_count": len(validation_errors),
    }

    artifact = {
        "artifact": "negin_erp_bank_reconciliation_evidence_backed_implementation_readiness_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "status": "DESIGN_READY_FOR_FIRST_THREE_READ_SIDE_SLICES_NOT_READY_FOR_COMMAND_PILOT",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_row_values_read": 0,
            "identity_or_membership_values_read": 0,
        },
        "summary": summary,
        "readiness_decision": {
            "start_target_schema_and_read_only_profile_catalog": True,
            "start_isolated_parser_staging": True,
            "start_session_read_model_summary_candidate": True,
            "start_match_unmatch_confirm_commands": False,
            "start_pilot": False,
            "start_production": False,
            "reason": "static contracts and redacted formulas are strong enough for bounded read-side foundations, while runtime parity, authenticated UAT, transaction implementation and owner decisions remain open",
        },
        "readiness_dimensions": dimensions,
        "ordered_implementation_slices": slices,
        "hard_pilot_gates": hard_pilot_gates,
        "definition_of_done": definition_of_done,
        "non_inference_rules": [
            "static call evidence does not prove runtime result parity",
            "zero clone profile rows do not prove production has no profiles",
            "legacy Edit does not grant target Confirm and legacy Delete does not grant target Cancel",
            "aggregate permission counts do not prove an individual allow",
            "Amount set to zero is not a computed reconciliation result",
            "RBANKDARFT and RCASHDRAF are observed Summary literals and are not silently normalized to matching discriminators",
            "loaded profile columns are not treated as active when the parser never consumes them",
            "legacy duplicate suppression is not copied as a safe idempotency key",
            "legacy parity does not mean reproducing the confirm procedure one-link early-return defect",
            "a committed confirmer marker does not prove every linked instrument was marked reconciled",
            "deleting all ReconcileItem rows by BankBillId is not a confirmed-session reversal",
            "a misleading form name does not create a queue, route or command",
        ],
        "source_evidence": [
            {
                "name": name,
                "path": str(paths[name]).replace("\\", "/"),
                "artifact": inputs[name]["artifact"],
                "validation": inputs[name]["validation"],
            }
            for name in INPUT_NAMES
        ],
        "validation_errors": validation_errors,
        "limits": [
            "No Varanegar or NGT database connection was opened by this builder.",
            "No target bank-reconciliation implementation exists in this artifact.",
            "No authenticated UAT, process-owner approval, pilot or production execution is claimed.",
            "Clone catalog snapshots and static IL evidence can drift and require controlled refresh.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
