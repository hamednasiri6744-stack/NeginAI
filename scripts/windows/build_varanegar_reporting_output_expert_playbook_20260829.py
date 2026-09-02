"""Build evidence-first reporting/output incident playbooks."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "envelope": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "golden": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "print_batch": "artifacts/varanegar_analysis/domains/print_batch_contract_20260829.json",
    "sale_print": "artifacts/varanegar_analysis/domains/sale_invoice_print_audit_boundary_20260829.json",
    "bank_envelope": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_command_envelope_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_checkpoint_20260829.json",
}
COMMON = [
    "capture command/correlation id, actor/resource scope, output kind, document/query identity, template/query hash, filter hash and source watermark without PII",
    "verify evidence and policy hashes; stop on drift",
    "read render, spooler/physical-print, completion audit, external file and delegated command receipts",
    "compare requested, rendered, physically confirmed, audit committed and delivered states separately",
    "classify NATURAL_BEHAVIOR, DATA_DEBT, BUG or UNPROVEN",
    "quarantine unknown or conflicting completion before retry",
    "stop before reprint, audit synthesis, file regeneration on a new watermark or import replay",
    "design isolated fault injection if the durable boundary remains unproven",
]
PLAYBOOKS = [
    {"id": "RO-PB-01", "incident": "print batch returned success while a child failed", "focus": "batch orchestration is per-item and legacy completion paths have no local rollback", "extra": "fold all child outcomes; retain confirmed successes and retry only failed/unconfirmed items", "risks": ["R-005", "R-007", "R-023"]},
    {"id": "RO-PB-02", "incident": "render succeeded but completion or audit is missing", "focus": "render, physical confirmation and audit commit are distinct durable stages", "extra": "classify RENDERED_NOT_COMPLETED or UNKNOWN; never blind reprint or synthesize completion", "risks": ["R-007", "R-017", "R-036"]},
    {"id": "RO-PB-03", "incident": "sale invoice was reprinted or printed after terminal cancellation", "focus": "retained history has repeated prints and post-cancellation events without request identity", "extra": "correlate document state, template, request/correlation and audit time; repeated history alone is not a defect", "risks": ["R-008", "R-017", "R-059"]},
    {"id": "RO-PB-04", "incident": "export file differs or retry produces new content", "focus": "query receipt, source watermark, content hash and delivery are separate", "extra": "compare pinned query/filter/watermark/content hash; a new watermark is a new command, not retry", "risks": ["R-002", "R-005", "R-059"]},
    {"id": "RO-PB-05", "incident": "healthy-cardex print is marked complete although render failed", "focus": "legacy print attempt occurs before render", "extra": "use the four-state audit sequence and reject PRINT_REQUESTED as completion evidence", "risks": ["R-007", "R-017", "R-023"]},
    {"id": "RO-PB-06", "incident": "bank statement import/export has partial or mismatched outcome", "focus": "signed summary presentation and delegated treasury mutations have different owners", "extra": "preserve signed metric keys; reconcile each import row to its treasury receipt before retry", "risks": ["R-005", "R-006", "R-036"]},
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
    playbooks = [{**item, "steps": COMMON + [item["extra"]], "stop_conditions": ["hash drift", "write or replay required", "owner policy required", "raw output or sensitive values would be persisted"], "runtime_diagnosis": "NOT_PERFORMED"} for item in PLAYBOOKS]
    summary = {
        "playbook_count": len(playbooks),
        "minimum_step_count": min(len(x["steps"]) for x in playbooks),
        "command_surface_count": data["envelope"]["summary"]["command_surface_count"],
        "golden_case_count": data["golden"]["summary"]["case_count"],
        "runtime_incidents_diagnosed_count": 0,
        "repairs_or_replays_performed_count": 0,
        "owner_approved_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    known_risks = {x["id"] for x in data["risk"]["risks"]}
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "six_playbooks": len(playbooks) == 6,
        "nine_steps": all(len(x["steps"]) == 9 for x in playbooks),
        "four_way": all("NATURAL_BEHAVIOR, DATA_DEBT, BUG or UNPROVEN" in x["steps"][4] for x in playbooks),
        "all_risks_exist": all(risk in known_risks for x in playbooks for risk in x["risks"]),
        "eight_and_fifty_six": summary["command_surface_count"] == 8 and summary["golden_case_count"] == 56,
        "completion_and_watermark_rules": any("RENDERED_NOT_COMPLETED" in x["extra"] for x in playbooks) and any("new watermark" in x["extra"] for x in playbooks),
        "runtime_zero": summary["runtime_incidents_diagnosed_count"] == summary["repairs_or_replays_performed_count"] == summary["owner_approved_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_expert_playbook_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_EVIDENCE_SYNTHESIS", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "playbooks": playbooks,
        "diagnostic_result_contract": {"allowed": ["NATURAL_BEHAVIOR", "DATA_DEBT", "BUG", "UNPROVEN"], "requires_named_incident_evidence": True, "repair_reprint_replay_is_separate_authorized_work": True},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"structure": "HIGH", "incident_diagnosis": "REQUIRES_INCIDENT_EVIDENCE"},
        "limits": ["No named incident was diagnosed.", "No repair, reprint, replay or UAT was executed.", "Historical aggregates are not production-current truth."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
