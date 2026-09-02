"""Build a 14-module evidence density and readiness matrix for Negin ERP."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DOMAIN_TO_MODULES = {
    1: ("organization_context",),
    2: ("master_data",),
    3: ("master_data", "organization_context"),
    4: ("master_data",),
    5: ("master_data",),
    6: ("pricing_rules",),
    7: ("sales",),
    8: ("inventory",),
    9: ("distribution",),
    10: ("receivables_treasury",),
    11: ("sales", "inventory", "receivables_treasury"),
    12: ("receivables_treasury",),
    13: ("procurement_payables",),
    14: ("procurement_payables",),
    15: ("procurement_payables", "accounting"),
    16: ("identity_authorization",),
    17: ("configuration",),
    18: ("accounting",),
}

HIGH_GAP_MODULE = {
    "TreasuryOld.Forms.frmBankReconciliation": "receivables_treasury",
    "TreasuryOld.Forms.frmBankReconciliationList": "receivables_treasury",
    "TreasuryOld.Forms.frmChek": "procurement_payables",
    "TreasuryOld.Forms.frmList": "reporting_documents",
    "TreasuryOld.Forms.frmReconciliation": "receivables_treasury",
    "TreasuryOld.Forms.frmReconciliationSetup": "receivables_treasury",
    "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict": "configuration",
}

BLOCKERS = {
    "platform": ["technology stack not selected", "RPO/RTO and deployment ownership not selected"],
    "organization_context": ["business-owner confirmation of head-office DC=0 versus operational DC=1", "valid office/warehouse/context combinations need UAT"],
    "identity_authorization": ["identity source and real role assignments are not authorized", "aggregate legacy rights cannot be converted to grants"],
    "configuration": ["effective precedence and material-setting approval owners need signoff", "SpecialOptionsDistrict entrypoint and live usage remain unresolved"],
    "master_data": ["barcode duplicates/sentinels and legacy-to-NGT route crosswalk require quarantine decisions", "party duplicate indicators must not trigger automatic merge"],
    "pricing_rules": ["effective rule precedence and customer/product qualification need owner UAT", "legacy MAX(Id)+1 must be replaced and parallel allocation tested"],
    "sales": ["order-to-sale conversion and return side effects need transaction-boundary implementation", "command contracts are synthetic design only"],
    "inventory": ["zero unexplained residuals on the clone, but the 1,594-key open-sale stock obligation formula must be preserved", "ledger, operational obligations and stock projection must be independently rebuildable before commands"],
    "distribution": ["26,086 distributions carry a valid mode-dependent integer path code, but human labels and route hierarchy require an authoritative crosswalk", "exit/distribution multi-aggregate failures need target fault tests"],
    "receivables_treasury": ["sales-return gross/net contract is now verified with zero official residual across 14,091 returns; 49 cross-customer settlements still require disposition", "bank reconciliation has target contracts for profile, isolated staging, scoped read model, state machine and command envelope; only the first three bounded slices may start, while real profile rows, runtime formula/alias/tolerance parity, authenticated UAT, cancel/reversal ownership and target transaction implementation remain unresolved"],
    "procurement_payables": ["155 SOURCE_USED_UNLINKED cheque leaves require an owner-approved reuse policy because historical actor/time provenance is absent", "supplier cardex parity and payable workflow require owner signoff"],
    "accounting": ["1094 CURRENT_POINTER_HISTORY_FORK vouchers, 14946 detached events and one DRAFT_EMPTY_NUMBERED_SHELL require accountant disposition before posting/numbering enablement", "posting/reversal and fiscal-close UAT are not complete"],
    "reporting_documents": ["stateful print-completed surfaces must not be treated as pure reads", "report parity, export privacy and document provenance need UAT"],
    "integration_migration": ["no source snapshot/import run has been executed", "dual-write, pilot and cutover remain unauthorized"],
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _command_module(command: str) -> str:
    if command.startswith("master_data."):
        return "master_data"
    if command.startswith(("order.", "sales_return.")):
        return "sales"
    if command.startswith("distribution."):
        return "distribution"
    if command.startswith("received_cheque."):
        return "receivables_treasury"
    if command.startswith(("payable_cheque.", "supplier_")):
        return "procurement_payables"
    if command.startswith(("stock_voucher.", "inventory.")):
        return "inventory"
    raise ValueError(f"unmapped command prefix: {command}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--forms", required=True, type=Path)
    parser.add_argument("--calls", required=True, type=Path)
    parser.add_argument("--workflows", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("--orchestrator-golden", required=True, type=Path)
    parser.add_argument("--extension-golden", required=True, type=Path)
    parser.add_argument("--report-golden", required=True, type=Path)
    parser.add_argument("--master-golden", required=True, type=Path)
    parser.add_argument("--foundation-golden", required=True, type=Path)
    parser.add_argument("--bank-reconciliation-golden", required=True, type=Path)
    parser.add_argument("--migration", required=True, type=Path)
    parser.add_argument("--gaps", required=True, type=Path)
    parser.add_argument("--roots", required=True, type=Path)
    parser.add_argument("--p0-backlog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = _load(args.manifest)
    blueprint = _load(args.blueprint)
    forms = _load(args.forms)
    calls = _load(args.calls)
    workflows = _load(args.workflows)
    reports = _load(args.reports)
    golden = _load(args.golden)
    orchestrator = _load(args.orchestrator_golden)
    extension = _load(args.extension_golden)
    report_golden = _load(args.report_golden)
    master_golden = _load(args.master_golden)
    foundation_golden = _load(args.foundation_golden)
    bank_reconciliation_golden = _load(args.bank_reconciliation_golden)
    migration = _load(args.migration)
    gaps = _load(args.gaps)
    roots = _load(args.roots)
    p0 = _load(args.p0_backlog)

    domain_by_stage = {row["stage"]: row for row in manifest["domains"]}
    module_domains: dict[str, set[int]] = {row["id"]: set() for row in blueprint["modules"]}
    for stage, module_ids in DOMAIN_TO_MODULES.items():
        for module_id in module_ids:
            module_domains[module_id].add(stage)

    form_counts: Counter[str] = Counter()
    for row in forms["forms"]:
        stage = row["primary_domain_id"]
        for module_id in DOMAIN_TO_MODULES.get(stage, ()):
            form_counts[module_id] += 1
    call_counts: Counter[str] = Counter()
    for row in calls["forms"]:
        stage = row["primary_domain_id"]
        for module_id in DOMAIN_TO_MODULES.get(stage, ()):
            call_counts[module_id] += 1
    workflow_counts: Counter[str] = Counter()
    for row in workflows["workflows"]:
        for module_id in DOMAIN_TO_MODULES.get(row["primary_domain_id"], ()):
            workflow_counts[module_id] += 1
    report_counts: Counter[str] = Counter()
    for row in reports["reports"]:
        report_counts["reporting_documents"] += 1
        for module_id in DOMAIN_TO_MODULES.get(row["primary_domain_id"], ()):
            report_counts[module_id] += 1

    golden_counts: Counter[str] = Counter()
    golden_commands: dict[str, set[str]] = {row["id"]: set() for row in blueprint["modules"]}
    for payload in (golden, orchestrator, master_golden):
        for row in payload["cases"]:
            module_id = _command_module(row["command"])
            golden_counts[module_id] += 1
            golden_commands[module_id].add(row["command"])
    for row in extension["cases"]:
        module_id = row["target_module"]
        golden_counts[module_id] += 1
        golden_commands[module_id].add(row["surface"])
    for row in report_golden["golden_cases"]:
        module_id = row["target_module"]
        golden_counts[module_id] += 1
        golden_commands[module_id].add(row["surface"])
    for row in foundation_golden["cases"]:
        module_id = row["target_module"]
        golden_counts[module_id] += 1
        golden_commands[module_id].add(row["command"])
    for row in bank_reconciliation_golden["cases"]:
        module_id = "receivables_treasury"
        golden_counts[module_id] += 1
        golden_commands[module_id].add(row["command"])

    migration_counts: Counter[str] = Counter()
    for row in migration["ordered_slices"]:
        for module_id in row["target_modules"]:
            migration_counts[module_id] += 1

    high_gap_counts = Counter(
        HIGH_GAP_MODULE[row["type"]]
        for row in gaps["forms"]
        if row["priority"] == "high"
    )
    unresolved_root_counts = Counter(
        HIGH_GAP_MODULE[row["type"]]
        for row in roots["resolutions"]
        if "STILL_UNRESOLVED" in row["status"]
    )
    phases_by_module: dict[str, list[str]] = {row["id"]: [] for row in blueprint["modules"]}
    for phase in blueprint["phases"]:
        for module_id in phase["modules"]:
            phases_by_module[module_id].append(phase["id"])

    matrix = []
    for module in blueprint["modules"]:
        module_id = module["id"]
        domain_rows = [domain_by_stage[stage] for stage in sorted(module_domains[module_id])]
        counts = {
            "validated_domain_count": len(domain_rows),
            "domain_table_count": sum(row["table_count"] for row in domain_rows),
            "domain_form_candidate_count": form_counts[module_id],
            "compact_call_contract_count": call_counts[module_id],
            "workflow_surface_count": workflow_counts[module_id],
            "report_surface_count": report_counts[module_id],
            "synthetic_golden_case_count": golden_counts[module_id],
            "target_command_with_golden_cases_count": len(golden_commands[module_id]),
            "migration_slice_count": migration_counts[module_id],
            "high_priority_form_gap_count": high_gap_counts[module_id],
            "unresolved_root_entrypoint_count": unresolved_root_counts[module_id],
            "domain_evidence_limit_count": sum(row["evidence_limit_count"] for row in domain_rows),
        }
        if module_id == "platform":
            knowledge_status = "TARGET_FOUNDATION_CONTRACT_DEFINED_RUNTIME_SEMANTICS_INDIRECT"
        elif module_id == "integration_migration":
            knowledge_status = "MIGRATION_CONTRACT_DEFINED_NO_RUN_EVIDENCE"
        elif module_id == "reporting_documents" and counts["report_surface_count"]:
            knowledge_status = "REPORT_SURFACE_EVIDENCE_WITH_OPEN_OUTPUT_SEMANTICS"
        elif counts["validated_domain_count"] and counts["domain_form_candidate_count"] >= 10 and (
            counts["workflow_surface_count"] or counts["report_surface_count"] or counts["synthetic_golden_case_count"]
        ):
            knowledge_status = "SUBSTANTIAL_MULTI_SOURCE_EVIDENCE_NOT_COMPLETE"
        elif counts["validated_domain_count"] and counts["domain_form_candidate_count"]:
            knowledge_status = "DATA_AND_UI_EVIDENCE_WITH_OPEN_SEMANTICS"
        elif counts["validated_domain_count"]:
            knowledge_status = "DATA_AND_POLICY_EVIDENCE_RUNTIME_LIGHT"
        else:
            knowledge_status = "TARGET_CONTRACT_ONLY"

        if module_id in {"platform", "organization_context", "identity_authorization", "configuration", "integration_migration"}:
            readiness = "P0_READY_FOR_REFINEMENT_NOT_IMPLEMENTATION"
        elif module_id in {"master_data", "reporting_documents"}:
            readiness = "P1_READ_ONLY_SLICE_READY_FOR_REFINEMENT"
        else:
            readiness = "LATER_PHASE_DESIGN_AND_SYNTHETIC_TEST_CONTRACT_ONLY"
        matrix.append(
            {
                "module": module_id,
                "phases": phases_by_module[module_id],
                "owns": module["owns"],
                "depends_on": module["depends_on"],
                "source_domains": [
                    {"stage": row["stage"], "slug": row["slug"], "validation": row["validation"]}
                    for row in domain_rows
                ],
                "evidence_counts": counts,
                "knowledge_status": knowledge_status,
                "implementation_readiness": readiness,
                "open_blockers": BLOCKERS[module_id],
                "command_ready": False,
                "pilot_ready": False,
                "production_ready": False,
            }
        )

    module_ids = {row["module"] for row in matrix}
    expected_module_ids = {row["id"] for row in blueprint["modules"]}
    errors = []
    if module_ids != expected_module_ids:
        errors.append("module coverage mismatch")
    if set(BLOCKERS) != expected_module_ids:
        errors.append("blocker coverage mismatch")
    if set(DOMAIN_TO_MODULES) != set(range(1, 19)):
        errors.append("domain mapping coverage mismatch")
    if sum(high_gap_counts.values()) != 7:
        errors.append("high-priority gap mapping mismatch")
    if sum(unresolved_root_counts.values()) != 3:
        errors.append("unresolved-root mapping mismatch")
    if golden_counts.total() != 970:
        errors.append("golden-case mapping mismatch")

    artifact = {
        "artifact": "negin_personal_erp_module_evidence_and_readiness_matrix",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_MODULE_READINESS_DERIVATION_FROM_AGGREGATE_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_grants_persisted": 0,
            "implementation_pilot_or_cutover_authorized": 0,
        },
        "summary": {
            "module_count": len(matrix),
            "module_with_substantial_multi_source_evidence_count": sum(row["knowledge_status"].startswith("SUBSTANTIAL") for row in matrix),
            "p0_ready_for_refinement_count": sum(row["implementation_readiness"].startswith("P0") for row in matrix),
            "p1_read_only_ready_for_refinement_count": sum(row["implementation_readiness"].startswith("P1") for row in matrix),
            "later_phase_design_only_count": sum(row["implementation_readiness"].startswith("LATER") for row in matrix),
            "command_ready_module_count": sum(row["command_ready"] for row in matrix),
            "pilot_ready_module_count": sum(row["pilot_ready"] for row in matrix),
            "production_ready_module_count": sum(row["production_ready"] for row in matrix),
            "mapped_validated_domain_count": len(DOMAIN_TO_MODULES),
            "unique_form_candidate_count": len(forms["forms"]),
            "unique_form_candidate_with_primary_domain_count": sum(row["primary_domain_id"] is not None for row in forms["forms"]),
            "unmapped_form_candidate_count": sum(row["primary_domain_id"] is None for row in forms["forms"]),
            "mapped_form_candidate_assignments": sum(form_counts.values()),
            "unique_workflow_surface_count": len(workflows["workflows"]),
            "mapped_workflow_assignments": sum(workflow_counts.values()),
            "unique_report_surface_count": len(reports["reports"]),
            "mapped_report_assignments": sum(report_counts.values()),
            "mapped_synthetic_golden_case_count": golden_counts.total(),
            "high_priority_form_gap_count": sum(high_gap_counts.values()),
            "unresolved_root_entrypoint_count": sum(unresolved_root_counts.values()),
            "p0_backlog_item_count": p0["summary"]["item_count"],
            "validation_error_count": len(errors),
        },
        "interpretation": {
            "knowledge_status": "evidence density, not percent complete or correctness guarantee",
            "implementation_readiness": "next planning gate, not authorization to code or deploy",
            "zero_command_ready": "contracts and synthetic cases exist, but no target runtime implementation/UAT exists",
        },
        "modules": matrix,
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
