"""Build the evidence-backed P0 backlog for the Negin personal ERP.

This builder is offline and produces design contracts only. It does not create
a database, repository, service, user, role, migration, or runtime command.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _item(
    item_id: str,
    title: str,
    workstream: str,
    depends_on: list[str],
    deliverables: list[str],
    acceptance: list[str],
    evidence: list[str],
    *,
    status: str = "READY_FOR_REFINEMENT",
    signoff_role: str | None = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": title,
        "workstream": workstream,
        "status": status,
        "depends_on": depends_on,
        "signoff_role_template": signoff_role,
        "evidence_refs": evidence,
        "deliverables": deliverables,
        "acceptance": acceptance,
        "mandatory_tests": [
            "positive",
            "deny_or_invalid_context",
            "retry_or_replay_where_applicable",
            "audit_and_provenance",
        ],
        "prohibited_shortcuts": [
            "direct operational Varanegar write",
            "production identity or grant inference from aggregate evidence",
            "silent repair or dropping of legacy anomalies",
            "implementation claim without fresh tests and readback",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--migration", required=True, type=Path)
    parser.add_argument("--roles", required=True, type=Path)
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("--orchestrator-golden", required=True, type=Path)
    parser.add_argument("--extension-golden", required=True, type=Path)
    parser.add_argument("--report-golden", required=True, type=Path)
    parser.add_argument("--master-golden", required=True, type=Path)
    parser.add_argument("--foundation-golden", required=True, type=Path)
    parser.add_argument("--form-gaps", required=True, type=Path)
    parser.add_argument("--root-entrypoints", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    blueprint = _load(args.blueprint)
    migration = _load(args.migration)
    roles = _load(args.roles)
    golden = _load(args.golden)
    orchestrator_golden = _load(args.orchestrator_golden)
    extension_golden = _load(args.extension_golden)
    report_golden = _load(args.report_golden)
    master_golden = _load(args.master_golden)
    foundation_golden = _load(args.foundation_golden)
    gaps = _load(args.form_gaps)
    roots = _load(args.root_entrypoints)
    E = {
        "blueprint": args.blueprint.as_posix(),
        "migration": args.migration.as_posix(),
        "roles": args.roles.as_posix(),
        "golden": args.golden.as_posix(),
        "orchestrator_golden": args.orchestrator_golden.as_posix(),
        "extension_golden": args.extension_golden.as_posix(),
        "report_golden": args.report_golden.as_posix(),
        "master_golden": args.master_golden.as_posix(),
        "foundation_golden": args.foundation_golden.as_posix(),
        "form_gaps": args.form_gaps.as_posix(),
        "root_entrypoints": args.root_entrypoints.as_posix(),
    }

    items = [
        _item("P0-001", "select and record target technology stack", "architecture", [], ["signed ADR for backend, web, database, deployment and test stack"], ["stack supports Persian RTL, transactional SQL, migrations, background jobs and local deployment", "choice records rejected alternatives and support owner"], [E["blueprint"]], status="NEEDS_USER_DECISION"),
        _item("P0-002", "modular-monolith boundary and dependency rules", "architecture", ["P0-001"], ["module skeleton for fourteen ownership boundaries", "automated forbidden-dependency checks"], ["all fourteen blueprint modules exist", "cross-module writes are rejected outside application commands"], [E["blueprint"]]),
        _item("P0-003", "isolated target environments and least-privilege accounts", "platform", ["P0-001"], ["local development and isolated test databases", "separate migration, application and read-only accounts"], ["application account cannot alter schema", "test proves no route reaches operational Varanegar write credentials"], [E["blueprint"], E["migration"]], signoff_role="security_administrator"),
        _item("P0-004", "versioned schema migration pipeline", "platform", ["P0-002", "P0-003"], ["forward migration runner", "schema history and checksum table", "empty-database bootstrap test"], ["two consecutive runs converge", "failed migration is visible and cannot masquerade as success"], [E["blueprint"]]),
        _item("P0-005", "organization and operational-context kernel", "context", ["P0-004"], ["company/head-office, DC, sales-office, warehouse and fiscal-context schema", "explicit effective-date rules"], ["DC=0 and DC=1 remain distinguishable", "operational year and fiscal year are not interchangeable", "invalid context combinations are denied"], [E["blueprint"], E["migration"]]),
        _item("P0-006", "deny-first capability evaluation", "authorization", ["P0-004", "P0-005"], ["capability registry", "deny-first decision service", "decision reason codes"], ["explicit deny overrides allow", "menu visibility never authorizes a command", "45 atomic capabilities can be seeded without identities"], [E["roles"]], signoff_role="security_administrator"),
        _item("P0-007", "data-scope and context authorization", "authorization", ["P0-006"], ["DC, office, warehouse, route and own/team scope policy", "query and command guard adapters"], ["cross-scope reads and writes fail closed", "scope decision is included in audit evidence"], [E["roles"], E["blueprint"]], signoff_role="security_administrator"),
        _item("P0-008", "append-only audit contract", "platform", ["P0-004", "P0-006"], ["audit event schema", "actor/context/correlation/version provenance", "tamper-evident retention policy"], ["accepted and denied commands both emit bounded audit records", "audit records contain no secrets"], [E["blueprint"], E["roles"]]),
        _item("P0-009", "command envelope and optimistic concurrency", "platform", ["P0-004", "P0-008"], ["command_id, correlation_id, expected_version and context envelope", "standard result and reconciliation status"], ["stale version is rejected", "same command_id cannot create a second business outcome"], [E["blueprint"], E["golden"], E["orchestrator_golden"], E["extension_golden"], E["report_golden"], E["master_golden"], E["foundation_golden"]]),
        _item("P0-010", "idempotency receipt store", "platform", ["P0-009"], ["request fingerprint and durable result receipt", "in-progress/accepted/rejected/unknown states"], ["same key plus same payload returns original result", "same key plus changed payload is rejected", "crash-after-commit retry converges"], [E["golden"], E["orchestrator_golden"], E["extension_golden"], E["report_golden"], E["master_golden"], E["foundation_golden"]]),
        _item("P0-011", "transactional outbox and idempotent inbox", "platform", ["P0-009", "P0-010"], ["outbox/inbox schema", "lease/retry/dead-letter worker contract"], ["business commit and outbox append are atomic", "duplicate delivery changes no projection twice", "poison message is observable"], [E["blueprint"], E["orchestrator_golden"], E["extension_golden"], E["report_golden"], E["master_golden"], E["foundation_golden"]]),
        _item("P0-012", "correlation, metrics and structured logging", "observability", ["P0-008", "P0-011"], ["correlation propagation", "health/readiness endpoints", "bounded metric and log taxonomy"], ["command, outbox and import run share correlation id", "PII and secrets are redacted", "unknown reconciliation is alertable"], [E["blueprint"]]),
        _item("P0-013", "secret and configuration boundary", "configuration", ["P0-003", "P0-004"], ["externalized secret provider", "versioned typed configuration registry", "effective-value explanation"], ["no secret is stored in source, artifact or browser", "configuration precedence and effective dates are testable", "publisher cannot self-approve material policy"], [E["blueprint"], E["roles"]], signoff_role="configuration_publisher"),
        _item("P0-014", "read-only source snapshot adapter", "migration", ["P0-003", "P0-012"], ["least-privilege snapshot interface", "bounded batch and retry policy", "source watermark contract"], ["adapter refuses an updateable source", "no source connection secret is persisted in manifests", "snapshot never repairs source rows"], [E["migration"]], signoff_role="migration_operator"),
        _item("P0-015", "immutable snapshot manifest and provenance", "migration", ["P0-014"], ["snapshot/run manifest", "source object and extraction hash lineage", "business-date window metadata"], ["same source snapshot has reproducible fingerprints", "every imported row traces to source key and snapshot", "migration timestamp is not substituted for business date"], [E["migration"]], signoff_role="migration_reviewer"),
        _item("P0-016", "versioned crosswalk registry", "migration", ["P0-004", "P0-015"], ["source-system/key to target-UUID registry", "exact/derived/ambiguous/quarantined/retired statuses"], ["mapping history is immutable", "ambiguous or quarantined mapping cannot activate commands", "target identity never reuses mutable legacy codes"], [E["migration"]], signoff_role="migration_reviewer"),
        _item("P0-017", "quarantine and anomaly evidence registry", "migration", ["P0-016"], ["quarantine case schema", "owner/reason/evidence/decision lifecycle", "six known anomaly-class seeds"], ["all six aggregate anomaly baselines are represented without personal rows", "no case disappears without reviewed resolution", "unknown difference blocks acceptance"], [E["migration"]], signoff_role="migration_reviewer"),
        _item("P0-018", "reconciliation rule engine", "migration", ["P0-015", "P0-016", "P0-017"], ["row/count/amount/state/ledger reconciliation contracts", "blocking and explained-difference classifications"], ["zero unexplained blocking differences is a machine gate", "rule output identifies snapshot, slice and evidence", "re-run is deterministic"], [E["migration"]], signoff_role="migration_reviewer"),
        _item("P0-019", "import-run ledger and resumable slice execution", "migration", ["P0-018", "P0-010"], ["import run/slice/checkpoint schema", "resume and rollback-to-empty-test policy"], ["failed batch resumes without duplicate target rows", "every slice records counts, quarantine and reconciliation", "source write-back is impossible"], [E["migration"]], signoff_role="migration_operator"),
        _item("P0-020", "synthetic golden-case harness", "quality", ["P0-006", "P0-009", "P0-011"], ["fixture builders", "case runner for 877 contracts", "fault-injection hooks"], ["77 active-route, 154 orchestrator, 215 extension, 175 report, 64 customer/goods and 192 supplier/context/pricing cases are addressable", "no case runner accepts Varanegar or clone as execution target", "retry and failure-stage assertions are deterministic"], [E["golden"], E["orchestrator_golden"], E["extension_golden"], E["report_golden"], E["master_golden"], E["foundation_golden"]]),
        _item("P0-021", "backup, restore and disaster-recovery proof", "operations", ["P0-004", "P0-012"], ["encrypted backup job", "restore runbook", "restore verification record"], ["fresh isolated restore passes schema and audit checks", "RPO/RTO are recorded as user-approved targets", "restore drill does not touch Varanegar"], [E["blueprint"]], status="NEEDS_USER_DECISION"),
        _item("P0-022", "developer and operator runbooks", "operations", ["P0-012", "P0-019", "P0-021"], ["bootstrap, migration, import, reconciliation, backup and incident runbooks"], ["new environment can be rebuilt from documented commands", "every destructive target action requires exact target verification"], [E["blueprint"], E["migration"]]),
        _item("P0-023", "P1 read-only context and master query contract", "read_model", ["P0-005", "P0-007", "P0-018"], ["scoped organization/product/party/route query DTOs", "snapshot provenance and freshness fields"], ["queries are authenticated and scope-filtered", "unknown mappings are visible but not silently merged", "read model reconciles to approved snapshot"], [E["blueprint"], E["migration"]], signoff_role="business_reader"),
        _item("P0-024", "authenticated RTL web review shell", "web", ["P0-001", "P0-006", "P0-023"], ["Persian RTL shell", "context selector", "read-only master review and evidence drawer"], ["no command button exists in P0/P1 read-only slice", "context and denial reason are visible", "browser receives no source credentials"], [E["blueprint"]], status="BLOCKED_BY_P0_001", signoff_role="business_reader"),
        _item("P0-025", "unresolved legacy-entrypoint decision record", "evidence", [], ["owner-reviewed disposition for three unresolved roots", "retain/replace/retire rationale and evidence"], ["no root is retired from static absence alone", "decision covers bank reconciliation list/setup and special district options", "any retained capability receives owner and acceptance tests"], [E["form_gaps"], E["root_entrypoints"]], status="NEEDS_BUSINESS_OWNER_EVIDENCE"),
        _item("P0-026", "P0 exit review and signed gate", "governance", ["P0-002", "P0-007", "P0-013", "P0-019", "P0-020", "P0-022", "P0-025"], ["P0 evidence manifest", "open-risk register", "P1 authorization record"], ["all required dependencies pass fresh tests", "stack and recovery decisions are signed", "no operational write, dual-write, pilot or cutover is implied"], [E["blueprint"], E["migration"], E["roles"]], status="BLOCKED_BY_DEPENDENCIES", signoff_role="migration_reviewer"),
    ]

    ids = [row["id"] for row in items]
    id_set = set(ids)
    dependency_errors = sorted(
        f"{row['id']}->{dependency}"
        for row in items
        for dependency in row["depends_on"]
        if dependency not in id_set
    )
    duplicate_ids = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    module_ids = {row["id"] for row in blueprint["modules"]}
    role_names = {row["role"] for row in roles["role_templates"]}
    role_errors = sorted(
        row["id"] for row in items
        if row["signoff_role_template"] and row["signoff_role_template"] not in role_names
    )
    evidence = {
        "target_module_count": blueprint["module_count"],
        "target_module_ids": sorted(module_ids),
        "p0_blueprint_modules": next(row for row in blueprint["phases"] if row["id"] == "P0")["modules"],
        "migration_slice_count": migration["slice_count"],
        "role_template_count": roles["role_template_count"],
        "atomic_capability_count": roles["atomic_capability_count"],
        "synthetic_golden_case_count": golden["summary"]["case_count"] + orchestrator_golden["summary"]["case_count"] + extension_golden["summary"]["case_count"] + report_golden["summary"]["golden_case_count"] + master_golden["summary"]["case_count"] + foundation_golden["summary"]["case_count"],
        "material_extension_golden_case_count": extension_golden["summary"]["case_count"],
        "report_query_export_print_golden_case_count": report_golden["summary"]["golden_case_count"],
        "customer_goods_master_data_golden_case_count": master_golden["summary"]["case_count"],
        "supplier_context_pricing_golden_case_count": foundation_golden["summary"]["case_count"],
        "high_priority_form_gap_count": gaps["summary"]["priority_counts"]["high"],
        "unresolved_root_entrypoint_count": roots["summary"]["still_unresolved_root_count"],
    }
    validation_errors = dependency_errors + [f"duplicate:{x}" for x in duplicate_ids] + [f"unknown-role:{x}" for x in role_errors]
    artifact = {
        "artifact": "negin_personal_erp_p0_evidence_backed_backlog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_BACKLOG_DESIGN_FROM_REDACTED_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "files_outside_output_changed": 0,
            "source_or_target_commands_executed": 0,
            "environments_accounts_or_roles_created": 0,
            "production_write_pilot_or_cutover_authorized": 0,
        },
        "evidence": evidence,
        "planning_assumptions": {
            "architecture": "modular_monolith_first",
            "technology_stack": "not_selected_by_user",
            "blueprint_elapsed_estimate_weeks": [2, 3],
            "estimate_condition": "focused small team after stack, hosting, recovery targets and owner availability are decided",
            "single_developer_warning": "sum of task effort is not represented by the 2-3 week elapsed range and requires re-estimation after P0-001",
        },
        "summary": {
            "item_count": len(items),
            "workstream_count": len({row["workstream"] for row in items}),
            "ready_for_refinement_count": sum(row["status"] == "READY_FOR_REFINEMENT" for row in items),
            "needs_user_decision_count": sum(row["status"] == "NEEDS_USER_DECISION" for row in items),
            "needs_business_owner_evidence_count": sum(row["status"] == "NEEDS_BUSINESS_OWNER_EVIDENCE" for row in items),
            "blocked_by_dependency_count": sum(row["status"].startswith("BLOCKED_BY") for row in items),
            "dependency_edge_count": sum(len(row["depends_on"]) for row in items),
            "validation_error_count": len(validation_errors),
        },
        "definition_of_ready": [
            "evidence_refs exist and uncertainty is explicit",
            "owner and signoff role are known",
            "dependencies are complete",
            "positive, deny, retry and reconciliation tests are specified",
            "source/target environments and forbidden operations are explicit",
        ],
        "items": items,
        "validation_errors": validation_errors,
        "not_authorized": [
            "operational Varanegar write or command execution",
            "dual-write, pilot, production deployment or cutover",
            "real identity grants inferred from aggregate legacy evidence",
            "silent legacy cleanup or migration before reconciliation approval",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
