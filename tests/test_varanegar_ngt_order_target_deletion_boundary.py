from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_order_target_deletion_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_ngt_order_deletion_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_deletion_boundary_is_read_only_and_redacted():
    payload = _load(BOUNDARY_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_target_deletion_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_or_application_command_executions"] == 0
    assert payload["safety"]["sql_definitions_persisted"] == 0
    raw = BOUNDARY_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_only_four_static_direct_delete_procedures_survive_comment_stripping():
    payload = _load(BOUNDARY_PATH)
    assert payload["summary"]["module_referencing_target_count"] == 404
    assert payload["summary"]["direct_delete_module_count"] == 4
    assert payload["summary"]["executable_static_delete_candidate_count"] == 4
    names = {
        f"{row['schema_name']}.{row['object_name']}"
        for row in payload["direct_delete_module_profiles"]
    }
    assert names == {
        "dbo.NGT_RollBackTour",
        "dbo.usp_sdsnet_Order_Delete",
        "dbo.USP_sdsnet_UndoUserExtraInfo",
        "SLE.usp_sdsnet_ConfirmFreeInvoice",
    }


def test_only_ngt_rollback_delete_path_knows_tour_history():
    payload = _load(BOUNDARY_PATH)
    rows = payload["direct_delete_module_profiles"]
    assert sum(row["tour_history_signal"] for row in rows) == 1
    assert next(row for row in rows if row["tour_history_signal"])["object_name"] == "NGT_RollBackTour"
    assert sum(row["ngt_order_line_signal"] for row in rows) == 0
    assert sum(row["order_crosswalk_signal"] for row in rows) == 0
    assert payload["summary"]["direct_delete_with_transaction_count"] == 3
    assert payload["summary"]["direct_delete_with_try_catch_count"] == 3
    assert payload["summary"]["direct_delete_with_xact_abort_count"] == 0


def test_delete_triggers_do_not_reconcile_ngt_crosswalk_or_history():
    payload = _load(BOUNDARY_PATH)
    deletes = [
        row
        for row in payload["target_trigger_profiles"]
        if row["event_type"] == "DELETE" and not row["is_disabled"]
    ]
    assert len(deletes) == 3
    assert sum(row["replication_log_signal"] for row in deletes) == 1
    assert sum(row["ngt_crosswalk_signal"] for row in deletes) == 0
    assert sum(row["tour_history_signal"] for row in deletes) == 0


def test_target_has_no_temporal_cdc_or_change_tracking_tombstone():
    payload = _load(BOUNDARY_PATH)
    assert payload["table_features"] == {
        "temporal_type_desc": "NON_TEMPORAL_TABLE",
        "is_tracked_by_cdc": False,
        "change_tracking_enabled": 0,
        "temporal_history_present": 0,
    }
    fks = payload["referencing_foreign_keys"]
    assert len(fks) == 12
    assert sum(row["delete_referential_action_desc"] == "NO_ACTION" for row in fks) == 11
    assert sum(row["delete_referential_action_desc"] == "CASCADE" for row in fks) == 1
    assert all(not row["is_disabled"] and row["is_not_trusted"] for row in fks)
    assert payload["direct_delete_callers"] == [{
        "caller_schema": "dbo",
        "caller_name": "usp_sdsnet_Order_Save",
        "caller_type": "SQL_STORED_PROCEDURE",
        "callee_schema": "dbo",
        "callee_name": "usp_sdsnet_Order_Delete",
    }]


def test_r070_is_high_and_does_not_claim_causal_attribution():
    risks = _load(RISK_PATH)
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-070")
    assert risk["severity"] == "HIGH"
    assert "does not attribute any current missing target" in risk["failure_mode"]
    assert len(risk["controls"]) == 6
    assert len(risk["exit_criteria"]) == 6
    trace = _load(TRACE_PATH)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_order_deletion_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_deletion_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 15,
        "passed_check_count": 15,
        "failed_check_count": 0,
        "referencing_module_count": 404,
        "direct_delete_procedure_count": 4,
        "active_delete_trigger_count": 3,
        "ngt_aware_delete_procedure_count": 1,
        "risk_count": 84,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 15
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
