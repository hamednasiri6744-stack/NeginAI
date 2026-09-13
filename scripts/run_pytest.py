from __future__ import annotations

import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / ".pytest-runtime"
BASE_TEMP = TEMP_ROOT / uuid.uuid4().hex
TEMP_ROOT.mkdir(parents=True, exist_ok=True)

command = [sys.executable, "-m", "pytest", *sys.argv[1:], f"--basetemp={BASE_TEMP}"]
try:
    exit_code = subprocess.call(command, cwd=ROOT)
finally:
    shutil.rmtree(BASE_TEMP, ignore_errors=True)
    try:
        TEMP_ROOT.rmdir()
    except OSError:
        pass

raise SystemExit(exit_code)
