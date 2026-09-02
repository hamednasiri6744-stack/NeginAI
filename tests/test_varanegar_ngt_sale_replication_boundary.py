from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_sale_replication_boundary_20260829.json"
RUNTIME_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_sale_replication_runtime_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_ngt_sale_replication_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sale_sql_boundary_is_read_only_and_redacted():
    payload = _load(SQL_PATH)
    assert payload["artifact"] == "varanegar_ngt_sale_replication_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_or_application_command_executions"] == 0
    assert payload["safety"]["sql_definitions_persisted"] == 0
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_type8_has_138_exact_same_target_timestamp_duplicate_pairs():
    payload = _load(SQL_PATH)
    assert payload["summary"] == {
        "procedure_count": 4,
        "type_8_history_count": 3731,
        "type_8_entity_count": 3593,
        "multi_history_entity_count": 138,
        "duplicate_same_target_entity_count": 138,
        "multi_target_entity_count": 0,
        "missing_current_sale_target_count": 0,
    }
    contract = payload["sale_replication_contract"]
    assert contract["history_in_multi_group_count"] == 276
    assert contract["max_history_per_entity"] == 2
    assert contract["duplicate_same_timestamp_entity_count"] == 138
    assert contract["multi_target_entity_count"] == 0


def test_all_current_type8_crosswalks_match_order_header_and_sale_target():
    contract = _load(SQL_PATH)["sale_replication_contract"]
    assert contract["missing_ngt_order_count"] == 0
    assert contract["header_invoice_uuid_mismatch_count"] == 0
    assert contract["header_invoice_ref_mismatch_count"] == 0
    assert contract["missing_current_sale_target_count"] == 0
    assert contract["type_8_history_unique_guard_present"] is False
    assert contract["order_invoice_crosswalk_unique_guard_present"] is False


def test_runtime_places_replication_before_invoice_crosswalk_setters():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_ngt_sale_replication_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "parsed_target_method_body_count": 3,
        "selected_method_count": 3,
        "selected_instruction_count": 26321,
        "method_body_error_count": 0,
        "sale_crosswalk_setter_count": 3,
    }
    contract = payload["sale_runtime_contract"]
    assert contract["new_replication_call_count"] == 1
    assert contract["sale_crosswalk_setter_count"] == 3
    assert contract["new_replication_call_precedes_managed_transaction_in_linear_il"] is True
    assert contract["new_replication_call_precedes_sale_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_before_sale_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_after_sale_crosswalk_setters_in_linear_il"] is True
    assert payload["safety"]["assembly_loads_or_execution"] == 0
    assert not GUID.search(RUNTIME_PATH.read_text(encoding="utf-8"))


def test_r068_is_critical_but_does_not_claim_duplicate_sale_effects():
    risks = _load(RISK_PATH)
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-068")
    assert risk["severity"] == "CRITICAL"
    assert "does not prove duplicate Sale, stock or accounting effects" in risk["failure_mode"]
    assert len(risk["controls"]) == 6
    assert len(risk["exit_criteria"]) == 6
    trace = _load(TRACE_PATH)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_sale_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_sale_replication_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 16,
        "passed_check_count": 16,
        "failed_check_count": 0,
        "type_8_history_count": 3731,
        "type_8_entity_count": 3593,
        "duplicate_same_target_entity_count": 138,
        "sale_crosswalk_setter_count": 3,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 16
    import hashlib

    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
