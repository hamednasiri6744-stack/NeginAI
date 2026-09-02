import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "artifacts/varanegar_analysis/domains/sale_accounting_crosswalk_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_sale_accounting_crosswalk_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_boundary_is_read_only_redacted_and_hash_pinned():
    p = _load(BOUNDARY)
    assert p["validation"] == "PASS"
    assert p["safety"]["database_updateability"] == "READ_ONLY" and p["safety"]["can_update"] == 0
    assert p["safety"]["stored_procedure_view_form_or_application_command_executions"] == 0
    assert p["safety"]["sale_snapshot_accounting_customer_user_host_or_raw_values_persisted"] == 0
    assert len(p["sql_module_profiles"]) == 3
    assert all(len(x["definition_sha256"]) == 64 for x in p["sql_module_profiles"])
    raw = BOUNDARY.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_creator_eligibility_uses_current_sale_not_snapshot_and_writers_need_owner():
    assert all(_load(BOUNDARY)["static_sale_accounting_contract"].values())


def test_current_sale_accounting_crosswalk_is_balanced_and_complete_to_journal():
    p = _load(BOUNDARY); s = p["summary"]
    assert s["sale_accounting_source_count"] == 202636
    assert s["sale_accounting_line_count"] == 625839
    assert s["sale_accounting_source_without_current_sale_count"] == 0
    assert s["sale_accounting_source_with_multiple_batch_count"] == 0
    assert s["unbalanced_sale_accounting_source_count"] == 0
    chain = p["sale_batch_journal_chain"]
    assert chain["batch_count"] == 101649 and chain["source_batch_links"] == 202636
    assert chain["missing_batch_link_count"] == 0 and chain["link_without_journal_count"] == 0
    assert chain["link_with_multiple_journal_count"] == 0
    assert chain["link_with_one_active_journal_count"] == 202636


def test_open_month_is_pending_watermark_not_incident_and_one_old_outlier_is_separate():
    p = _load(BOUNDARY)
    active = next(x for x in p["sale_state_accounting_shapes"] if (x["Status"], x["CancelFlag"], x["has_sale_no"]) == (1, 0, 1))
    assert active["sale_count"] == 212759 and active["with_accounting_source_count"] == 202636
    assert active["without_accounting_source_count"] == 10123
    months = {x["business_month"]: x for x in p["active_final_accounting_coverage_by_business_month"]}
    assert months["1405/03"]["without_accounting_source_count"] == 0
    assert months["1405/04"]["without_accounting_source_count"] == 0
    assert months["1405/05"]["sale_count"] == 10122
    assert months["1405/05"]["with_accounting_source_count"] == 0
    assert months["1403/01"]["without_accounting_source_count"] == 1
    assert sum(x["without_accounting_source_count"] for x in months.values()) == 10123


def test_snapshot_and_accounting_are_independent_state_dimensions():
    p = _load(BOUNDARY)
    q = {(x["has_snapshot"], x["has_accounting_source"]): x for x in p["active_final_snapshot_accounting_quadrants"]}
    assert q[(0, 0)]["sale_count"] == 480
    assert q[(0, 1)]["sale_count"] == 9008
    assert q[(1, 0)]["sale_count"] == 9643
    assert q[(1, 1)]["sale_count"] == 193628
    x = p["sale_snapshot_accounting_crosswalk"]
    assert x["snapshot_count"] == 266183 and x["snapshot_without_accounting_source_count"] == 72555
    assert x["cancelled_snapshot_without_accounting_source_count"] == 60698
    assert p["summary"]["cancelled_sale_accounting_source_count"] == 0


def test_historical_grouping_and_amounts_are_not_reinterpreted_as_errors():
    p = _load(BOUNDARY)
    g = {x["source_shape"]: x for x in p["sale_batch_source_grouping"]}
    assert g["SINGLE_SOURCE"]["batch_count"] == 101279
    assert g["MULTI_SOURCE"]["batch_count"] == 370
    assert g["MULTI_SOURCE"]["source_assignments"] == 101357
    assert g["MULTI_SOURCE"]["maximum_sources"] == 1131
    active = next(x for x in p["sale_state_accounting_shapes"] if (x["Status"], x["CancelFlag"], x["has_sale_no"]) == (1, 0, 1))
    assert active["debit_equals_sale_amount_count"] == 27594
    assert active["debit_differs_sale_amount_count"] == 175042
    assert any("business correctness" in x for x in p["evidence_limits"])


def test_r083_and_checkpoint_are_current_and_caveated():
    risks, trace, checkpoint = _load(RISKS), _load(TRACE), _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84 and risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31 and risks["summary"]["open_count"] == 84
    risk = next(x for x in risks["risks"] if x["id"] == "R-083")
    assert risk["severity"] == "CRITICAL"
    assert "must not be called an incident" in risk["failure_mode"]
    assert "does not prove historical non-issuance" in risk["failure_mode"]
    assert "must not be called an accounting mismatch" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS" and checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
