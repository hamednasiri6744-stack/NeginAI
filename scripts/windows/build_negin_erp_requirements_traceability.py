"""Build an offline evidence-to-module traceability matrix for Negin ERP."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


CORE_COMMAND_MODULE = {
    "distribution": "distribution",
    "inventory": "inventory",
    "received_cheque": "receivables_treasury",
    "payable_cheque": "procurement_payables",
}
ORCHESTRATOR_COMMAND_MODULE = {
    "order": "sales",
    "sales_return": "sales",
    "supplier_invoice": "procurement_payables",
    "supplier_return": "procurement_payables",
    "stock_voucher": "inventory",
}
MASTER_COMMAND_MODULE = {"master_data": "master_data"}
WORKSTREAM_MODULE = {
    "architecture": "platform",
    "authorization": "identity_authorization",
    "configuration": "configuration",
    "context": "organization_context",
    "evidence": "integration_migration",
    "governance": "platform",
    "migration": "integration_migration",
    "observability": "platform",
    "operations": "platform",
    "platform": "platform",
    "quality": "platform",
    "read_model": "reporting_documents",
    "web": "platform",
}
ACTIVITY_DOMAIN_MODULES = {
    "collections_payments_and_open_invoices": ("receivables_treasury",),
    "distribution_and_delivery": ("distribution",),
    "general_ledger_staging_and_posting": ("accounting",),
    "inventory_reservation_and_exit": ("inventory",),
    "order_to_sale_lifecycle": ("sales",),
    "parties_customers_suppliers_personnel": ("master_data",),
    "pricing_discounts_and_prizes": ("pricing_rules",),
    "product_catalog": ("master_data",),
    "received_cheque_lifecycle_and_returned_cheque_settlement": ("receivables_treasury",),
    "sales_returns_stock_entry_and_credit_settlement": ("sales", "inventory", "receivables_treasury"),
    "supplier_disbursement_and_payable_cheque_lifecycle": ("procurement_payables",),
    "supplier_purchase_returns_and_payables": ("procurement_payables",),
    "units_stock_and_document_types": ("organization_context", "master_data"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prefix(command: str) -> str:
    return command.split(".", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--risks", required=True, type=Path)
    parser.add_argument("--backlog", required=True, type=Path)
    parser.add_argument("--core-golden", required=True, type=Path)
    parser.add_argument("--orchestrator-golden", required=True, type=Path)
    parser.add_argument("--extension-golden", required=True, type=Path)
    parser.add_argument("--report-golden", required=True, type=Path)
    parser.add_argument("--master-golden", required=True, type=Path)
    parser.add_argument("--foundation-golden", required=True, type=Path)
    parser.add_argument("--activity", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {
        "readiness": args.readiness,
        "risks": args.risks,
        "backlog": args.backlog,
        "core_golden": args.core_golden,
        "orchestrator_golden": args.orchestrator_golden,
        "extension_golden": args.extension_golden,
        "report_golden": args.report_golden,
        "master_golden": args.master_golden,
        "foundation_golden": args.foundation_golden,
        "activity": args.activity,
    }
    payloads = {name: _load(path) for name, path in paths.items()}
    readiness = payloads["readiness"]
    risks = payloads["risks"]
    backlog = payloads["backlog"]
    core = payloads["core_golden"]
    orchestrator = payloads["orchestrator_golden"]
    extension = payloads["extension_golden"]
    report_golden = payloads["report_golden"]
    master_golden = payloads["master_golden"]
    foundation_golden = payloads["foundation_golden"]
    activity = payloads["activity"]

    module_ids = [row["module"] for row in readiness["modules"]]
    module_set = set(module_ids)
    errors: list[str] = []
    for name, payload in payloads.items():
        if payload.get("validation") not in (None, "PASS"):
            errors.append(f"source {name} is not PASS")

    golden_by_module: dict[str, list[dict[str, str]]] = defaultdict(list)
    unmapped_golden: list[str] = []
    for case in core["cases"]:
        module = CORE_COMMAND_MODULE.get(_prefix(case["command"]))
        if module:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "core", "surface": case["command"]})
        else:
            unmapped_golden.append(case["case_id"])
    for case in orchestrator["cases"]:
        module = ORCHESTRATOR_COMMAND_MODULE.get(_prefix(case["command"]))
        if module:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "orchestrator", "surface": case["command"]})
        else:
            unmapped_golden.append(case["case_id"])
    for case in extension["cases"]:
        module = case.get("target_module")
        if module in module_set:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "extension", "surface": case["surface"]})
        else:
            unmapped_golden.append(case["case_id"])
    for case in report_golden["golden_cases"]:
        module = case.get("target_module")
        if module in module_set:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "report", "surface": case["surface"]})
        else:
            unmapped_golden.append(case["case_id"])
    for case in master_golden["cases"]:
        module = MASTER_COMMAND_MODULE.get(_prefix(case["command"]))
        if module:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "master", "surface": case["command"]})
        else:
            unmapped_golden.append(case["case_id"])
    for case in foundation_golden["cases"]:
        module = case.get("target_module")
        if module in module_set:
            golden_by_module[module].append({"case_id": case["case_id"], "source": "foundation", "surface": case["command"]})
        else:
            unmapped_golden.append(case["case_id"])

    risks_by_module: dict[str, list[dict[str, str]]] = defaultdict(list)
    for risk in risks["risks"]:
        for module in risk["modules"]:
            if module not in module_set:
                errors.append(f"risk {risk['id']} references unknown module {module}")
                continue
            risks_by_module[module].append(
                {"id": risk["id"], "severity": risk["severity"], "title": risk["title"], "status": risk["status"]}
            )

    backlog_by_module: dict[str, list[dict[str, str]]] = defaultdict(list)
    unmapped_backlog: list[str] = []
    for item in backlog["items"]:
        module = WORKSTREAM_MODULE.get(item["workstream"])
        if module:
            backlog_by_module[module].append(
                {"id": item["id"], "status": item["status"], "workstream": item["workstream"], "title": item["title"]}
            )
        else:
            unmapped_backlog.append(item["id"])

    activity_by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmapped_activity: list[str] = []
    for source in activity["sources"]:
        mapped_modules = ACTIVITY_DOMAIN_MODULES.get(source["domain"], ())
        if not mapped_modules:
            unmapped_activity.append(source["domain"])
            continue
        ref = {
            "domain": source["domain"],
            "artifact": source["artifact"],
            "window_block_count": source["window_block_count"],
            "window_json_paths": [block["json_path"] for block in source["window_blocks"]],
        }
        for module in mapped_modules:
            activity_by_module[module].append(ref)

    rows: list[dict[str, Any]] = []
    for source_row in readiness["modules"]:
        module = source_row["module"]
        module_risks = sorted(risks_by_module[module], key=lambda row: row["id"])
        module_backlog = sorted(backlog_by_module[module], key=lambda row: row["id"])
        module_golden = sorted(golden_by_module[module], key=lambda row: (row["source"], row["case_id"]))
        module_activity = sorted(activity_by_module[module], key=lambda row: row["domain"])
        evidence_counts = source_row["evidence_counts"]
        rows.append(
            {
                "module": module,
                "implementation_readiness": source_row["implementation_readiness"],
                "knowledge_status": source_row["knowledge_status"],
                "source_domains": source_row["source_domains"],
                "owns": source_row["owns"],
                "depends_on": source_row["depends_on"],
                "evidence_counts": evidence_counts,
                "golden_case_count": len(module_golden),
                "golden_case_source_counts": dict(sorted(Counter(row["source"] for row in module_golden).items())),
                "golden_cases": module_golden,
                "open_risk_count": len(module_risks),
                "risk_severity_counts": dict(sorted(Counter(row["severity"] for row in module_risks).items())),
                "risks": module_risks,
                "direct_p0_item_count": len(module_backlog),
                "direct_p0_items": module_backlog,
                "three_month_activity_evidence_count": len(module_activity),
                "three_month_activity_evidence": module_activity,
                "open_blockers": source_row["open_blockers"],
                "traceability_status": (
                    "TARGET_FOUNDATION_TRACED_WITH_OPEN_GATES"
                    if not source_row["source_domains"]
                    and (module_golden or module_backlog or evidence_counts["report_surface_count"])
                    else "MULTI_SOURCE_TRACED_WITH_OPEN_GATES"
                    if source_row["source_domains"]
                    and (
                        module_golden
                        or evidence_counts["domain_form_candidate_count"]
                        or evidence_counts["workflow_surface_count"]
                        or evidence_counts["report_surface_count"]
                    )
                    else "DESIGN_ONLY_EVIDENCE_GAP"
                ),
            }
        )

    expected_golden = core["summary"]["case_count"] + orchestrator["summary"]["case_count"] + extension["summary"]["case_count"] + report_golden["summary"]["golden_case_count"] + master_golden["summary"]["case_count"] + foundation_golden["summary"]["case_count"]
    mapped_golden = sum(row["golden_case_count"] for row in rows)
    if unmapped_golden:
        errors.append(f"{len(unmapped_golden)} golden cases unmapped")
    if mapped_golden != expected_golden:
        errors.append(f"mapped golden count {mapped_golden} != expected {expected_golden}")
    if unmapped_backlog:
        errors.append(f"{len(unmapped_backlog)} backlog items unmapped")
    if unmapped_activity:
        errors.append(f"{len(unmapped_activity)} activity domains unmapped")
    if len(rows) != 14:
        errors.append(f"module count {len(rows)} != 14")

    artifact = {
        "artifact": "negin_personal_erp_requirement_evidence_test_risk_traceability_matrix",
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
            "implementation_or_production_readiness_inferred": 0,
        },
        "sources": {name: {"path": path.as_posix(), "sha256": _sha(path)} for name, path in paths.items()},
        "mapping_policy": {
            "core_command_prefix_to_module": CORE_COMMAND_MODULE,
            "orchestrator_command_prefix_to_module": ORCHESTRATOR_COMMAND_MODULE,
            "master_command_prefix_to_module": MASTER_COMMAND_MODULE,
            "backlog_workstream_to_direct_owner_module": WORKSTREAM_MODULE,
            "activity_domain_to_modules": ACTIVITY_DOMAIN_MODULES,
            "extension_cases_use_persisted_target_module": True,
            "report_cases_use_persisted_target_module": True,
            "direct_p0_mapping_does_not_remove_cross_module_dependencies": True,
        },
        "summary": {
            "module_count": len(rows),
            "traced_module_count": sum(row["traceability_status"] != "DESIGN_ONLY_EVIDENCE_GAP" for row in rows),
            "design_only_evidence_gap_module_count": sum(row["traceability_status"] == "DESIGN_ONLY_EVIDENCE_GAP" for row in rows),
            "mapped_golden_case_count": mapped_golden,
            "mapped_risk_assignment_count": sum(row["open_risk_count"] for row in rows),
            "unique_risk_count": len(risks["risks"]),
            "mapped_p0_item_count": sum(row["direct_p0_item_count"] for row in rows),
            "mapped_three_month_activity_block_count": sum(
                source["window_block_count"] for source in activity["sources"]
            ),
            "module_with_direct_three_month_activity_evidence_count": sum(
                bool(row["three_month_activity_evidence_count"]) for row in rows
            ),
            "module_with_critical_risk_count": sum("CRITICAL" in row["risk_severity_counts"] for row in rows),
            "command_ready_module_count": sum(row["implementation_readiness"].startswith("COMMAND_READY") for row in rows),
            "validation_error_count": len(errors),
        },
        "modules": rows,
        "unmapped": {
            "golden_case_ids": unmapped_golden,
            "p0_item_ids": unmapped_backlog,
            "activity_domains": unmapped_activity,
        },
        "validation_errors": errors,
        "interpretation": [
            "Traceability links evidence and test obligations; it does not prove implementation, UAT, pilot, or production readiness.",
            "Risk assignments can be many-to-many, so assignment count is larger than unique risk count.",
            "P0 workstream ownership is an explicit planning rule and not a claim about legacy Varanegar ownership.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
