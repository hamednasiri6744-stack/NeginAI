"""Build evidence-first cross-module reconciliation incident playbooks."""
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
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_golden_checkpoint_20260829.json",
}
COMMON_STEPS = [
    "capture correlation/command id, source and target immutable identities, company/DC/fiscal/date scope and expected versions without PII",
    "verify artifact and policy hashes; stop on drift",
    "read source, target, crosswalk, ordered history, audit and outbox evidence without executing a command or report",
    "compare identity, scope, version, state and durable effects separately",
    "classify NATURAL_BEHAVIOR, DATA_DEBT, BUG or UNPROVEN and record a reconciliation status",
    "quarantine ambiguous or conflicting evidence before any retry",
    "stop before repair, replay, synthetic line creation, pointer replacement or physical deletion",
    "design an isolated synthetic Golden replay if runtime parity remains uncertain",
]
PLAYBOOKS = [
    {"id": "XMR-PB-01", "edge_type": "command_to_command_receipt", "incident": "duplicate CommandId has an unknown or conflicting result", "focus": "legacy commands lack explicit idempotency parameters", "extra": "compare canonical PayloadHash and original typed outcome; conflicting payload is IDENTITY_CONFLICT and same payload returns only original outcome", "quarantine": "UNKNOWN_COMMAND_OUTCOME", "risks": ["R-005", "R-006", "R-007"]},
    {"id": "XMR-PB-02", "edge_type": "sale_to_accounting_source", "incident": "sale snapshot and accounting source disagree", "focus": "snapshot-only rows can be legitimate expected absence", "extra": "prove current active sale identity and balance; never synthesize accounting from a snapshot-only row", "quarantine": "SOURCE_ONLY", "risks": ["R-002", "R-008", "R-023"]},
    {"id": "XMR-PB-03", "edge_type": "accounting_source_to_batch_journal", "incident": "accounting source, batch link and journal disagree", "focus": "one source has one batch but one batch may aggregate many sources", "extra": "verify source-to-batch uniqueness and active journal resolution; do not label a multi-source batch duplicate", "quarantine": "DUPLICATE_OR_CONFLICTING_CROSSWALK", "risks": ["R-006", "R-034", "R-036"]},
    {"id": "XMR-PB-04", "edge_type": "distribution_to_sale_link", "incident": "distribution and sale-link history fork", "focus": "current status does not reconstruct ordered link history", "extra": "compare expected aggregate versions and ordered event positions; never replace current pointer with MAX(id)", "quarantine": "POINTER_HISTORY_FORK", "risks": ["R-007", "R-023", "R-048"]},
    {"id": "XMR-PB-05", "edge_type": "distribution_to_exit", "incident": "distribution exists while exit is absent or scoped differently", "focus": "physical absence is not cancellation evidence", "extra": "correlate distribution, scoped exit lifecycle, history and audit; classify expected absence only from an explicit rule", "quarantine": "SCOPE_OR_VERSION_MISMATCH", "risks": ["R-008", "R-034", "R-043"]},
    {"id": "XMR-PB-06", "edge_type": "exit_to_type60_voucher", "incident": "exit and type-60 voucher/delete evidence disagree", "focus": "cancelled exits require immutable delete evidence", "extra": "resolve active voucher graph or cancellation plus delete audit; missing voucher alone remains UNPROVEN", "quarantine": "MISSING_DELETE_OR_AUDIT_EVIDENCE", "risks": ["R-007", "R-034", "R-043"]},
    {"id": "XMR-PB-07", "edge_type": "ngt_payment_to_backoffice_receipt", "incident": "payment/receipt identity matches but amounts differ", "focus": "receipt amount scope differs for most linked receipts", "extra": "reconcile Ref, UniqueId and receipt number independently from allocation; amount difference alone is NATURAL_BEHAVIOR, not an identity defect", "quarantine": "DUPLICATE_OR_CONFLICTING_CROSSWALK", "risks": ["R-005", "R-006", "R-036"]},
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
    playbooks = [{**item, "steps": COMMON_STEPS + [item["extra"]], "stop_conditions": ["hash drift", "write or repair required", "owner policy required", "raw sensitive values would be persisted"], "runtime_diagnosis": "NOT_PERFORMED"} for item in PLAYBOOKS]
    summary = {
        "playbook_count": len(playbooks),
        "minimum_step_count": min(len(x["steps"]) for x in playbooks),
        "edge_type_count": data["contract"]["summary"]["edge_type_count"],
        "golden_case_count": data["golden"]["summary"]["case_count"],
        "runtime_incidents_diagnosed_count": 0,
        "repairs_performed_count": 0,
        "retries_performed_count": 0,
        "owner_approved_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    existing_risks = {x["id"] for x in data["risk"]["risks"]}
    contract_edges = {x["edge"] for x in data["contract"]["cross_module_edges"]}
    contract_quarantines = set(data["contract"]["target_reconciliation_receipt_schema"]["quarantine"])
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "seven_playbooks": len(playbooks) == 7,
        "one_per_edge": {x["edge_type"] for x in playbooks} == contract_edges,
        "nine_steps": all(len(x["steps"]) == 9 for x in playbooks),
        "four_way": all("NATURAL_BEHAVIOR, DATA_DEBT, BUG or UNPROVEN" in x["steps"][4] for x in playbooks),
        "quarantines_valid": all(x["quarantine"] in contract_quarantines for x in playbooks),
        "all_risks_exist": all(risk in existing_risks for x in playbooks for risk in x["risks"]),
        "seven_and_thirty_five": summary["edge_type_count"] == 7 and summary["golden_case_count"] == 35,
        "runtime_zero": summary["runtime_incidents_diagnosed_count"] == summary["repairs_performed_count"] == summary["retries_performed_count"] == summary["owner_approved_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_cross_module_reconciliation_playbook_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_EVIDENCE_SYNTHESIS", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "playbooks": playbooks,
        "diagnostic_result_contract": {"allowed": ["NATURAL_BEHAVIOR", "DATA_DEBT", "BUG", "UNPROVEN"], "requires_named_incident_evidence": True, "repair_or_retry_is_separate_authorized_work": True},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"structure": "HIGH", "incident_diagnosis": "REQUIRES_INCIDENT_EVIDENCE"},
        "limits": ["No named incident was diagnosed.", "No repair, retry, command or UAT was executed.", "Static and clone aggregates are not production-current certification."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
