"""Build an offline formula/grain policy matrix for the eleven true result owners."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "reports": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "golden": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "intake": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "party": "artifacts/varanegar_analysis/domains/party_cardex_reference_contract_20260829.json",
    "call_center": "artifacts/varanegar_analysis/domains/call_center_report_contract_20260829.json",
    "return_template": "artifacts/varanegar_analysis/domains/return_report_template_boundary_20260829.json",
    "sale_invoice": "artifacts/varanegar_analysis/varanegar_sale_invoice_print_checkpoint_20260829.json",
    "production_order": "artifacts/varanegar_analysis/domains/production_order_report_contract_20260829.json",
    "production_detail": "artifacts/varanegar_analysis/domains/production_detail_report_contract_20260829.json",
    "stock": "artifacts/varanegar_analysis/domains/stock_report_reference_contract_20260829.json",
    "healthy": "artifacts/varanegar_analysis/domains/healthy_cardex_report_contract_20260829.json",
    "bank": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_read_model_contract_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.json",
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
    surfaces = {row["contract_id"]: row for row in data["reports"]["surfaces"]}
    result_ids = sorted(row["contract_id"] for row in surfaces.values() if row["independent_result_parity_applicable"])
    fixture_counts = Counter(row["contract_id"] for row in data["golden"]["cases"] if row["contract_id"] in result_ids)

    dimensions = [
        {"id": "FP-01", "dimension": "row_grain_and_stable_comparison_key"},
        {"id": "FP-02", "dimension": "business_date_basis_source_watermark_and_as_of_cutoff"},
        {"id": "FP-03", "dimension": "tenant_fiscal_dc_resource_scope_and_authorization"},
        {"id": "FP-04", "dimension": "status_cancel_delete_void_and_absent_line_inclusion"},
        {"id": "FP-05", "dimension": "null_empty_missing_and_zero_semantics"},
        {"id": "FP-06", "dimension": "debit_credit_quantity_and_movement_sign_direction"},
        {"id": "FP-07", "dimension": "decimal_precision_scale_and_rounding_stage"},
        {"id": "FP-08", "dimension": "unit_currency_rate_and_conversion_basis"},
        {"id": "FP-09", "dimension": "stable_ordering_pagination_subtotals_and_final_totals"},
        {"id": "FP-10", "dimension": "opening_period_closing_and_carry_forward_policy"},
        {"id": "FP-11", "dimension": "branch_mode_report_role_and_discriminator_mapping"},
        {"id": "FP-12", "dimension": "external_template_query_subreport_formula_and_parameter_binding"},
        {"id": "FP-13", "dimension": "master_detail_and_cross_projection_reconciliation"},
        {"id": "FP-14", "dimension": "query_template_projection_and_formula_version_identity"},
    ]
    common = ["FP-01", "FP-02", "FP-03", "FP-04", "FP-05", "FP-06", "FP-07", "FP-08", "FP-09", "FP-14"]
    specs = {
        "RPT-05": ("party", "QUERY_BOUND", "PARTY_DOCUMENT_MOVEMENT", "MEASURE_FAMILIES_KNOWN_OWNER_FORMULA_POLICY_MISSING", ["FP-10"]),
        "RPT-06": ("call_center", "QUERY_BOUND", "BRANCH_DEPENDENT_CUSTOMER_OR_PRODUCT_PERFORMANCE", "BRANCH_MEASURES_KNOWN_MODE_VALUE_MAPPING_AND_OWNER_FORMULA_MISSING", ["FP-11"]),
        "RPT-07": ("party", "QUERY_BOUND", "PARTY_DOCUMENT_MOVEMENT_TRANSACTION_CURRENCY", "MEASURE_FAMILIES_KNOWN_CURRENCY_RATE_AND_OWNER_FORMULA_POLICY_MISSING", ["FP-10"]),
        "RPT-08": ("party", "QUERY_BOUND", "PARTY_DOCUMENT_MOVEMENT_BASE_CURRENCY", "MEASURE_FAMILIES_KNOWN_OWNER_FORMULA_POLICY_MISSING", ["FP-10"]),
        "RPT-11": ("return_template", "EXTERNAL_TEMPLATE_OWNED", "TEMPLATE_OWNED_UNEXTRACTED", "TEMPLATE_QUERY_SUBREPORT_AND_FORMULA_EXTRACTION_MISSING", ["FP-12"]),
        "RPT-12": ("sale_invoice", "EXTERNAL_TEMPLATE_OWNED", "TEMPLATE_OWNED_UNEXTRACTED", "TEMPLATE_QUERY_SUBREPORT_AND_FORMULA_EXTRACTION_MISSING", ["FP-12"]),
        "RPT-13": ("production_order", "QUERY_BOUND", "PRODUCTION_ORDER_ITEM", "QUANTITY_SHAPE_KNOWN_OWNER_FORMULA_POLICY_MISSING", []),
        "RPT-14": ("production_detail", "QUERY_BOUND", "PRODUCTION_BATCH_MASTER_DETAIL_BRANCH", "MODE_SHAPE_KNOWN_DISCRIMINATOR_AND_OWNER_FORMULA_MISSING", ["FP-11", "FP-13"]),
        "RPT-15": ("stock", "QUERY_BOUND_MULTI_ROLE", "ROLE_DEPENDENT_TEN_DERIVED_STOCK_REPORT_PROCEDURES", "PROCEDURE_SHAPES_KNOWN_PER_ROLE_FORMULA_POLICY_MISSING", ["FP-11", "FP-13"]),
        "RPT-18": ("healthy", "QUERY_BOUND_MASTER_DETAIL", "HEALTHY_CARDEX_MASTER_DETAIL", "MASTER_DETAIL_SHAPE_KNOWN_RAW_WHERE_REPLACEMENT_AND_OWNER_FORMULA_MISSING", ["FP-13"]),
        "RPT-19": ("bank", "TYPED_READ_MODEL_AND_SUMMARY", "BANK_SESSION_STATEMENT_ROW_LINK_AND_SUMMARY", "ELEVEN_FORMULA_EXPRESSIONS_DESIGNED_RUNTIME_AND_OWNER_PARITY_MISSING", ["FP-10", "FP-13"]),
    }
    rows = []
    for contract_id in result_ids:
        anchor, owner_kind, grain, formula_state, extra = specs[contract_id]
        surface = surfaces[contract_id]
        rows.append(
            {
                "contract_id": contract_id,
                "legacy_type": surface["legacy_type"],
                "ownership_class": surface["ownership_class"],
                "result_owner_kind": owner_kind,
                "evidence_anchor": SOURCES[anchor],
                "grain_contract": grain,
                "grain_policy_status": "UNKNOWN_UNTIL_TEMPLATE_EXTRACTION" if owner_kind == "EXTERNAL_TEMPLATE_OWNED" else "STATIC_SHAPE_DEFINED_OWNER_APPROVAL_MISSING",
                "formula_policy_status": formula_state,
                "required_policy_dimension_ids": common + extra,
                "designed_golden_fixture_count": fixture_counts[contract_id],
                "executed_golden_fixture_count": 0,
                "accepted_formula_packet_count": 0,
                "owner_approved_formula_count": 0,
                "result_parity_proven": False,
                "command_ready": False,
                "pilot_ready": False,
            }
        )

    packet_fields = [
        "contract_id",
        "source_query_or_template_contract_hash",
        "query_template_subreport_definition_hash_set",
        "frozen_fixture_snapshot_hash",
        "filter_hash",
        "scope_hash",
        "source_watermark",
        "grain_policy_version_hash",
        "formula_policy_version_hash",
        "null_policy_version_hash",
        "sign_policy_version_hash",
        "rounding_policy_version_hash",
        "currency_unit_policy_version_hash",
        "status_inclusion_policy_version_hash",
        "legacy_run_receipt_hash",
        "target_run_receipt_hash",
        "legacy_key_set_hash",
        "target_key_set_hash",
        "measure_delta_manifest_hash",
        "owner_approval_reference_hash",
    ]
    summary = {
        "report_surface_count": data["reports"]["summary"]["report_surface_count"],
        "result_owner_surface_count": len(rows),
        "query_bound_result_owner_count": sum("QUERY_BOUND" in row["result_owner_kind"] for row in rows),
        "external_template_result_owner_count": sum(row["result_owner_kind"] == "EXTERNAL_TEMPLATE_OWNED" for row in rows),
        "typed_bank_summary_result_owner_count": sum(row["result_owner_kind"] == "TYPED_READ_MODEL_AND_SUMMARY" for row in rows),
        "grain_static_shape_defined_surface_count": sum(row["grain_policy_status"].startswith("STATIC_SHAPE_DEFINED") for row in rows),
        "template_grain_unknown_surface_count": sum(row["grain_policy_status"] == "UNKNOWN_UNTIL_TEMPLATE_EXTRACTION" for row in rows),
        "explicit_formula_expression_design_surface_count": 1 if len(data["bank"]["summary_formula_contracts"]) == 11 else 0,
        "explicit_bank_formula_expression_count": len(data["bank"]["summary_formula_contracts"]),
        "policy_dimension_count": len(dimensions),
        "surface_policy_obligation_count": sum(len(row["required_policy_dimension_ids"]) for row in rows),
        "required_packet_field_count": len(packet_fields),
        "designed_golden_fixture_count": sum(row["designed_golden_fixture_count"] for row in rows),
        "executed_golden_fixture_count": 0,
        "accepted_formula_packet_count": 0,
        "owner_approved_formula_surface_count": 0,
        "result_parity_proven_surface_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "eleven_exact_result_owners": result_ids == ["RPT-05", "RPT-06", "RPT-07", "RPT-08", "RPT-11", "RPT-12", "RPT-13", "RPT-14", "RPT-15", "RPT-18", "RPT-19"],
        "owner_partition_8_2_1": summary["query_bound_result_owner_count"] == 8
        and summary["external_template_result_owner_count"] == 2
        and summary["typed_bank_summary_result_owner_count"] == 1,
        "grain_partition_9_2": summary["grain_static_shape_defined_surface_count"] == 9
        and summary["template_grain_unknown_surface_count"] == 2,
        "bank_formula_design_11_not_parity": summary["explicit_formula_expression_design_surface_count"] == 1
        and summary["explicit_bank_formula_expression_count"] == 11,
        "fourteen_dimensions_123_obligations": summary["policy_dimension_count"] == 14
        and summary["surface_policy_obligation_count"] == 123,
        "twenty_fields_fifty_fixtures": summary["required_packet_field_count"] == 20
        and summary["designed_golden_fixture_count"] == 50,
        "execution_approval_parity_readiness_zero": summary["executed_golden_fixture_count"]
        == summary["accepted_formula_packet_count"]
        == summary["owner_approved_formula_surface_count"]
        == summary["result_parity_proven_surface_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_report_formula_grain_policy_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_REPORT_FORMULA_GRAIN_RESULT_PARITY_DESIGN",
            "gate_id": "CG-05",
            "covers_result_owner_subgate_only": True,
            "cg05_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "reports_queries_templates_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "raw_business_values_or_outputs_read_or_persisted": 0,
            "data_mutations": 0,
            "write_access_created": 0,
        },
        "summary": summary,
        "policy_dimensions": dimensions,
        "result_owner_formula_grain_matrix": rows,
        "formula_packet_schema": {
            "required_fields": packet_fields,
            "prohibited_fields": [
                "raw_business_row_or_report_output",
                "person_identity_or_credential",
                "mutable_or_unsigned_approval",
                "unversioned_formula_or_template",
                "null_to_zero_or_rounding_inference_without_owner_policy",
            ],
            "acceptance_rule": "The exact source and target runs share frozen fixture, filter, scope and watermark; grain and every applicable formula policy are versioned; key sets match before measures; unexplained differences are zero; the accountable result owner approves the exact immutable packet.",
        },
        "global_formula_invariants": [
            "Compare stable key sets before aggregate totals; equal totals cannot hide redistributed or missing rows.",
            "Never coerce null, missing or empty to zero without an approved per-field policy.",
            "Declare precision, scale and the exact rounding stage; per-row and post-aggregate rounding are not interchangeable.",
            "Declare sign at the movement-kind boundary; presentation direction must not silently change ledger direction.",
            "Base currency, transaction currency, unit conversion and rate source are separate dimensions.",
            "Business date and source watermark are explicit; create, migration or render timestamps are not substitutes.",
            "Status, cancel, delete, void and absent-line inclusion are versioned formula inputs.",
            "Template-owned surfaces require query, subreport, formula-field and parameter extraction before grain or parity claims.",
            "Ordering, pagination and subtotal/final-total scopes are compared separately from row content.",
            "A passing design artifact or 11 written bank formulas is not runtime result parity or owner approval.",
        ],
        "cg05_result_owner_subgate": {
            "required_formula_packet_count": 11,
            "current_accepted_formula_packet_count": 0,
            "required_executed_golden_fixture_count": 50,
            "current_executed_golden_fixture_count": 0,
            "status": "OPEN_EXTERNAL_REPORT_UAT_GATE",
            "non_result_surface_packet_count_outside_this_matrix": 9,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_report_formula_grain_policy_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This matrix designs the eleven result-owner formula packets; it does not close the nine non-result CG-05 packets.",
            "No report, query, template, formula or Golden fixture was executed.",
            "Formula parity, owner approval, command readiness and pilot readiness remain zero.",
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
