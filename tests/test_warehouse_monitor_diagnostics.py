"""Exercise failure reporting without scheduler, real processes or live data."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell diagnostic")


def test_monitor_records_failure_metadata_without_sensitive_message(tmp_path):
    source = (ROOT / "scripts/start_public_service.ps1").read_text(encoding="utf-8")
    diagnostic_prefix = source.split("$serviceIdentity =", 1)[0]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (tmp_path / "logs").mkdir()
    probe = scripts / "probe.ps1"
    probe.write_text(
        diagnostic_prefix
        + "\n$warehouseProcess=[pscustomobject]@{ProcessId=123;CommandLine=$null}\n"
        + "Write-Error -Message 'SENSITIVE_FIXTURE_VALUE' -ErrorId 'FixtureBoundary'\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    raw = (tmp_path / "logs/public-service-monitor-failure.json").read_text(encoding="utf-8-sig")
    report = json.loads(raw)
    assert report["ErrorId"].split(",")[0] == "FixtureBoundary"
    assert report["WorkerPid"] == 123
    assert report["WorkerCommandVisible"] is False
    assert report["Line"] > 0
    assert "SENSITIVE_FIXTURE_VALUE" not in raw


def test_inaccessible_identity_is_rejected_before_stopping_worker():
    source = (ROOT / "scripts/start_public_service.ps1").read_text(encoding="utf-8")
    guard = source.index("if ($warehouseProcess -and -not $warehouseProcess.CommandLine)")
    refusal = source.index("throw 'Warehouse worker command line is inaccessible", guard)
    stop = source.index("Stop-Process -Id $warehouseListener.OwningProcess -Force")
    assert guard < refusal < stop
    assert "do not relax the identity guard" in source
