"""Build deterministic synthetic freshness and clock-policy evidence for P3/P4."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from varanegar_evidence_freshness_reference import OUTCOMES, evaluate


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "propagation": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.json",
    "propagation_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint_20260829.json",
    "custody": "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.json",
    "handoff": "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_matrix_20260829.json",
    "capture": "artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json",
    "verification": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "reference": "scripts/windows/varanegar_evidence_freshness_reference.py",
}

TEMPORAL_ARTIFACT_TYPES = [
    "CAPTURE_AUTHORIZATION",
    "REDACTION_ATTESTATION",
    "CUSTODY_RECEIPT",
    "COMPARISON_HANDOFF",
]

TEMPORAL_ENVELOPE_FIELDS = [
    "temporal_evidence_id",
    "temporal_artifact_type",
    "custody_requirement_id",
    "policy_version_sha256",
    "clock_source_reference",
    "clock_attestation_sha256",
    "evaluated_at",
    "valid_from",
    "expires_at",
    "revocation_reference",
    "supersession_reference",
    "timezone_policy_reference",
    "maximum_clock_skew_seconds",
    "freshness_outcome",
    "evaluator_version_sha256",
    "evaluation_receipt_sha256",
]

CLOCK_POLICY_RULES = [
    "evaluated_at_valid_from_and_expires_at_must_be_timezone_aware",
    "valid_from_is_inclusive",
    "expires_at_is_exclusive",
    "valid_from_must_be_strictly_before_expires_at",
    "trusted_clock_attestation_required",
    "clock_skew_budget_must_be_policy_versioned_and_bounded",
    "policy_version_mismatch_fails_closed",
    "revocation_precedes_current_time_window",
    "supersession_precedes_current_time_window",
    "expiry_never_auto_extends_or_auto_reaccepts",
]


def base_envelope() -> dict:
    return {
        "evaluated_at": "2026-01-01T12:00:00+00:00",
        "valid_from": "2026-01-01T11:00:00+00:00",
        "expires_at": "2026-01-01T13:00:00+00:00",
        "policy_version_matches": True,
        "clock_trusted": True,
        "revoked": False,
        "superseded": False,
    }


def vectors() -> list[dict]:
    specs = []
    def add(vector_id: str, expected: str, **changes) -> None:
        envelope = base_envelope()
        envelope.update(changes)
        specs.append({"vector_id": vector_id, "synthetic_envelope": envelope, "expected_outcome": expected, "synthetic_only": True})
    add("FRV-01-CURRENT-MIDDLE", "CURRENT")
    add("FRV-02-VALID-FROM-INCLUSIVE", "CURRENT", evaluated_at="2026-01-01T11:00:00+00:00")
    add("FRV-03-BEFORE-VALID-FROM", "NOT_YET_VALID", evaluated_at="2026-01-01T10:59:59.999999+00:00")
    add("FRV-04-EXPIRES-AT-EXCLUSIVE", "EXPIRED", evaluated_at="2026-01-01T13:00:00+00:00")
    add("FRV-05-AFTER-EXPIRY", "EXPIRED", evaluated_at="2026-01-01T13:00:00.000001+00:00")
    add("FRV-06-REVOKED", "REVOKED", revoked=True)
    add("FRV-07-SUPERSEDED", "SUPERSEDED", superseded=True)
    add("FRV-08-MISSING-EXPIRY", "MISSING_TEMPORAL_EVIDENCE", expires_at=None)
    add("FRV-09-UNTRUSTED-CLOCK", "CLOCK_OR_INTERVAL_INVALID", clock_trusted=False)
    add("FRV-10-POLICY-MISMATCH", "POLICY_VERSION_MISMATCH", policy_version_matches=False)
    add("FRV-11-INVERTED-INTERVAL", "CLOCK_OR_INTERVAL_INVALID", valid_from="2026-01-01T14:00:00+00:00")
    add("FRV-12-NAIVE-TIMESTAMP", "CLOCK_OR_INTERVAL_INVALID", evaluated_at="2026-01-01T12:00:00")
    return specs


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items() if path.suffix == ".json"}
    custody = documents["custody"]
    official = documents["tests"]
    synthetic_vectors = vectors()
    evaluations = []
    for artifact_type in TEMPORAL_ARTIFACT_TYPES:
        for vector in synthetic_vectors:
            observed = evaluate(vector["synthetic_envelope"])
            evaluations.append(
                {
                    "temporal_artifact_type": artifact_type,
                    "vector_id": vector["vector_id"],
                    "expected_outcome": vector["expected_outcome"],
                    "observed_outcome": observed,
                    "validation": "PASS" if observed == vector["expected_outcome"] else "FAIL",
                    "system_wall_clock_used": False,
                    "real_evidence_evaluated": False,
                }
            )

    obligations = [
        {
            "freshness_obligation_id": f"FRO-{index:03d}-{artifact_type}",
            "custody_requirement_id": requirement["custody_requirement_id"],
            "capture_pair_id": requirement["capture_pair_id"],
            "cg05_receipt_slot_id": requirement["cg05_receipt_slot_id"],
            "temporal_artifact_type": artifact_type,
            "required_fields": TEMPORAL_ENVELOPE_FIELDS,
            "current_outcome": "MISSING_TEMPORAL_EVIDENCE",
            "evaluation_count": 0,
            "readiness_effect": "NONE",
        }
        for index, requirement in enumerate(custody["custody_requirements"], start=1)
        for artifact_type in TEMPORAL_ARTIFACT_TYPES
    ]
    summary = {
        "temporal_artifact_type_count": len(TEMPORAL_ARTIFACT_TYPES),
        "freshness_outcome_count": len(OUTCOMES),
        "synthetic_vector_count": len(synthetic_vectors),
        "synthetic_evaluation_count": len(evaluations),
        "synthetic_evaluation_pass_count": sum(item["validation"] == "PASS" for item in evaluations),
        "synthetic_evaluation_fail_count": sum(item["validation"] != "PASS" for item in evaluations),
        "custody_requirement_count": len(custody["custody_requirements"]),
        "freshness_obligation_count": len(obligations),
        "temporal_envelope_field_count": len(TEMPORAL_ENVELOPE_FIELDS),
        "clock_policy_rule_count": len(CLOCK_POLICY_RULES),
        "reference_evaluator_implementation_count": 1,
        "real_clock_evaluation_count": 0,
        "current_evidence_count": 0,
        "accepted_freshness_count": 0,
        "comparison_handoff_ready_count": 0,
        "result_parity_proven_packet_count": 0,
        "cg05_closed_packet_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_freshness_contract": 1404,
        "design_lower_bound_after_freshness_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("propagation", "propagation_checkpoint", "custody", "handoff", "capture", "verification", "tests")
        ),
        "types_4_outcomes_8_vectors_12": (
            summary["temporal_artifact_type_count"],
            summary["freshness_outcome_count"],
            summary["synthetic_vector_count"],
        )
        == (4, 8, 12),
        "evaluations_48_all_pass": summary["synthetic_evaluation_count"]
        == summary["synthetic_evaluation_pass_count"]
        == 48
        and summary["synthetic_evaluation_fail_count"] == 0,
        "requirements_54_obligations_216": summary["custody_requirement_count"] == 54
        and summary["freshness_obligation_count"] == 216,
        "fields_16_rules_10": summary["temporal_envelope_field_count"] == 16
        and summary["clock_policy_rule_count"] == 10,
        "all_outcomes_covered": {vector["expected_outcome"] for vector in synthetic_vectors} == set(OUTCOMES),
        "all_obligations_missing": all(item["current_outcome"] == "MISSING_TEMPORAL_EVIDENCE" for item in obligations),
        "real_acceptance_parity_readiness_zero": summary["real_clock_evaluation_count"]
        == summary["current_evidence_count"]
        == summary["accepted_freshness_count"]
        == summary["comparison_handoff_ready_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_freshness_contract"]
        == summary["design_lower_bound_after_freshness_contract"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "offline_fixed_clock_synthetic_freshness_reference",
            "continuation_complete": False,
            "real_clock_or_evidence_evaluation_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "system_or_external_clock_reads_for_vectors": 0,
            "real_evidence_evaluations": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "temporal_artifact_types": TEMPORAL_ARTIFACT_TYPES,
        "freshness_outcomes": OUTCOMES,
        "temporal_envelope_fields": TEMPORAL_ENVELOPE_FIELDS,
        "clock_policy_rules": CLOCK_POLICY_RULES,
        "synthetic_freshness_vectors": synthetic_vectors,
        "synthetic_evaluation_results": evaluations,
        "freshness_obligations": obligations,
        "freshness_rule": {
            "valid_from_boundary": "INCLUSIVE",
            "expires_at_boundary": "EXCLUSIVE",
            "timezone_aware_required": True,
            "trusted_clock_attestation_required": True,
            "automatic_expiry_extension_allowed": False,
            "revoked_or_superseded_can_be_current": False,
            "system_wall_clock_used_by_synthetic_vectors": False,
            "freshness_alone_proves_evidence_acceptance_or_result_parity": False,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {
                "name": name,
                "path": SOURCES[name],
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "All evaluations use fixed synthetic timestamps and no system or external clock.",
            "The reference evaluator is not an operational trust service and evaluated no real receipt authorization or attestation.",
            "CURRENT freshness alone does not prove evidence acceptance result parity CG-05 closure UAT or readiness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

