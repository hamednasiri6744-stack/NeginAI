import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "varanegar_analysis_checkpoint_20260828.json"
)


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_checkpoint_is_offline_valid_and_hashes_every_source() -> None:
    payload = _load()
    assert payload["artifact"] == "varanegar_analysis_checkpoint_20260828"
    assert payload["schema_version"] == 1
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert payload["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_PERSISTED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "business_rows_or_raw_values_read": 0,
    }
    assert payload["summary"]["source_count"] == len(payload["source_manifest"])
    assert payload["summary"]["failed_check_count"] == 0
    assert all(payload["checks"].values())
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert _sha256(path) == row["sha256"]


def test_checkpoint_freezes_current_evidence_gates() -> None:
    summary = _load()["summary"]
    assert summary == {
        "source_count": 21,
        "passed_check_count": 33,
        "failed_check_count": 0,
        "voucher_hash_pinned_binary_count": 7,
        "replication_hash_pinned_binary_count": 4,
        "replication_target_method_contract_count": 49,
        "risk_count": 56,
        "critical_risk_count": 31,
        "mapped_risk_assignment_count": 221,
        "unique_risk_count": 56,
        "command_ready_module_count": 0,
    }
