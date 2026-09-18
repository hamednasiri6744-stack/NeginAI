from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "architecture" / "NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv"
STRUCTURE = ROOT / "docs" / "architecture" / "NEGINAI_TARGET_SCREEN_STRUCTURE_V1.csv"

VALID_LEVELS = {"L0", "L1", "L2", "L3", "L4", "L5"}

def load(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def main() -> int:
    registry_rows = load(REGISTRY)
    structure_rows = load(STRUCTURE)
    known = {row["capability_id"].strip() for row in registry_rows}
    errors: list[str] = []

    for line, row in enumerate(structure_rows, start=2):
        prefix = f"line {line} ({row.get('surface', '?')} / {row.get('section', '?')})"
        if row.get("level", "").strip() not in VALID_LEVELS:
            errors.append(f"{prefix}: invalid level {row.get('level')!r}")
        if not row.get("ownership_rule", "").strip():
            errors.append(f"{prefix}: empty ownership_rule")
        ids = [item.strip() for item in row.get("capabilities", "").split("|") if item.strip()]
        if not ids:
            errors.append(f"{prefix}: no capability IDs")
        for capability_id in ids:
            if capability_id not in known:
                errors.append(f"{prefix}: unknown capability ID {capability_id}")

    if errors:
        print("Target screen structure validation FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print(
        f"Target screen structure validation PASSED "
        f"({len(structure_rows)} structure rows against {len(known)} capabilities)"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
