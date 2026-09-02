"""Build the Discount V2 engine and dynamic-rule checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "engine": "artifacts/varanegar_analysis/domains/discount_v2_engine_runtime_20260829.json",
    "sql": "artifacts/varanegar_analysis/domains/discount_v2_dynamic_rule_sql_20260829.json",
    "families": "artifacts/varanegar_analysis/domains/discount_v2_condition_families_20260829.json",
    "authoring": "artifacts/varanegar_analysis/domains/discount_rule_authoring_boundary_20260829.json",
    "authorization": "artifacts/varanegar_analysis/domains/discount_rule_authorization_boundary_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_discount_v2_query_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "engine_extractor": "scripts/windows/extract_varanegar_discount_v2_engine_runtime.py",
    "sql_extractor": "scripts/sql/extract_varanegar_discount_v2_dynamic_rule_sql.py",
    "family_extractor": "scripts/sql/extract_varanegar_discount_v2_condition_families.py",
    "authoring_extractor": "scripts/windows/extract_varanegar_discount_rule_authoring_boundary.py",
    "authorization_extractor": "scripts/sql/extract_varanegar_discount_rule_authorization_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_discount_v2_engine_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_discount_v2_engine_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/DISCOUNT_V2_ENGINE_PIPELINE_AND_DYNAMIC_RULE_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    engine, sql, families, authoring, authorization, previous, risks, trace = (
        _load(name) for name in ("engine", "sql", "families", "authoring", "authorization", "previous_checkpoint", "risk_register", "traceability")
    )
    r079 = next(row for row in risks["risks"] if row["id"] == "R-079")
    checks = {
        "static_engine_pipeline_passes": engine["validation"] == "PASS"
        and engine["summary"]["engine_assembly_count"] == 3
        and engine["summary"]["managed_method_count"] == 7156
        and engine["summary"]["selected_method_count"] == 22
        and engine["summary"]["sds_per_candidate_dynamic_query_loop_count"] == 1
        and engine["summary"]["sds_injected_context_preference_count"] == 1
        and engine["safety"]["assembly_loads_or_executions"] == 0,
        "dynamic_executor_contract_is_proven": engine["summary"]["dynamic_rule_executor_count"] == 2
        and engine["assertions"]["advanced_condition_uses_sp_executesql_with_parameters"],
        "read_only_rule_profile_passes": sql["validation"] == "PASS"
        and sql["summary"]["primary_nonempty_condition_count"] == 845
        and sql["summary"]["primary_distinct_condition_hash_count"] == 44
        and sql["safety"]["data_mutations"] == 0,
        "current_rule_text_shape_is_bounded": sql["summary"]["primary_write_dml_shape_count"] == 0
        and sql["summary"]["primary_ddl_or_permission_shape_count"] == 0
        and sql["summary"]["primary_external_or_delay_shape_count"] == 0,
        "raw_rule_text_and_ids_are_absent": sql["safety"]["raw_conditions_persisted"] == 0
        and sql["safety"]["row_identifiers_persisted"] == 0,
        "condition_family_usage_is_sanitized_and_bounded": families["validation"] == "PASS"
        and families["summary"]["condition_family_count"] == 44
        and families["summary"]["three_month_used_condition_family_count"] == 2
        and families["summary"]["three_month_advanced_condition_applied_row_count"] == 471
        and families["summary"]["current_effective_rule_instance_count"] == 57
        and families["summary"]["current_effective_condition_family_count"] == 16
        and families["safety"]["raw_conditions_persisted"] == 0,
        "rule_authoring_and_execution_validation_path_is_proven": authoring["validation"] == "PASS"
        and authoring["summary"]["selected_method_count"] == 32
        and authoring["summary"]["selected_sql_condition_setter_method_count"] == 2
        and authoring["summary"]["validation_adapter_dynamic_execute_count"] == 4
        and authoring["summary"]["discount_specific_method_local_authorization_reference_count"] == 0
        and authoring["summary"]["internal_command_permission_recheck_count"] == 0
        and authoring["summary"]["session_permission_lookup_database_call_count"] == 0
        and authoring["summary"]["base_permission_allowlisted_keys"] == ["Delete", "Edit", "New", "Print"]
        and authoring["authorization_interpretation"]["permission_lookup_source"] == "IN_MEMORY_USER_PERMISSION_SNAPSHOT"
        and authoring["authorization_interpretation"]["base_form_toolbar_permission_gate_proven"]
        and not authoring["authorization_interpretation"]["internal_command_permission_recheck_proven"]
        and not authoring["authorization_interpretation"]["separate_save_permission_key_in_selected_list_base_proven"]
        and authoring["safety"]["dynamic_conditions_executed"] == 0,
        "rule_authorization_has_crud_nodes_but_no_review_publish_split": authorization["validation"] == "PASS"
        and authorization["summary"]["root_access_node_id"] == 404
        and authorization["summary"]["command_node_count"] == 4
        and authorization["summary"]["command_effective_allow_counts"] == {"Delete": 15, "Edit": 15, "New": 15, "View": 15}
        and authorization["interpretation"]["separate_view_new_edit_delete_nodes_proven"]
        and not authorization["interpretation"]["separate_review_or_publish_node_proven"]
        and authorization["safety"]["write_statements_executed"] == 0,
        "r079_integrates_engine_evidence_without_inflation": (ROOT / SOURCES["engine"]).as_posix()
        in r079["evidence_refs"]
        and (ROOT / SOURCES["sql"]).as_posix() in r079["evidence_refs"]
        and (ROOT / SOURCES["families"]).as_posix() in r079["evidence_refs"]
        and (ROOT / SOURCES["authoring"]).as_posix() in r079["evidence_refs"]
        and (ROOT / SOURCES["authorization"]).as_posix() in r079["evidence_refs"]
        and "44 distinct hashes" in r079["failure_mode"]
        and risks["summary"]["risk_count"] == 84,
        "metrics_and_chain_pass": previous["validation"] == "PASS"
        and risks["source_checkpoint"]["discount_v2_engine_managed_method_count"] == 7156
        and risks["source_checkpoint"]["discount_v2_distinct_condition_hash_count"] == 44
        and risks["source_checkpoint"]["discount_v2_three_month_used_condition_family_count"] == 2
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest = [
        {
            "name": name,
            "path": path,
            "size_bytes": (ROOT / path).stat().st_size,
            "sha256": _sha(ROOT / path),
        }
        for name, path in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_discount_v2_engine_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_STATIC_AND_READ_ONLY_AGGREGATE_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "engine_method_count": engine["summary"]["managed_method_count"],
            "advanced_condition_count": sql["summary"]["primary_nonempty_condition_count"],
            "distinct_condition_hash_count": sql["summary"]["primary_distinct_condition_hash_count"],
            "three_month_used_condition_family_count": families["summary"]["three_month_used_condition_family_count"],
            "three_month_advanced_applied_row_count": families["summary"]["three_month_advanced_condition_applied_row_count"],
            "authoring_selected_method_count": authoring["summary"]["selected_method_count"],
            "authoring_dynamic_validation_execute_count": authoring["summary"]["validation_adapter_dynamic_execute_count"],
            "authoring_permission_lookup_database_call_count": authoring["summary"]["session_permission_lookup_database_call_count"],
            "authorization_command_node_count": authorization["summary"]["command_node_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
