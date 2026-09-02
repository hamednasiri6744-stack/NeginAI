"""Map continuation evidence to existing ERP modules, contracts and risks."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "gap": "artifacts/varanegar_analysis/varanegar_24h_continuation_gap_map_20260829.json",
    "inventory": "artifacts/varanegar_analysis/varanegar_accounting_command_inventory_correction_20260829.json",
    "generic_save": "artifacts/varanegar_analysis/varanegar_manual_voucher_generic_save_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_command_readiness_delta_20260829.json",
    "accounting_golden": "artifacts/varanegar_analysis/varanegar_accounting_golden_uat_cases_20260829.json",
    "report_golden": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_checkpoint_20260829.json",
}

MAPPINGS = [
    {
        "id": "E24-01",
        "source": "gap",
        "modules": ["accounting", "receivables_treasury", "distribution", "reporting_documents", "platform"],
        "requirement_contracts": ["continuation.gap.priority_and_authority_boundary"],
        "risk_ids": ["R-026"],
        "effect": "Separates four statically advanceable gaps from the owner/UAT external gate.",
    },
    {
        "id": "E24-02",
        "source": "inventory",
        "modules": ["accounting", "platform", "identity_authorization", "integration_migration"],
        "requirement_contracts": ["accounting.command.inventory.semantic_correction", "accounting.ui_close.not_financial_cancel"],
        "risk_ids": ["R-002", "R-005", "R-007", "R-023", "R-084"],
        "effect": "Replaces the seven-candidate historical view with six authoritative command paths.",
    },
    {
        "id": "E24-03",
        "source": "generic_save",
        "modules": ["accounting", "platform", "integration_migration"],
        "requirement_contracts": ["accounting.manual_voucher.generic_save_transaction_boundary"],
        "risk_ids": ["R-002", "R-005", "R-006", "R-007"],
        "effect": "Pins generic handler/adapter binding and Commit ownership while leaving the runtime branch unproven.",
    },
    {
        "id": "E24-04",
        "source": "readiness",
        "modules": ["accounting", "platform", "identity_authorization"],
        "requirement_contracts": ["accounting.command.outcome_retry.target_design"],
        "risk_ids": ["R-006", "R-007", "R-026", "R-049"],
        "effect": "Advances design coverage only; runtime, command and pilot readiness remain zero.",
    },
    {
        "id": "E24-05",
        "source": "accounting_golden",
        "modules": ["accounting", "platform", "identity_authorization", "integration_migration"],
        "requirement_contracts": ["accounting.command.synthetic_acceptance_42_cases"],
        "risk_ids": ["R-005", "R-006", "R-007", "R-023", "R-048", "R-049"],
        "effect": "Adds denial, concurrency, idempotency, fault, scope, success and command-specific designs without runtime claims.",
    },
    {
        "id": "E24-06",
        "source": "report_golden",
        "modules": ["reporting_documents", "identity_authorization", "integration_migration", "platform"],
        "requirement_contracts": ["reporting.surface.synthetic_fixture_88_cases", "reporting.ownership_aware_parity"],
        "risk_ids": ["R-002", "R-004", "R-007", "R-017", "R-021", "R-023", "R-031", "R-059", "R-084"],
        "effect": "Defines ownership-aware assertions for twenty surfaces without promoting routing shells to data owners.",
    },
    {
        "id": "E24-07",
        "source": "playbook",
        "modules": ["accounting", "platform", "identity_authorization"],
        "requirement_contracts": ["accounting.incident.evidence_first_playbook", "accounting.target_erp.nine_section_contract"],
        "risk_ids": ["R-005", "R-006", "R-007", "R-008", "R-043", "R-048", "R-049"],
        "effect": "Turns corrected semantics into five diagnostic playbooks and a nine-section target contract.",
    },
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    risk_ids = {risk["id"] for risk in documents["risk"]["risks"]}
    trace_modules = {module["module"]: module for module in documents["trace"]["modules"]}
    evidence_sources = {mapping["source"] for mapping in MAPPINGS}
    linked_risks = sorted({risk for mapping in MAPPINGS for risk in mapping["risk_ids"]})
    requirement_contracts = sorted({item for mapping in MAPPINGS for item in mapping["requirement_contracts"]})
    risk_link_count = sum(len(mapping["risk_ids"]) for mapping in MAPPINGS)
    module_link_count = sum(len(mapping["modules"]) for mapping in MAPPINGS)
    checks = {
        "all_sources_pass": all(documents[name]["validation"] == "PASS" for name in SOURCES if name not in {"risk", "trace"})
        and documents["risk"]["validation"] == documents["trace"]["validation"] == "PASS",
        "seven_continuation_evidence_items": len(MAPPINGS) == len(evidence_sources) == 7,
        "all_evidence_sources_declared": evidence_sources <= set(SOURCES),
        "all_modules_exist": all(module in trace_modules for mapping in MAPPINGS for module in mapping["modules"]),
        "all_risks_exist": all(risk in risk_ids for mapping in MAPPINGS for risk in mapping["risk_ids"]),
        "each_risk_matches_a_mapped_module": all(
            any(risk in {item["id"] for item in trace_modules[module]["risks"]} for module in mapping["modules"])
            for mapping in MAPPINGS
            for risk in mapping["risk_ids"]
        ),
        "base_counts_stable": documents["risk"]["summary"]["risk_count"] == 84
        and documents["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
        "runtime_readiness_not_promoted": documents["readiness"]["summary"]["command_ready_module_count"] == 0
        and documents["readiness"]["summary"]["pilot_ready_module_count"] == 0,
        "golden_design_not_execution": documents["accounting_golden"]["summary"]["executed_case_count"] == 0
        and documents["report_golden"]["summary"]["executed_case_count"] == 0,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_continuation_traceability_delta_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_EVIDENCE_SYNTHESIS",
            "database_connections": 0,
            "commands_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "sensitive_values_persisted": 0,
        },
        "summary": {
            "continuation_evidence_count": len(MAPPINGS),
            "requirement_contract_delta_count": len(requirement_contracts),
            "module_evidence_link_count": module_link_count,
            "risk_evidence_link_count": risk_link_count,
            "unique_linked_risk_count": len(linked_risks),
            "base_risk_count": 84,
            "base_mapped_risk_assignment_count": 343,
            "new_risk_count": 0,
            "runtime_readiness_promotions": 0,
        },
        "policy": {
            "relationship": "ADDITIVE_EVIDENCE_DELTA_ONLY",
            "base_registers_unchanged": True,
            "no_closed_risk_claim": True,
            "no_uat_or_owner_approval_claim": True,
        },
        "mappings": MAPPINGS,
        "requirement_contracts": requirement_contracts,
        "linked_existing_risks": linked_risks,
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ],
        "confidence": {
            "static_and_design_trace": "HIGH",
            "runtime_effect_parity": "UNPROVEN",
            "owner_acceptance": "UNPROVEN",
        },
        "limits": [
            "This artifact supplements but does not rewrite the 84-risk register or the 343-assignment base traceability ledger.",
            "A risk link means relevant evidence, not closure or mitigation completion.",
            "Synthetic Golden designs do not constitute UAT execution or owner acceptance.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
