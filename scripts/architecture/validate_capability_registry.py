from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "architecture" / "NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv"

REQUIRED_COLUMNS = {
    "capability_id",
    "capability_name",
    "scope",
    "owner_domain",
    "canonical_surface",
    "primary_source",
    "semantic_authority",
    "backend_boundary",
    "allowed_projections",
    "interaction_mode",
    "availability",
    "notes",
}

VALID_SCOPES = {"seller", "global", "enterprise", "platform"}
VALID_OWNERS = {
    "Identity & System",
    "Field Operations",
    "Customer Intelligence",
    "Commercial & Orders",
    "Finance & Collections",
    "Distribution & Returns",
    "Intelligence & Analysis",
    "AI Intelligence",
    "Admin & Planning",
    "Platform & Knowledge",
    "Warehouse Operations",
}
VALID_INTERACTIONS = {
    "read",
    "read+local-write",
    "controlled-write",
    "external-preview",
    "analysis",
    "orchestration",
}
VALID_AVAILABILITY = {
    "active",
    "partial",
    "gap",
    "gated",
    "disabled",
    "separate-domain",
}
VALID_PROJECTION_TYPES = {
    "signal",
    "badge",
    "summary",
    "context",
    "aggregate",
    "deep-link",
    "alert",
    "history",
}
BLOCKED_PROJECTION_WORDS = {"canonical", "full-workflow", "manage", "edit"}

def fail(message: str, errors: list[str]) -> None:
    errors.append(message)

def main() -> int:
    if not REGISTRY.exists():
        print(f"ERROR: registry not found: {REGISTRY}")
        return 1

    with REGISTRY.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            print(f"ERROR: missing columns: {sorted(missing)}")
            return 1
        rows = list(reader)

    errors: list[str] = []
    ids = [row["capability_id"].strip() for row in rows]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        fail(f"duplicate capability_id values: {duplicates}", errors)

    for index, row in enumerate(rows, start=2):
        capability_id = row["capability_id"].strip()
        prefix = f"line {index} ({capability_id or 'missing-id'})"

        for column in REQUIRED_COLUMNS - {"allowed_projections"}:
            if not row[column].strip():
                fail(f"{prefix}: empty required field {column}", errors)

        if row["scope"].strip() not in VALID_SCOPES:
            fail(f"{prefix}: invalid scope {row['scope']!r}", errors)

        if row["owner_domain"].strip() not in VALID_OWNERS:
            fail(f"{prefix}: invalid owner_domain {row['owner_domain']!r}", errors)

        if row["interaction_mode"].strip() not in VALID_INTERACTIONS:
            fail(f"{prefix}: invalid interaction_mode {row['interaction_mode']!r}", errors)

        if row["availability"].strip() not in VALID_AVAILABILITY:
            fail(f"{prefix}: invalid availability {row['availability']!r}", errors)

        projections = row["allowed_projections"].strip()
        if projections and projections.lower() != "none":
            for projection in projections.split("|"):
                if ":" not in projection:
                    fail(f"{prefix}: malformed projection {projection!r}", errors)
                    continue
                surface, projection_type = (part.strip() for part in projection.split(":", 1))
                if not surface:
                    fail(f"{prefix}: projection surface is empty", errors)
                if projection_type not in VALID_PROJECTION_TYPES:
                    fail(f"{prefix}: invalid projection type {projection_type!r}", errors)
                if projection_type in BLOCKED_PROJECTION_WORDS:
                    fail(f"{prefix}: projection attempts duplicate workflow {projection!r}", errors)

        if row["availability"].strip() == "disabled" and row["interaction_mode"].strip() == "controlled-write":
            # Disabled controlled-write capabilities are legal, but their notes must say they are disabled.
            if "disabled" not in row["notes"].lower():
                fail(f"{prefix}: disabled controlled-write must explicitly document disabled state", errors)

        if row["scope"].strip() == "seller" and row["owner_domain"].strip() in {"Warehouse Operations", "Admin & Planning"}:
            fail(f"{prefix}: seller capability cannot be owned by bounded enterprise domain", errors)

    if errors:
        print("Capability registry validation FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print(
        "Capability registry validation PASSED "
        f"({len(rows)} capabilities, {len(VALID_OWNERS)} owner domains)"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
