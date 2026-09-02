import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/return_issue_cancel_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/return_issue_cancel_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_return_issue_cancel_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_evidence_is_read_only_redacted_and_hash_pinned():
    p = _load(SQL); assert p["validation"] == "PASS"
    assert p["safety"]["database_updateability"] == "READ_ONLY" and p["safety"]["can_update"] == 0
    assert p["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert p["safety"]["return_sale_voucher_payment_customer_user_host_or_raw_values_persisted"] == 0
    assert len(p["sql_module_profiles"]) == 9
    assert all(len(x["definition_sha256"]) == 64 for x in p["sql_module_profiles"])
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_issue_and_cancel_sql_ownership_is_explicit():
    c = _load(SQL)["static_issue_cancel_contract"]
    assert all(c.values())


def test_current_return_voucher_and_payment_projection_is_clean_but_flag_is_historical():
    p = _load(SQL); s = p["summary"]
    assert s["active_return_count"] == 13913 and s["cancelled_return_count"] == 178
    assert s["active_return_with_type10_voucher_count"] == 13913
    assert s["cancelled_return_with_type10_voucher_count"] == 0
    assert s["cancelled_return_with_payment_count"] == 0 and s["recent_cancelled_return_count"] == 2
    rows = {x["CancelFlag"]: x for x in p["current_return_state"]["by_cancel_flag"]}
    assert rows[0]["voucher_flag_one_count"] == 13913
    assert rows[1]["voucher_flag_one_count"] == 178
    v = p["current_return_state"]["voucher_integrity"]
    assert v["current_type10_voucher_count"] == 13913
    assert v["voucher_without_current_return_count"] == 0
    assert v["voucher_linked_cancelled_return_count"] == 0
    assert v["active_return_non_single_voucher_count"] == 0
    assert v["active_return_unconfirmed_voucher_count"] == 0


def test_return_audit_has_no_absent_identity_and_delete_candidates_are_capability_only():
    p = _load(SQL); coverage = p["generic_return_log_lifecycle"]["logged_id_coverage"]
    assert coverage["logged_return_count"] == 14091 and coverage["current_count"] == 14091
    assert coverage["absent_count"] == 0 and coverage["recent_absent_count"] == 0
    assert p["summary"]["retained_return_delete_log_count"] == 0
    assert len(p["direct_physical_return_delete_candidates"]) == 3
    assert any("capability" in x for x in p["evidence_limits"])


def test_managed_route_is_hash_pinned_and_preserves_transaction_limit():
    p = _load(RUNTIME)
    assert p["validation"] == "PASS"
    assert p["summary"] == {"assembly_count": 3, "selected_method_count": 5,
                            "selected_instruction_count": 404, "source_hash_mismatch_count": 0,
                            "method_or_coverage_error_count": 0}
    assert all(x["inventory_sha256_match"] for x in p["source"])
    c = p["managed_return_contract"]
    assert c["ui_cancel_calls_business_without_explicit_context_commit_or_rollback"]
    assert c["business_cancel_is_thin_adapter_delegate"] and c["business_generate_is_thin_adapter_delegate"]
    assert c["adapter_cancel_uses_named_save_or_cancel_procedures"] and c["adapter_generate_uses_named_generator"]
    assert c["adapter_cancel_context_query_or_execute"] and c["adapter_cancel_has_explicit_commit"]
    assert not c["adapter_cancel_has_explicit_rollback"]
    assert c["adapter_generate_queries_named_generator_without_explicit_context_commit_or_rollback"]
    assert not c["managed_to_sql_physical_transaction_enlistment_proven"]


def test_r081_and_checkpoint_are_current_and_caveated():
    risks, trace, checkpoint = _load(RISKS), _load(TRACE), _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84 and risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(x for x in risks["risks"] if x["id"] == "R-081")
    assert risk["severity"] == "CRITICAL"
    assert "Current state is clean and must not be called an incident" in risk["failure_mode"]
    assert "are capability only" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS" and checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
