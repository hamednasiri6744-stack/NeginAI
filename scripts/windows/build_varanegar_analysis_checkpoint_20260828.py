"""Build the offline Varanegar 2026-08-28 analysis checkpoint.

The builder reads only persisted, redacted project evidence. It does not connect
to Varanegar, SQL Server, network shares, or the live UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "voucher_policy": "artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json",
    "replication_transport": "artifacts/varanegar_analysis/domains/rule_replication_transport_boundary_20260828.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260827.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260827.json",
    "voucher_extractor": "scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py",
    "replication_extractor": "scripts/sql/extract_varanegar_rule_replication_transport_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "traceability_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "voucher_tests": "tests/test_varanegar_voucher_creation_atomicity_policy.py",
    "replication_tests": "tests/test_varanegar_rule_replication_transport_boundary.py",
    "risk_trace_tests": "tests/test_varanegar_ui_evidence.py",
    "rule_publish_doc": "docs/varanegar_reconstruction/domains/24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md",
    "replication_doc": "docs/varanegar_reconstruction/domains/25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md",
    "risk_doc": "docs/varanegar_reconstruction/RISK_REGISTER_20260827_FA.md",
    "traceability_doc": "docs/varanegar_reconstruction/REQUIREMENTS_TRACEABILITY_MATRIX_20260827_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "checkpoint_builder": "scripts/windows/build_varanegar_analysis_checkpoint_20260828.py",
    "checkpoint_tests": "tests/test_varanegar_analysis_checkpoint_20260828.py",
    "checkpoint_doc": "docs/varanegar_reconstruction/CHECKPOINT_20260828_RULE_REPLICATION_FA.md",
    "reconstruction_readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    missing = [relative for relative in SOURCES.values() if not (ROOT / relative).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    voucher = _load_json("voucher_policy")
    replication = _load_json("replication_transport")
    risks = _load_json("risk_register")
    trace = _load_json("traceability")

    expected_artifacts = {
        "voucher_policy": "varanegar_voucher_creation_atomicity_and_policy_contract",
        "replication_transport": "varanegar_rule_replication_transport_boundary",
        "risk_register": "negin_personal_erp_evidence_backed_risk_register",
        "traceability": "negin_personal_erp_requirement_evidence_test_risk_traceability_matrix",
    }
    actual_artifacts = {
        name: payload["artifact"]
        for name, payload in {
            "voucher_policy": voucher,
            "replication_transport": replication,
            "risk_register": risks,
            "traceability": trace,
        }.items()
    }

    checks = {
        "artifact_identities_match": actual_artifacts == expected_artifacts,
        "voucher_hash_pinned_binary_count_is_7": len(
            voucher["deployed_call_and_transaction_contract"]["assembly_hashes"]
        )
        == 7,
        "voucher_desktop_transaction_boundary_proven": voucher[
            "deployed_call_and_transaction_contract"
        ]["business_boundary"]["transaction_mode_operand_before_context_ctor"]
        == 0
        and voucher["deployed_call_and_transaction_contract"]["business_boundary"][
            "dispose_is_in_finally"
        ],
        "voucher_server_transaction_not_overclaimed": voucher[
            "procedure_contracts"
        ]["dbo.usp_DoExternalVoucher"]["transaction_tokens"]["begin_transaction"]
        == 0,
        "voucher_historical_policy_reproducibility_not_overclaimed": voucher[
            "historical_grouping_policy_drift"
        ]["current_policy_fully_explains_history"]
        is False,
        "voucher_committed_source_snapshot_not_overclaimed": voucher[
            "dynamic_rule_sql_and_source_snapshot_profile"
        ]["deployed_sql_semantics"]["source_read_is_guaranteed_committed_consistent"]
        is False,
        "voucher_explicit_isolation_not_overclaimed": voucher[
            "transaction_isolation_and_source_version_profile"
        ]["summary"]["provider_explicit_isolation_level"]
        is False,
        "voucher_rule_editor_authority_not_overclaimed": voucher[
            "rule_configuration_write_authority_profile"
        ]["summary"]["configuration_write_authority_attributed_to_deployed_form"]
        is False,
        "voucher_template_publish_atomicity_not_overclaimed": voucher[
            "rule_configuration_write_authority_profile"
        ]["summary"]["template_transfer_procedure_with_transaction_count"]
        == 0,
        "voucher_template_schema_compatibility_not_overclaimed": voucher[
            "rule_replication_trigger_profile"
        ]["summary"]["template_article_dynamic_insert_schema_compatible"]
        is False,
        "voucher_rule_trigger_ident_current_impact_not_overclaimed": voucher[
            "rule_replication_trigger_profile"
        ]["summary"]["rule_trigger_control_flow_depends_on_returned_log_id"]
        is False,
        "voucher_binary_log_mapping_ident_current_boundary_frozen": voucher[
            "rule_replication_trigger_profile"
        ]["insert_to_log_global_output_boundary"][
            "binary_mapping_trigger_using_returned_ident_current_count"
        ]
        == 2
        and voucher["rule_replication_trigger_profile"][
            "insert_to_log_global_output_boundary"
        ]["binary_mapping_table_with_unique_index_count"]
        == 0
        and voucher["rule_replication_trigger_profile"][
            "insert_to_log_global_output_boundary"
        ]["concurrent_wrong_log_mapping_observed_in_snapshot"]
        is False
        and voucher["rule_replication_trigger_profile"][
            "insert_to_log_global_output_boundary"
        ]["binary_mapping_table_reader_module_count"]
        == 0
        and voucher["rule_configuration_write_authority_profile"][
            "summary"
        ]["application_binary_voucher_mapping_literal_site_count"]
        == 0,
        "voucher_global_replication_trigger_footprint_frozen": voucher[
            "rule_replication_trigger_profile"
        ]["insert_to_log_global_output_boundary"]["trigger_footprint"]
        == {
            "trigger_count": 1142,
            "parent_table_count": 376,
            "parent_schema_count": 6,
            "enabled_count": 1142,
            "not_for_replication_count": 0,
            "cursor_signal_count": 1140,
            "try_catch_count": 0,
            "xact_abort_count": 3,
        }
        and voucher["rule_replication_trigger_profile"][
            "insert_to_log_global_output_boundary"
        ]["trigger_event_counts"]
        == {"DELETE": 378, "INSERT": 384, "UPDATE": 384},
        "voucher_replication_trigger_schema_blast_radius_frozen": [
            (row["parent_schema"], row["trigger_count"], row["parent_table_count"])
            for row in voucher["rule_replication_trigger_profile"][
                "insert_to_log_global_output_boundary"
            ]["trigger_schema_footprint"]
        ]
        == [
            ("Acc", 53, 17),
            ("dbo", 426, 140),
            ("GNR", 321, 107),
            ("ICA", 15, 5),
            ("inv", 45, 15),
            ("SLE", 282, 92),
        ],
        "voucher_replication_trigger_event_shapes_frozen": [
            (
                row["has_insert"],
                row["has_update"],
                row["has_delete"],
                row["trigger_count"],
                row["cursor_signal_count"],
            )
            for row in voucher["rule_replication_trigger_profile"][
                "insert_to_log_global_output_boundary"
            ]["trigger_event_shapes"]
        ]
        == [
            (0, 0, 1, 376, 376),
            (0, 1, 0, 382, 382),
            (1, 0, 0, 382, 382),
            (1, 1, 1, 2, 0),
        ],
        "replication_hash_pinned_binary_count_is_4": replication["summary"][
            "hash_pinned_binary_count"
        ]
        == 4,
        "replication_outbox_proven": replication["summary"][
            "outbound_binary_outbox_proven"
        ]
        is True,
        "replication_receive_transaction_proven": replication["summary"][
            "receive_script_and_receipt_transaction_proven"
        ]
        is True,
        "replication_executor_failure_receipt_guard_proven": replication["summary"][
            "executor_failure_prevents_receive_receipt_proven"
        ]
        is True,
        "replication_receipt_idempotency_not_overclaimed": replication["summary"][
            "replication_receipt_idempotency_proven"
        ]
        is False,
        "replication_content_authentication_not_overclaimed": replication["summary"][
            "replication_package_content_authentication_proven"
        ]
        is False,
        "replication_rollback_observability_not_overclaimed": replication["summary"][
            "rollback_failure_observability_proven"
        ]
        is False,
        "replication_cleanup_recovery_not_overclaimed": replication["summary"][
            "receive_cleanup_recoverable_after_commit_failure_proven"
        ]
        is False,
        "replication_periodic_single_flight_not_overclaimed": replication[
            "summary"
        ]["periodic_service_single_flight_proven"]
        is False,
        "replication_package_deadline_not_overclaimed": replication["summary"][
            "bounded_package_execution_deadline_proven"
        ]
        is False,
        "replication_rejection_quarantine_not_overclaimed": replication[
            "summary"
        ]["rejected_package_quarantine_and_retry_safety_proven"]
        is False,
        "risk_register_valid": risks["validation"] == "PASS",
        "risk_count_is_56": risks["summary"]["risk_count"] == 56,
        "critical_risk_count_is_31": risks["summary"]["critical_count"] == 31,
        "traceability_valid": trace["validation"] == "PASS",
        "traceability_assignment_count_is_221": trace["summary"][
            "mapped_risk_assignment_count"
        ]
        == 221,
        "traceability_unique_risk_count_is_56": trace["summary"][
            "unique_risk_count"
        ]
        == 56,
        "command_ready_module_count_is_zero": trace["summary"][
            "command_ready_module_count"
        ]
        == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)

    source_manifest = [
        {
            "name": name,
            "path": relative.replace("\\", "/"),
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha256(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]

    return {
        "artifact": "varanegar_analysis_checkpoint_20260828",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_PERSISTED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "business_rows_or_raw_values_read": 0,
        },
        "source_manifest": source_manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(source_manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "voucher_hash_pinned_binary_count": len(
                voucher["deployed_call_and_transaction_contract"]["assembly_hashes"]
            ),
            "replication_hash_pinned_binary_count": replication["summary"][
                "hash_pinned_binary_count"
            ],
            "replication_target_method_contract_count": replication["summary"][
                "target_method_contract_count"
            ],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "mapped_risk_assignment_count": trace["summary"][
                "mapped_risk_assignment_count"
            ],
            "unique_risk_count": trace["summary"]["unique_risk_count"],
            "command_ready_module_count": trace["summary"][
                "command_ready_module_count"
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
