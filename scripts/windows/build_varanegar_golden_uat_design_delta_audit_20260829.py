"""Audit post-consolidated Golden/UAT design deltas without double counting."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "consolidated": "artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "terminal": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "platform": "artifacts/varanegar_analysis/varanegar_platform_golden_uat_cases_20260829.json",
    "organization": "artifacts/varanegar_analysis/varanegar_organization_context_golden_uat_cases_20260829.json",
    "identity": "artifacts/varanegar_analysis/varanegar_identity_authorization_golden_uat_cases_20260829.json",
    "configuration": "artifacts/varanegar_analysis/varanegar_configuration_golden_uat_cases_20260829.json",
    "master": "artifacts/varanegar_analysis/varanegar_master_data_golden_uat_cases_20260829.json",
    "pricing": "artifacts/varanegar_analysis/varanegar_pricing_rule_golden_uat_cases_20260829.json",
    "distribution": "artifacts/varanegar_analysis/varanegar_distribution_golden_uat_cases_20260829.json",
    "treasury": "artifacts/varanegar_analysis/varanegar_treasury_golden_uat_cases_20260829.json",
    "accounting": "artifacts/varanegar_analysis/varanegar_accounting_golden_uat_cases_20260829.json",
    "reporting": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "integration": "artifacts/varanegar_analysis/varanegar_integration_migration_golden_uat_cases_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    base = {
        row["module"]: row["truth_table_dimensions"]["golden_cases"]["synthetic_design_count"]
        for row in data["readiness"]["modules"]
    }
    platform_count = data["platform"]["summary"]["combined_platform_acceptance_design_count"]

    exact = {
        "organization_context": ("organization", "combined_organization_context_acceptance_design_count"),
        "identity_authorization": ("identity", "combined_identity_acceptance_design_count"),
        "configuration": ("configuration", "combined_configuration_acceptance_design_count"),
        "master_data": ("master", "combined_master_data_acceptance_design_count"),
        "integration_migration": ("integration", "combined_integration_acceptance_design_count"),
    }
    rows = [
        {
            "module": "platform",
            "consolidated_design_count": platform_count,
            "newer_artifact_design_count": platform_count,
            "exact_additive_delta_count": 0,
            "counting_status": "ALREADY_INCLUDED_AS_EXTERNAL_PLATFORM_DELTA_IN_1229",
            "evidence_source": SOURCES["platform"],
        }
    ]
    for module in sorted(base):
        if module == "platform":
            continue
        if module in exact:
            source, key = exact[module]
            artifact = data[source]["summary"]
            existing = artifact["existing_reused_case_count"]
            combined = artifact[key]
            delta = artifact["delta_case_count"]
            status = "EXACT_ADDITIVE_DELTA_EXISTING_REUSE_MATCHES_CONSOLIDATED_MODULE_COUNT"
            rows.append(
                {
                    "module": module,
                    "consolidated_design_count": base[module],
                    "newer_artifact_existing_reused_count": existing,
                    "newer_artifact_delta_count": delta,
                    "newer_artifact_design_count": combined,
                    "exact_additive_delta_count": delta if existing == base[module] and combined == existing + delta else 0,
                    "counting_status": status if existing == base[module] and combined == existing + delta else "UNRESOLVED_REUSE_BASE_MISMATCH",
                    "evidence_source": SOURCES[source],
                }
            )
        elif module == "pricing_rules":
            s = data["pricing"]["summary"]
            rows.append(
                {
                    "module": module,
                    "consolidated_design_count": base[module],
                    "newer_artifact_existing_reused_count": s["existing_reused_case_count"],
                    "newer_artifact_delta_count": s["delta_case_count"],
                    "newer_artifact_design_count": s["combined_pricing_acceptance_design_count"],
                    "exact_additive_delta_count": 0,
                    "counting_status": "UNRESOLVED_CROSSWALK_REUSE_BASE_64_DIFFERS_FROM_CONSOLIDATED_82",
                    "evidence_source": SOURCES["pricing"],
                }
            )
        elif module in {"distribution", "receivables_treasury", "accounting", "reporting_documents"}:
            source = {
                "distribution": "distribution",
                "receivables_treasury": "treasury",
                "accounting": "accounting",
                "reporting_documents": "reporting",
            }[module]
            observed = data[source]["summary"]["case_count"]
            relation = (
                "NARROWER_COMMAND_CASE_SET_NOT_ADDITIVE_TO_BROADER_CONSOLIDATED_DESIGN"
                if observed <= base[module]
                else "UNRESOLVED_OVERLAP_NEWER_CASE_SET_NOT_SAFE_TO_ADD"
            )
            rows.append(
                {
                    "module": module,
                    "consolidated_design_count": base[module],
                    "newer_artifact_design_count": observed,
                    "exact_additive_delta_count": 0,
                    "counting_status": relation,
                    "evidence_source": SOURCES[source],
                }
            )
        else:
            rows.append(
                {
                    "module": module,
                    "consolidated_design_count": base[module],
                    "newer_artifact_design_count": base[module],
                    "exact_additive_delta_count": 0,
                    "counting_status": "NO_NEWER_MODULE_GOLDEN_DELTA_ARTIFACT_IN_SCOPE",
                    "evidence_source": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
                }
            )
    rows.sort(key=lambda row: (row["module"] != "platform", row["module"]))
    exact_rows = [row for row in rows if row["counting_status"].startswith("EXACT_ADDITIVE_DELTA")]
    unresolved_rows = [row for row in rows if row["counting_status"].startswith(("UNRESOLVED", "NARROWER"))]
    no_newer_rows = [row for row in rows if row["counting_status"].startswith("NO_NEWER")]
    exact_delta = sum(row["exact_additive_delta_count"] for row in rows)
    baseline = data["consolidated"]["summary"]["synthetic_acceptance_design_obligation_count"]
    summary = {
        "module_count": len(rows),
        "readiness_module_design_count": sum(base.values()),
        "platform_external_design_count_already_in_baseline": platform_count,
        "consolidated_snapshot_design_obligation_count": baseline,
        "exact_non_duplicated_post_consolidated_delta_count": exact_delta,
        "current_proven_non_duplicated_design_lower_bound": baseline + exact_delta,
        "exact_additive_delta_module_count": len(exact_rows),
        "unresolved_or_narrower_crosswalk_module_count": len(unresolved_rows),
        "no_newer_delta_module_count": len(no_newer_rows),
        "already_included_platform_module_count": 1,
        "unresolved_case_count_added_to_lower_bound": 0,
        "executed_case_count": data["terminal"]["summary"]["executed_obligation_count"],
        "owner_approved_module_count": data["terminal"]["summary"]["owner_approved_module_count"],
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "fourteen_modules": len(rows) == len({row["module"] for row in rows}) == 14,
        "baseline_reconciles_1187_plus_42": summary["readiness_module_design_count"] == 1187
        and summary["platform_external_design_count_already_in_baseline"] == 42
        and summary["consolidated_snapshot_design_obligation_count"] == 1229,
        "five_exact_deltas_175": summary["exact_additive_delta_module_count"] == 5
        and summary["exact_non_duplicated_post_consolidated_delta_count"] == 175,
        "lower_bound_1404": summary["current_proven_non_duplicated_design_lower_bound"] == 1404,
        "five_unresolved_three_no_newer": summary["unresolved_or_narrower_crosswalk_module_count"] == 5
        and summary["no_newer_delta_module_count"] == 3,
        "unresolved_not_counted": summary["unresolved_case_count_added_to_lower_bound"] == 0,
        "execution_approval_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_golden_uat_design_delta_audit_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_GOLDEN_UAT_DESIGN_DEDUPLICATION_AUDIT",
            "consolidated_1229_status": "VALID_HISTORICAL_SNAPSHOT_NOT_LATEST_PROVEN_DESIGN_LOWER_BOUND",
            "counting_changes_runtime_or_readiness": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "golden_uat_cases_commands_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_business_values_outputs_identity_or_credentials_persisted": 0,
            "data_mutations": 0,
            "write_access_created": 0,
        },
        "summary": summary,
        "module_design_delta_audit": rows,
        "deduplication_rules": [
            "A delta is additive only when its artifact declares existing_reused equal to the consolidated module count and combined equals existing plus delta.",
            "Platform 42 is already added outside the readiness module sum in the consolidated 1,229 and is never added again.",
            "A narrower command/report case set is not additive to a broader module count without a case-id crosswalk.",
            "A newer artifact whose existing_reused count differs from the consolidated module count remains unresolved and contributes zero to the lower bound.",
            "Design count, even when deduplicated, does not prove execution, pass, owner approval or readiness.",
        ],
        "unresolved_crosswalk_work_queue": [
            {"module": row["module"], "status": row["counting_status"], "required_evidence": "case-id and semantic-obligation crosswalk against the consolidated module design set"}
            for row in unresolved_rows
        ],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_golden_uat_design_delta_audit_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The 1,404 value is a proven non-duplicated design lower bound, not a final exhaustive count.",
            "Five unresolved/narrower module artifacts contribute zero until case-level crosswalks exist.",
            "No Golden/UAT case was executed and no owner approval or readiness state was created.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
