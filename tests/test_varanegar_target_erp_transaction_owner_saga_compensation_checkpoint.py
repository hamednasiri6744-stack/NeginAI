import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.py"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.json"


def test_rebuild(tmp_path):
    output = tmp_path / "checkpoint.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_checkpoint_chain_and_safety():
    document = json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"))
    assert document["validation"] == "PASS" and not document["failed_checks"]
    assert document["previous_checkpoint"]["path"].endswith("varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829.json")
    assert set(document["safety"].values()) == {0}
    for source in document["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
