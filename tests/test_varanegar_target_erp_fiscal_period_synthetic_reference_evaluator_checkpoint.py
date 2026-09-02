import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint_20260829.py"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint_20260829.json"


def test_rebuild(tmp_path):
    output = tmp_path / "checkpoint.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_checkpoint_chain_and_safety():
    data = json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"))
    assert data["validation"] == "PASS" and not data["failed_checks"]
    assert data["previous_checkpoint"]["path"].endswith("varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_checkpoint_20260829.json")
    assert set(data["safety"].values()) == {0}
    for item in data["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
