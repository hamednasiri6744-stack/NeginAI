import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "artifacts" / "varanegar_analysis" / "domains"
UI = ROOT / "artifacts" / "varanegar_analysis" / "ui"
SQL_BOUNDARY = DOMAIN / "ngt_payment_settlement_boundary_20260829.json"
RUNTIME_BOUNDARY = DOMAIN / "ngt_payment_runtime_boundary_20260829.json"
AUTH_ENDPOINTS = DOMAIN / "ngt_authorization_endpoint_coverage_20260828.json"
RISK = UI / "negin_erp_risk_register_20260829.json"
TRACE = UI / "negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = (
    ROOT / "artifacts" / "varanegar_analysis"
    / "varanegar_ngt_payment_checkpoint_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_payment_sql_boundary_is_read_only_private_and_definition_free():
    payload = _load(SQL_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_payment_settlement_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_AND_ANONYMOUS_STATE_AGGREGATES",
        "target_is_local": True,
        "database_name": "NeginPakhsh_WebDev",
        "expected_analysis_login_verified": True,
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_customer_user_cheque_sayad_account_device_comment_configuration_values_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "safe_schema_table_column_status_label_and_module_identifiers_persisted": True,
        "source_or_target_state_changed": 0,
    }
    text = SQL_BOUNDARY.read_text(encoding="utf-8")
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        text,
    )
    assert '"definition":' not in text


def test_payment_boundary_summary_is_exact():
    assert _load(SQL_BOUNDARY)["summary"] == {
        "target_table_count": 5,
        "catalog_column_count": 82,
        "payment_header_count": 3523,
        "payment_detail_count": 3917,
        "allocation_mismatch_count": 57,
        "underallocated_count": 57,
        "overallocated_count": 0,
        "receipt_linked_count": 274,
        "receipt_amount_scope_differs_count": 270,
        "exact_header_fingerprint_duplicate_group_count": 0,
        "related_foreign_key_count": 24,
        "untrusted_related_foreign_key_count": 24,
        "disabled_related_foreign_key_count": 0,
        "non_primary_unique_business_index_count": 0,
        "sql_module_fingerprint_count": 20,
        "target_trigger_count": 0,
    }


def test_all_four_settlement_types_resolve_to_the_expected_taxonomy():
    rows = _load(SQL_BOUNDARY)["population"]["semantic_settlement_type_usage"]
    assert {row["base_type"] for row in rows} == {"SettlementType"}
    assert {row["settlement_type"]: row["payments"] for row in rows} == {
        "كارت‌خوان": 3179,
        "نقد": 180,
        "چك": 159,
        "رسيد": 5,
    }
    integrity = _load(SQL_BOUNDARY)["integrity"]["referential_and_scope"]
    assert integrity["unresolved_settlement_type"] == 0
    assert integrity["wrong_settlement_base_type"] == 0


def test_57_active_headers_are_underallocated_and_none_are_overallocated():
    allocation = _load(SQL_BOUNDARY)["allocation"]
    assert allocation["header_detail_reconciliation"] == {
        "active_payments": 3523,
        "without_detail": 14,
        "one_detail": 3250,
        "multiple_details": 259,
        "amount_exact_to_cent": 3466,
        "amount_mismatch_to_cent": 57,
        "underallocated": 57,
        "overallocated": 0,
    }
    assert {
        row["settlement_type"]: (
            row["active_payments"], row["without_detail"], row["underallocated"]
        )
        for row in allocation["by_settlement_type"]
    } == {
        "كارت‌خوان": (3179, 7, 24),
        "نقد": (180, 2, 7),
        "چك": (159, 0, 21),
        "رسيد": (5, 5, 5),
    }


def test_detail_target_modes_separate_current_orders_from_old_sales():
    assert _load(SQL_BOUNDARY)["allocation"]["detail_target_modes"] == {
        "old_invoice_with_sale_uuid": 172,
        "old_invoice_with_ngt_order": 0,
        "current_order_with_ngt_order": 3745,
        "current_order_with_sale_uuid": 0,
        "no_order_or_sale_target": 0,
        "both_order_and_sale_uuid": 0,
    }


def test_payment_parent_scope_is_clean_and_one_cross_call_allocation_is_bounded():
    integrity = _load(SQL_BOUNDARY)["integrity"]
    refs = integrity["referential_and_scope"]
    assert {key: refs[key] for key in (
        "orphan_payment_call",
        "active_payment_removed_call",
        "payment_call_scope_mismatch",
        "orphan_detail_payment",
        "active_detail_removed_payment",
        "detail_payment_scope_mismatch",
        "orphan_detail_order",
        "active_detail_removed_order",
    )} == {key: 0 for key in (
        "orphan_payment_call",
        "active_payment_removed_call",
        "payment_call_scope_mismatch",
        "orphan_detail_payment",
        "active_detail_removed_payment",
        "detail_payment_scope_mismatch",
        "orphan_detail_order",
        "active_detail_removed_order",
    )}
    assert refs["detail_order_belongs_to_other_call"] == 1
    assert integrity["cross_call_detail_context_without_identifiers"] == [
        {
            "settlement_type": "كارت‌خوان",
            "same_tour": 1,
            "same_customer": 1,
            "IsOldInvoice": False,
            "order_removed": False,
            "receipt_linked": 0,
            "details": 1,
        }
    ]


def test_current_duplicate_candidates_are_zero_but_business_uniqueness_is_not_declared():
    payload = _load(SQL_BOUNDARY)
    duplicates = payload["integrity"]["duplicate_candidates"]
    assert duplicates == {
        "exact_header_fingerprint_duplicate_groups": 0,
        "headers_in_exact_fingerprint_duplicate_groups": 0,
        "duplicate_receipt_uuid_groups": 0,
        "headers_in_duplicate_receipt_uuid_groups": 0,
        "exact_detail_fingerprint_duplicate_groups": 0,
        "maximum_payments_per_customer_call": 8,
    }
    assert payload["summary"]["non_primary_unique_business_index_count"] == 0
    assert payload["summary"]["target_trigger_count"] == 0
    assert payload["summary"]["untrusted_related_foreign_key_count"] == 24


def test_receipt_identity_matches_but_amount_grain_usually_differs():
    receipt = _load(SQL_BOUNDARY)["backoffice_receipt_crosswalk"]
    assert receipt["identity_and_amount"] == {
        "linked": 274,
        "distinct_receipts": 274,
        "numeric_and_uuid_agree": 274,
        "amount_exact_to_cent": 4,
        "amount_scope_differs": 270,
        "receipt_number_agrees": 274,
        "confirmed_receipts": 274,
    }
    assert set(receipt["unmatched_and_ambiguous"].values()) == {0}


def test_tour_payment_approval_is_not_payment_presence():
    approval = _load(SQL_BOUNDARY)["tour_payment_approval"][
        "tour_payment_presence_vs_approval"
    ]
    assert approval == {
        "tours": 64561,
        "approved": 345,
        "with_payment": 458,
        "approved_without_payment": 26,
        "unapproved_with_payment": 139,
        "approved_with_payment": 319,
    }


def test_payment_configuration_retains_active_links_to_removed_terms():
    configuration = _load(SQL_BOUNDARY)["payment_configuration"]
    assert configuration["payment_terms"] == {
        "terms": 404,
        "active": 15,
        "removed": 389,
        "active_enabled": 15,
        "active_allow_receipt": 12,
        "active_certified": 0,
        "active_groups": 4,
        "active_minimum_payment_time": 3,
        "active_maximum_payment_time": 600,
    }
    assert configuration["dealer_bridge"]["mappings"] == 2521
    assert configuration["dealer_bridge"]["active_mapping_to_removed_type"] == 482
    assert configuration["pos_without_values"] == {
        "devices": 47,
        "active": 46,
        "removed": 1,
        "active_bank_accounts": 4,
        "active_serial_present": 46,
    }


def test_payment_runtime_is_static_and_all_17_core_methods_resolve():
    payload = _load(RUNTIME_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_payment_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
        "assemblies_loaded_or_executed": 0,
        "application_endpoints_or_commands_called": 0,
        "configuration_files_or_values_read": 0,
        "business_rows_or_identifiers_read": 0,
        "non_allowlisted_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    assert payload["summary"] == {
        "assembly_count": 4,
        "method_body_count": 27788,
        "method_body_error_count": 3,
        "signal_named_body_error_count": 0,
        "selected_method_count": 532,
        "focused_method_count": 138,
        "focused_mutation_method_count": 11,
        "core_method_count": 17,
        "missing_core_method_count": 0,
    }
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        RUNTIME_BOUNDARY.read_text(encoding="utf-8"),
    )


def test_payment_save_owns_a_transaction_but_update_tour_has_separate_children():
    payload = _load(RUNTIME_BOUNDARY)
    assert payload["payment_save_transaction_and_allocation_contract"] == {
        "explicit_begin_transaction": True,
        "explicit_commit": True,
        "explicit_rollback": True,
        "bulk_merge_present": True,
        "existing_cash_payment_filter_reference_present": True,
        "soft_remove_reference_present": True,
        "header_amount_accumulator_reference_present": True,
        "detail_paid_amount_accumulator_reference_present": True,
        "direct_static_caller_count": 1,
    }
    key = "NGT.Business.Domain.CustomerCallPaymentDomain.SaveTourPaymentChanges"
    save = payload["core_method_contracts"][key]
    assert save["mutation_calls_in_order"] == [
        "System.Data.Entity.Database.BeginTransaction",
        "TypeSpecRow.UpdateBatchAsync",
        "TypeSpecRow.BulkMergeListAsync",
        "TypeSpecRow.SaveChangesAsync",
        "System.Data.Entity.DbContextTransaction.Commit",
        "System.Data.Entity.DbContextTransaction.Rollback",
    ]
    caller = payload["direct_static_caller_contracts"][key][0]
    assert caller["owner"] == "NGT.Business.Domain.TourDomain+<UpdateTour>d__14"
    assert caller["mutation_calls_in_order"] == []
    child_calls = caller["call_references_in_order"]
    assert key in child_calls
    assert "NGT.Business.Domain.StockLevelDomain.SaveTourStockLevelChanges" in child_calls
    assert "NGT.Business.Domain.CustomerCallOrderDomain.UpdateFromNGT" in child_calls


def test_payment_confirmation_and_withdrawal_change_only_tour_approval_in_their_bodies():
    core = _load(RUNTIME_BOUNDARY)["core_method_contracts"]
    for name in ("ConfirmTourPayments", "WithdrawTourPayments"):
        method = core[f"NGT.Business.Domain.TourDomain.{name}"]
        assert method["mutation_calls_in_order"] == [
            "TypeSpecRow.UpdateBatchAsync",
            "TypeSpecRow.SaveChangesAsync",
        ]
        assert "NGT.DataAccess.Models.TourModel.Tour.set_PaymentApproved" in method[
            "state_references_in_order"
        ]
        assert "TourStatus.get_Received" in method["call_references_in_order"]


def test_payment_web_commands_keep_authorization_but_four_withdrawals_use_get():
    endpoints = _load(AUTH_ENDPOINTS)["endpoints"]
    names = {
        "ConfirmPreSaleTourPayments",
        "WithdrawPreSaleTourPayments",
        "ConfirmHotSaleTourPayments",
        "WithdrawHotSaleTourPayments",
        "ConfirmDistTourPayments",
        "WithdrawDistTourPayments",
        "ConfirmVanSaleTourPayments",
        "WithdrawVanSaleTourPayments",
    }
    rows = [
        row
        for row in endpoints
        if row["controller"] == "NGT.WebApi.Controllers.V2.TourController"
        and row["method"] in names
    ]
    assert len(rows) == 8
    assert sum("GET" in row["http_verbs"] for row in rows) == 4
    assert sum("POST" in row["http_verbs"] for row in rows) == 4
    assert all(row["ngt_authorize_attribute_count"] == 1 for row in rows)
    pos = [
        row
        for row in endpoints
        if row["controller"] == "NGT.WebApi.Controllers.V2.PosController"
        and row["method"] in {"Save", "Put", "Delete"}
    ]
    assert {row["method"]: row["http_verbs"] for row in pos} == {
        "Save": ["POST"],
        "Put": ["PUT"],
        "Delete": ["DELETE"],
    }
    assert all(row["ngt_authorization_shapes"] == ["resource_and_action"] for row in pos)


def test_payment_evidence_extends_transaction_and_configuration_risks_and_adds_r063():
    risks = _load(RISK)
    assert risks["validation"] == "PASS"
    assert risks["summary"] == {
        "risk_count": 84,
        "critical_count": 50,
        "high_count": 31,
        "medium_count": 3,
        "open_count": 84,
        "covered_module_count": 14,
        "risk_with_exit_criteria_count": 84,
        "validation_error_count": 0,
    }
    by_id = {row["id"]: row for row in risks["risks"]}
    assert "SaveTourPaymentChanges" in by_id["R-007"]["failure_mode"]
    assert "482 point to removed payment terms" in by_id["R-061"]["failure_mode"]
    assert by_id["R-063"]["severity"] == "CRITICAL"
    assert "57 are underallocated" in by_id["R-063"]["failure_mode"]
    trace = _load(TRACE)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_payment_checkpoint_is_hash_pinned_offline_and_complete():
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["artifact"] == "varanegar_ngt_payment_checkpoint_20260829"
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"] == {
        "source_count": 18,
        "passed_check_count": 40,
        "failed_check_count": 0,
        "payment_header_count": 3523,
        "payment_detail_count": 3917,
        "allocation_mismatch_count": 57,
        "receipt_linked_count": 274,
        "active_mapping_to_removed_term_count": 482,
        "runtime_core_method_count": 17,
        "withdrawal_get_endpoint_count": 4,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert all(checkpoint["checks"].values())
    assert checkpoint["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "configuration_values_business_rows_or_identifiers_read": 0,
    }
