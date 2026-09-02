import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "artifacts" / "varanegar_analysis" / "domains"
UI = ROOT / "artifacts" / "varanegar_analysis" / "ui"
SQL_BOUNDARY = DOMAIN / "ngt_payment_replication_boundary_20260829.json"
RUNTIME_BOUNDARY = DOMAIN / "ngt_payment_replication_runtime_boundary_20260829.json"
RISK_REGISTER = UI / "negin_erp_risk_register_20260829.json"
TRACEABILITY = UI / "negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts" / "varanegar_analysis" / "varanegar_ngt_payment_replication_checkpoint_20260829.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_artifact_is_read_only_and_privacy_safe():
    payload = load(SQL_BOUNDARY)
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "guid_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    assert re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        SQL_BOUNDARY.read_text(encoding="utf-8"),
    ) is None


def test_replication_sql_chain_and_settlement_literals_are_resolved():
    payload = load(SQL_BOUNDARY)
    assert payload["summary"] == {
        "target_table_count": 8,
        "catalog_column_count": 236,
        "procedure_count": 4,
        "procedure_definition_length": 195909,
        "procedure_mutation_statement_count": 145,
        "procedure_mutation_object_count": 55,
        "procedure_exec_call_count": 69,
        "procedure_dependency_count": 190,
        "tour_history_type_count": 4,
        "payment_type_10_history_count": 447,
        "settlement_type_literal_count": 7,
    }
    profiles = {row["qualified_name"]: row for row in payload["replication_procedure_profiles"]}
    assert set(profiles) == {
        "dbo.NGT_DoReplicateTour",
        "dbo.NGT_ReplicateTour",
        "dbo.NGT_CreateReceipt_ForDistInfo",
        "dbo.NGT_CreateSettlement_Merge",
    }
    receipt_objects = {
        row["qualified_object"]
        for row in profiles["dbo.NGT_CreateReceipt_ForDistInfo"]["mutation_object_counts"]
    }
    assert {
        "Receipt",
        "RCash",
        "RCashDetail",
        "acc.TblCheque",
        "acc.tblChqHist",
        "acc.tblBankOrders",
        "#FinalResult",
    }.issubset(receipt_objects)
    assert profiles["dbo.NGT_CreateReceipt_ForDistInfo"]["has_explicit_begin_transaction"] is False
    assert profiles["dbo.NGT_CreateSettlement_Merge"]["has_explicit_begin_transaction"] is False
    settlement_types = {
        row["settlement_type"]
        for row in payload["settlement_type_literal_contract"]["settlement_type_profiles"]
    }
    assert settlement_types == {
        "تخفيف",
        "رسيد",
        "كارت‌خوان",
        "نقد",
        "پرداخت از مانده بستانكاري",
        "پرداخت با واسطه",
        "چك",
    }


def test_type_10_history_exposes_partial_and_repeated_crosswalks():
    history = load(SQL_BOUNDARY)["tour_history_contract"]
    assert history["payment_type_10_crosswalk"] == {
        "type_10_history_count": 447,
        "distinct_entity_count": 344,
        "entity_not_current_payment_count": 0,
        "entity_is_payment_count": 447,
        "entity_is_active_payment_count": 447,
        "history_uuid_resolves_receipt_count": 438,
        "history_ref_resolves_receipt_count": 438,
        "history_uuid_ref_agree_count": 438,
        "history_uuid_ref_no_agree_count": 438,
        "payment_and_history_crosswalk_agree_count": 274,
    }
    assert history["payment_perspective"] == {
        "active_payment_count": 3523,
        "with_receipt_uuid_count": 274,
        "with_type_10_history_count": 344,
        "receipt_crosswalk_without_type_10_history_count": 0,
        "type_10_history_without_current_receipt_crosswalk_count": 70,
        "exact_type_10_crosswalk_count": 274,
    }
    assert history["type_10_duplicate_entity_groups"] == {
        "duplicate_entity_group_count": 70,
        "histories_in_duplicate_groups": 173,
        "maximum_histories_per_entity": 6,
    }
    assert history["type_10_exact_duplicate_groups"] == {
        "exact_duplicate_group_count": 72,
        "histories_in_exact_duplicate_groups": 173,
        "maximum_exact_duplicate_count": 4,
    }
    assert history["type_10_field_presence"] == [
        {
            "history_multiplicity": "MULTIPLE_HISTORIES",
            "has_current_uuid": 0,
            "has_current_ref": 0,
            "has_current_no": 1,
            "payment_count": 70,
            "history_count": 173,
        },
        {
            "history_multiplicity": "ONE_HISTORY",
            "has_current_uuid": 1,
            "has_current_ref": 1,
            "has_current_no": 1,
            "payment_count": 274,
            "history_count": 274,
        },
    ]


def test_type_10_has_no_unique_current_key_fk_or_trigger():
    catalog = load(SQL_BOUNDARY)["tour_history_catalog_contract"]
    unique = [row for row in catalog["indexes"] if row["is_unique"]]
    assert len(unique) == 1
    assert unique[0]["filter_targets_type_1"] is True
    assert unique[0]["filter_targets_type_10"] is False
    assert catalog["foreign_keys"] == []
    assert catalog["triggers"] == []


def test_runtime_adapter_has_a_separate_crosswalk_writeback_phase():
    payload = load(RUNTIME_BOUNDARY)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY"
    assert payload["safety"]["assembly_loads_or_execution"] == 0
    assert payload["safety"]["application_endpoint_or_command_executions"] == 0
    assert payload["summary"]["selected_method_count"] == 3
    assert payload["summary"]["method_body_error_count"] == 0
    assert payload["summary"]["crosswalk_setter_candidate_count"] == 2
    contract = payload["replicate_tour_crosswalk_writeback_contract"]
    assert contract["replicate_tour_method_present"] is True
    assert contract["new_replicate_tour_call_count"] == 1
    assert contract["payment_crosswalk_setter_event_count"] == 3
    assert contract["new_replication_call_precedes_payment_setters_in_linear_il"] is True
    assert contract["commit_exists_before_payment_setters_in_linear_il"] is True
    assert contract["commit_exists_after_payment_setters_in_linear_il"] is True
    assert {name.rsplit(".", 1)[-1] for name in contract["payment_crosswalk_setter_members"]} == {
        "set_BackOfficeReceiptUniqueId",
        "set_BackOfficeReceiptRef",
        "set_BackOfficeReceiptNo",
    }


def test_risk_register_adds_r064_and_extends_transaction_risk():
    risks = load(RISK_REGISTER)
    assert risks["validation"] == "PASS"
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    by_id = {row["id"]: row for row in risks["risks"]}
    assert by_id["R-064"]["severity"] == "CRITICAL"
    assert "447 rows for 344 active payments" in by_id["R-064"]["failure_mode"]
    assert "70 active payments with multiple Type=10 histories" in by_id["R-007"]["failure_mode"]
    trace = load(TRACEABILITY)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_checkpoint_passes():
    payload = load(CHECKPOINT)
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert payload["summary"]["type_10_history_count"] == 447
    assert payload["summary"]["multi_history_payment_count"] == 70
    assert payload["summary"]["risk_count"] == 84
    assert payload["summary"]["mapped_risk_assignment_count"] == 343
