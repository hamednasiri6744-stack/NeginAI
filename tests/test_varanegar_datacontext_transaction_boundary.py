import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/varanegar_analysis/domains/datacontext_transaction_runtime_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_datacontext_transaction_checkpoint_20260829.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_runtime_extraction_is_hash_pinned_static_and_package_wide():
    payload = _load(ARTIFACT)
    assert payload["validation"] == "PASS"
    assert payload["summary"]["required_assembly_count"] == 3
    assert payload["summary"]["managed_inventory_assembly_scan_count"] == 59
    assert payload["summary"]["inventory_parse_error_count"] == 0
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["safety"]["database_connections"] == 0
    assert payload["safety"]["form_procedure_or_application_command_executions"] == 0


def test_default_context_is_no_transaction_and_commit_rollback_are_noops_without_dbtransaction():
    payload = _load(ARTIFACT)
    assert payload["contract"]["transaction_enum"] == {"Begin": 0, "No": 1}
    assert payload["contract"]["default_datacontext_mode"] == "NO_TRANSACTION"
    assert payload["contract"]["commit_without_db_transaction"] == "NO_OP"
    assert payload["contract"]["rollback_without_db_transaction"] == "NO_OP"
    assert payload["assertions"]["default_context_selects_no_transaction_mode"]
    assert payload["assertions"]["commit_and_rollback_are_null_transaction_noops"]


def test_each_context_builds_provider_connection_and_binds_its_transaction():
    payload = _load(ARTIFACT)
    assert payload["contract"]["context_connection_ownership"] == "NEW_PROVIDER_AND_CONNECTION_PER_CONTEXT_BY_DEFAULT"
    assert payload["assertions"]["each_mode_context_builds_provider_and_connection"]
    assert payload["assertions"]["provider_begins_transaction_only_for_begin_mode"]
    assert payload["assertions"]["commands_bind_provider_connection_and_transaction"]
    assert payload["summary"]["custom_provider_or_connection_factory_setter_callsite_count"] == 0
    assert payload["assertions"]["no_packaged_custom_provider_or_connection_factory_setter_callsite"]


def test_discount_v2_preparation_and_adapter_conversion_have_separate_transaction_boundaries():
    payload = _load(ARTIFACT)
    assert payload["assertions"]["discount_v2_preparation_uses_no_transaction_context"]
    assert payload["assertions"]["adapter_conversion_uses_begin_context_and_commit"]
    assert payload["assertions"]["business_v2_calls_transactional_adapter_delegate_overload"]
    contract = payload["contract"]
    assert contract["discount_v2_preparation_transaction"] == "NONE_AUTOCOMMIT_PER_COMMAND"
    assert contract["order_sale_adapter_transaction"] == "SEPARATE_BEGIN_CONTEXT"
    assert not contract["discount_v2_preparation_and_sale_conversion_share_physical_transaction"]


def test_direct_core_fallback_is_not_a_managed_transaction_owner():
    payload = _load(ARTIFACT)
    assert payload["assertions"]["direct_core_overload_falls_back_to_default_context_without_commit"]
    direct = payload["order_sale_methods"]["business_direct_core"]
    assert direct["data_context_constructor_modes"] == [
        {"offset": 17, "mode_value": None, "mode": "DEFAULT_OR_CONTEXT_DEPENDENT"}
    ]
    assert all(event.get("member") != "Thunderstruck.DataContext.Commit" for event in direct["events"])


def test_r079_and_checkpoint_integrate_transaction_boundary_without_count_inflation():
    risks = _load(RISKS)
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    assert ARTIFACT.as_posix() in risk["evidence_refs"]
    assert any("single injected transaction owner" in item for item in risk["controls"])
    assert risks["summary"]["risk_count"] == 84
    source = risks["source_checkpoint"]
    assert source["datacontext_managed_assembly_scan_count"] == 59
    assert source["datacontext_custom_factory_setter_callsite_count"] == 0
    assert source["datacontext_order_sale_split_transaction"] is True
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
