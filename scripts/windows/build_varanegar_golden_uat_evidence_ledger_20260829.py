"""Build an offline Golden Case/UAT evidence ledger without executing business paths."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "commands": "artifacts/varanegar_analysis/varanegar_command_readiness_ledger_20260829.json",
    "reports": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "synthetic": "artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_command_readiness_checkpoint_20260829.json",
}

def load(path: Path): return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--output", required=True, type=Path); a = p.parse_args()
    paths = {k: ROOT / v for k, v in SOURCES.items()}; data = {k: load(v) for k, v in paths.items()}
    c, r, g = data["commands"], data["reports"], data["synthetic"]
    cases = g["cases"]; kinds = dict(sorted(Counter(x["kind"] for x in cases).items()))
    tracks = [
        {"track":"COMMAND","designed_case_count":len(cases),"executed_case_count":0,"result_parity_proven_count":0,"owner_approved_count":0,"ready":False,"next_evidence":"isolated target test DB + synthetic fixtures + captured deterministic assertions"},
        {"track":"REPORT","designed_case_count":0,"executed_case_count":0,"result_parity_proven_count":r["summary"]["result_parity_proven_count"],"owner_approved_count":r["summary"]["owner_golden_value_count"],"ready":False,"next_evidence":"owner-approved fixtures + legacy/target output comparison + render/value assertions"},
    ]
    summary = {
        "evidence_track_count": len(tracks), "synthetic_command_case_count": len(cases),
        "synthetic_case_kind_counts": kinds, "command_module_count": c["summary"]["module_count"],
        "report_surface_count": r["summary"]["report_surface_count"], "executed_case_count": 0,
        "result_parity_proven_count": 0, "owner_approved_golden_count": 0,
        "uat_ready_track_count": 0, "pilot_ready_track_count": 0,
        "risk_count": c["summary"]["risk_count"],
    }
    checks = {
        "validated_inputs": c["validation"] == r["validation"] == "PASS",
        "synthetic_source_pinned": len(cases) == c["summary"]["legacy_synthetic_golden_case_count"] == 77,
        "no_synthetic_as_execution": summary["executed_case_count"] == 0,
        "no_ownership_inference": summary["owner_approved_golden_count"] == 0,
        "no_parity_inference": summary["result_parity_proven_count"] == 0,
        "risk_stable": summary["risk_count"] == 84,
    }
    failed = sorted(k for k, v in checks.items() if not v)
    out = {
        "artifact":"varanegar_golden_uat_evidence_ledger_20260829", "schema_version":1,
        "generated_at":datetime.now().astimezone().isoformat(), "validation":"PASS" if not failed else "FAIL",
        "safety":{"mode":"OFFLINE_EVIDENCE_RECONCILIATION","database_connections":0,"commands_executed":0,"forms_or_reports_executed":0,"data_mutations":0,"business_values_persisted":0},
        "summary":summary,
        "evidence_ladder":[
            {"level":1,"name":"DESIGNED_SYNTHETIC","meaning":"test contract only; not execution evidence"},
            {"level":2,"name":"EXECUTED_ISOLATED","meaning":"run against isolated target fixtures with captured assertions"},
            {"level":3,"name":"RESULT_PARITY_PROVEN","meaning":"legacy and target outputs/effects reconciled"},
            {"level":4,"name":"OWNER_APPROVED","meaning":"business owner accepted named golden evidence"},
        ],
        "tracks":tracks,
        "promotion_gate":{"uat_ready_requires":["executed success/denial/stale/retry/rollback/reconciliation cases","zero unexplained parity differences","named owner approval"],"pilot_ready_requires":["UAT ready","authorization and scope evidence","atomicity/effect/retry evidence","risk acceptance for remaining limitations"]},
        "checks":checks,"failed_checks":failed,
        "risk_links":["RISK-REPORT-PARITY-NOT-PROVEN","RISK-COMMAND-RUNTIME-NOT-PROVEN","RISK-GOLDEN-OWNER-APPROVAL-MISSING"],
        "source_manifest":[{"name":k,"path":SOURCES[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],
        "confidence":{"classification":"HIGH","runtime_or_business_acceptance":"NOT_OBSERVED"},
        "limits":["No legacy or target business path was executed.","The 77 command cases remain synthetic test designs.","No report value/render parity or owner approval is claimed."],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(a.output.resolve()); print(out["validation"]); return 0 if not failed else 1

if __name__ == "__main__": raise SystemExit(main())
