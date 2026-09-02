"""Build non-additive Golden/UAT refinements and failure oracles for open gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "golden_audit": "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_20260829.json",
    "identity": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_20260829.json",
    "pos": "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_20260829.json",
    "report": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "handoff": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_cross_gate_diagnostic_playbook_addendum_20260829.json",
    "terminal": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


IDENTITY = [
    ("IA-R01", "unauthenticated mutating declaration gap", "deny before handler and zero durable effect", "handler entry or any durable effect is observed", "IA-GAP-01"),
    ("IA-R02", "wrong membership user scope", "deny before data access and classify scope mismatch", "request reaches an owner-unfiltered repository path", "IA-GAP-03"),
    ("IA-R03", "revoked or stale session epoch", "deny and invalidate the stale session context", "revoked context remains effective", "IA-GAP-01"),
    ("IA-R04", "admin role short-circuit", "explicit approved policy path with immutable decision receipt", "admin label alone bypasses resource/action evaluation", "IA-GAP-05"),
    ("IA-R05", "orphan membership user", "quarantine identity mapping and deny", "orphan mapping grants effective access", "IA-GAP-04"),
    ("IA-R06", "cross-type owner key collision", "typed owner identity remains unambiguous", "numeric-key equality merges distinct owner types", "IA-GAP-04"),
    ("IA-R07", "async state-machine authorization path", "authorization decision is proven before awaited handler effects", "only wrapper metadata exists or decision occurs after an effect", "IA-GAP-02"),
    ("IA-R08", "resource/action contract absent", "explicit resource/action disposition is accepted", "endpoint defaults to allow or broad scope", "IA-GAP-06"),
]

POS = [
    ("POS-R01", "safety-cap truncation and opaque queue", "queue identity and reviewed bound are complete", "cap truncation is treated as a complete graph", "POS-STATIC-01"),
    ("POS-R02", "depth-three callable frontier", "151 callable and 32 table frontier nodes remain separately reconciled", "the 183-node frontier is reported as all callable", "POS-STATIC-01"),
    ("POS-R03", "cyclic trigger component", "cycle entry, exit and affected write targets are bounded", "a cycle is interpreted as runtime order or atomicity proof", "POS-STATIC-02"),
    ("POS-R04", "dynamic SQL signal at frontier", "resolved target evidence or explicit opaque classification exists", "lexical visibility is treated as an exhaustive target set", "POS-STATIC-03"),
    ("POS-R05", "actionable unresolved name or type", "all 11 actionable items receive a reviewed disposition", "aliases, types and true missing objects are collapsed together", "POS-STATIC-04"),
    ("POS-R06", "resolved write-target lower bound", "48 targets are retained as a lower bound", "48 targets are promoted to an exhaustive mutation set", "POS-STATIC-03"),
    ("POS-R07", "transaction signal without runtime proof", "static transaction signals remain design evidence only", "44 frontier signals or 28 cyclic signals are called atomicity proof", "POS-STATIC-05"),
    ("POS-R08", "inserted/deleted pseudotable references", "168 pseudotables are excluded from actionable missing-object count", "pseudotables inflate the 11-item actionable queue", "POS-STATIC-04"),
]

REPORT = [
    ("RPT-R01", "row grain and stable comparison key", "keyset and grain match before totals", "matching totals hide missing, extra or duplicate keys", "FP-01"),
    ("RPT-R02", "external template grain unknown", "template extraction pins grain before parity", "unknown template grain is inferred from a UI label", "FP-01"),
    ("RPT-R03", "typed bank summary formula set", "all 11 formula expressions reconcile independently", "one aggregate total substitutes for formula-level parity", "FP-02"),
    ("RPT-R04", "null and empty semantics", "null, empty and zero remain distinct per approved policy", "normalization silently changes result meaning", "FP-03"),
    ("RPT-R05", "rounding precision and allocation", "row and total rounding basis is versioned and reconciled", "post-aggregate rounding masks row drift", "FP-04"),
    ("RPT-R06", "authorization and filter scope", "actor scope and filter hash match the frozen fixture", "broader scope produces plausible but unauthorized totals", "FP-05"),
    ("RPT-R07", "join cardinality and duplicate amplification", "source key multiplicity is reconciled before measures", "duplicated detail rows are accepted because totals look plausible", "FP-06"),
    ("RPT-R08", "business date basis and watermark", "date basis, timezone and source watermark are pinned", "different temporal cuts are compared as parity", "FP-07"),
    ("RPT-R09", "grid export render relationship", "grid values, export content hash and render policy are checked separately", "successful render is treated as result-value parity", "FP-08"),
    ("RPT-R10", "policy version and approved exception", "exception identity and policy version are explicit and current", "an unexplained difference is relabeled as an exception", "FP-14"),
]


def make_template(lane: str, row: tuple[str, str, str, str, str], result_classes: list[str]) -> dict:
    template_id, scenario, pass_condition, failure_condition, source_ref = row
    lane_receipt = {
        "IDENTITY_AUTHORIZATION": "DENY_BEFORE_HANDLER_AND_ZERO_EFFECT_RECEIPT",
        "POS_STATIC_GRAPH": "REDACTED_STATIC_GRAPH_EXPORT_AND_QUEUE_RECEIPT",
        "REPORT_FORMULA_GRAIN": "FROZEN_FIXTURE_KEYSET_FORMULA_COMPARISON_RECEIPT",
        "EXTERNAL_GATE_HANDOFF": "IMMUTABLE_PACKET_VALIDATION_AND_HANDOFF_RECEIPT",
    }[lane]
    return {
        "id": template_id,
        "lane": lane,
        "scenario": scenario,
        "source_reference": source_ref,
        "existing_design_bucket": "CURRENT_1404_NON_DUPLICATED_DESIGN_LOWER_BOUND_OR_EXISTING_GATE_OBLIGATION",
        "counting_effect": "REFINEMENT_NOT_ADDITIVE",
        "additive_design_obligation_count": 0,
        "execution_status": "NOT_EXECUTED",
        "owner_acceptance_status": "NOT_ACCEPTED",
        "failure_oracle": {
            "pass_condition": pass_condition,
            "failure_condition": failure_condition,
            "default_when_receipts_missing_or_stale": "UNPROVEN",
            "allowed_result_classes": result_classes,
        },
        "required_receipts": [
            "PINNED_SOURCE_POLICY_BUILDER_AND_CHECKPOINT_HASH_RECEIPT",
            lane_receipt,
            "OBSERVATION_OR_STATIC_RESULT_RECEIPT_WITHOUT_RAW_BUSINESS_VALUES",
            "KEYSET_COUNT_STATE_OR_FORMULA_RECONCILIATION_RECEIPT",
            "ACCOUNTABLE_ROLE_DISPOSITION_AND_EXPIRY_RECEIPT",
        ],
        "prohibited_inferences": [
            "design refinement is not an executed or passed UAT case",
            "missing evidence is not success",
            "a receipt does not promote command-ready or pilot-ready state by itself",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    result_classes = sorted(data["playbook"]["diagnostic_result_contract"])
    templates = []
    templates += [make_template("IDENTITY_AUTHORIZATION", row, result_classes) for row in IDENTITY]
    templates += [make_template("POS_STATIC_GRAPH", row, result_classes) for row in POS]
    templates += [make_template("REPORT_FORMULA_GRAIN", row, result_classes) for row in REPORT]
    gate_rows = {row["gate_id"]: row for row in data["handoff"]["gate_handoff_matrix"]}
    for gate_id in sorted(gate_rows):
        gate = gate_rows[gate_id]
        templates.append(
            make_template(
                "EXTERNAL_GATE_HANDOFF",
                (
                    f"HOF-R{int(gate_id[-2:]):02d}",
                    f"{gate_id} {gate['lane']} handoff completeness and freshness",
                    "every required current unit is accepted and the immutable handoff validates",
                    "missing, stale, rejected or partial units are promoted downstream",
                    gate_id,
                ),
                result_classes,
            )
        )
    templates.sort(key=lambda row: row["id"])
    lane_counts = {lane: sum(row["lane"] == lane for row in templates) for lane in sorted({row["lane"] for row in templates})}
    prior_lower_bound = data["golden_audit"]["summary"]["current_proven_non_duplicated_design_lower_bound"]
    summary = {
        "refinement_template_count": len(templates),
        "identity_refinement_template_count": lane_counts.get("IDENTITY_AUTHORIZATION", 0),
        "pos_refinement_template_count": lane_counts.get("POS_STATIC_GRAPH", 0),
        "report_refinement_template_count": lane_counts.get("REPORT_FORMULA_GRAIN", 0),
        "handoff_refinement_template_count": lane_counts.get("EXTERNAL_GATE_HANDOFF", 0),
        "failure_oracle_count": sum("failure_oracle" in row for row in templates),
        "required_refinement_receipt_slot_count": sum(len(row["required_receipts"]) for row in templates),
        "accepted_refinement_receipt_slot_count": 0,
        "design_lower_bound_before_refinement": prior_lower_bound,
        "additive_design_obligation_count": sum(row["additive_design_obligation_count"] for row in templates),
        "design_lower_bound_after_refinement": prior_lower_bound,
        "executed_refinement_case_count": 0,
        "owner_accepted_refinement_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "thirty_two_unique_templates": len(templates) == len({row["id"] for row in templates}) == 32,
        "lane_split_8_8_10_6": lane_counts == {"EXTERNAL_GATE_HANDOFF": 6, "IDENTITY_AUTHORIZATION": 8, "POS_STATIC_GRAPH": 8, "REPORT_FORMULA_GRAIN": 10},
        "all_non_additive": all(row["counting_effect"] == "REFINEMENT_NOT_ADDITIVE" and row["additive_design_obligation_count"] == 0 for row in templates),
        "lower_bound_unchanged_1404": summary["design_lower_bound_before_refinement"] == summary["design_lower_bound_after_refinement"] == 1404,
        "oracle_and_five_receipts_each": summary["failure_oracle_count"] == 32 and summary["required_refinement_receipt_slot_count"] == 160,
        "source_boundaries_pinned": data["identity"]["summary"]["triage_required_unit_count"] == 139
        and data["pos"]["summary"]["actionable_unresolved_name_or_type_count"] == 11
        and data["report"]["summary"]["surface_policy_obligation_count"] == 123
        and data["handoff"]["summary"]["gate_count"] == 6,
        "execution_acceptance_readiness_zero": summary["accepted_refinement_receipt_slot_count"]
        == summary["executed_refinement_case_count"]
        == summary["owner_accepted_refinement_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_cross_gate_golden_uat_refinement_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "OFFLINE_NON_ADDITIVE_GOLDEN_UAT_REFINEMENT", "continuation_complete": False},
        "safety": {
            "database_connections": 0,
            "forms_queries_reports_procedures_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_persisted": 0,
        },
        "summary": summary,
        "counting_policy": {
            "current_non_duplicated_design_lower_bound": 1404,
            "refinement_templates_are_additive": False,
            "promotion_rule": "ADD_ZERO_UNTIL_EXACT_CASE_ID_AND_SEMANTIC_OBLIGATION_CROSSWALK_PROVES_A_NEW_NON_DUPLICATED_CASE",
            "receipt_slots_are_not_case_counts": True,
        },
        "diagnostic_result_contract": data["playbook"]["diagnostic_result_contract"],
        "refinement_templates": templates,
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [{"name": "builder", "path": "scripts/windows/build_varanegar_cross_gate_golden_uat_refinement_matrix_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": [
            "The 32 templates refine existing obligations and add zero to the 1,404 design lower bound.",
            "No receipt was accepted and no scenario was executed.",
            "Runtime diagnosis, repair, replay, grant, approval and readiness promotion remain outside this artifact.",
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
