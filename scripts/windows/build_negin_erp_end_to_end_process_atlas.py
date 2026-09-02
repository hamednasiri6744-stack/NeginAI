"""Build an offline end-to-end process atlas from persisted Varanegar evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROCESS_DEFINITIONS = (
    {
        "id": "P01_FOUNDATION_GOVERNANCE",
        "title": "organization, authorization and effective configuration",
        "domain_ids": (1, 16, 17),
        "modules": ("platform", "organization_context", "identity_authorization", "configuration"),
        "surface_prefixes": (
            "authorization.",
            "configuration.",
            "organization_context.",
            "inventory.stock_accounting_context.",
        ),
        "state_machines": (),
        "gate": "deny-first role/context tests, versioned settings and four-eyes material publish",
    },
    {
        "id": "P02_MASTER_AND_PRICING",
        "title": "party, product and effective pricing preparation",
        "domain_ids": (2, 3, 4, 5, 6),
        "modules": ("master_data", "pricing_rules"),
        "surface_prefixes": (
            "party.",
            "pricing.",
            "master_data.",
            "pricing_rules.",
        ),
        "state_machines": (),
        "gate": "crosswalk quality, effective-date precedence and parallel identifier allocation tests",
    },
    {
        "id": "P03_ORDER_TO_SALE",
        "title": "order capture, confirmation, conversion and sale",
        "domain_ids": (7,),
        "modules": ("sales", "pricing_rules", "master_data", "accounting"),
        "surface_prefixes": ("order.",),
        "state_machines": (),
        "gate": "authorized idempotent order and conversion commands reconcile totals and posting provenance",
    },
    {
        "id": "P04_INVENTORY_TO_DELIVERY",
        "title": "reservation, stock voucher, exit and distribution delivery",
        "domain_ids": (8, 9),
        "modules": ("inventory", "distribution", "sales", "accounting"),
        "surface_prefixes": ("inventory.", "stock_voucher.", "distribution."),
        "state_machines": ("distribution",),
        "gate": "cardex parity, explicit reverse paths and no unexplained stock or route mismatch",
    },
    {
        "id": "P05_RETURN_TO_CREDIT",
        "title": "sales return, stock re-entry, credit and reversal",
        "domain_ids": (11,),
        "modules": ("sales", "inventory", "receivables_treasury", "accounting"),
        "surface_prefixes": ("sales_return.",),
        "state_machines": (),
        "gate": "return, stock, credit and accounting effects commit or quarantine with preserved source provenance",
    },
    {
        "id": "P06_COLLECTION_AND_RECEIVED_CHEQUE",
        "title": "receipt, allocation, received cheque lifecycle and customer balance",
        "domain_ids": (10, 12),
        "modules": ("receivables_treasury", "sales", "accounting"),
        "surface_prefixes": ("received_cheque.",),
        "state_machines": ("received_cheque",),
        "gate": "allowed-edge validation, immutable history/current pointer and allocation/open-invoice reconciliation",
    },
    {
        "id": "P07_PROCURE_TO_PAY",
        "title": "supplier invoice, return, disbursement and payable cheque",
        "domain_ids": (13, 14, 15),
        "modules": ("procurement_payables", "inventory", "accounting"),
        "surface_prefixes": ("supplier_", "payable_cheque."),
        "state_machines": ("payable_cheque",),
        "gate": "supplier cardex, stock relation, payment link and cheque-book lifecycle reconcile",
    },
    {
        "id": "P08_LEDGER_POSTING",
        "title": "pre-voucher, external voucher, journal posting and reversal",
        "domain_ids": (18,),
        "modules": ("accounting", "platform"),
        "surface_prefixes": (),
        "state_machines": (),
        "gate": "balanced entries, immutable versions, current pointer and reversal/fiscal-close UAT",
    },
    {
        "id": "P09_POS_SESSION_REPLICATION",
        "title": "POS safe/session query and receipt batch replication",
        "domain_ids": (),
        "modules": ("sales", "inventory", "receivables_treasury", "accounting", "integration_migration", "platform"),
        "surface_prefixes": ("pos.",),
        "state_machines": (),
        "gate": "snapshot hash, per-receipt idempotency, quarantine and six-boundary reconciliation without source write-back",
    },
    {
        "id": "P10_REPORTING_AND_MIGRATION",
        "title": "read models, reports, exports, snapshot import and reconciliation",
        "domain_ids": (),
        "modules": ("reporting_documents", "integration_migration", "platform"),
        "surface_prefixes": (),
        "state_machines": (),
        "gate": "bounded read models, privacy/export controls, fresh snapshot and Golden reconciliation",
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", required=True, type=Path)
    parser.add_argument("--state-machines", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--traceability", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    workflows = _load(args.workflows)
    states = _load(args.state_machines)
    reports = _load(args.reports)
    traceability = _load(args.traceability)

    module_rows = {row["module"]: row for row in traceability["modules"]}
    all_modules = set(module_rows)
    errors = []
    process_rows = []
    workflow_assignments: dict[str, list[str]] = {}
    report_assignments: dict[str, list[str]] = {}
    state_assignments: dict[str, list[str]] = {}
    golden_assignments: dict[str, list[str]] = {}

    for definition in PROCESS_DEFINITIONS:
        process_id = definition["id"]
        unknown = set(definition["modules"]) - all_modules
        if unknown:
            errors.append(f"{process_id} has unknown modules: {','.join(sorted(unknown))}")

        selected_workflows = [
            row for row in workflows["workflows"] if row.get("primary_domain_id") in definition["domain_ids"]
        ]
        selected_reports = (
            list(reports["surfaces"])
            if process_id == "P10_REPORTING_AND_MIGRATION"
            else [row for row in reports["surfaces"] if row.get("primary_domain_id") in definition["domain_ids"]]
        )
        selected_states = [
            row for row in states["state_machines"] if row["machine_id"] in definition["state_machines"]
        ]
        selected_golden = []
        seen_cases = set()
        for module in definition["modules"]:
            for case in module_rows[module]["golden_cases"]:
                if definition["surface_prefixes"] and not case["surface"].startswith(definition["surface_prefixes"]):
                    continue
                if case["case_id"] not in seen_cases:
                    seen_cases.add(case["case_id"])
                    selected_golden.append(case)
        selected_risks = sorted(
            {
                risk["id"]: risk
                for module in definition["modules"]
                for risk in module_rows[module]["risks"]
            }.values(),
            key=lambda row: row["id"],
        )

        for row in selected_workflows:
            workflow_assignments.setdefault(row["type"], []).append(process_id)
        for row in selected_reports:
            report_assignments.setdefault(row["type"], []).append(process_id)
        for row in selected_states:
            state_assignments.setdefault(row["machine_id"], []).append(process_id)
        for row in selected_golden:
            golden_assignments.setdefault(row["case_id"], []).append(process_id)

        process_rows.append(
            {
                "process_id": process_id,
                "title": definition["title"],
                "source_domain_ids": list(definition["domain_ids"]),
                "target_modules": list(definition["modules"]),
                "workflow_surface_count": len(selected_workflows),
                "workflow_surfaces": [
                    {
                        "type": row["type"],
                        "command_method_count": len(row["command_methods"]),
                        "query_method_count": len(row["query_methods"]),
                        "external_contract_call_count": len(row["external_contract_calls"]),
                    }
                    for row in selected_workflows
                ],
                "report_surface_count": len(selected_reports),
                "report_surfaces": [
                    {"type": row["type"], "classification": row["classification"], "output_contract": row["output_contract"]}
                    for row in selected_reports
                ],
                "state_machine_count": len(selected_states),
                "state_machines": [
                    {
                        "machine_id": row["machine_id"],
                        "state_count": len(row["states"]),
                        "observed_transition_count": len(row["observed_transitions"]),
                        "allowed_transition_count": len(row.get("allowed_transitions") or []),
                    }
                    for row in selected_states
                ],
                "target_golden_case_count": len(selected_golden),
                "target_golden_case_source_counts": {
                    source: sum(case["source"] == source for case in selected_golden)
                    for source in (
                        "core",
                        "orchestrator",
                        "extension",
                        "report",
                        "master",
                        "foundation",
                    )
                },
                "target_surfaces": sorted({case["surface"] for case in selected_golden}),
                "open_risk_count": len(selected_risks),
                "critical_risk_ids": [risk["id"] for risk in selected_risks if risk["severity"] == "CRITICAL"],
                "open_risk_ids": [risk["id"] for risk in selected_risks],
                "acceptance_gate": definition["gate"],
                "implementation_ready": False,
                "pilot_ready": False,
                "production_ready": False,
            }
        )

    for row in process_rows:
        if sum(row["target_golden_case_source_counts"].values()) != row["target_golden_case_count"]:
            errors.append(f"{row['process_id']} Golden source count mismatch")

    all_workflow_types = {row["type"] for row in workflows["workflows"]}
    all_report_types = {row["type"] for row in reports["surfaces"]}
    all_state_ids = {row["machine_id"] for row in states["state_machines"]}
    all_golden_case_ids = {
        case["case_id"]
        for module in traceability["modules"]
        for case in module["golden_cases"]
    }
    if set(workflow_assignments) != all_workflow_types:
        errors.append("workflow coverage mismatch")
    if set(report_assignments) != all_report_types:
        errors.append("report coverage mismatch")
    if set(state_assignments) != all_state_ids:
        errors.append("state machine coverage mismatch")
    if any(len(owners) != 1 for owners in state_assignments.values()):
        errors.append("state machine must have exactly one primary process")
    if set(golden_assignments) != all_golden_case_ids:
        errors.append("Golden case process coverage mismatch")

    artifact = {
        "artifact": "negin_personal_erp_end_to_end_process_evidence_atlas",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_PERSISTED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "implementation_or_release_readiness_inferred": 0,
        },
        "sources": {
            name: {"path": path.as_posix(), "sha256": _sha(path)}
            for name, path in {
                "workflows": args.workflows,
                "state_machines": args.state_machines,
                "reports": args.reports,
                "traceability": args.traceability,
            }.items()
        },
        "summary": {
            "process_count": len(process_rows),
            "unique_workflow_surface_count": len(all_workflow_types),
            "workflow_assignment_count": sum(len(value) for value in workflow_assignments.values()),
            "unique_report_surface_count": len(all_report_types),
            "report_assignment_count": sum(len(value) for value in report_assignments.values()),
            "state_machine_count": len(all_state_ids),
            "state_machine_assignment_count": sum(len(value) for value in state_assignments.values()),
            "unique_golden_case_count": len(all_golden_case_ids),
            "golden_case_assignment_count": sum(len(value) for value in golden_assignments.values()),
            "unassigned_golden_case_count": len(all_golden_case_ids - set(golden_assignments)),
            "process_with_target_golden_cases_count": sum(bool(row["target_golden_case_count"]) for row in process_rows),
            "process_with_critical_risk_count": sum(bool(row["critical_risk_ids"]) for row in process_rows),
            "implementation_ready_process_count": 0,
            "pilot_ready_process_count": 0,
            "production_ready_process_count": 0,
            "validation_error_count": len(errors),
        },
        "processes": process_rows,
        "coverage": {
            "workflow_assignments": workflow_assignments,
            "report_assignments": report_assignments,
            "state_machine_assignments": state_assignments,
            "golden_case_assignments": golden_assignments,
        },
        "validation_errors": errors,
        "limits": [
            "A process is an ERP design boundary derived from evidence, not a claim that legacy Varanegar uses the same named boundary.",
            "Workflow and report surfaces can participate in more than one end-to-end business process.",
            "Implementation, authenticated UAT, pilot and production readiness remain false.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
