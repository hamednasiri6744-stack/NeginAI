"""Build synthetic Golden cases for material extension target contracts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _case(case_id: str, surface: str, category: str, setup: str, action: str, expected: list[str]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "surface": surface,
        "category": category,
        "setup": setup,
        "action": action,
        "expected": expected,
        "execution_target": "NEGIN_ERP_TEST_HARNESS_ONLY",
        "legacy_execution_allowed": False,
    }


def _command_cases(contract: dict[str, Any], index: int) -> list[dict[str, Any]]:
    command = contract["command"]
    prefix = f"EXT-C{index:02d}"
    cases = [
        _case(f"{prefix}-HAPPY", command, "happy_path", "authorized actor, valid scope, current expected_version and valid payload", "submit once", ["accepted exactly once", "version advances once", "audit and outbox identifiers returned", "reconciliation status is explicit"]),
        _case(f"{prefix}-AUTH-DENY", command, "authorization", "actor lacks command capability", "submit otherwise-valid command", ["denied before mutation", "no aggregate/current-pointer/outbox change", "denial audited without sensitive payload"]),
        _case(f"{prefix}-SCOPE-DENY", command, "scope", "actor has capability but requested organization/data scope is outside delegated scope", "submit command", ["denied before mutation", "no existence oracle for hidden object", "no cross-scope row or event"]),
        _case(f"{prefix}-STALE", command, "concurrency", "aggregate version differs from expected_version", "submit command", ["optimistic-concurrency conflict", "current version not overwritten", "caller can safely reload"]),
        _case(f"{prefix}-RETRY-SAME", command, "idempotency", "first attempt committed but response was lost", "retry same command_id and same payload", ["original result returned", "no duplicate aggregate event", "no duplicate outbox effect"]),
        _case(f"{prefix}-RETRY-MISMATCH", command, "idempotency", "command_id already exists with another payload hash", "retry with changed payload", ["idempotency conflict", "original result and state preserved", "security/audit event emitted"]),
    ]
    for invariant_index, invariant in enumerate(contract["invariants"], 1):
        cases.append(
            _case(
                f"{prefix}-INV-{invariant_index:02d}",
                command,
                "invariant",
                f"all conditions valid except: {invariant}",
                "submit command",
                ["rejected with stable validation code", "no accepted partial outcome", "no sensitive field echoed"],
            )
        )
    for stage_index, stage in enumerate(contract["failure_stages"], 1):
        cases.append(
            _case(
                f"{prefix}-FAULT-{stage_index:02d}",
                command,
                "fault_injection",
                f"inject process/database failure immediately after {stage}",
                "submit then retry after recovery",
                ["no partial accepted business outcome", "retry converges to exactly one result", "outbox and current pointer agree with aggregate version"],
            )
        )
    for check_index, check in enumerate(contract["reconciliation"], 1):
        cases.append(
            _case(
                f"{prefix}-RECON-{check_index:02d}",
                command,
                "reconciliation",
                f"seed a controlled mismatch in {check}",
                "run read-only reconciliation",
                ["mismatch detected deterministically", "source evidence and target keys identified", "no auto-fix or silent acceptance", "quarantine/owner state recorded"],
            )
        )
    return cases


def _query_cases(contract: dict[str, Any], index: int) -> list[dict[str, Any]]:
    query = contract["query"]
    prefix = f"EXT-Q{index:02d}"
    return [
        _case(f"{prefix}-HAPPY", query, "happy_path", "authorized actor and valid scoped records", "read two pages", ["only scoped records returned", "stable identifiers/status returned", "page tokens produce no duplicate or missing records"]),
        _case(f"{prefix}-AUTH-DENY", query, "authorization", "actor lacks query capability", "execute query", ["denied", "no result count or existence oracle", "denial audited"]),
        _case(f"{prefix}-SCOPE", query, "scope", "records exist in two organizations but actor has one", "filter with broad/forged scope", ["only delegated scope returned", "server ignores or rejects forged scope", "no hidden totals leaked"]),
        _case(f"{prefix}-PAGING", query, "pagination", "more rows than page_size with identical sort keys", "walk all pages twice", ["stable deterministic ordering", "same snapshot/cutoff produces same sequence", "no duplicate or omission"]),
        _case(f"{prefix}-CUTOFF", query, "freshness", "projection watermark is behind source event watermark", "execute query", ["cutoff/watermark and reconciliation status exposed", "stale result is not labeled current", "no mutation attempted"]),
        _case(f"{prefix}-NO-MUTATION", query, "read_only", "write-spy blocks any command/data mutation dependency", "execute every query branch", ["zero write/command call", "projection remains byte/row equivalent", "audit access may append only through isolated audit channel"]),
        _case(f"{prefix}-SENSITIVE", query, "privacy", "actor lacks sensitive-field sub-capability", "request sensitive balance/contact fields", ["fields omitted or access denied", "no value in log/cache/error", "aggregate-safe result remains available if authorized"]),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    contracts = _load(args.contracts)
    errors: list[str] = []
    if contracts.get("validation") != "PASS":
        errors.append("source target contracts are not PASS")

    cases: list[dict[str, Any]] = []
    for index, contract in enumerate(contracts["commands"], 1):
        cases.extend(_command_cases(contract, index))
    for index, contract in enumerate(contracts["queries"], 1):
        cases.extend(_query_cases(contract, index))

    surface_modules = {
        **{row["command"]: row["owner"] for row in contracts["commands"]},
        **{row["query"]: row["owner"] for row in contracts["queries"]},
    }
    for case in cases:
        case["target_module"] = surface_modules[case["surface"]]

    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case_id")
    categories = Counter(case["category"] for case in cases)
    for contract in contracts["commands"]:
        covered = {case["category"] for case in cases if case["surface"] == contract["command"]}
        required = {"happy_path", "authorization", "scope", "concurrency", "idempotency", "invariant", "fault_injection", "reconciliation"}
        if not required <= covered:
            errors.append(f"command coverage incomplete: {contract['command']}")
    for contract in contracts["queries"]:
        query_cases = [case for case in cases if case["surface"] == contract["query"]]
        if not any(case["category"] == "read_only" for case in query_cases):
            errors.append(f"query lacks no-mutation case: {contract['query']}")

    artifact = {
        "artifact": "negin_erp_material_extension_synthetic_golden_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_or_queries_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
        },
        "summary": {
            "command_surface_count": len(contracts["commands"]),
            "query_surface_count": len(contracts["queries"]),
            "case_count": len(cases),
            "category_counts": dict(sorted(categories.items())),
            "legacy_execution_allowed_count": sum(case["legacy_execution_allowed"] for case in cases),
            "validation_error_count": len(errors),
        },
        "cases": cases,
        "acceptance_gate": [
            "every case is implemented in an isolated target test harness",
            "fault tests demonstrate atomic rollback or deterministic retry convergence",
            "read-only query tests prove no mutation dependency is invoked",
            "reconciliation mismatches are detected and quarantined without automatic acceptance",
            "role/context matrix is approved before UAT and no test is run against operational Varanegar",
        ],
        "validation_errors": errors,
        "limits": [
            "Cases are synthetic target specifications and have not been executed.",
            "They validate known contracts but cannot discover missing business rules by themselves.",
            "Production fixtures, expected business values and role identities require owner-approved UAT data.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
