from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/order_sale_evc_runtime_boundary_20260829.json"
SQL = ROOT / "artifacts/varanegar_analysis/domains/order_sale_evc_sql_boundary_20260829.json"
DOC = ROOT / "docs/varanegar_reconstruction/ORDER_TO_SALE_EVC_SPLIT_AND_DISCOUNT_V2_BOUNDARY_20260829_FA.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_runtime_artifact_is_hash_pinned_and_static() -> None:
    data = _load(RUNTIME)
    assert data["validation"] == "PASS"
    assert all(row["inventory_sha256_match"] for row in data["source"])
    assert data["safety"]["assembly_loads_or_executions"] == 0
    assert data["summary"]["managed_inventory_parse_error_count"] == 0


def test_discount_v2_flag_has_no_typed_setter_after_constructor() -> None:
    data = _load(RUNTIME)
    assert data["summary"]["managed_inventory_assembly_scan_count"] == 59
    assert data["summary"]["calc_for_discount_v2_setter_callsite_count"] == 1
    rows = data["inventory_member_callsites"]["calc_flag_setter"]
    assert rows == [
        {
            "assembly_file": "VN.SDS.Common.dll",
            "type": "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper",
            "method": ".ctor",
        }
    ]


def test_discount_v2_entry_is_reached_from_order_to_sale_form() -> None:
    data = _load(RUNTIME)
    assert any(
        row["type"] == "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale"
        for row in data["inventory_member_callsites"]["discount_v2_entry"]
    )


def test_runtime_contains_both_single_create_and_double_insert_literals() -> None:
    data = _load(RUNTIME)
    literals = {
        literal.get("safe_literal", "")
        for method in data["methods"]
        for literal in method["string_literals"]
    }
    assert any("CREATE TABLE #SaleItemPaymentUsance" in literal for literal in literals)
    assert any("INSERT INTO [#SaleSaleItemPaymentUsance]" in literal for literal in literals)
    assert data["inventory_temp_table_literal_scan"]["double_temp_create_literal_files"] == []


def test_global_calc_data_name_is_not_a_process_static_cache() -> None:
    data = _load(RUNTIME)
    assert data["summary"]["global_calc_data_field_access_count"] > 0
    assert data["assertions"]["global_calc_data_is_instance_not_static_field_access"]
    assert data["assertions"]["get_instance_constructs_fresh_evc_handler"]


def test_selected_v2_load_path_has_many_synchronous_context_reads() -> None:
    data = _load(RUNTIME)
    assert data["assertions"]["selected_v2_load_path_has_35_direct_context_reads"]
    methods = {(row["type"], row["method"]): row for row in data["methods"]}
    initial = methods[("VN.SDS.Sales.Business.EVC.EVCHandler", "InitialCalcData")]
    extract = methods[("VN.SDS.Sales.Business.EVC.EVCHandler", "ExtractCalcDataFromDB")]
    assert initial["member_reference_counts"]["Thunderstruck.DataContext.AllRawEntity"] == 17
    assert initial["member_reference_counts"]["Thunderstruck.DataContext.GetValue"] == 1
    assert extract["member_reference_counts"]["Thunderstruck.DataContext.AllRawEntity"] == 17
    assert data["assertions"]["desktop_v2_accept_runs_inside_background_worker"]
    assert data["assertions"][
        "batch_cancellation_is_checked_before_each_selected_conversion_not_inside_db_call"
    ]


def test_selected_v2_load_paths_inject_sds_advanced_condition_helper() -> None:
    data = _load(RUNTIME)
    assert data["summary"]["selected_sds_advanced_condition_helper_injection_count"] == 2
    assert data["assertions"][
        "selected_v2_load_paths_inject_sds_advanced_condition_helper_into_calcdata"
    ]


def test_test_data_export_is_gated_but_unpermissioned_and_unencrypted() -> None:
    runtime = _load(RUNTIME)
    sql = _load(SQL)
    assert runtime["assertions"]["discount_v2_toolbar_exposes_unpermissioned_test_data_checkbox"]
    assert runtime["assertions"]["test_data_export_serializes_full_calcdata_to_gzip_bytes"]
    assert runtime["assertions"]["test_data_export_has_no_named_encryption_call"]
    assert runtime["assertions"][
        "diagnostic_export_executes_legacy_do_evc_before_managed_promotion"
    ]
    assert sql["assertions"]["current_clone_has_single_disabled_discount_v2_key"]
    assert sql["summary"]["discount_v2_enabled_key_count"] == 0
    assert runtime["runtime_share_diagnostic_export_snapshot"] == {
        "relative_directory": "TestDataDiscountV2",
        "directory_exists": False,
        "file_count": 0,
        "total_bytes": 0,
        "file_names_or_contents_persisted": 0,
    }


def test_sql_default_and_legacy_fallback_are_explicit() -> None:
    data = _load(SQL)
    assert data["validation"] == "PASS"
    assert data["assertions"]["calc_for_discount_v2_default_is_zero"]
    assert data["assertions"]["legacy_evc_branch_is_guarded_by_flag_zero"]
    assert data["assertions"]["legacy_branch_fills_evc_and_builds_single_usance_temp"]


def test_sql_uses_only_single_temp_name_and_persists_from_it() -> None:
    data = _load(SQL)
    assert data["summary"]["double_temp_name_module_count"] == 0
    assert data["summary"]["single_temp_name_module_count"] == 5
    assert data["assertions"]["create_sale_by_evc_reads_single_temp_and_persists_rows"]


def test_document_states_split_fallback_and_target_contract() -> None:
    text = DOC.read_text(encoding="utf-8-sig")
    for marker in (
        "fallback دو محاسبه‌ای",
        "#SaleSaleItemPaymentUsance",
        "PricingSnapshotId",
        "یک `DataContext(Transaction.Begin)` جدا",
        "TestDataDiscountV2",
    ):
        assert marker in text
