import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/order_sale_authorization_sql_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/order_sale_authorization_runtime_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_order_sale_authorization_checkpoint_20260829.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_authorization_extraction_is_read_only_and_redacted():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["selected_sql_module_count"] == 4
    assert payload["safety"]["connection_readonly"]
    assert payload["safety"]["operational_stored_procedure_executions"] == 0
    assert payload["safety"]["raw_sql_definitions_messages_string_literals_or_identities_persisted"] == 0
    assert payload["safety"]["source_or_target_state_changed"] == 0
    assert re.search(r"(?i)(password|pwd)\s*[=:]", SQL.read_text(encoding="utf-8")) is None


def test_server_area_scope_is_conditional_and_current_clone_gate_is_disabled():
    payload = _load(SQL)
    checks = payload["semantic_assertions"]
    assert checks["wrapper_calls_conditional_area_access_before_core"]
    assert checks["area_access_is_enabled_only_by_global_key_value_one"]
    assert checks["area_access_scopes_customer_sale_area_to_user_projection"]
    assert checks["area_access_allows_customer_without_sale_area"]
    assert checks["current_clone_global_and_general_area_access_are_disabled"]
    assert payload["summary"]["global_area_access_enabled_key_count"] == 0
    assert payload["summary"]["general_config_area_access_true_count"] == 0
    assert payload["summary"]["sale_user_access_projection_row_count"] == 2


def test_order_type_rights_have_no_convert_action_and_are_not_core_authorization():
    payload = _load(SQL)
    assert payload["semantic_assertions"]["order_type_permission_has_no_convert_action"]
    assert payload["semantic_assertions"]["order_type_permission_supports_admin_direct_and_group_rights"]
    assert payload["semantic_assertions"]["core_accepts_actor_but_has_no_access_or_right_dependency"]
    contract = payload["contract"]
    assert contract["order_type_right_actions"] == [
        "VIEW", "NEW", "EDIT", "DELETE", "CANCEL", "CONFIRM", "UNCONFIRM"
    ]
    assert not contract["order_type_right_has_convert_action"]
    assert contract["server_action_authorization_for_convert_order_to_sale"] == "NOT_PROVEN_IN_SELECTED_COMMANDS"


def test_exact_conversion_form_and_selected_conversion_methods_have_no_named_permission_call():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["assembly_count"] == 3
    assert payload["summary"]["selected_method_count"] == 12
    assert payload["summary"]["selected_conversion_method_count"] == 7
    assert payload["summary"]["order_to_sale_form_permission_call_count"] == 0
    assert payload["assertions"]["order_to_sale_form_has_no_permission_or_access_member_call"]
    assert payload["assertions"]["selected_conversion_methods_have_no_permission_or_access_member_call"]
    assert payload["safety"]["assembly_loads_or_executions"] == 0


def test_order_type_permission_ui_callsites_are_list_actions_not_conversion_form():
    payload = _load(RUNTIME)
    assert payload["assertions"]["order_type_permission_is_called_from_order_lists_not_conversion_form"]
    assert payload["assertions"]["business_order_type_permission_delegates_to_adapter"]
    assert payload["assertions"]["adapter_order_type_permission_reads_session_actor_and_named_procedure"]
    callsites = payload["contract"]["order_type_permission_ui_callsites"]
    assert len(callsites) == 10
    assert all(row["type"].endswith(("FormOrderList", "FormLoanOrderList")) for row in callsites)
    assert all("FormOrderToSale" not in row["type"] for row in callsites)


def test_r079_and_checkpoint_integrate_authorization_without_count_inflation():
    risks = _load(RISKS)
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    assert SQL.as_posix() in risk["evidence_refs"]
    assert RUNTIME.as_posix() in risk["evidence_refs"]
    assert any("ConvertOrderToSale" in item for item in risk["controls"])
    assert any("direct API negative tests" in item for item in risk["exit_criteria"])
    assert risks["summary"]["risk_count"] == 84
    source = risks["source_checkpoint"]
    assert source["order_sale_authorization_sql_module_count"] == 4
    assert source["order_sale_authorization_form_permission_call_count"] == 0
    assert source["order_sale_authorization_order_type_ui_callsite_count"] == 10
    assert source["order_sale_authorization_current_global_area_gate_count"] == 0
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
