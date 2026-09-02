from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
NGROK = ROOT / "tools" / "ngrok-bin" / "ngrok.exe"
LOG = ROOT / "logs" / "ngrok.log"


def main() -> None:
    token = str(dotenv_values(ROOT / ".env").get("NGROK_AUTHTOKEN", "")).strip()
    if not token:
        raise SystemExit("NGROK_AUTHTOKEN is missing")
    if not NGROK.exists():
        raise SystemExit("ngrok.exe is missing")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")
    environment = os.environ.copy()
    environment["NGROK_AUTHTOKEN"] = token
    process = subprocess.Popen(
        [str(NGROK), "http", "8000", "--log", str(LOG), "--log-format", "json", "--log-level", "info"],
        cwd=ROOT,
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    print(f"ngrok_pid={process.pid}")


if __name__ == "__main__":
    main()
