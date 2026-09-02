"""Build a non-duplicative diagnostic addendum for the latest cross-gate findings."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "identity": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_20260829.json",
    "pos": "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_20260829.json",
    "formula": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "handoff": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "identity_playbook": "artifacts/varanegar_analysis/varanegar_identity_authorization_expert_playbook_20260829.json",
    "integration_playbook": "artifacts/varanegar_analysis/varanegar_integration_migration_expert_playbook_20260829.json",
    "reporting_playbook": "artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_checkpoint_20260829.json",
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
    existing_ids = {
        row["id"]
        for key in ("identity_playbook", "integration_playbook", "reporting_playbook")
        for row in data[key]["playbooks"]
    }
    common_steps = [
        "assign an opaque diagnostic case id and capture observation time, environment class and accountable role types without person identity or raw business values",
        "verify the exact source artifact, builder, policy and checkpoint hashes; stop and re-baseline when any source drift is present",
        "freeze the bounded evidence request and distinguish persisted static facts from requested external or runtime evidence",
        "recompute the relevant aggregate, key set, graph or policy assignment from the persisted redacted artifact before interpreting it",
        "apply the scenario-specific disambiguation steps and record only counts, states, hashes and approved classifications",
        "classify the result as EXPECTED_BOUNDARY, STATIC_EVIDENCE_GAP, DATA_OR_CONFIGURATION_DEBT, CONTRACT_OR_IMPLEMENTATION_DEFECT or UNPROVEN",
        "produce a hash-pinned evidence request naming the missing owner role, acceptance rule and prohibited payloads",
        "stop before endpoint/query/procedure/form execution, repair, replay, grant, mutation, readiness promotion or approval synthesis",
    ]
    specs = [
        {
            "id": "XG-PB-01",
            "boundary": "AUTHORIZATION_METADATA_DRIFT",
            "symptom": "authorization declaration, HTTP verb or manual-signal counts differ from the pinned 60/38/22 boundary",
            "source": "identity",
            "specific_steps": [
                "reconcile the verb split and signal classes independently: 31 POST, six PUT, one DELETE, 22 GET and zero named manual decisions",
                "attribute any changed count to assembly/metadata/extractor drift first; do not infer that a changed count is a security fix or incident",
            ],
            "evidence_to_request": ["hash-pinned endpoint metadata export", "extractor version/hash", "explicit endpoint disposition packet"],
            "not_duplicate_of": ["IA-PB-02"],
            "escalation_roles": ["SECURITY_AUTHORIZATION_OWNER_ROLE", "API_PLATFORM_OWNER_ROLE"],
            "risks": ["R-002", "R-024", "R-057"],
        },
        {
            "id": "XG-PB-02",
            "boundary": "MEMBERSHIP_SCOPE_CONCENTRATION",
            "symptom": "scope mismatch count changes or is generalized beyond the observed membership-user class",
            "source": "identity",
            "specific_steps": [
                "confirm that all 58 observed mismatches are membership_user_scope_mismatch and keep the orphan membership and owner-key collision separate",
                "compare hierarchy, owner-filter and admin-short-circuit policy versions without editing membership, grants or owner keys",
            ],
            "evidence_to_request": ["redacted hierarchy digest", "scope-disposition manifest", "owner-filter policy/implementation hash"],
            "not_duplicate_of": ["IA-PB-03", "IA-PB-04"],
            "escalation_roles": ["IDENTITY_DATA_OWNER_ROLE", "SECURITY_AUTHORIZATION_OWNER_ROLE"],
            "risks": ["R-003", "R-024", "R-059"],
        },
        {
            "id": "XG-PB-03",
            "boundary": "POS_GRAPH_TRUNCATION_AND_FRONTIER",
            "symptom": "the bounded POS graph is treated as complete or the opaque queue is equated with the visible depth-three frontier",
            "source": "pos",
            "specific_steps": [
                "separate the opaque unexpanded queue count 160 from the visible 151 callable and 32 table boundary nodes",
                "request a redacted higher-bound static export with queue identity manifest; never reconnect or expand through operational execution in this playbook",
            ],
            "evidence_to_request": ["redacted static catalog export", "queue identity manifest", "reviewed depth/node bound and extractor hash"],
            "not_duplicate_of": ["IM-PB-04"],
            "escalation_roles": ["INTEGRATION_TECHNICAL_OWNER_ROLE", "DATABASE_STATIC_EVIDENCE_OWNER_ROLE"],
            "risks": ["R-006", "R-023", "R-036"],
        },
        {
            "id": "XG-PB-04",
            "boundary": "POS_CYCLIC_TRIGGER_CASCADE",
            "symptom": "transaction ownership or mutation order is inferred from cyclic SQL dependencies",
            "source": "pos",
            "specific_steps": [
                "recompute the eleven cyclic components, 68 nodes and maximum size 17 and preserve trigger/table/procedure type counts",
                "treat 48 resolved write targets as a lower bound and lexical transaction/TRY/dynamic-SQL signals as non-runtime evidence",
            ],
            "evidence_to_request": ["component-level mutation crosswalk", "transaction-owner design", "fault/readback evidence packet"],
            "not_duplicate_of": ["IM-PB-03", "IM-PB-04"],
            "escalation_roles": ["TRANSACTION_CONTROL_OWNER_ROLE", "INTEGRATION_TECHNICAL_OWNER_ROLE"],
            "risks": ["R-005", "R-007", "R-034"],
        },
        {
            "id": "XG-PB-05",
            "boundary": "REPORT_KEYSET_GRAIN_MISMATCH",
            "symptom": "legacy and target totals match while row identity, grain or distribution differs",
            "source": "formula",
            "specific_steps": [
                "compare the exact stable key-set hashes before measures and bind both runs to the same fixture, filter, scope and watermark",
                "select the surface-specific grain policy dimensions; equal totals with a key-set mismatch cannot be accepted as result parity",
            ],
            "evidence_to_request": ["legacy/target key-set hashes", "grain policy version", "measure delta manifest"],
            "not_duplicate_of": ["RO-PB-04", "RO-PB-06"],
            "escalation_roles": ["REPORT_RESULT_OWNER_ROLE", "BUSINESS_CONTROL_OWNER_ROLE"],
            "risks": ["R-004", "R-017", "R-043"],
        },
        {
            "id": "XG-PB-06",
            "boundary": "TEMPLATE_OWNED_FORMULA_UNKNOWN",
            "symptom": "a template-owned sale/return report is assigned a grain or formula from its UI route or filename",
            "source": "formula",
            "specific_steps": [
                "verify the exact template hash and require query, subreport, formula-field and parameter-binding extraction before any formula comparison",
                "keep RPT-11 and RPT-12 at UNKNOWN_UNTIL_TEMPLATE_EXTRACTION; route, file existence and render success are not result ownership evidence",
            ],
            "evidence_to_request": ["template hash", "redacted query/subreport/formula manifest", "owner-approved template policy"],
            "not_duplicate_of": ["RO-PB-02", "RO-PB-03"],
            "escalation_roles": ["REPORT_TEMPLATE_OWNER_ROLE", "REPORT_RESULT_OWNER_ROLE"],
            "risks": ["R-017", "R-036", "R-043"],
        },
        {
            "id": "XG-PB-07",
            "boundary": "REPORT_POLICY_DIMENSION_DELTA",
            "symptom": "result difference is normalized away as null/zero, sign, rounding, currency, date or status noise",
            "source": "formula",
            "specific_steps": [
                "isolate one policy dimension at a time across null, sign, rounding stage, unit/currency/rate, business date and status inclusion",
                "require an approved policy version before normalization; convenient coercion or aggregate-only comparison remains unexplained",
            ],
            "evidence_to_request": ["per-dimension policy hashes", "unexplained-difference manifest", "owner approval bound to exact runs"],
            "not_duplicate_of": ["RO-PB-04", "RO-PB-06"],
            "escalation_roles": ["REPORT_RESULT_OWNER_ROLE", "FINANCIAL_CONTROL_OWNER_ROLE"],
            "risks": ["R-004", "R-017", "R-043"],
        },
        {
            "id": "XG-PB-08",
            "boundary": "ACCEPTED_PACKET_SUPERSESSION_OR_STALE_HANDOFF",
            "symptom": "a downstream gate references a stale, partial, proposed or superseded upstream evidence packet",
            "source": "handoff",
            "specific_steps": [
                "validate that every dependency edge points to the exact ACCEPTED_CURRENT packet-set hash and that all required units were accepted",
                "when a newer packet supersedes a source, invalidate downstream binding and request re-evaluation; never reuse an old approval or promote readiness",
            ],
            "evidence_to_request": ["current packet-set hash", "supersession chain", "downstream rebind and acceptance receipt"],
            "not_duplicate_of": [],
            "escalation_roles": ["EVIDENCE_GATE_COORDINATOR_ROLE", "ACCOUNTABLE_GATE_OWNER_ROLE"],
            "risks": ["R-002", "R-007", "R-023"],
        },
    ]
    playbooks = []
    for spec in specs:
        playbooks.append(
            {
                **spec,
                "steps": common_steps[:5] + spec["specific_steps"] + common_steps[5:],
                "stop_conditions": [
                    "source, policy, builder or checkpoint hash drift",
                    "operational execution, write access, replay, repair, grant, approval synthesis or readiness promotion required",
                    "raw business output, identity, credential, permission value or SQL definition would be persisted",
                    "accountable external owner decision is required",
                ],
                "current_diagnosis_count": 0,
                "repairs_or_executions_performed_count": 0,
            }
        )
    result_classes = {
        "EXPECTED_BOUNDARY": "the pinned contract explicitly explains the observation without contradiction",
        "STATIC_EVIDENCE_GAP": "the bounded static evidence cannot identify the required path, grain, packet or graph frontier",
        "DATA_OR_CONFIGURATION_DEBT": "a hierarchy, mapping, lineage or configuration defect is evidenced without proving implementation contradiction",
        "CONTRACT_OR_IMPLEMENTATION_DEFECT": "fresh evidence contradicts a pinned invariant or accepted contract",
        "UNPROVEN": "evidence is missing, stale, indirect or insufficient for another class",
    }
    summary = {
        "addendum_playbook_count": len(playbooks),
        "minimum_step_count": min(len(row["steps"]) for row in playbooks),
        "diagnostic_result_class_count": len(result_classes),
        "prior_playbook_count": len(existing_ids),
        "duplicate_playbook_id_count": sum(row["id"] in existing_ids for row in playbooks),
        "identity_triage_required_unit_count": data["identity"]["summary"]["triage_required_unit_count"],
        "pos_static_work_queue_count": len(data["pos"]["static_review_work_queue"]),
        "report_formula_policy_obligation_count": data["formula"]["summary"]["surface_policy_obligation_count"],
        "blocked_handoff_edge_count": data["handoff"]["summary"]["blocked_handoff_edge_count"],
        "runtime_diagnosis_count": 0,
        "repair_replay_grant_query_or_command_execution_count": 0,
        "accepted_evidence_packet_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "eight_non_duplicate_playbooks": summary["addendum_playbook_count"] == 8
        and summary["duplicate_playbook_id_count"] == 0,
        "minimum_ten_steps": summary["minimum_step_count"] >= 10,
        "five_result_classes": summary["diagnostic_result_class_count"] == 5,
        "latest_boundaries_bound": summary["identity_triage_required_unit_count"] == 139
        and summary["pos_static_work_queue_count"] == 5
        and summary["report_formula_policy_obligation_count"] == 123
        and summary["blocked_handoff_edge_count"] == 9,
        "every_playbook_has_disambiguation_and_roles": all(
            row["specific_steps"] and row["evidence_to_request"] and row["escalation_roles"] for row in playbooks
        ),
        "diagnosis_execution_acceptance_readiness_zero": summary["runtime_diagnosis_count"]
        == summary["repair_replay_grant_query_or_command_execution_count"]
        == summary["accepted_evidence_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_cross_gate_diagnostic_playbook_addendum_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_CROSS_GATE_DIAGNOSTIC_DESIGN_ADDENDUM",
            "replaces_existing_domain_playbooks": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "endpoints_queries_reports_templates_procedures_forms_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "repairs_replays_grants_or_approvals_performed": 0,
            "credentials_identity_raw_business_values_or_sql_definitions_persisted": 0,
            "data_mutations": 0,
            "write_access_created": 0,
        },
        "summary": summary,
        "diagnostic_result_contract": result_classes,
        "playbooks": playbooks,
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_cross_gate_diagnostic_playbook_addendum_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This addendum diagnoses evidence boundaries and does not replace the twenty existing operational domain playbooks.",
            "No runtime incident was diagnosed and no repair, replay, grant, query, command or approval was performed.",
            "All external gates, evidence packets and readiness states remain open or zero.",
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
