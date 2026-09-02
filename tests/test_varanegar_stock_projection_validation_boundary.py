import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "artifacts/varanegar_analysis/domains/stock_projection_validation_boundary_20260829.json"
RECONCILIATION = ROOT / "artifacts/varanegar_analysis/ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_stock_projection_validation_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_boundary_is_read_only_redacted_and_definition_hash_pinned():
    payload = _load(BOUNDARY)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert safety["voucher_goods_stock_document_user_host_or_raw_row_values_persisted"] == 0
    assert safety["sql_definitions_error_texts_or_business_identifiers_persisted"] == 0
    assert len(payload["sql_module_profiles"]) == 10
    assert all(len(row["definition_sha256"]) == 64 for row in payload["sql_module_profiles"])
    raw = BOUNDARY.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_confirm_commits_before_advisory_after_validation_on_direct_structure():
    contract = _load(BOUNDARY)["static_validation_and_projection_contract"]
    assert contract["confirm_first_commit_precedes_after_validation"]
    assert contract["confirm_appends_after_message_without_abort_guard"]
    assert contract["confirm_after_cursor_excludes_generated_type15_mode"]


def test_unconfirm_runs_after_before_commit_but_does_not_guard_returned_message():
    contract = _load(BOUNDARY)["static_validation_and_projection_contract"]
    assert contract["unconfirm_after_validation_precedes_commit"]
    assert contract["unconfirm_appends_after_message_then_commits_without_abort_guard"]


def test_after_validation_has_message_only_contract_and_explicit_exemptions():
    payload = _load(BOUNDARY)
    contract = payload["static_validation_and_projection_contract"]
    assert contract["after_has_no_local_transaction_raise_or_throw"]
    assert contract["after_calls_four_expected_validation_modules"]
    assert contract["after_uses_nolock_reads"]
    assert contract["after_type20_batch_state_update_precedes_validation"]
    assert contract["after_skips_common_onhand_and_cardex_checks_for_types12_and13"]
    assert contract["after_cardex_checks_only_when_confirmed"]
    after = next(row for row in payload["sql_module_profiles"] if row["qualified_name"] == "inv.AfterInvVocherHdr")
    assert after["nolock_signal_count"] == 9
    assert after["dependency_count"] == 11


def test_cardex_effect_matrix_is_complete_versionable_rule_snapshot():
    payload = _load(BOUNDARY)
    aggregate = payload["cardex_effect_contract"]["aggregate"]
    assert aggregate == {
        "row_count": 50,
        "voucher_type_count": 30,
        "onhand_effect_row_count": 29,
        "damaged_effect_row_count": 15,
        "reserved_effect_row_count": 4,
        "positive_effect_row_count": 27,
        "negative_effect_row_count": 22,
        "zero_effect_row_count": 1,
    }
    matrix = payload["cardex_effect_contract"]["effect_matrix"]
    assert len(matrix) == 50
    assert sum(row["row_count"] for row in matrix) == 50
    assert len({row["VocherTypeCode"] for row in matrix}) == 30


def test_projection_triggers_and_negative_guard_preserve_bypass_limits():
    payload = _load(BOUNDARY)
    contract = payload["static_validation_and_projection_contract"]
    assert contract["header_projection_uses_cursor_and_can_rollback"]
    assert contract["item_projection_uses_cursor_try_catch_and_can_rollback"]
    assert contract["stock_negative_guard_is_set_based"]
    assert contract["stock_negative_guard_has_session_and_replication_bypass"]
    assert payload["summary"]["active_projection_or_guard_trigger_count"] == 3
    assert all(not row["is_disabled"] for row in payload["projection_and_guard_trigger_state"])


def test_current_projection_is_clean_and_official_formula_has_zero_residual():
    payload = _load(BOUNDARY)
    stock = payload["projection_snapshot"]["stock_goods"]
    detail = payload["projection_snapshot"]["stock_goods_detail"]
    assert stock["row_count"] == 67161
    assert payload["summary"]["stock_projection_negative_component_count"] == 0
    assert stock["batch_enabled_count"] == 0
    assert detail["row_count"] == 0
    reconciliation = _load(RECONCILIATION)
    assert reconciliation["summary"]["cardex_only_mismatch_count"] == 1594
    assert reconciliation["summary"]["official_formula_mismatch_count"] == 0


def test_r077_traceability_and_checkpoint_are_current_and_caveated():
    risks = _load(RISKS)
    trace = _load(TRACE)
    checkpoint = _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-077")
    assert risk["severity"] == "CRITICAL"
    assert "no current validation failure or bypass incident is asserted" in risk["failure_mode"]
    assert "message-only validation" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
