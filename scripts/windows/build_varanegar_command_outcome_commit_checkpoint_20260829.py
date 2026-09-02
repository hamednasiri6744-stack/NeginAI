"""Build the offline command-outcome and commit-semantics checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/domains/command_outcome_commit_matrix_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_sale_invoice_print_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "matrix_builder": "scripts/windows/build_varanegar_command_outcome_commit_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_command_outcome_commit_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_command_outcome_commit_matrix.py",
    "domain_doc": "docs/varanegar_reconstruction/COMMAND_OUTCOME_MESSAGE_COMMIT_AND_ROLLBACK_MATRIX_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name):
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    matrix = _load("matrix")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    raw = (ROOT / SOURCES["matrix"]).read_text(encoding="utf-8")
    classes = {case["outcome_classification"] for case in matrix["cases"]}
    covered_risks = {
        item["id"]
        for item in risks["risks"]
        if item["id"] in {"R-046", "R-048", "R-077", "R-078", "R-079", "R-080", "R-081", "R-084"}
    }
    checks = {
        "offline_redacted": (
            matrix["validation"] == "PASS"
            and matrix["safety"]["database_connections"] == 0
            and matrix["safety"]["live_ui_actions"] == 0
            and matrix["safety"]["assemblies_loaded_or_executed"] == 0
            and matrix["safety"]["operational_commands_executed"] == 0
            and matrix["safety"]["raw_business_rows_ids_names_messages_or_sql_definitions_persisted"] == 0
        ),
        "source_assertions": (
            len(matrix["source_manifest"]) == 12
            and len(matrix["source_assertions"]) == 10
            and all(matrix["source_assertions"].values())
            and matrix["failed_assertions"] == []
        ),
        "taxonomy": (
            matrix["summary"]["case_count"] == 10
            and matrix["summary"]["domain_count"] == 6
            and matrix["summary"]["outcome_class_count"] == 10
            and matrix["summary"]["message_or_result_control_case_count"] == 6
            and matrix["summary"]["case_with_unproven_physical_transaction_owner_count"] == 3
        ),
        "critical_classes_present": {
            "SAFE_ONLY_BY_CURRENT_STATEMENT_ORDER",
            "REJECTED_RESULT_WITH_COMMITTABLE_PREWRITE",
            "POST_COMMIT_ADVISORY_FAILURE",
            "PRECOMMIT_ADVISORY_FAILURE",
            "CALLER_ENFORCED_REJECTION",
            "CALLER_DEPENDENT_ATOMICITY",
            "NESTED_COMMIT_AND_BRANCHABLE_ROLLBACK",
            "SQL_OWNED_ATOMIC_COMMAND",
            "SUCCESS_GATED_SEPARATE_AUDIT_COMMIT",
        }.issubset(classes),
        "target_invariants": (
            len(matrix["target_invariants"]) == 8
            and matrix["target_invariants"][0]
            == "A display message is never a transaction-control primitive."
            and any("UNKNOWN" in item for item in matrix["target_invariants"])
        ),
        "risk_coverage_not_duplicate": covered_risks
        == {"R-046", "R-048", "R-077", "R-078", "R-079", "R-080", "R-081", "R-084"},
        "previous_chain": previous["validation"] == "PASS" and previous["summary"]["risk_count"] == 84,
        "register_trace": (
            risks["summary"]["risk_count"] == 84
            and risks["summary"]["critical_count"] == 50
            and risks["summary"]["high_count"] == 31
            and trace["summary"]["unique_risk_count"] == 84
            and trace["summary"]["mapped_risk_assignment_count"] == 343
            and trace["summary"]["command_ready_module_count"] == 0
        ),
        "no_uuid_secret": (
            re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", raw) is None
            and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None
        ),
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
        "artifact": "varanegar_command_outcome_commit_checkpoint_20260829",
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
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "case_count": matrix["summary"]["case_count"],
            "outcome_class_count": matrix["summary"]["outcome_class_count"],
            "covered_existing_risk_count": len(covered_risks),
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
