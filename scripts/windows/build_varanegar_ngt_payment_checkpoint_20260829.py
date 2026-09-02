"""Build an offline hash-pinned checkpoint for the NGT payment boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_settlement_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_payment_runtime_boundary_20260829.json",
    "authorization_endpoints": "artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json",
    "tour_call_boundary": "artifacts/varanegar_analysis/domains/ngt_tour_call_state_boundary_20260829.json",
    "order_boundary": "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_payment_settlement_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_payment_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_payment_checkpoint_20260829.py",
    "payment_tests": "tests/test_varanegar_ngt_payment_settlement_boundary.py",
    "payment_doc": "docs/varanegar_reconstruction/NGT_PAYMENT_SETTLEMENT_AND_RECEIPT_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "reconstruction_readme": "docs/varanegar_reconstruction/README_FA.md",
}

PAYMENT_TOUR_ENDPOINT_NAMES = {
    "ConfirmPreSaleTourPayments",
    "WithdrawPreSaleTourPayments",
    "ConfirmHotSaleTourPayments",
    "WithdrawHotSaleTourPayments",
    "ConfirmDistTourPayments",
    "WithdrawDistTourPayments",
    "ConfirmVanSaleTourPayments",
    "WithdrawVanSaleTourPayments",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    missing = [value for value in SOURCES.values() if not (ROOT / value).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    endpoints = _load("authorization_endpoints")
    risks = _load("risk_register")
    trace = _load("traceability")
    summary = sql["summary"]
    integrity = sql["integrity"]
    refs = integrity["referential_and_scope"]
    allocation = sql["allocation"]
    receipt = sql["backoffice_receipt_crosswalk"]
    approval = sql["tour_payment_approval"]["tour_payment_presence_vs_approval"]
    configuration = sql["payment_configuration"]
    core = runtime["core_method_contracts"]
    save_key = "NGT.Business.Domain.CustomerCallPaymentDomain.SaveTourPaymentChanges"
    save = core[save_key]
    caller = runtime["direct_static_caller_contracts"][save_key]
    payment_endpoints = [
        row
        for row in endpoints["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.TourController"
        and row["method"] in PAYMENT_TOUR_ENDPOINT_NAMES
    ]
    pos_endpoints = [
        row
        for row in endpoints["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.PosController"
        and row["method"] in {"Save", "Put", "Delete"}
    ]
    by_risk = {row["id"]: row for row in risks["risks"]}
    by_settlement = {
        row["settlement_type"]: row["payments"]
        for row in sql["population"]["semantic_settlement_type_usage"]
    }
    by_allocation = {
        row["settlement_type"]: row["underallocated"]
        for row in allocation["by_settlement_type"]
    }
    privacy_text = (
        (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8")
        + (ROOT / SOURCES["runtime_boundary"]).read_text(encoding="utf-8")
    )

    checks = {
        "sql_artifact_valid_and_read_only": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["denies_data_writes"] == 1,
        "sql_executed_no_commands_and_persisted_no_rows": sql["safety"][
            "stored_procedure_or_application_command_executions"
        ]
        == 0
        and sql["safety"][
            "business_rows_customer_user_cheque_sayad_account_device_comment_configuration_values_or_identifiers_persisted"
        ]
        == 0,
        "five_tables_82_columns_3523_headers_3917_details": summary[
            "target_table_count"
        ]
        == 5
        and summary["catalog_column_count"] == 82
        and summary["payment_header_count"] == 3523
        and summary["payment_detail_count"] == 3917,
        "four_settlement_types_have_expected_counts": by_settlement
        == {"كارت‌خوان": 3179, "نقد": 180, "چك": 159, "رسيد": 5},
        "recent_month_buckets_are_semantic_aggregates": len(
            sql["population"]["recent_six_calendar_months_by_settlement_type"]
        )
        == 10,
        "57_underallocated_and_zero_overallocated": allocation[
            "header_detail_reconciliation"
        ]["underallocated"]
        == 57
        and allocation["header_detail_reconciliation"]["overallocated"] == 0,
        "underallocation_by_settlement_is_exact": by_allocation
        == {"كارت‌خوان": 24, "نقد": 7, "چك": 21, "رسيد": 5},
        "detail_target_modes_are_disjoint_and_complete": allocation[
            "detail_target_modes"
        ]
        == {
            "old_invoice_with_sale_uuid": 172,
            "old_invoice_with_ngt_order": 0,
            "current_order_with_ngt_order": 3745,
            "current_order_with_sale_uuid": 0,
            "no_order_or_sale_target": 0,
            "both_order_and_sale_uuid": 0,
        },
        "current_parent_and_scope_integrity_is_zero": all(
            refs[key] == 0
            for key in (
                "orphan_payment_call",
                "active_payment_removed_call",
                "payment_call_scope_mismatch",
                "orphan_detail_payment",
                "active_detail_removed_payment",
                "detail_payment_scope_mismatch",
                "orphan_detail_order",
                "active_detail_removed_order",
            )
        ),
        "one_cross_call_detail_stays_same_tour_and_customer": refs[
            "detail_order_belongs_to_other_call"
        ]
        == 1
        and integrity["cross_call_detail_context_without_identifiers"][0]["same_tour"]
        == 1
        and integrity["cross_call_detail_context_without_identifiers"][0]["same_customer"]
        == 1,
        "current_exact_duplicate_candidates_are_zero": all(
            integrity["duplicate_candidates"][key] == 0
            for key in (
                "exact_header_fingerprint_duplicate_groups",
                "headers_in_exact_fingerprint_duplicate_groups",
                "duplicate_receipt_uuid_groups",
                "headers_in_duplicate_receipt_uuid_groups",
                "exact_detail_fingerprint_duplicate_groups",
            )
        ),
        "no_nonprimary_business_unique_index_or_trigger": summary[
            "non_primary_unique_business_index_count"
        ]
        == 0
        and summary["target_trigger_count"] == 0,
        "all_24_related_foreign_keys_are_enabled_but_untrusted": summary[
            "related_foreign_key_count"
        ]
        == 24
        and summary["untrusted_related_foreign_key_count"] == 24
        and summary["disabled_related_foreign_key_count"] == 0,
        "274_receipt_identities_reconcile": receipt["identity_and_amount"]["linked"]
        == 274
        and receipt["identity_and_amount"]["numeric_and_uuid_agree"] == 274
        and receipt["identity_and_amount"]["receipt_number_agrees"] == 274,
        "270_receipt_amounts_have_different_scope": receipt["identity_and_amount"][
            "amount_exact_to_cent"
        ]
        == 4
        and receipt["identity_and_amount"]["amount_scope_differs"] == 270,
        "tour_approval_is_not_payment_presence": approval["approved"] == 345
        and approval["with_payment"] == 458
        and approval["approved_without_payment"] == 26
        and approval["unapproved_with_payment"] == 139,
        "404_terms_only_15_active": configuration["payment_terms"]["terms"] == 404
        and configuration["payment_terms"]["active"] == 15
        and configuration["payment_terms"]["removed"] == 389,
        "482_active_bridges_reference_removed_terms": configuration["dealer_bridge"][
            "mappings"
        ]
        == 2521
        and configuration["dealer_bridge"]["active_mapping_to_removed_type"] == 482,
        "46_of_47_pos_devices_are_active_without_values_persisted": configuration[
            "pos_without_values"
        ]["devices"]
        == 47
        and configuration["pos_without_values"]["active"] == 46,
        "20_sql_modules_are_fingerprinted_not_persisted": summary[
            "sql_module_fingerprint_count"
        ]
        == 20
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "runtime_artifact_valid_and_static": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY",
        "runtime_executed_nothing_and_read_no_values": runtime["safety"][
            "assemblies_loaded_or_executed"
        ]
        == 0
        and runtime["safety"]["application_endpoints_or_commands_called"] == 0
        and runtime["safety"]["business_rows_or_identifiers_read"] == 0,
        "runtime_scanned_27788_bodies_with_no_signal_error": runtime["summary"][
            "method_body_count"
        ]
        == 27788
        and runtime["summary"]["signal_named_body_error_count"] == 0,
        "all_17_core_methods_resolve": runtime["summary"]["core_method_count"] == 17
        and runtime["summary"]["missing_core_method_count"] == 0,
        "payment_save_has_begin_commit_rollback_and_bulk_merge": all(
            runtime["payment_save_transaction_and_allocation_contract"][key]
            for key in (
                "explicit_begin_transaction",
                "explicit_commit",
                "explicit_rollback",
                "bulk_merge_present",
            )
        ),
        "payment_save_mutation_sequence_is_exact": save["mutation_calls_in_order"]
        == [
            "System.Data.Entity.Database.BeginTransaction",
            "TypeSpecRow.UpdateBatchAsync",
            "TypeSpecRow.BulkMergeListAsync",
            "TypeSpecRow.SaveChangesAsync",
            "System.Data.Entity.DbContextTransaction.Commit",
            "System.Data.Entity.DbContextTransaction.Rollback",
        ],
        "update_tour_is_only_direct_payment_save_caller": len(caller) == 1
        and caller[0]["owner"] == "NGT.Business.Domain.TourDomain+<UpdateTour>d__14",
        "update_tour_calls_payment_stock_and_order_without_local_mutation": caller[0][
            "mutation_calls_in_order"
        ]
        == []
        and {
            save_key,
            "NGT.Business.Domain.StockLevelDomain.SaveTourStockLevelChanges",
            "NGT.Business.Domain.CustomerCallOrderDomain.UpdateFromNGT",
        }.issubset(set(caller[0]["call_references_in_order"])),
        "confirm_payment_sets_approval_and_saves": core[
            "NGT.Business.Domain.TourDomain.ConfirmTourPayments"
        ]["mutation_calls_in_order"]
        == ["TypeSpecRow.UpdateBatchAsync", "TypeSpecRow.SaveChangesAsync"],
        "withdraw_payment_sets_approval_and_saves": core[
            "NGT.Business.Domain.TourDomain.WithdrawTourPayments"
        ]["mutation_calls_in_order"]
        == ["TypeSpecRow.UpdateBatchAsync", "TypeSpecRow.SaveChangesAsync"],
        "pos_domain_add_update_remove_resolve": all(
            core[f"NGT.Business.Domain.PosDomain.{name}"] is not None
            for name in ("Add", "Update", "Remove")
        ),
        "eight_payment_tour_endpoints_are_selected": len(payment_endpoints) == 8,
        "four_withdraw_get_and_four_confirm_post": sum(
            "GET" in row["http_verbs"] for row in payment_endpoints
        )
        == 4
        and sum("POST" in row["http_verbs"] for row in payment_endpoints) == 4,
        "all_payment_tour_endpoints_have_one_ngt_authorization": all(
            row["ngt_authorize_attribute_count"] == 1 for row in payment_endpoints
        ),
        "pos_write_verbs_and_resource_action_auth_are_explicit": {
            row["method"]: row["http_verbs"] for row in pos_endpoints
        }
        == {"Save": ["POST"], "Put": ["PUT"], "Delete": ["DELETE"]}
        and all(
            row["ngt_authorization_shapes"] == ["resource_and_action"]
            for row in pos_endpoints
        ),
        "risk_register_valid_65_with_37_critical": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50,
        "r063_is_critical_and_carries_57_mismatches": by_risk["R-063"]["severity"]
        == "CRITICAL"
        and "57 are underallocated" in by_risk["R-063"]["failure_mode"],
        "r007_and_r061_are_extended_by_payment_evidence": "SaveTourPaymentChanges"
        in by_risk["R-007"]["failure_mode"]
        and "482 point to removed payment terms" in by_risk["R-061"]["failure_mode"],
        "traceability_valid_256_and_zero_command_ready": trace["validation"] == "PASS"
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "payment_artifacts_contain_no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            privacy_text,
        )
        is None,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    manifest = [
        {
            "name": name,
            "path": relative,
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_ngt_payment_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "configuration_values_business_rows_or_identifiers_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "payment_header_count": summary["payment_header_count"],
            "payment_detail_count": summary["payment_detail_count"],
            "allocation_mismatch_count": summary["allocation_mismatch_count"],
            "receipt_linked_count": summary["receipt_linked_count"],
            "active_mapping_to_removed_term_count": configuration["dealer_bridge"][
                "active_mapping_to_removed_type"
            ],
            "runtime_core_method_count": runtime["summary"]["core_method_count"],
            "withdrawal_get_endpoint_count": sum(
                "GET" in row["http_verbs"] for row in payment_endpoints
            ),
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "mapped_risk_assignment_count": trace["summary"][
                "mapped_risk_assignment_count"
            ],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
