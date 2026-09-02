"""Map cross-module reconciliation evidence to existing modules, requirements and risks."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_contract_20260829.json",
    "golden": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_golden_cases_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_playbook_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_playbook_checkpoint_20260829.json",
}
MODULES = ["accounting", "receivables_treasury", "distribution", "inventory", "sales", "platform", "integration_migration"]
RISKS = ["R-002", "R-005", "R-006", "R-007", "R-008", "R-023", "R-034", "R-036", "R-043", "R-048"]
MAPPINGS = [
    {
        "id": "XMR-E24-01",
        "source": "contract",
        "modules": MODULES,
        "requirements": [
            "cross_module.reconciliation.receipt_schema",
            "cross_module.identity_scope_version_effect_separation",
            "cross_module.expected_absence_explicit_policy",
            "cross_module.quarantine_before_retry",
            "cross_module.no_max_history_inference",
        ],
        "risks": RISKS,
    },
    {
        "id": "XMR-E24-02",
        "source": "golden",
        "modules": MODULES,
        "requirements": [
            "cross_module.synthetic_acceptance_35",
            "cross_module.payment_amount_identity_independence",
            "cross_module.multi_source_batch_validity",
        ],
        "risks": RISKS,
    },
    {
        "id": "XMR-E24-03",
        "source": "playbook",
        "modules": MODULES,
        "requirements": [
            "cross_module.incident.playbook",
            "cross_module.repair_retry_separate_authority",
        ],
        "risks": RISKS,
    },
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    existing_risks = {x["id"] for x in data["risk"]["risks"]}
    module_risks = {x["module"]: {risk["id"] for risk in x["risks"]} for x in data["trace"]["modules"]}
    requirements = sorted({req for mapping in MAPPINGS for req in mapping["requirements"]})
    linked_risks = sorted({risk for mapping in MAPPINGS for risk in mapping["risks"]})
    summary = {
        "cross_module_evidence_count": len(MAPPINGS),
        "requirement_contract_delta_count": len(requirements),
        "module_evidence_link_count": sum(len(x["modules"]) for x in MAPPINGS),
        "risk_evidence_link_count": sum(len(x["risks"]) for x in MAPPINGS),
        "unique_linked_risk_count": len(linked_risks),
        "base_risk_count": 84,
        "base_mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
        "runtime_readiness_promotions": 0,
    }
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "three_evidence": summary["cross_module_evidence_count"] == 3,
        "ten_requirements": summary["requirement_contract_delta_count"] == 10,
        "link_counts": summary["module_evidence_link_count"] == 21 and summary["risk_evidence_link_count"] == 30,
        "ten_existing": summary["unique_linked_risk_count"] == 10 and set(linked_risks) <= existing_risks,
        "module_consistent": all(any(risk in module_risks[module] for module in mapping["modules"]) for mapping in MAPPINGS for risk in mapping["risks"]),
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
        "runtime_zero": data["contract"]["summary"]["runtime_reconciliation_executed_count"] == data["golden"]["summary"]["executed_case_count"] == data["playbook"]["summary"]["runtime_incidents_diagnosed_count"] == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_cross_module_reconciliation_traceability_delta_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_EVIDENCE_SYNTHESIS", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "policy": {"relationship": "ADDITIVE_EVIDENCE_DELTA_ONLY", "base_registers_unchanged": True, "no_risk_closure_or_runtime_promotion": True},
        "mappings": MAPPINGS,
        "requirements": requirements,
        "linked_existing_risks": linked_risks,
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"design_trace": "HIGH", "runtime_effect_parity": "UNPROVEN"},
        "limits": ["Risk links do not close risks.", "The 84-risk and 343-assignment base registers remain unchanged.", "No runtime UAT, repair or diagnosis is claimed."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
