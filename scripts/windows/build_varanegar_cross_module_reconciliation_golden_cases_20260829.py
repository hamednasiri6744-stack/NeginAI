"""Design synthetic Golden cases for the seven cross-module reconciliation edges."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_checkpoint_20260829.json",
}
SCENARIOS = [
    ("MATCHED", "source and target identities, scope, version, state and durable effect agree", "MATCHED", None),
    ("SOURCE_ONLY", "source exists but the required target/crosswalk is absent", "UNPROVEN", "SOURCE_ONLY"),
    ("TARGET_ONLY", "target exists but its immutable source cannot be resolved", "IDENTITY_CONFLICT", "TARGET_ONLY"),
    ("DUPLICATE_CROSSWALK", "more than one conflicting target/crosswalk claims the same source", "IDENTITY_CONFLICT", "DUPLICATE_OR_CONFLICTING_CROSSWALK"),
    ("SCOPE_VERSION_MISMATCH", "identities resolve but scope or expected version differs", "VERSION_FORK", "SCOPE_OR_VERSION_MISMATCH"),
]
EDGE_RULES = {
    "command_to_command_receipt": {
        "matched_assertion": "same CommandId and PayloadHash returns the original typed outcome exactly once",
        "semantic_guard": "same CommandId with a different PayloadHash is an identity conflict, never a retry",
    },
    "sale_to_accounting_source": {
        "matched_assertion": "active sale source resolves to balanced accounting source lines",
        "semantic_guard": "snapshot-only absence can be EXPECTED_ABSENCE only with an explicit policy rule",
    },
    "accounting_source_to_batch_journal": {
        "matched_assertion": "one source resolves to one batch link and one active journal",
        "semantic_guard": "a batch containing multiple sources is valid and is not duplicate evidence",
    },
    "distribution_to_sale_link": {
        "matched_assertion": "distribution and sale link resolve at the expected ordered history version",
        "semantic_guard": "current status cannot replace ordered link-history evidence",
    },
    "distribution_to_exit": {
        "matched_assertion": "distribution resolves to one scoped active exit or explicit cancelled lifecycle",
        "semantic_guard": "physical absence of an exit is not cancellation proof",
    },
    "exit_to_type60_voucher": {
        "matched_assertion": "active exit resolves to its type-60 graph; cancelled exit resolves to delete evidence",
        "semantic_guard": "voucher absence without immutable delete evidence remains unproven",
    },
    "ngt_payment_to_backoffice_receipt": {
        "matched_assertion": "payment and receipt crosswalk identities agree independently of allocation amount",
        "semantic_guard": "different receipt amount scope does not turn an identity match into a mismatch",
    },
}


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
    edges = data["contract"]["cross_module_edges"]
    cases = []
    for edge_index, edge in enumerate(edges, 1):
        rule = EDGE_RULES[edge["edge"]]
        for code, setup, classification, quarantine in SCENARIOS:
            cases.append({
                "case_id": f"XMR-G-{edge_index:02d}-{code}",
                "edge_type": edge["edge"],
                "setup": setup,
                "expected_classification": classification,
                "expected_quarantine_reason": quarantine,
                "assertions": [
                    rule["matched_assertion"],
                    rule["semantic_guard"],
                    "identity, scope, version, state and durable effect comparisons are recorded separately",
                    "no repair, retry or target write occurs during reconciliation",
                ],
                "status": "DESIGNED_NOT_EXECUTED",
            })
    summary = {
        "edge_type_count": len(edges),
        "case_count": len(cases),
        "case_count_per_edge": 5,
        "classification_counts": dict(sorted(collections.Counter(x["expected_classification"] for x in cases).items())),
        "executed_case_count": 0,
        "passed_runtime_case_count": 0,
        "owner_approved_case_count": 0,
        "runtime_reconciliation_proven_edge_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "seven_edges": len(edges) == len(EDGE_RULES) == 7,
        "five_each": len(cases) == 35 and all(sum(x["edge_type"] == e["edge"] for x in cases) == 5 for e in edges),
        "unique_ids": len({x["case_id"] for x in cases}) == 35,
        "semantic_rules_complete": set(EDGE_RULES) == {x["edge"] for x in edges},
        "payment_amount_independent": any("amount scope does not" in a for x in cases if x["edge_type"] == "ngt_payment_to_backoffice_receipt" for a in x["assertions"]),
        "multi_source_batch_valid": any("multiple sources is valid" in a for x in cases if x["edge_type"] == "accounting_source_to_batch_journal" for a in x["assertions"]),
        "unexecuted": {x["status"] for x in cases} == {"DESIGNED_NOT_EXECUTED"},
        "runtime_zero": summary["executed_case_count"] == summary["passed_runtime_case_count"] == summary["owner_approved_case_count"] == summary["runtime_reconciliation_proven_edge_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_cross_module_reconciliation_golden_cases_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_SYNTHETIC_DESIGN", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "execution_gate": {
            "environment": "isolated target only",
            "requirements": ["synthetic cross-module identities and scopes", "fault injection around durable-effect boundaries", "legacy-target receipt comparator", "owner-approved expected-absence and cancellation policies"],
            "promotion_rule": "all 35 cases execute with zero unexplained identity, scope, version, state or durable-effect difference",
        },
        "cases": cases,
        "risk_links": ["R-002", "R-005", "R-006", "R-007", "R-008", "R-023", "R-034", "R-036", "R-043", "R-048"],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"design": "HIGH", "runtime": "NOT_EXECUTED"},
        "limits": ["These are synthetic designs, not runtime UAT results.", "Expected absence and cancellation require explicit evidence.", "No command, report, query or procedure was executed."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
