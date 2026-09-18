from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app
OUTPUT = ROOT / "vnext" / "neginai.openapi.json"

def main() -> None:
    spec = app.openapi()
    OUTPUT.write_text(json.dumps(spec, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"OPENAPI_OK paths={len(spec.get('paths', {}))} output={OUTPUT}")

if __name__ == "__main__":
    main()
