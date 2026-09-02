"""Design synthetic Golden/UAT cases for eight reporting output command surfaces."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "envelope": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_reporting_output_readiness_delta_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_reporting_output_readiness_checkpoint_20260829.json",
}
CASES = [
    ("AUTH_DENIED", "authorization", "actor lacks output kind or resource capability", "REJECTED_NO_EFFECT"),
    ("STALE_WATERMARK_TEMPLATE", "versioning", "source watermark or template/query hash differs from request", "REJECTED_NO_EFFECT"),
    ("DUPLICATE_COMMAND_ID", "idempotency", "same command id and payload is submitted twice", "COMMITTED_ORIGINAL_OUTCOME_ONLY_ONCE"),
    ("RENDER_FAILURE", "failure_injection", "renderer fails before confirmed output", "REJECTED_NO_EFFECT_OR_RENDERED_NOT_COMPLETED"),
    ("COMPLETION_FAILURE", "failure_injection", "output exists but completion/audit/external delivery receipt fails", "RENDERED_NOT_COMPLETED_OR_UNKNOWN_REQUIRES_READBACK"),
    ("PARTIAL_BATCH", "partial_failure", "one child fails after an earlier child succeeds", "PARTIAL_BATCH_WITH_PER_ITEM_OUTCOMES"),
    ("SUCCESS", "success", "authorized pinned request completes", "COMMITTED_COMPLETION_OR_EXTERNAL_FILE_RECEIPT"),
]
SPECIAL = {
    "RPT-09": "assert only failed or unconfirmed batch items are retried",
    "RPT-11": "assert template identity is pinned and physical-print audit is separate from render",
    "RPT-12": "assert a new intentional reprint uses a new command id and preserves cancellation provenance",
    "RPT-14": "assert export creates no ERP fact mutation and pins FetchReason/mode",
    "RPT-15": "assert delivery retry reuses the pinned query receipt and watermark",
    "RPT-18": "assert PRINT_REQUESTED never equals PHYSICAL_PRINT_CONFIRMED",
    "RPT-19": "assert signed metrics survive presentation formatting and export",
    "RPT-20": "assert successful treasury row receipts are never repeated by import retry",
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
    cases = []
    for surface in data["envelope"]["surfaces"]:
        for code, kind, setup, expected in CASES:
            cases.append({
                "case_id": f"RO-G-{surface['contract_id'].split('-')[-1]}-{code}",
                "contract_id": surface["contract_id"],
                "command": surface["command"],
                "case_kind": kind,
                "setup": setup,
                "expected_outcome": expected,
                "assertions": [
                    "typed outcome matches render, completion, audit, file and delegated-command durable evidence",
                    "each batch or import child has an independent outcome",
                    "same command id never duplicates a confirmed durable effect",
                    "preview creates no completion event",
                    SPECIAL[surface["contract_id"]],
                ],
                "status": "DESIGNED_NOT_EXECUTED",
            })
    summary = {
        "command_surface_count": 8,
        "case_count": len(cases),
        "case_count_per_surface": 7,
        "case_kind_counts": dict(sorted(collections.Counter(x["case_kind"] for x in cases).items())),
        "executed_case_count": 0,
        "passed_runtime_case_count": 0,
        "owner_approved_case_count": 0,
        "runtime_retry_idempotency_proven_module_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "eight_surfaces": len(data["envelope"]["surfaces"]) == len(SPECIAL) == 8,
        "seven_each": len(cases) == 56 and all(sum(x["contract_id"] == surface["contract_id"] for x in cases) == 7 for surface in data["envelope"]["surfaces"]),
        "unique_ids": len({x["case_id"] for x in cases}) == 56,
        "all_special": set(SPECIAL) == {x["contract_id"] for x in data["envelope"]["surfaces"]},
        "partial_and_completion": any(x["expected_outcome"].startswith("PARTIAL_BATCH") for x in cases) and any("UNKNOWN_REQUIRES_READBACK" in x["expected_outcome"] for x in cases),
        "unexecuted": {x["status"] for x in cases} == {"DESIGNED_NOT_EXECUTED"},
        "runtime_zero": summary["executed_case_count"] == summary["passed_runtime_case_count"] == summary["owner_approved_case_count"] == summary["runtime_retry_idempotency_proven_module_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "seven_contract_modules": data["readiness"]["summary"]["outcome_target_contract_module_count_after"] == 7,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_golden_uat_cases_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_SYNTHETIC_DESIGN", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "execution_gate": {"environment": "isolated target only", "requirements": ["synthetic documents and signed metrics", "stub renderer, spooler and object storage", "fault injection before/after every durable output boundary", "legacy/target receipt comparator", "owner-approved reprint, cancellation, expiry and privacy policies"], "promotion_rule": "all 56 cases execute with zero unexplained durable-effect difference and owner approval"},
        "cases": cases,
        "risk_links": ["R-002", "R-005", "R-006", "R-007", "R-017", "R-023", "R-036", "R-059"],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"design": "HIGH", "runtime": "NOT_EXECUTED"},
        "limits": ["These are synthetic designs, not UAT results.", "Physical print and external delivery completion require controlled adapters.", "No report or output command was executed."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
