import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "artifacts/varanegar_analysis/domains/command_outcome_commit_matrix_20260829.json"
)
CHECKPOINT = (
    ROOT
    / "artifacts/varanegar_analysis/varanegar_command_outcome_commit_checkpoint_20260829.json"
)


def _load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_matrix_is_offline_redacted_and_source_pinned():
    payload = _load()
    assert payload["validation"] == "PASS"
    assert payload["failed_assertions"] == []
    assert payload["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "raw_business_rows_ids_names_messages_or_sql_definitions_persisted": 0,
    }
    assert len(payload["source_manifest"]) == 12
    assert all(len(item["sha256"]) == 64 for item in payload["source_manifest"])
    raw = ARTIFACT.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_all_ten_source_assertions_are_independently_true():
    payload = _load()
    assert len(payload["source_assertions"]) == 10
    assert all(payload["source_assertions"].values())


def test_matrix_preserves_distinct_failure_and_durability_semantics():
    payload = _load()
    summary = payload["summary"]
    assert summary == {
        "case_count": 10,
        "domain_count": 6,
        "outcome_class_count": 10,
        "case_with_unproven_physical_transaction_owner_count": 3,
        "message_or_result_control_case_count": 6,
        "failed_assertion_count": 0,
    }
    cases = {case["case_id"]: case for case in payload["cases"]}
    assert list(cases) == [f"OC-{number:02d}" for number in range(1, 11)]
    assert cases["OC-01"]["outcome_classification"] == "SAFE_ONLY_BY_CURRENT_STATEMENT_ORDER"
    assert cases["OC-02"]["outcome_classification"] == "REJECTED_RESULT_WITH_COMMITTABLE_PREWRITE"
    assert cases["OC-03"]["outcome_classification"] == "POST_COMMIT_ADVISORY_FAILURE"
    assert cases["OC-04"]["outcome_classification"] == "PRECOMMIT_ADVISORY_FAILURE"
    assert cases["OC-05"]["outcome_classification"] == "CALLER_ENFORCED_REJECTION"
    assert cases["OC-06"]["outcome_classification"] == "LATE_VALIDATION_WITH_LOCAL_ROLLBACK"
    assert cases["OC-07"]["outcome_classification"] == "CALLER_DEPENDENT_ATOMICITY"
    assert cases["OC-08"]["outcome_classification"] == "NESTED_COMMIT_AND_BRANCHABLE_ROLLBACK"
    assert cases["OC-09"]["outcome_classification"] == "SQL_OWNED_ATOMIC_COMMAND"
    assert cases["OC-10"]["outcome_classification"] == "SUCCESS_GATED_SEPARATE_AUDIT_COMMIT"


def test_target_contract_never_uses_display_text_as_transaction_control():
    payload = _load()
    assert payload["target_invariants"][0] == (
        "A display message is never a transaction-control primitive."
    )
    assert any("Only ACCEPTED" in item for item in payload["target_invariants"])
    assert any("UNKNOWN" in item for item in payload["target_invariants"])
    assert all(case["target_contract_rule"] for case in payload["cases"])


def test_limits_do_not_overstate_runtime_or_incident_evidence():
    limits = _load()["evidence_limits"]
    assert any("not branch frequency" in item for item in limits)
    assert any("No new database" in item for item in limits)
    assert any("Clean current aggregates" in item for item in limits)


def test_checkpoint_covers_existing_risks_without_inventing_a_duplicate():
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"))
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"] == {
        "source_count": 11,
        "passed_check_count": 9,
        "failed_check_count": 0,
        "case_count": 10,
        "outcome_class_count": 10,
        "covered_existing_risk_count": 8,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
    }
