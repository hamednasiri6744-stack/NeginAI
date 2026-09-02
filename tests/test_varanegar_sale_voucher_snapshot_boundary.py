import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/sale_voucher_snapshot_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/sale_voucher_snapshot_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_sale_voucher_snapshot_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_evidence_is_read_only_redacted_and_hash_pinned():
    p = _load(SQL)
    assert p["validation"] == "PASS"
    assert p["safety"]["database_updateability"] == "READ_ONLY" and p["safety"]["can_update"] == 0
    assert p["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert p["safety"]["sale_order_snapshot_customer_user_host_or_raw_values_persisted"] == 0
    assert len(p["sql_module_profiles"]) == 6
    assert all(len(x["definition_sha256"]) == 64 for x in p["sql_module_profiles"])
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_snapshot_create_reverse_and_cancel_contract_is_explicit():
    assert all(_load(SQL)["static_snapshot_contract"].values())


def test_snapshot_number_and_graph_are_currently_reconciled():
    p = _load(SQL); s = p["summary"]
    assert s["sale_with_voucher_number_count"] == 266183
    assert s["sale_with_snapshot_count"] == 266183
    assert s["voucher_number_or_snapshot_mismatch_count"] == 0
    assert s["snapshot_header_count"] == 266183 and s["snapshot_item_count"] == 2128253
    i = p["current_sale_voucher_state"]["snapshot_integrity"]
    assert i["orphan_snapshot_count"] == 0 and i["duplicate_sale_snapshot_group_count"] == 0
    assert i["orphan_snapshot_item_count"] == 0


def test_retained_cancelled_snapshots_and_amount_difference_are_stage_semantics():
    p = _load(SQL); s = p["summary"]
    assert s["cancelled_sale_with_snapshot_count"] == 60698
    assert s["snapshot_amount_diff_count"] == 11750 and s["recent_snapshot_amount_diff_count"] == 1537
    rows = p["current_sale_voucher_state"]["sale_state_shapes"]
    differing = [x for x in rows if x["snapshot_amount_diff_count"]]
    assert len(differing) == 1
    assert (differing[0]["Status"], differing[0]["CancelFlag"], differing[0]["has_sale_no"]) == (1, 0, 1)
    assert all(x["number_without_snapshot_count"] == 0 and x["snapshot_without_number_count"] == 0 for x in rows)


def test_audit_absence_is_historical_and_delete_candidate_is_capability_only():
    p = _load(SQL); coverage = p["generic_snapshot_log_lifecycle"]["logged_id_coverage"]
    assert coverage["logged_snapshot_count"] == 266201 and coverage["current_count"] == 266183
    assert coverage["absent_count"] == 18 and coverage["recent_absent_count"] == 0
    assert p["summary"]["retained_snapshot_delete_count"] == 0
    assert len(p["direct_snapshot_delete_candidates"]) == 1
    assert any("capability" in x for x in p["evidence_limits"])


def test_managed_reverse_route_is_hash_pinned_and_transaction_owner_is_caveated():
    p = _load(RUNTIME)
    assert p["validation"] == "PASS"
    assert p["summary"] == {"assembly_count": 3, "selected_method_count": 4,
                            "selected_instruction_count": 243, "source_hash_mismatch_count": 0,
                            "method_or_coverage_error_count": 0}
    assert all(x["inventory_sha256_match"] for x in p["source"])
    c = p["managed_snapshot_conversion_contract"]
    assert c["ui_calls_business_without_explicit_context_commit_or_rollback"]
    assert c["business_constructs_context_validates_then_calls_adapter"]
    assert not c["business_has_explicit_commit"] and not c["business_has_explicit_rollback"]
    assert c["adapter_uses_named_conversion_procedure"] and c["adapter_queries_or_executes"]
    assert c["adapter_has_explicit_context"]
    assert not c["adapter_has_explicit_commit"] and not c["adapter_has_explicit_rollback"]
    assert not c["managed_to_sql_physical_transaction_enlistment_proven"]


def test_r082_and_checkpoint_are_current_and_caveated():
    risks, trace, checkpoint = _load(RISKS), _load(TRACE), _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84 and risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(x for x in risks["risks"] if x["id"] == "R-082")
    assert risk["severity"] == "CRITICAL"
    assert "must not be called corruption" in risk["failure_mode"]
    assert "capability only" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS" and checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
