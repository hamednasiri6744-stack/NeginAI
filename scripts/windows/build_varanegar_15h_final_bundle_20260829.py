"""Build the final reproducible baseline/bundle for the 15-hour read-only pass."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "artifacts" / "varanegar_analysis"

AXES = {
    "sales_order_distribution": [
        "varanegar_sale_conversion_checkpoint_20260829.json",
        "varanegar_sale_cancellation_checkpoint_20260829.json",
        "varanegar_return_issue_cancel_checkpoint_20260829.json",
        "varanegar_distribution_exit_checkpoint_20260829.json",
        "varanegar_sale_voucher_snapshot_checkpoint_20260829.json",
        "varanegar_sale_accounting_crosswalk_checkpoint_20260829.json",
        "varanegar_sale_invoice_print_checkpoint_20260829.json",
    ],
    "receipts_settlement_cheques": [
        "varanegar_ngt_payment_checkpoint_20260829.json",
        "varanegar_ngt_payment_replication_checkpoint_20260829.json",
        "varanegar_payable_cheque_undo_checkpoint_20260829.json",
        "varanegar_received_cheque_undo_checkpoint_20260829.json",
        "varanegar_received_cheque_delete_checkpoint_20260829.json",
    ],
    "inventory_purchase": [
        "varanegar_stock_voucher_state_checkpoint_20260829.json",
        "varanegar_stock_projection_validation_checkpoint_20260829.json",
        "varanegar_supplier_cost_apply_checkpoint_20260829.json",
        "varanegar_supplier_unapply_delete_checkpoint_20260829.json",
    ],
    "documents_and_rules": [
        "varanegar_sale_accounting_crosswalk_checkpoint_20260829.json",
        "varanegar_discount_v2_engine_checkpoint_20260829.json",
        "varanegar_discount_v2_query_checkpoint_20260829.json",
    ],
    "authorization_scope_operationdate_feature": [
        "varanegar_authorization_checkpoint_20260829.json",
        "varanegar_configuration_checkpoint_20260829.json",
        "varanegar_operation_date_checkpoint_20260829.json",
        "varanegar_order_sale_authorization_checkpoint_20260829.json",
        "varanegar_order_sale_operation_date_checkpoint_20260829.json",
        "varanegar_order_sale_policy_flag_checkpoint_20260829.json",
    ],
    "reports_and_reference_outputs": [
        "varanegar_sale_invoice_print_checkpoint_20260829.json",
        "varanegar_sale_voucher_snapshot_checkpoint_20260829.json",
        "varanegar_analysis_checkpoint_20260828.json",
    ],
    "errors_transactions_idempotency_replication": [
        "varanegar_command_outcome_commit_checkpoint_20260829.json",
        "varanegar_datacontext_transaction_checkpoint_20260829.json",
        "varanegar_idempotency_guard_checkpoint_20260829.json",
        "varanegar_ngt_replication_compensation_checkpoint_20260829.json",
        "varanegar_ngt_sale_replication_checkpoint_20260829.json",
        "varanegar_ngt_return_checkpoint_20260829.json",
    ],
}

# Freeze the temporal boundary of this baseline.  A repository-wide glob makes
# the historical 15-hour bundle absorb checkpoints created by later waves.
BASELINE_CHECKPOINT_NAMES = sorted(
    {
        name
        for names in AXES.values()
        for name in names
        if name.endswith("20260829.json")
    }
    | {
        "varanegar_ngt_order_checkpoint_20260829.json",
        "varanegar_ngt_order_delete_log_checkpoint_20260829.json",
        "varanegar_ngt_order_deletion_checkpoint_20260829.json",
        "varanegar_ngt_order_history_checkpoint_20260829.json",
        "varanegar_ngt_tour_call_checkpoint_20260829.json",
        "varanegar_order_sale_evc_checkpoint_20260829.json",
    }
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    checkpoint_paths = [ANALYSIS / name for name in BASELINE_CHECKPOINT_NAMES]
    checkpoints = {path.name: load(path) for path in checkpoint_paths}
    prior = ANALYSIS / "varanegar_analysis_checkpoint_20260828.json"
    checkpoints[prior.name] = load(prior)
    test_result = load(args.test_result)
    risk = load(ANALYSIS / "ui" / "negin_erp_risk_register_20260829.json")
    trace = load(ANALYSIS / "ui" / "negin_erp_requirements_traceability_20260829.json")
    axis_evidence = {
        axis: [
            {
                "checkpoint": name,
                "validation": checkpoints[name]["validation"],
                "sha256": sha256(ANALYSIS / name),
            }
            for name in names
        ]
        for axis, names in AXES.items()
    }
    all_axis_pass = all(
        row["validation"] == "PASS"
        for rows in axis_evidence.values()
        for row in rows
    )
    all_current_pass = all(payload.get("validation") == "PASS" for payload in checkpoints.values())
    checks = {
        "all_36_current_checkpoints_pass": len(checkpoint_paths) == 36 and all_current_pass,
        "all_requested_analysis_axes_have_passing_evidence": len(axis_evidence) == 7 and all_axis_pass,
        "final_offline_evidence_suite_passes": test_result.get("validation") == "PASS"
        and test_result.get("runner", {}).get("passed_test_count", 0) >= 525,
        "risk_and_traceability_baseline_is_stable": risk["summary"]["risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "discount_engine_tail_checkpoint_passes": checkpoints[
            "varanegar_discount_v2_engine_checkpoint_20260829.json"
        ]["validation"] == "PASS",
        "checkpoint_safety_has_no_operational_execution": all(
            payload.get("safety", {}).get("operational_commands_executed", 0) == 0
            and payload.get("safety", {}).get("assemblies_loaded_or_executed", 0) == 0
            for payload in checkpoints.values()
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    manifest_paths = checkpoint_paths + [
        prior,
        args.test_result,
        ANALYSIS / "ui" / "negin_erp_risk_register_20260829.json",
        ANALYSIS / "ui" / "negin_erp_requirements_traceability_20260829.json",
        ROOT / "docs" / "VARANEGAR_KNOWLEDGE_FA.md",
        ROOT / "docs" / "varanegar_reconstruction" / "DISCOVERY_LOG_FA.md",
        ROOT / "docs" / "varanegar_reconstruction" / "README_FA.md",
        ROOT / "scripts" / "windows" / "run_varanegar_15h_final_tests.py",
        Path(__file__).resolve(),
    ]
    manifest = [
        {
            "path": path.resolve().relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in manifest_paths
    ]
    artifact = {
        "artifact": "varanegar_15h_final_baseline_bundle_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "READ_ONLY_DOCUMENTED_RECONSTRUCTION",
            "target_end_time_tehran": "2026-08-29T02:10:00+03:30",
            "requested_axis_count": len(AXES),
        },
        "baseline": {
            "checkpoint_count_20260829": len(checkpoint_paths),
            "passing_checkpoint_count_20260829": sum(
                payload.get("validation") == "PASS"
                for name, payload in checkpoints.items()
                if name.endswith("20260829.json")
            ),
            "risk_count": risk["summary"]["risk_count"],
            "critical_risk_count": risk["summary"]["critical_count"],
            "high_risk_count": risk["summary"]["high_count"],
            "medium_risk_count": risk["summary"]["medium_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
            "offline_test_passed_count": test_result["runner"]["passed_test_count"],
        },
        "axis_evidence": axis_evidence,
        "checks": checks,
        "failed_checks": failed,
        "safety": {
            "operational_forms_or_procedures_executed": 0,
            "varanegar_or_ngt_data_mutations": 0,
            "write_access_created": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_credentials_persisted": 0,
        },
        "manifest": manifest,
        "limits": [
            "Passing evidence contracts do not make any web-ERP command implementation-ready; command_ready_module_count remains zero.",
            "Static IL and read-only clone evidence cannot prove every production branch, external integration, or operator-only workflow.",
            "A later 25-hour pass should extend unresolved command truth tables and golden-case runtime comparison in isolated UAT.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["baseline"], ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
