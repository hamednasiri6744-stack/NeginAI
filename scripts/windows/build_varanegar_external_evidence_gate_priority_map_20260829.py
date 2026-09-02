"""Build an evidence-first priority map for the six remaining external gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "consolidated": "artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json",
    "boundary": "artifacts/varanegar_analysis/varanegar_identity_integration_transaction_mutation_boundary_20260829.json",
    "platform": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "reports": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_identity_integration_transaction_mutation_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    gates = {row["id"]: row for row in data["consolidated"]["remaining_gates"]}

    rows = [
        {
            "priority_rank": 1,
            "gate_id": "CG-06",
            "lane": "FOUNDATION_DECISION",
            "dependency_gate_ids": [],
            "parallel_with_gate_ids": ["CG-05"],
            "why_now": "The selected stack, hosting, recovery targets and deployment owner define the isolated runtime evidence environment.",
            "current_proof": "PROVIDER_NEUTRAL_TARGET_DESIGN_ONLY",
            "required_evidence_packet": [
                "approved stack/database/hosting decision references",
                "approved RPO/RTO and recovery-test policy reference",
                "named accountable deployment-owner role without personal identity",
                "isolated non-production environment attestation",
            ],
            "acceptance_rule": "All four decisions are approved and hash-pinned; no proposal is treated as approval.",
            "promotion_effect_before_acceptance": "NONE",
        },
        {
            "priority_rank": 2,
            "gate_id": "CG-05",
            "lane": "BOUNDED_REPORT_PARITY",
            "dependency_gate_ids": [],
            "parallel_with_gate_ids": ["CG-06"],
            "why_now": "Twenty ownership boundaries are closed, so formula/grain/scope packets can be prepared without claiming result parity.",
            "current_proof": "OWNERSHIP_20_OF_20_RESULT_PARITY_0_OWNER_GOLDEN_0",
            "required_evidence_packet": [
                "frozen isolated fixture reference per applicable result owner",
                "owner-approved formula, grain, scope, rounding and null policy",
                "hash-pinned expected totals and row-key set without raw business values in this artifact",
                "legacy/target output comparison receipt and unexplained-difference disposition",
            ],
            "acceptance_rule": "Every applicable surface has frozen-input parity and approved Golden values; shells are not misclassified as query owners.",
            "promotion_effect_before_acceptance": "NONE",
        },
        {
            "priority_rank": 3,
            "gate_id": "CG-01",
            "lane": "ISOLATED_RUNTIME_FOUNDATION",
            "dependency_gate_ids": ["CG-06"],
            "parallel_with_gate_ids": ["CG-02"],
            "why_now": "Authenticated deny-first and resource-scope evidence is a universal runtime prerequisite.",
            "current_proof": "AUTHORIZATION_DESIGN_14_RUNTIME_0",
            "required_evidence_packet": [
                "synthetic authenticated principal-role fixtures",
                "allow/deny/scope/SoD decision receipts for all fourteen modules",
                "server-side resource-scope and session-revocation evidence",
                "negative-path audit evidence with no identity values persisted here",
            ],
            "acceptance_rule": "All allow, deny, scope and revocation cases pass in the approved isolated environment with owner/security approval.",
            "promotion_effect_before_acceptance": "NONE",
        },
        {
            "priority_rank": 4,
            "gate_id": "CG-02",
            "lane": "ISOLATED_RUNTIME_FOUNDATION",
            "dependency_gate_ids": ["CG-06"],
            "parallel_with_gate_ids": ["CG-01"],
            "why_now": "Effect comparisons are not trustworthy until rollback and partial-failure atomicity are observable.",
            "current_proof": "TRANSACTION_DESIGN_OR_STATIC_12_RUNTIME_ATOMICITY_0",
            "required_evidence_packet": [
                "fault-injection matrix at each declared transaction boundary",
                "before/after immutable state digest and rollback receipt",
                "partial-success quarantine and unknown-outcome classification",
                "retry-after-failure convergence evidence",
            ],
            "acceptance_rule": "Every injected failure converges to one approved committed or rolled-back state with no unexplained partial effect.",
            "promotion_effect_before_acceptance": "NONE",
        },
        {
            "priority_rank": 5,
            "gate_id": "CG-03",
            "lane": "ISOLATED_EFFECT_PARITY",
            "dependency_gate_ids": ["CG-06", "CG-02"],
            "parallel_with_gate_ids": [],
            "why_now": "Mutation, result and external-effect parity depends on an observable atomicity boundary.",
            "current_proof": "MUTATION_STATIC_12_RUNTIME_EFFECT_PARITY_0",
            "required_evidence_packet": [
                "declared mutation/effect set per command",
                "immutable result and external-effect receipt",
                "readback and reconciliation digest",
                "duplicate/retry/compensation convergence evidence",
            ],
            "acceptance_rule": "Declared database, result and external effects reconcile under first-run, retry, duplicate and compensation cases.",
            "promotion_effect_before_acceptance": "NONE",
        },
        {
            "priority_rank": 6,
            "gate_id": "CG-04",
            "lane": "TERMINAL_OWNER_UAT",
            "dependency_gate_ids": ["CG-01", "CG-02", "CG-03", "CG-05", "CG-06"],
            "parallel_with_gate_ids": [],
            "why_now": "The 1,229 synthetic obligations become promotion evidence only after the component runtime and report gates are accepted.",
            "current_proof": "DESIGN_1229_EXECUTED_0_OWNER_APPROVED_0",
            "required_evidence_packet": [
                "executed obligation manifest with immutable run receipts",
                "zero unexplained mismatch register",
                "business-owner approval references by module",
                "security, finance, operations and platform exception dispositions",
            ],
            "acceptance_rule": "All in-scope obligations execute in isolation, unexplained differences are zero, and accountable owners approve the bounded result.",
            "promotion_effect_before_acceptance": "NONE",
        },
    ]
    for row in rows:
        row["gap"] = gates[row["gate_id"]]["gap"]
        row["status"] = gates[row["gate_id"]]["status"]
        row["affected_module_count"] = gates[row["gate_id"]]["affected_module_count"]

    ranks = [row["priority_rank"] for row in rows]
    ids = [row["gate_id"] for row in rows]
    dependency_ordered = all(
        next(item["priority_rank"] for item in rows if item["gate_id"] == dependency) < row["priority_rank"]
        for row in rows
        for dependency in row["dependency_gate_ids"]
    )
    summary = {
        "gate_count": len(rows),
        "open_external_gate_count": len(rows),
        "foundation_decision_gate_count": sum(row["lane"] == "FOUNDATION_DECISION" for row in rows),
        "bounded_parallel_report_gate_count": sum(row["lane"] == "BOUNDED_REPORT_PARITY" for row in rows),
        "isolated_runtime_gate_count": sum(row["lane"].startswith("ISOLATED_") for row in rows),
        "terminal_owner_uat_gate_count": sum(row["lane"] == "TERMINAL_OWNER_UAT" for row in rows),
        "approved_platform_decision_count": data["platform"]["summary"]["approved_recovery_policy_count"],
        "runtime_authorization_proven_module_count": data["consolidated"]["summary"]["runtime_authorization_proven_module_count"],
        "runtime_atomicity_proven_module_count": data["consolidated"]["summary"]["runtime_atomicity_proven_module_count"],
        "runtime_effect_parity_proven_module_count": data["consolidated"]["summary"]["runtime_effect_parity_proven_module_count"],
        "report_result_parity_proven_count": data["reports"]["summary"]["result_parity_proven_count"],
        "owner_approved_case_count": data["consolidated"]["summary"]["owner_approved_case_count"],
        "synthetic_acceptance_design_obligation_count": data["consolidated"]["summary"]["synthetic_acceptance_design_obligation_count"],
        "identity_integration_target_design_command_count": data["boundary"]["summary"]["command_with_target_transaction_design_count"],
        "identity_integration_complete_legacy_static_proof_count": data["boundary"]["summary"]["command_with_complete_legacy_static_proof_count"],
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "six_exact_gates": set(ids) == {f"CG-0{i}" for i in range(1, 7)} and len(ids) == 6,
        "rank_is_total_and_unique": ranks == list(range(1, 7)),
        "dependencies_precede_consumers": dependency_ordered,
        "foundation_and_parallel_first": ids[:2] == ["CG-06", "CG-05"],
        "uat_is_terminal": ids[-1] == "CG-04" and len(rows[-1]["dependency_gate_ids"]) == 5,
        "evidence_packets_complete": all(len(row["required_evidence_packet"]) == 4 for row in rows),
        "no_promotion_claim": all(row["promotion_effect_before_acceptance"] == "NONE" for row in rows),
        "runtime_and_owner_zero": summary["approved_platform_decision_count"]
        == summary["runtime_authorization_proven_module_count"]
        == summary["runtime_atomicity_proven_module_count"]
        == summary["runtime_effect_parity_proven_module_count"]
        == summary["report_result_parity_proven_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_external_evidence_gate_priority_map_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "OFFLINE_EXISTING_ARTIFACT_PRIORITY_DESIGN", "continuation_complete": False},
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "priority_map": rows,
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_external_evidence_gate_priority_map_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Priority is a dependency-aware evidence plan, not permission to execute any gate.",
            "CG-05 may prepare bounded packets in parallel with CG-06; this does not prove report parity.",
            "No gate is closed and no readiness state is promoted by this artifact.",
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
