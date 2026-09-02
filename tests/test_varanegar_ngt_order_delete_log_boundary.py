from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_order_delete_log_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_ngt_order_delete_log_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_delete_log_boundary_is_read_only_and_identity_redacted():
    payload = _load(BOUNDARY_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_delete_log_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_trigger_or_application_command_executions"] == 0
    assert payload["safety"]["business_rows_or_identifiers_persisted"] == 0
    assert payload["safety"]["app_user_host_or_session_values_persisted"] == 0
    raw = BOUNDARY_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_trigger_and_log_schema_preserve_exact_delete_target_key():
    payload = _load(BOUNDARY_PATH)
    trigger = payload["delete_trigger_contract"]
    assert trigger["reads_deleted_id"] is True
    assert trigger["operation_type_delete_literal"] is True
    assert trigger["operation_table_target_literal"] is True
    assert trigger["operation_id_from_deleted_record"] is True
    assert trigger["canonical_delete_script_signal"] is True
    assert trigger["calls_insert_to_log"] is True
    log = payload["log_schema_contract"]
    assert log["column_count"] == 11
    assert all(
        log[key]
        for key in (
            "has_operation_type",
            "has_operation_table",
            "has_operation_id",
            "has_transaction_date",
            "has_app_name",
            "has_user_name",
            "has_host_name",
            "has_session_id",
            "operation_table_id_index_present",
        )
    )


def test_all_1024_missing_targets_have_one_exact_retained_delete_log():
    payload = _load(BOUNDARY_PATH)
    assert payload["summary"] == {
        "retained_order_delete_log_count": 1907,
        "missing_target_count": 1024,
        "missing_target_with_exact_delete_log_count": 1024,
        "missing_target_without_delete_log_count": 0,
        "delete_after_last_history_count": 1024,
        "recent_three_month_matched_delete_target_count": 115,
    }
    match = payload["missing_target_delete_match_contract"]
    assert match["missing_history_line_count"] == 5533
    assert match["matching_delete_log_count"] == 1024
    retained = payload["retained_delete_log_contract"]
    assert retained["retained_delete_log_count"] == 1907
    assert retained["distinct_delete_target_count"] == 1907
    assert retained["canonical_delete_script_count"] == 1907
    assert retained["distinct_direction_count"] == 1


def test_every_delete_follows_last_history_within_30_days():
    chronology = _load(BOUNDARY_PATH)["history_delete_chronology_contract"]
    assert chronology == {
        "target_count": 1024,
        "delete_at_or_after_last_history_count": 1024,
        "delete_before_first_history_count": 0,
        "delete_between_history_count": 0,
        "same_day_count": 298,
        "lag_1_7_day_count": 534,
        "lag_8_30_day_count": 192,
        "lag_over_30_day_count": 0,
        "min_lag_minutes": 0,
        "max_lag_minutes": 35783,
    }


def test_retained_delete_partition_and_monthly_counts_are_complete():
    payload = _load(BOUNDARY_PATH)
    assert payload["retained_delete_partition"] == {
        "retained_delete_id_count": 1907,
        "id_currently_present_count": 0,
        "missing_type1_target_count": 1024,
        "other_currently_absent_count": 883,
    }
    monthly = payload["monthly_matched_delete_counts"]
    assert len(monthly) == 24
    assert sum(row["matched_delete_count"] for row in monthly) == 1024
    assert monthly[0]["month_bucket"] == "2024-09"
    assert monthly[-1]["month_bucket"] == "2026-08"


def test_origin_evidence_is_anonymous_and_not_single_source_attribution():
    origin = _load(BOUNDARY_PATH)["anonymous_origin_cardinality_and_concentration"]
    assert origin == {
        "row_count": 1024,
        "distinct_app_count": 23,
        "distinct_user_count": 1,
        "distinct_host_count": 25,
        "distinct_session_count": 466,
        "null_app_count": 0,
        "null_user_count": 0,
        "max_rows_single_app": 567,
        "max_rows_single_host": 267,
        "max_rows_single_app_host_pair": 262,
        "distinct_app_host_pair_count": 39,
    }
    retention = _load(BOUNDARY_PATH)["log_retention_profiles"]
    assert len(retention) == 2
    assert all(not row["deletes_main_log_signal"] for row in retention)
    assert all(row["uses_last_exec_watermark_signal"] for row in retention)


def test_logged_tail_excludes_normal_ngt_rollback_and_undo_sequences():
    payload = _load(BOUNDARY_PATH)
    assert payload["delete_pathway_fingerprint"] == {
        "target_count": 1024,
        "item_before_visit_before_header_count": 1024,
        "visit_before_item_before_header_count": 0,
        "no_item_signal_count": 0,
        "no_visit_signal_count": 0,
        "immediately_preceding_visit_count": 1008,
        "non_adjacent_preceding_visit_count": 16,
        "preceding_sale_header_delete_signal_count": 0,
    }
    rows = {row["object_name"]: row for row in payload["static_delete_sequence_contracts"]}
    assert rows["NGT_RollBackTour"]["visit_before_item_before_header"] is True
    assert rows["NGT_RollBackTour"]["tour_history_delete_follows_order_header"] is True
    assert rows["usp_sdsnet_Order_Delete"]["item_before_visit_before_header"] is True
    assert "visit_order" not in rows["USP_sdsnet_UndoUserExtraInfo"]["delete_target_sequence"]
    assert rows["usp_sdsnet_ConfirmFreeInvoice"]["item_before_visit_before_header"] is True
    assert rows["usp_sdsnet_ConfirmFreeInvoice"]["sale_delete_precedes_order_item"] is True


def test_missing_target_order_type_partition_does_not_overclaim_route():
    assert _load(BOUNDARY_PATH)["missing_target_order_type_partition"] == {
        "target_count": 1024,
        "parent_count": 1022,
        "free_invoice_true_target_count": 524,
        "free_invoice_true_parent_count": 522,
        "free_invoice_false_target_count": 7,
        "free_invoice_null_target_count": 493,
    }


def test_r069_and_r070_now_prove_deletion_but_not_route_or_reason():
    risks = _load(RISK_PATH)
    r069 = next(row for row in risks["risks"] if row["id"] == "R-069")
    r070 = next(row for row in risks["risks"] if row["id"] == "R-070")
    assert "This proves target deletion after replication" in r069["failure_mode"]
    assert "does not identify the calling procedure" in r069["failure_mode"]
    assert "exactly matches all 1,024" in r070["failure_mode"]
    assert "does not attribute any current missing target" in r070["failure_mode"]
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    trace = _load(TRACE_PATH)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_delete_log_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_delete_log_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 16,
        "passed_check_count": 21,
        "failed_check_count": 0,
        "retained_delete_log_count": 1907,
        "matched_missing_target_count": 1024,
        "delete_after_history_count": 1024,
        "recent_matched_delete_count": 115,
        "risk_count": 84,
        "critical_risk_count": 50,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 16
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
