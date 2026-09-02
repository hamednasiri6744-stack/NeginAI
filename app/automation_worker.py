from __future__ import annotations

import json
import sys
from pathlib import Path

from app.automation_service import _run_report_inline
from app.config import get_settings
from app.database import sqlite_connection


def run_task(automation_id: int, output_path: Path) -> int:
    settings = get_settings()
    try:
        with sqlite_connection(settings.sqlite_path) as conn:
            row = conn.execute(
                "SELECT * FROM automations WHERE id=? AND deleted_at IS NULL",
                (automation_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("automation not found")
        response = _run_report_inline(settings, dict(row))
        payload = {"ok": True, "response": response}
        code = 0
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:1800]}"}
        code = 1
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return code


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    return run_task(int(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
