from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "artifacts" / "varanegar_analysis"
DOMAINS = ANALYSIS / "domains"
DOCS = ROOT / "docs" / "varanegar_reconstruction"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(map(str, value)) | {
            key for child in value.values() for key in _mapping_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in _mapping_keys(child)}
    return set()


def test_manifest_covers_all_read_only_domains() -> None:
    manifest = _json(ANALYSIS / "manifest_20260826.json")
    assert manifest["validation"] == "PASS"
    assert manifest["domain_count"] == 18
    assert len(manifest["domains"]) == 18
    assert manifest["all_extractors_static_sql_is_read_only"] is True
    assert manifest["unexpected_domain_artifacts"] == []
    assert manifest["sensitive_raw_data_key_hits"] == 0
    assert manifest[
        "all_domain_docs_have_golden_cases_open_questions_reproduction_and_target_contract"
    ] is True
    for row in manifest["domains"]:
        payload = _json(ROOT / row["artifact"])
        assert payload["safety"]["updateability"] == "READ_ONLY"
        assert payload["safety"]["can_update"] == 0
        assert payload["safety"]["denies_data_writes"] == 1


def test_every_domain_document_has_reconstruction_contract() -> None:
    readme = (DOCS / "README_FA.md").read_text(encoding="utf-8")
    documents = sorted((DOCS / "domains").glob("*.md"))
    # The original reconstruction bundle contained 18 domains.  Seven
    # accounting/runtime domains were added later and are indexed by README.
    assert len(documents) == 25
    for document in documents:
        text = document.read_text(encoding="utf-8")
        assert document.name in readme
        domain_number = int(document.name.split("_", 1)[0])
        if domain_number <= 18:
            assert "Golden Case" in text
            assert "ابهام" in text
            assert "دستور بازتولید" in text
            assert "مدل مقصد" in text or "قرارداد مدل مقصد" in text
        else:
            # The later evidence-boundary documents use a risk/contract format.
            assert "قرارداد مقصد" in text or "Golden Case" in text


def test_configuration_artifact_contains_no_raw_values_or_identities() -> None:
    payload = _json(DOMAINS / "configuration_and_rule_flags_20260826.json")
    forbidden = {
        "KeyValue", "KeyValueOld", "Password", "PWD", "Token", "Secret",
        "URL", "Url", "Path", "HostName", "Hostname", "ApplicationName",
        "UserName", "Username", "DeviceOwner", "OwnerName",
    }
    assert forbidden.isdisjoint(_mapping_keys(payload))
    assert payload["key_value_configs"]["general_config_without_values"]["current_rows"] == 177
    assert payload["key_value_configs"]["server_config_without_values"]["current_rows"] == 334


def test_identity_and_financial_artifacts_are_aggregate_only() -> None:
    policies = {
        "parties_customers_suppliers_personnel_20260826.json": {
            "CustomerName", "CustName", "SupplierName", "PersonnelName",
            "ContactName", "NationalCode", "NationalID", "NationalId",
            "Mobile", "Phone", "Address", "Email", "UserName", "Username",
            "Password", "PasswordHash", "Hash", "SecurityStamp", "Token",
        },
        "collections_payments_open_invoices_20260826.json": {
            "CustomerName", "CustName", "ChequeNo", "ChqNo", "SayadNo",
            "AccountNo", "IBAN", "CardNo", "Comment", "Description",
        },
        "received_cheque_lifecycle_20260826.json": {
            "CustomerName", "CustName", "ChequeNo", "ChqNo", "SayadNo",
            "AccountNo", "IBAN", "CardNo", "Comment", "Description",
        },
        "supplier_disbursement_and_payable_cheques_20260826.json": {
            "SupplierName", "ChequeNo", "ChqNo", "SayadNo", "AccountNo",
            "IBAN", "CardNo", "Comment", "Description",
        },
        "supplier_cardex_contract_20260826.json": {
            "SupplierName", "ContactName", "ChequeNo", "ChqNo", "SayadNo",
            "AccountNo", "IBAN", "Comment", "Description",
        },
        "authorization_legacy_ngt_20260826.json": {
            "Name", "UserName", "Username", "Password", "PasswordHash",
            "Hash", "SecurityStamp", "Token", "Email", "Phone", "Mobile",
        },
    }
    for artifact, forbidden in policies.items():
        assert forbidden.isdisjoint(_mapping_keys(_json(DOMAINS / artifact))), artifact


def test_general_ledger_pipeline_is_balanced_and_uses_canonical_reverse_link() -> None:
    payload = _json(DOMAINS / "general_ledger_staging_and_posting_20260826.json")
    assert {"SimpleQuery", "definition_text", "sql_definition"}.isdisjoint(
        _mapping_keys(payload)
    )
    ledger = payload["general_ledger"]["double_entry_balance"]
    external = payload["external_voucher_pipeline"]
    staging = payload["pre_voucher_staging"]
    assert ledger["unbalanced_active"] == 0
    assert ledger["active_debit"] == ledger["active_credit"]
    assert external["line_double_entry_balance"]["unbalanced_headers"] == 0
    assert staging["balance_by_source_group"]["unbalanced_source_groups"] == 0
    header = external["header_population"]
    assert header["canonical_reverse_linked_to_ledger"] == header["headers"] == 197_518
    assert header["header_voucher_id_agrees_with_canonical"] == 0
    assert header["header_voucher_id_matches_canonical_voucher_no"] == 0
    assert payload["voucher_creator_crosswalk"]["integrity"] == {
        "orphan_creator_lines": 0,
        "orphan_field_definitions": 0,
        "unused_creators": 6,
        "used_creators": 11,
    }
    view_contracts = payload["voucher_creator_view_contracts"]
    assert view_contracts["integrity"] == {
        "used_creators_without_resolved_view": 0,
        "used_creator_views_without_visible_definition": 0,
    }
    assert len(view_contracts["used_creator_view_fingerprints"]) == 11
    assert len(view_contracts["used_creator_output_schema"]) == 561
    assert len(view_contracts["used_creator_dependencies"]) == 186


def test_three_month_baseline_has_expected_coverage_and_posting_parity() -> None:
    baseline = _json(ANALYSIS / "three_month_operational_activity_20260826.json")
    assert (baseline["from"], baseline["to"]) == ("1405/03/01", "1405/05/31")
    assert baseline["source_domain_count"] == 13
    assert baseline["window_block_count"] == 14
    assert baseline["generated_at"] == max(
        source["source_generated_at"] for source in baseline["sources"]
    )
    ledger_source = next(
        source for source in baseline["sources"]
        if source["domain"] == "general_ledger_staging_and_posting"
    )
    block = next(
        item["aggregate"] for item in ledger_source["window_blocks"]
        if item["json_path"] == "$.business_window"
    )["summary"]
    assert block["pre_voucher_lines"] == block["external_lines"] == 109_428
    assert block["pre_voucher_debit"] == block["external_debit"]
    assert block["pre_voucher_credit"] == block["external_credit"]
    assert block["journal_headers"] == 887
    assert block["manual_journal_headers"] == 683
    assert block["external_linked_journal_headers"] == block["external_headers"] == 204
    assert int(block["journal_debit"]) - int(block["external_debit"]) == int(
        block["manual_journal_debit"]
    )
    assert block["manual_journal_debit"] == block["manual_journal_credit"]


def test_cross_domain_handoffs_are_durable() -> None:
    manifest = _json(ANALYSIS / "manifest_20260826.json")
    analyses = {row["analysis"] for row in manifest["cross_domain_reports"]}
    assert analyses == {
        "four_hour_reconstruction_baseline",
        "varanegar_three_month_operational_activity",
        "reconstruction_readiness_matrix",
        "continuation_checkpoint",
    }
    assert {row["path"] for row in manifest["index_files"]} == {
        "docs/varanegar_reconstruction/README_FA.md",
        "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    }
    assert (DOCS / "FOUR_HOUR_ANALYSIS_20260826_FA.md").is_file()
    assert (DOCS / "THREE_MONTH_OPERATIONAL_ACTIVITY_20260826_FA.md").is_file()
    readiness = (DOCS / "RECONSTRUCTION_READINESS_MATRIX_20260826_FA.md").read_text(
        encoding="utf-8"
    )
    assert "Definition of Done" in readiness
    assert "۲۱ تا ۳۳ هفته" in readiness
    checkpoint = (DOCS / "CHECKPOINT_20260826_FA.md").read_text(encoding="utf-8")
    assert "domain_count=18" in checkpoint
    assert "7 passed" in checkpoint
