"""Build an offline stack and recovery ADR input from local project evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _requirement_names(path: Path) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"[A-Za-z0-9_.-]+", line)
        if match:
            names.append(match.group(0).casefold())
    return sorted(set(names))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--backlog", required=True, type=Path)
    parser.add_argument("--traceability", required=True, type=Path)
    parser.add_argument("--risks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    project = args.project_root.resolve()
    blueprint = _load(args.blueprint)
    backlog = _load(args.backlog)
    traceability = _load(args.traceability)
    risks = _load(args.risks)
    requirements = project / "requirements.txt"

    app_python = sorted((project / "app").rglob("*.py"))
    route_python = sorted((project / "app" / "routes").glob("*.py"))
    static_files = [path for path in (project / "app" / "static").glob("*") if path.is_file()]
    tests = sorted((project / "tests").glob("test_*.py"))
    extensions = Counter(path.suffix.casefold() or "[none]" for path in static_files)
    package_names = _requirement_names(requirements)
    expected_packages = {"fastapi", "uvicorn", "pyodbc", "python-tds", "pytest"}
    errors = []
    if not expected_packages <= set(package_names):
        errors.append("expected current-stack packages missing")
    if traceability["summary"]["command_ready_module_count"] != 0:
        errors.append("traceability unexpectedly claims command readiness")

    decision_items = [item for item in backlog["items"] if item["status"] == "NEEDS_USER_DECISION"]
    critical_risks = [risk["id"] for risk in risks["risks"] if risk["severity"] == "CRITICAL"]
    artifact = {
        "artifact": "negin_personal_erp_stack_and_recovery_adr_decision_input",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "decision_status": "NEEDS_USER_DECISION_NOT_AN_APPROVED_ADR",
        "safety": {
            "mode": "OFFLINE_LOCAL_REPOSITORY_METADATA_AND_REDACTED_EVIDENCE",
            "environment_or_secret_files_read": 0,
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "production_stack_or_recovery_target_approved": 0,
        },
        "sources": {
            "blueprint": {"path": args.blueprint.as_posix(), "sha256": _sha(args.blueprint)},
            "backlog": {"path": args.backlog.as_posix(), "sha256": _sha(args.backlog)},
            "traceability": {"path": args.traceability.as_posix(), "sha256": _sha(args.traceability)},
            "risks": {"path": args.risks.as_posix(), "sha256": _sha(args.risks)},
            "requirements": {"path": requirements.as_posix(), "sha256": _sha(requirements)},
        },
        "current_project_evidence": {
            "python_app_file_count": len(app_python),
            "fastapi_route_module_count": len(route_python),
            "python_test_module_count": len(tests),
            "static_asset_extension_counts": dict(sorted(extensions.items())),
            "declared_python_packages": package_names,
            "observed_capabilities": [
                "FastAPI HTTP application",
                "SQL Server read adapters through pyodbc/python-tds",
                "local SQLite state",
                "plain HTML/CSS/JavaScript PWA assets",
                "pytest test suite",
                "Android and iOS companion source trees",
                "Caddy reverse-proxy configuration",
            ],
        },
        "mandatory_target_properties": [
            "Persian RTL and Jalali/business-date correctness",
            "transactional relational database with migrations and constraints",
            "modular monolith with one write owner per aggregate/table",
            "idempotent commands, audit, outbox/inbox and background jobs",
            "versioned settings, optimistic concurrency and approval/SoD",
            "read-only Varanegar adapters with no operational write credential",
            "rebuildable projections, reconciliation and quarantine",
            "repeatable tests, backup and isolated restore drills",
        ],
        "recommended_direction": {
            "status": "PROPOSAL_PENDING_USER_APPROVAL",
            "architecture": "modular monolith first",
            "backend": "evolve the existing Python/FastAPI capability into explicit domain modules",
            "web": "new TypeScript component-based RTL ERP shell; keep existing PWA as integration/reference, not the 445-form implementation surface",
            "database": "user decision between SQL Server and PostgreSQL; do not use SQLite as the multi-user financial system of record",
            "jobs": "database-backed jobs plus transactional outbox/inbox initially; add a separate broker only after measured need",
            "deployment": "one application boundary and one target database per environment behind the existing reverse-proxy pattern",
            "reasoning": [
                "reuses the project's strongest tested backend and SQL integration skills",
                "avoids a full backend rewrite before domain semantics stabilize",
                "typed component UI is more maintainable than extending one large plain-JavaScript ERP surface",
                "modular monolith matches the cross-domain transaction and reconciliation risks better than early microservices",
            ],
        },
        "alternatives": [
            {
                "id": "dotnet_sqlserver_typed_web",
                "fit": "strong when the long-term support team is primarily .NET/SQL Server and licensing/operations are already owned",
                "cost": "backend rewrite and duplicate platform/auth/integration effort before parity is proven",
                "decision": "viable_not_preferred_from_current_repository_evidence",
            },
            {
                "id": "extend_current_plain_js_and_sqlite",
                "fit": "acceptable for prototypes and offline personal control slices",
                "cost": "weak fit for concurrent financial ledgers, migrations, large form surface and long-lived typed UI contracts",
                "decision": "reject_for_full_write_enabled_erp",
            },
            {
                "id": "microservices_first",
                "fit": "possible after independent scaling and ownership needs are measured",
                "cost": "adds distributed failure, transaction, deployment and observability complexity now",
                "decision": "defer_until_measured_need",
            },
        ],
        "recovery_target_options": [
            {
                "id": "B_STANDARD_BUSINESS",
                "recommended": True,
                "rpo": "<= 5 minutes for committed financial data",
                "rto": "<= 60 minutes during supported business hours",
                "minimum_proof": ["continuous or frequent log/WAL backup", "daily encrypted full backup", "quarterly isolated restore drill", "application plus reconciliation smoke test"],
            },
            {
                "id": "A_COST_SENSITIVE",
                "recommended": False,
                "rpo": "<= 15 minutes",
                "rto": "<= 2 hours",
                "minimum_proof": ["frequent incremental/log backup", "daily encrypted full backup", "quarterly isolated restore drill"],
            },
            {
                "id": "C_HIGH_AVAILABILITY",
                "recommended": False,
                "rpo": "near zero",
                "rto": "<= 15 minutes",
                "minimum_proof": ["replicated database", "automated failover with split-brain controls", "scheduled failover and restore drills"],
            },
        ],
        "user_decisions_required": [
            "long-term support owner and strongest backend/database skill",
            "target database: SQL Server or PostgreSQL",
            "deployment environment: current Windows host, separate Windows server, or Linux VM/container",
            "approved recovery tier and business-hours support window",
            "number of concurrent users and expected first-year growth",
            "whether offline warehouse/seller operation is required in the first ERP release",
        ],
        "evidence_checkpoint": {
            "target_module_count": traceability["summary"]["module_count"],
            "golden_case_count": traceability["summary"]["mapped_golden_case_count"],
            "open_risk_count": risks["summary"]["open_count"],
            "critical_risk_ids": critical_risks,
            "needs_user_decision_backlog_ids": [item["id"] for item in decision_items],
            "estimated_total_weeks": blueprint["estimated_total_weeks"],
            "first_usable_read_only_slice_weeks": blueprint["first_usable_read_only_slice_weeks"],
        },
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({
        "validation": artifact["validation"],
        "python_app_file_count": len(app_python),
        "fastapi_route_module_count": len(route_python),
        "python_test_module_count": len(tests),
        "decision_item_count": len(decision_items),
        "critical_risk_count": len(critical_risks),
    }, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

