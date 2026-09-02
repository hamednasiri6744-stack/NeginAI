import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/order_sale_policy_flag_sql_20260829.json"
RUNTIME_ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/order_sale_policy_flag_runtime_20260829.json"
GATE_ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/order_sale_policy_gate_runtime_20260829.json"
CONFIG_ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/order_sale_policy_config_snapshot_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_order_sale_policy_flag_checkpoint_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_extraction_is_read_only_redacted_and_operationally_inert():
    payload = _load(SQL_ARTIFACT)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["connection_readonly"]
    assert safety["operational_stored_procedure_executions"] == 0
    assert safety["raw_definition_lines_or_string_literals_persisted"] == 0
    assert safety["business_rows_or_values_read"] == 0
    assert safety["source_or_target_state_changed"] == 0
    raw = SQL_ARTIFACT.read_text(encoding="utf-8")
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_static_runtime_extraction_is_hash_pinned_and_does_not_load_assemblies():
    payload = _load(RUNTIME_ARTIFACT)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["assembly_count"] == 3
    assert payload["summary"]["source_hash_mismatch_count"] == 0
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["safety"]["application_form_or_command_executions"] == 0
    assert payload["safety"]["raw_strings_or_business_values_persisted"] == 0


def test_sql_policy_contract_distinguishes_partial_stock_conversion_from_bypass():
    payload = _load(SQL_ARTIFACT)
    semantics = {row["policy"]: row for row in payload["semantic_contracts"]}
    stock = semantics["STOCK_SHORTAGE"]
    assert stock["caller_override_value"] == 1
    assert stock["effect"] == "REMOVE_SHORT_ITEMS_FROM_TEMP_CONVERSION_SET_AND_CONTINUE_IF_ANY_ITEM_REMAINS"
    assert stock["not_equivalent_to"] == "UNCONDITIONAL_STOCK_VALIDATION_BYPASS"
    checks = payload["semantic_assertions"]
    assert checks["stock_flag_is_forwarded_to_stock_checker"]
    assert checks["stock_flag_one_removes_short_items_from_conversion_temp"]
    assert checks["stock_checker_rejects_when_no_conversion_item_remains"]


def test_price_credit_and_limit_flags_have_distinct_server_semantics():
    payload = _load(SQL_ARTIFACT)
    semantics = {row["policy"]: row for row in payload["semantic_contracts"]}
    assert semantics["CONTRACT_PRICE"]["caller_override_value"] == 1
    assert semantics["USER_PRICE"]["independent_check_remaining"] == "ORDER_ITEM_PRICE_CHECK_BEFORE_FLAG_BRANCH"
    assert semantics["CUSTOMER_CREDIT"]["caller_override_value"] == [1, 1]
    assert semantics["DEALER_CREDIT"]["caller_override_value"] == [1, 1]
    assert semantics["CUSTOMER_CREDIT"]["other_combinations"] == "CALLER_VALUES_ARE_REPLACED_FROM_DC_SERVER_CONFIG"
    assert semantics["CUSTOMER_MAXIMUM_LIMIT"]["effect"] == "SKIP_CUSTOMER_MAXIMUM_LIMIT_CHECK"
    assert all(payload["semantic_assertions"].values())


def test_declared_only_expiry_and_narrow_rollback_switch_are_not_overclaimed():
    payload = _load(SQL_ARTIFACT)
    semantics = {row["policy"]: row for row in payload["semantic_contracts"]}
    assert semantics["EXPIRY_VALIDATION"]["effect"] == "DECLARED_ONLY_NO_RUNTIME_SQL_EFFECT_PROVEN_IN_CURRENT_WRAPPER"
    assert semantics["ROLLBACK_MODE"]["effect"] == "SUPPRESS_ROLLBACK_ONLY_FOR_DOOMED_XACT_STATE_BRANCH"
    assert semantics["ROLLBACK_MODE"]["not_equivalent_to"] == "DISABLE_ALL_ROLLBACK_BRANCHES"
    assert payload["summary"]["wrapper_declared_but_not_used_after_declaration_count"] == 1


def test_bulk_and_single_sale_callers_supply_different_policy_sources():
    payload = _load(RUNTIME_ARTIFACT)
    methods = {(row["type"], row["method"]): row for row in payload["methods"]}
    bulk_names = ("AcceptCommandOld", "AcceptCommandDiscountV2")
    for name in bulk_names:
        method = methods[("VN.SDS.Sales.UI.OrderToSale.FormOrderToSale", name)]
        setters = {event["member"].rsplit(".", 1)[-1]: event for event in method["events"] if ".set_" in event["member"]}
        assert setters["set_chkNotCPrice"]["value_source"] == {
            "class": "IMMEDIATE_NUMERIC_CONSTANT",
            "numeric_constant": 0,
        }
        assert setters["set_chkNotPrice"]["value_source"]["numeric_constant"] == 0
        assert setters["set_chkNotStock"]["value_source"]["member"].endswith(".DeleteItmsCheckEdit")
        assert setters["set_chkNotCheckMaxLimit"]["value_source"]["member"].endswith(".AdamEtebarMaxSabtCheckEdit")
    single = methods[("VN.SDS.Sales.UI.Sale.FormSaleDataEntry", "SaveCommand")]
    setters = {event["member"].rsplit(".", 1)[-1]: event for event in single["events"] if ".set_" in event["member"]}
    assert setters["set_chkNotCPrice"]["value_source"]["numeric_constant"] == 0
    assert setters["set_chkNotPrice"]["value_source"]["numeric_constant"] == 0
    assert setters["set_chkNotStock"]["value_source"]["member"].endswith(".CheckNotSaleItmStock")


def test_policy_gate_uses_two_distinct_three_state_mappings():
    payload = _load(GATE_ARTIFACT)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["assertions"]["six_policy_config_getters_return_nonnullable_cli_int32"]
    contracts = {row["policy"]: row["states"] for row in payload["configuration_state_contracts"]}
    credit = [
        {"server_config_value": 0, "control_enabled": 0, "control_checked": 1},
        {"server_config_value": 1, "control_enabled": 1, "control_checked": 0},
        {"server_config_value": 2, "control_enabled": 0, "control_checked": 0},
    ]
    stock = [
        {"server_config_value": 0, "control_enabled": 1, "control_checked": 0},
        {"server_config_value": 1, "control_enabled": 0, "control_checked": 1},
        {"server_config_value": 2, "control_enabled": 0, "control_checked": 0},
    ]
    assert contracts["CUSTOMER_DOCUMENT_CREDIT"] == credit
    assert contracts["DEALER_DEBT_CREDIT"] == credit
    assert contracts["CUSTOMER_MAXIMUM_LIMIT"] == credit
    assert contracts["STOCK_SHORTAGE_PARTIAL_CONVERSION"] == stock


def test_apply_setad_permission_does_not_guard_policy_controls_in_selected_method():
    payload = _load(GATE_ARTIFACT)
    contract = payload["selected_permission_method_contract"]
    assert contract["method"] == "ApplySetadPermission"
    assert contract["named_permission_decision_calls"] == []
    assert contract["observed_inputs"] == ["SERVER_CONFIG_SITE_TYPE", "USER_SESSION_DCREF"]
    assert contract["observed_target"] == "MENU_BUTTON_SELECT_ENABLED"
    assert not contract["policy_control_permission_enforcement_proven"]
    assert not contract["form_or_menu_open_authorization_outside_selected_method_proven"]


def test_current_anonymous_dc_profiles_preserve_null_as_unresolved():
    payload = _load(CONFIG_ARTIFACT)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "config_row_count": 2,
        "dc_count": 2,
        "orphan_dc_count": 0,
        "distinct_policy_profile_count": 2,
        "invalid_nonnull_policy_row_count": 0,
        "profile_row_with_null_policy_count": 1,
        "null_policy_cell_count": 5,
    }
    profiles = payload["anonymous_policy_profiles"]
    assert all(row["policy_modes"]["CheckSaleItmStock"]["enum_value"] == 2 for row in profiles)
    assert sum(
        value["mode"] == "NULL_UNRESOLVED"
        for row in profiles
        for value in row["policy_modes"].values()
    ) == 5
    null_boundary = payload["null_semantic_boundary"]
    assert null_boundary["ui_materializer_null_to_int32_behavior"] == "NOT_PROVEN"
    assert null_boundary["target_requirement"] == "REJECT_OR_RESOLVE_NULL_EXPLICITLY_BEFORE_POLICY_DECISION"


def test_r079_and_checkpoint_integrate_policy_evidence_without_count_inflation():
    risks = _load(RISKS)
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    assert SQL_ARTIFACT.as_posix() in risk["evidence_refs"]
    assert RUNTIME_ARTIFACT.as_posix() in risk["evidence_refs"]
    assert GATE_ARTIFACT.as_posix() in risk["evidence_refs"]
    assert CONFIG_ARTIFACT.as_posix() in risk["evidence_refs"]
    assert any("chkNot*" in item for item in risk["controls"])
    assert any("partial conversion" in item for item in risk["controls"])
    assert risks["summary"]["risk_count"] == 84
    assert risks["source_checkpoint"]["order_sale_policy_selected_sql_command_count"] == 3
    assert risks["source_checkpoint"]["order_sale_policy_declared_only_wrapper_flag_count"] == 1
    assert risks["source_checkpoint"]["order_sale_policy_gate_configured_control_count"] == 6
    assert risks["source_checkpoint"]["order_sale_policy_current_null_cell_count"] == 5
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
