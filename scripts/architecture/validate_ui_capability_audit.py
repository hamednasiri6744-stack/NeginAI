from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "architecture" / "NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv"
AUDIT = ROOT / "docs" / "architecture" / "NEGINAI_CURRENT_UI_CAPABILITY_AUDIT_V1.csv"

VALID_DECISIONS = {"KEEP", "MOVE", "MERGE", "PROJECTION_ONLY", "DUPLICATE", "MISSING"}
VALID_SEVERITY = {"P0", "P1", "P2"}
VALID_PROJECTION_TYPES = {"signal", "badge", "summary", "context", "aggregate", "deep-link", "alert", "history"}

def load(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def main() -> int:
    errors: list[str] = []
    if not REGISTRY.exists() or not AUDIT.exists():
        print("ERROR: registry or audit file missing")
        return 1

    registry_rows = load(REGISTRY)
    audit_rows = load(AUDIT)
    registry = {row["capability_id"].strip(): row for row in registry_rows}

    seen: set[str] = set()
    for line, row in enumerate(audit_rows, start=2):
        audit_id = row.get("audit_id", "").strip()
        capability_id = row.get("capability_id", "").strip()
        prefix = f"line {line} ({audit_id or 'missing-id'})"

        if not audit_id:
            errors.append(f"{prefix}: missing audit_id")
        elif audit_id in seen:
            errors.append(f"{prefix}: duplicate audit_id")
        seen.add(audit_id)

        capability = registry.get(capability_id)
        if not capability:
            errors.append(f"{prefix}: unknown capability_id {capability_id!r}")
            continue

        decision = row.get("decision", "").strip()
        if decision not in VALID_DECISIONS:
            errors.append(f"{prefix}: invalid decision {decision!r}")

        severity = row.get("severity", "").strip()
        if severity not in VALID_SEVERITY:
            errors.append(f"{prefix}: invalid severity {severity!r}")

        projection_type = row.get("projection_type", "").strip()
        if projection_type not in VALID_PROJECTION_TYPES:
            errors.append(f"{prefix}: invalid projection_type {projection_type!r}")

        owner = row.get("canonical_owner", "").strip()
        if owner != capability["owner_domain"].strip():
            errors.append(
                f"{prefix}: owner mismatch audit={owner!r} registry={capability['owner_domain'].strip()!r}"
            )

        if decision == "PROJECTION_ONLY":
            allowed = capability["allowed_projections"].strip()
            allowed_types = {
                item.split(":", 1)[1].strip()
                for item in allowed.split("|")
                if ":" in item
            }
            if projection_type not in allowed_types:
                errors.append(
                    f"{prefix}: projection type {projection_type!r} is not registered for {capability_id}"
                )

        if decision == "KEEP" and capability["availability"].strip() in {"disabled", "gap"}:
            errors.append(
                f"{prefix}: cannot KEEP an unavailable capability with state {capability['availability'].strip()!r}"
            )

    if errors:
        print("UI capability audit validation FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print(
        f"UI capability audit validation PASSED "
        f"({len(audit_rows)} audited elements mapped to {len(registry_rows)} capabilities)"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
