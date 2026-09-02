import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/idempotency_guard_boundary_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_idempotency_guard_checkpoint_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_extraction_is_read_only_redacted_and_hash_pinned():
    payload = _load()
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0 and safety["denies_data_writes"] == 1
    assert safety["stored_procedure_trigger_form_report_or_application_command_executions"] == 0
    assert safety["assembly_loads_or_executions"] == 0
    assert safety["business_rows_ids_names_messages_index_names_filters_or_raw_values_persisted"] == 0
    assert safety["sql_definitions_comments_or_literal_values_persisted"] == 0
    assert safety["source_or_target_state_changed"] == 0
    assert all(len(item["definition_sha256"]) == 64 for item in payload["command_profiles"])
    raw = ARTIFACT.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_selected_commands_have_no_explicit_retry_identity():
    payload = _load()
    summary = payload["summary"]
    assert summary["selected_command_count"] == 10
    assert summary["selected_command_with_explicit_idempotency_parameter_count"] == 0
    assert summary["selected_command_with_id_allocator_count"] == 6
    assert all(item["explicit_idempotency_parameter_count"] == 0 for item in payload["command_profiles"])
    assert all(item["explicit_idempotency_parameters"] == [] for item in payload["command_profiles"])


def test_storage_guards_have_different_semantic_coverage():
    payload = _load()
    tables = {item["qualified_name"]: item for item in payload["table_unique_guard_profiles"]}
    assert payload["summary"]["selected_table_count"] == 7
    assert payload["summary"]["selected_table_with_semantic_unique_guard_count"] == 5
    assert tables["SLE.tblSaleHdr"]["semantic_unique_guard_count"] == 0
    assert tables["GNR.tblPrintedDoc"]["semantic_unique_guard_count"] == 0
    assert tables["SLE.tblRetSaleHdr"]["semantic_unique_guard_count"] == 2
    assert tables["inv.tblExit"]["semantic_unique_guard_count"] == 1
    assert tables["inv.tblVocherHdr"]["semantic_unique_guard_count"] == 3
    assert tables["dbo.PreVoucher"]["semantic_unique_guard_count"] == 1
    assert tables["dbo.TourHistory"]["semantic_unique_guard_count"] == 1
    assert all(
        not guard["filter_literal_or_index_name_persisted"]
        for table in tables.values()
        for guard in table["unique_guards"]
    )


def test_current_guarded_shapes_are_clean_but_one_cohort_is_empty():
    payload = _load()
    summary = payload["summary"]
    shapes = payload["anonymous_duplicate_shapes"]
    assert summary["current_guarded_duplicate_group_count"] == 0
    assert summary["current_guarded_zero_population_shape_count"] == 1
    assert summary["current_sale_multi_active_order_group_count"] == 0
    assert shapes["sale_active_order"] == {
        "active_order_group_count": 214973,
        "duplicate_active_order_group_count": 0,
        "maximum_active_sales_per_order": 1,
    }
    assert shapes["sales_return_active_source"]["active_source_group_count"] == 0
    assert shapes["distribution_active_exit"]["duplicate_active_group_count"] == 0
    assert shapes["sales_return_type_voucher"]["duplicate_source_health_group_count"] == 0
    assert shapes["pre_voucher_line_signature"]["duplicate_signature_group_count"] == 0


def test_print_repetition_is_not_mislabeled_as_duplicate_retry():
    payload = _load()
    shape = payload["anonymous_duplicate_shapes"]["printed_document_event"]
    assert shape == {
        "printed_document_group_count": 197586,
        "repeated_document_group_count": 55792,
        "maximum_events_per_document": 88,
    }
    assert any("legitimate reprints" in item for item in payload["evidence_limits"])


def test_tour_history_guard_and_duplicate_shapes_are_type_specific():
    payload = _load()
    rows = {int(item["Type"]): item for item in payload["anonymous_duplicate_shapes"]["tour_history_by_type"]}
    assert rows[1]["entity_group_count"] == 1118244
    assert rows[1]["duplicate_entity_group_count"] == 0
    assert rows[8]["duplicate_entity_group_count"] == 138
    assert rows[10]["duplicate_entity_group_count"] == 70
    assert rows[10]["maximum_histories_per_entity"] == 6


def test_target_retry_contract_distinguishes_same_request_from_new_intent():
    contract = _load()["target_contract"]
    assert "CommandId" in contract["request_identity"] and "PayloadHash" in contract["request_identity"]
    assert "original typed outcome" in contract["same_key_same_payload"]
    assert "reject before mutation" in contract["same_key_different_payload"]
    assert "new CommandId" in contract["retry_vs_new_intent"]
    assert "quarantine" in contract["unknown_commit"]


def test_r006_and_checkpoint_include_the_new_evidence_without_count_inflation():
    risks = json.loads(RISKS.read_text(encoding="utf-8-sig"))
    risk = next(item for item in risks["risks"] if item["id"] == "R-006")
    assert risk["severity"] == "CRITICAL"
    assert ARTIFACT.as_posix() in risk["evidence_refs"]
    assert risks["summary"]["risk_count"] == 84
    assert risks["source_checkpoint"]["selected_high_impact_command_without_explicit_idempotency_parameter_count"] == 10
    assert risks["source_checkpoint"]["selected_idempotency_storage_guard_current_duplicate_group_count"] == 0
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"))
    assert checkpoint["validation"] == "PASS" and checkpoint["failed_checks"] == []
    assert checkpoint["summary"] == {
        "source_count": 13,
        "passed_check_count": 9,
        "failed_check_count": 0,
        "selected_command_count": 10,
        "selected_command_with_explicit_idempotency_parameter_count": 0,
        "selected_table_with_semantic_unique_guard_count": 5,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
    }
