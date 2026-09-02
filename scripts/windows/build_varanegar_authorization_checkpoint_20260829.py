"""Build an offline hash-pinned checkpoint for NGT authorization evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "runtime_artifact": "artifacts/varanegar_analysis/domains/ngt_authorization_runtime_boundary_20260828.json",
    "endpoint_artifact": "artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json",
    "manual_guard_artifact": "artifacts/varanegar_analysis/domains/ngt_authorization_manual_guard_boundary_20260829.json",
    "role_short_circuit_artifact": "artifacts/varanegar_analysis/domains/ngt_authorization_role_short_circuit_20260829.json",
    "effective_artifact": "artifacts/varanegar_analysis/domains/ngt_authorization_effective_boundary_20260828.json",
    "owner_scope_runtime_artifact": "artifacts/varanegar_analysis/domains/ngt_owner_scope_runtime_boundary_20260829.json",
    "owner_scope_repository_artifact": "artifacts/varanegar_analysis/domains/ngt_owner_scope_repository_boundary_20260829.json",
    "owner_scope_effective_artifact": "artifacts/varanegar_analysis/domains/ngt_owner_scope_effective_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "runtime_extractor": "scripts/windows/extract_varanegar_ngt_authorization_runtime_boundary.py",
    "endpoint_extractor": "scripts/windows/extract_varanegar_ngt_authorization_endpoint_coverage.py",
    "manual_guard_extractor": "scripts/windows/extract_varanegar_ngt_authorization_manual_guard_boundary.py",
    "role_short_circuit_extractor": "scripts/windows/extract_varanegar_ngt_authorization_role_short_circuit.py",
    "effective_extractor": "scripts/sql/extract_varanegar_ngt_authorization_effective_boundary.py",
    "owner_scope_runtime_extractor": "scripts/windows/extract_varanegar_ngt_owner_scope_runtime_boundary.py",
    "owner_scope_repository_extractor": "scripts/windows/extract_varanegar_ngt_owner_scope_repository_boundary.py",
    "owner_scope_effective_extractor": "scripts/sql/extract_varanegar_ngt_owner_scope_effective_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "domain_doc": "docs/varanegar_reconstruction/domains/16_AUTHORIZATION_LEGACY_AND_NGT_FA.md",
    "risk_delta_doc": "docs/varanegar_reconstruction/AUTHORIZATION_RISK_DELTA_20260829_FA.md",
    "owner_scope_doc": "docs/varanegar_reconstruction/NGT_OWNER_SCOPE_RUNTIME_AND_EFFECTIVE_BOUNDARY_20260829_FA.md",
    "checkpoint_doc": "docs/varanegar_reconstruction/CHECKPOINT_20260829_AUTHORIZATION_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "authorization_tests": "tests/test_varanegar_ngt_authorization_effective_boundary.py",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    runtime = _load("runtime_artifact")
    endpoint = _load("endpoint_artifact")
    manual = _load("manual_guard_artifact")
    role = _load("role_short_circuit_artifact")
    effective = _load("effective_artifact")
    owner_runtime = _load("owner_scope_runtime_artifact")
    owner_repository = _load("owner_scope_repository_artifact")
    owner_effective = _load("owner_scope_effective_artifact")
    risks = _load("risk_register")
    trace = _load("traceability")
    runtime_sha = _sha(ROOT / SOURCES["runtime_artifact"])
    endpoint_sha = _sha(ROOT / SOURCES["endpoint_artifact"])
    manual_sha = _sha(ROOT / SOURCES["manual_guard_artifact"])
    role_sha = _sha(ROOT / SOURCES["role_short_circuit_artifact"])
    owner_runtime_sha = _sha(ROOT / SOURCES["owner_scope_runtime_artifact"])
    owner_repository_sha = _sha(ROOT / SOURCES["owner_scope_repository_artifact"])

    checks = {
        "runtime_static_only": runtime["safety"]["assemblies_loaded_or_executed"] == 0,
        "runtime_all_assemblies_analyzed": runtime["summary"]["analyzed_file_count"] == 8
        and runtime["summary"]["failed_file_count"] == 0,
        "runtime_grant_one_filter": runtime["summary"]["runtime_guard_direct_query_grant_value"] == 1,
        "runtime_group_delegates_to_filtered_query": runtime["summary"]["runtime_guard_group_query_delegates_to_grant_filtered_direct_query"] is True,
        "runtime_action_normalization_exact": runtime["summary"]["runtime_guard_action_contract_is_comma_split_exact_membership"] is True,
        "runtime_negative_one_veto": runtime["summary"]["runtime_guard_post_union_veto_grant_value"] == -1,
        "runtime_catalog_not_direct": runtime["summary"]["runtime_guard_catalog_named_call_count"] == 0,
        "runtime_catalog_materializes_atomic": runtime["summary"]["catalog_save_materializes_atomic_permission_rows"] is True,
        "endpoint_static_only": endpoint["safety"]["assemblies_loaded_or_executed"] == 0,
        "endpoint_attributes_parse_clean": endpoint["summary"]["custom_attribute_parse_failure_count"] == 0,
        "endpoint_count_784": endpoint["summary"]["attribute_declared_endpoint_count"] == 784,
        "endpoint_ngt_count_595": endpoint["summary"]["endpoint_with_ngt_authorize_count"] == 595,
        "endpoint_declaration_gap_60": endpoint["summary"]["endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"] == 60,
        "endpoint_mutating_gap_38": endpoint["summary"]["mutating_endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"] == 38,
        "endpoint_no_explicit_bypass": endpoint["summary"]["endpoint_with_bypass_authorization_count"] == 0,
        "startup_no_named_global_authorizer": endpoint["startup_global_filter_contract"]["authorization_named_constructor_count"] == 0,
        "manual_static_only": manual["safety"]["assemblies_loaded_or_executed"] == 0,
        "manual_body_scan_clean": manual["summary"]["body_error_count"] == 0,
        "manual_all_60_scanned": manual["summary"]["selected_declaration_gap_endpoint_count"] == 60,
        "manual_async_43_followed": manual["summary"]["async_state_machine_followed_count"] == 43,
        "manual_named_decision_zero": manual["summary"]["endpoint_with_manual_authorization_decision_candidate_count"] == 0,
        "role_static_only": role["safety"]["assemblies_loaded_or_executed"] == 0,
        "role_admin_short_circuit": role["summary"]["admin_role_short_circuits_base_authorization"] is True,
        "role_non_admin_base_path": role["summary"]["non_admin_delegates_to_base_authorization"] is True,
        "role_explicit_bypass_zero": role["summary"]["explicit_endpoint_bypass_declaration_count"] == 0,
        "effective_clone_read_only": effective["safety"]["updateability"] == "READ_ONLY"
        and effective["safety"]["can_update"] == 0
        and effective["safety"]["denies_data_writes"] == 1,
        "effective_no_operational_execution": effective["safety"]["operational_procedures_executed"] == 0
        and effective["safety"]["assemblies_loaded_or_executed"] == 0,
        "effective_catalog_parity": effective["summary"]["catalog_direct_link_expansion_fully_matches_atomic_direction"] is True,
        "effective_catalog_gap_3": effective["summary"]["resource_action_contract_absent_from_all_application_owners_count"] == 3,
        "effective_admin_subject_aggregate_3": effective["summary"]["admin_role_current_assignment_subject_count"] == 3,
        "effective_runtime_coverage_not_overclaimed": effective["summary"]["runtime_endpoint_coverage_proven"] is False,
        "effective_legacy_crosswalk_not_overclaimed": effective["summary"]["legacy_to_ngt_crosswalk_proven"] is False,
        "effective_runtime_hash_link": effective["runtime_evidence"]["artifact_sha256"] == runtime_sha,
        "effective_endpoint_hash_link": effective["runtime_evidence"]["endpoint_artifact_sha256"] == endpoint_sha,
        "effective_manual_hash_link": effective["runtime_evidence"]["manual_guard_artifact_sha256"] == manual_sha,
        "effective_role_hash_link": effective["runtime_evidence"]["role_short_circuit_artifact_sha256"] == role_sha,
        "manual_endpoint_hash_link": manual["source"]["endpoint_artifact_sha256"] == endpoint_sha,
        "role_endpoint_hash_link": role["source"]["endpoint_artifact_sha256"] == endpoint_sha,
        "risk_register_pass": risks["validation"] == "PASS",
        "owner_runtime_static_only": owner_runtime["safety"]["assemblies_loaded_or_executed"] == 0,
        "owner_runtime_scope_body_clean": owner_runtime["summary"]["scope_named_method_body_error_count"] == 0,
        "owner_runtime_fallback_chain": owner_runtime["summary"]["header_fallback_chain_is_center_to_data_owner_to_owner"] is True,
        "owner_runtime_guid_headers": owner_runtime["summary"]["header_values_are_parsed_as_guid"] is True,
        "owner_runtime_single_key_fanout": owner_runtime["summary"]["authorization_domain_one_parameter_constructor_repeats_one_key_three_times"] is True,
        "owner_runtime_guard_owner_only": owner_runtime["summary"]["web_permission_guard_reads_owner_key_but_not_data_owner_headers"] is True,
        "owner_repository_static_only": owner_repository["safety"]["assemblies_loaded_or_executed"] == 0,
        "owner_repository_target_bodies_clean": owner_repository["summary"]["target_method_body_error_count"] == 0,
        "owner_repository_raw_query": owner_repository["summary"]["base_get_query_returns_raw_dbset"] is True,
        "owner_repository_filtered_query_separate": owner_repository["summary"]["get_query_by_owner_applies_calc_extra_predict"] is True,
        "owner_repository_permission_calls_raw": owner_repository["summary"]["authorization_permission_queries_call_raw_get_query"] is True,
        "owner_repository_permission_path_not_owner_filtered": owner_repository["summary"]["authorization_permission_query_uses_owner_filtered_repository_path"] is False,
        "owner_effective_clone_read_only": owner_effective["safety"]["updateability"] == "READ_ONLY"
        and owner_effective["safety"]["can_update"] == 0
        and owner_effective["safety"]["denies_data_writes"] == 1,
        "owner_effective_no_operational_execution": owner_effective["safety"]["operational_procedures_executed"] == 0
        and owner_effective["safety"]["write_statements_executed"] == 0,
        "owner_effective_grant_one_324": owner_effective["permission_application_scope"]["grant_one_rows_with_complete_application_chain"] == 324,
        "owner_effective_cross_application_zero": owner_effective["summary"]["cross_application_grant_one_row_count"] == 0
        and owner_effective["summary"]["active_group_expansion_application_mismatch_count"] == 0,
        "owner_effective_membership_group_scope": owner_effective["user_group_scope_consistency"]["membership_group_scope_mismatch"] == 0
        and owner_effective["user_group_scope_consistency"]["membership_user_scope_mismatch"] == 58,
        "owner_effective_default_center_fallback": owner_effective["summary"]["data_owner_to_center_fallback_resolves_default_center_count"] == 1
        and owner_effective["summary"]["header_fallback_same_key_resolves_valid_full_hierarchy"] is False,
        "owner_runtime_hash_link": owner_repository["source"]["runtime_scope_artifact_sha256"] == owner_runtime_sha,
        "owner_repository_hash_link": owner_effective["source"]["repository_scope_artifact_sha256"] == owner_repository_sha,
        "owner_effective_runtime_hash_link": owner_effective["source"]["runtime_scope_artifact_sha256"] == owner_runtime_sha,
        "risk_count_81": risks["summary"]["risk_count"] == 84,
        "critical_risk_count_47": risks["summary"]["critical_count"] == 50,
        "risk_057_present": any(row["id"] == "R-057" for row in risks["risks"]),
        "risk_058_present": any(row["id"] == "R-058" for row in risks["risks"]),
        "risk_059_present": any(row["id"] == "R-059" for row in risks["risks"]),
        "risk_060_present": any(row["id"] == "R-060" for row in risks["risks"]),
        "risk_061_present": any(row["id"] == "R-061" for row in risks["risks"]),
        "traceability_pass": trace["validation"] == "PASS",
        "traceability_assignment_328": trace["summary"]["mapped_risk_assignment_count"] == 343,
        "traceability_unique_risk_81": trace["summary"]["unique_risk_count"] == 84,
        "command_ready_zero": trace["summary"]["command_ready_module_count"] == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest = [
        {
            "name": name,
            "path": relative.replace("\\", "/"),
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_authorization_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "business_rows_or_identity_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "authorization_endpoint_count": endpoint["summary"]["attribute_declared_endpoint_count"],
            "authorization_declaration_gap_count": endpoint["summary"]["endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"],
            "mutating_authorization_declaration_gap_count": endpoint["summary"]["mutating_endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"],
            "admin_assignment_subject_aggregate_count": effective["summary"]["admin_role_current_assignment_subject_count"],
            "owner_scope_membership_user_mismatch_count": owner_effective["user_group_scope_consistency"]["membership_user_scope_mismatch"],
            "cross_application_effective_grant_count": owner_effective["summary"]["cross_application_grant_one_row_count"],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
