import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/order_sale_operation_date_sql_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/order_sale_operation_date_runtime_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_order_sale_operation_date_checkpoint_20260829.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_extraction_is_read_only_redacted_and_operationally_inert():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["selected_sql_module_count"] == 6
    assert payload["safety"]["connection_readonly"]
    assert payload["safety"]["operational_stored_procedure_executions"] == 0
    assert payload["safety"]["raw_sql_definitions_messages_or_string_literals_persisted"] == 0
    assert payload["safety"]["source_or_target_state_changed"] == 0
    assert re.search(r"(?i)(password|pwd)\s*[=:]", SQL.read_text(encoding="utf-8")) is None


def test_server_core_consumes_date_and_rejects_closed_or_non_forward_standard_sale():
    payload = _load(SQL)
    checks = payload["semantic_assertions"]
    assert checks["wrapper_forwards_create_sale_date_to_core"]
    assert checks["core_uses_operation_date_for_price_and_open_date_checks"]
    assert checks["date_open_rejects_closed_or_not_after_last_date"]
    contracts = {row["boundary"]: row for row in payload["semantic_contracts"]}
    finality = contracts["STANDARD_ORDER_DATE_FINALITY"]
    assert finality["applies_when"] == "ORDER_TYPE_NOT_IN_1007_1008"
    assert finality["reject_when"] == [
        "SALE_PERIOD_IS_CLOSED",
        "CREATE_SALE_DATE_LESS_THAN_OR_EQUAL_TO_LAST_DATE",
    ]
    assert finality["comparison_representation"] == "VARCHAR_10_LEXICAL_PERSIAN_DATE"


def test_special_order_exception_and_missing_boundary_are_explicit_not_silently_normalized():
    payload = _load(SQL)
    checks = payload["semantic_assertions"]
    assert checks["date_open_is_skipped_for_order_types_1007_and_1008"]
    assert checks["missing_boundary_row_has_no_explicit_rejection"]
    contracts = {row["boundary"]: row for row in payload["semantic_contracts"]}
    assert contracts["SPECIAL_ORDER_DATE_EXCEPTION"]["sale_date_open_check"] == "SKIPPED"
    missing = contracts["MISSING_OPERATION_DATE_ROW"]
    assert missing["effective_null_branch_behavior"] == "FAIL_OPEN_BY_SQL_THREE_VALUED_LOGIC"
    assert missing["target_requirement"].startswith("REQUIRE_EXACTLY_ONE_CURRENT_SALE_BOUNDARY")
    assert checks["both_date_open_exception_types_are_configured_but_have_no_current_clone_instances"]
    assert payload["summary"]["configured_special_order_type_count"] == 2
    assert payload["summary"]["current_special_order_count"] == 0
    assert payload["summary"]["current_special_sale_count"] == 0
    assert payload["summary"]["recent_special_order_count"] == 0
    assert payload["summary"]["recent_special_sale_count"] == 0


def test_fetch_reason_two_sql_column_order_matches_static_il_output_order():
    sql = _load(SQL)
    runtime = _load(RUNTIME)
    assert sql["semantic_assertions"]["fetch_reason_two_returns_last_date_then_operation_date"]
    assert runtime["assertions"]["fetch_reason_two_outputs_last_date_then_operation_date"]
    assert runtime["contract"]["fetch_reason_two_output_order"] == ["LAST_DATE", "OPERATION_DATE"]


def test_automatic_desktop_branches_put_operation_date_second_output_in_session():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["assembly_count"] == 2
    assert payload["summary"]["source_hash_mismatch_count"] == 0
    assert payload["assertions"]["automatic_session_assignment_uses_operation_date_second_output"]
    flows = payload["contract"]["automatic_date_flows"]
    assert len(flows) == 2
    assert all(row["operation_date_output_local"] == row["session_operation_date_source_local"] for row in flows)
    assert all(row["last_date_output_local"] != row["session_operation_date_source_local"] for row in flows)


def test_session_date_routes_and_permission_boundary_are_not_conflated():
    payload = _load(RUNTIME)
    assert payload["assertions"]["both_conversion_routes_use_session_operation_date_as_create_sale_date"]
    assert payload["assertions"]["business_gate_permission_resource_and_action_are_allowlisted"]
    assert payload["contract"]["set_operation_date_permission_resource"] == "VN.SDS.Sales"
    assert payload["contract"]["set_operation_date_permission_action"] == "SetOprDate"
    assert not payload["contract"]["operation_date_permission_is_conversion_permission"]
    assert not payload["contract"]["server_command_revalidates_actor_set_operation_date_permission"]
    assert payload["safety"]["assembly_loads_or_executions"] == 0


def test_current_snapshot_risk_and_checkpoint_preserve_the_confirmed_boundary():
    sql = _load(SQL)
    assert sql["summary"]["sale_boundary_row_count"] == 3
    assert sql["summary"]["open_sale_boundary_row_count"] == 1
    assert sql["summary"]["closed_sale_boundary_row_count"] == 2
    assert sql["summary"]["missing_sale_oprdate_count"] == 0
    risks = _load(RISKS)
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    assert SQL.as_posix() in risk["evidence_refs"]
    assert RUNTIME.as_posix() in risk["evidence_refs"]
    assert any("operation date" in item for item in risk["controls"])
    assert risks["summary"]["risk_count"] == 84
    assert risks["source_checkpoint"]["order_sale_operation_date_sql_module_count"] == 6
    assert risks["source_checkpoint"]["order_sale_operation_date_automatic_flow_count"] == 2
    assert risks["source_checkpoint"]["order_sale_operation_date_configured_special_type_count"] == 2
    assert risks["source_checkpoint"]["order_sale_operation_date_current_special_order_count"] == 0
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
