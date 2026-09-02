from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/discount_v2_query_contracts_20260829.json"
SQL = ROOT / "artifacts/varanegar_analysis/domains/discount_v2_dataset_sql_20260829.json"
DOC = ROOT / "docs/varanegar_reconstruction/DISCOUNT_V2_INPUT_DATASET_AND_QUERY_CONTRACT_20260829_FA.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_query_helper_contract_is_hash_pinned_and_complete() -> None:
    data = _load(RUNTIME)
    assert data["validation"] == "PASS"
    assert data["source"]["inventory_sha256_match"]
    assert data["summary"]["query_template_count"] == 42
    assert data["assertions"]["cctor_is_exact_ldstr_stsfld_pairs_plus_ret"]


def test_query_categories_and_dependencies_are_stable() -> None:
    data = _load(RUNTIME)
    assert data["summary"]["reference_or_rule_template_count"] == 17
    assert data["summary"]["order_request_template_count"] == 10
    assert data["summary"]["other_template_count"] == 15
    assert data["summary"]["unique_table_reference_count"] == 44
    assert data["summary"]["temporary_table_reference_count"] == 3
    assert data["summary"]["persistent_object_reference_count"] == 41


def test_templates_are_read_only_but_text_formatted() -> None:
    data = _load(RUNTIME)
    assert data["summary"]["write_or_exec_template_count"] == 0
    assert data["summary"]["select_star_template_count"] == 0
    assert data["summary"]["formatted_template_count"] == 27
    assert data["summary"]["format_placeholder_slot_count"] == 31
    assert data["safety"]["raw_sql_or_business_values_persisted"] == 0


def test_all_persistent_dependencies_resolve_in_read_only_clone() -> None:
    data = _load(SQL)
    assert data["validation"] == "PASS"
    assert data["summary"]["persistent_reference_count"] == 41
    assert data["summary"]["resolved_reference_count"] == 41
    assert data["summary"]["user_table_reference_count"] == 40
    assert data["summary"]["view_reference_count"] == 1
    assert data["safety"]["data_mutations"] == 0


def test_clone_isolation_is_statement_snapshot_not_unit_of_work_proof() -> None:
    data = _load(SQL)
    assert data["database_isolation"] == {
        "snapshot_isolation_state_desc": "ON",
        "is_read_committed_snapshot_on": True,
    }
    assert data["assertions"]["clone_uses_rcsi_and_allows_snapshot_isolation"]


def test_document_requires_versioned_pricing_snapshot() -> None:
    text = DOC.read_text(encoding="utf-8-sig")
    for marker in ("PricingSnapshotId", "statement-level RCSI", "۳۵ call", "۴۲ template"):
        assert marker in text
