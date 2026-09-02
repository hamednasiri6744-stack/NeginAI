"""Confirmed operational team structures used by internal reporting."""

from __future__ import annotations

from typing import Any


ALBORZ_TEAM_STRUCTURE: dict[str, Any] = {
    "branch": "دفتر فروش البرز",
    "lines": {
        "لاین مارکت": {
            "team_split": "brand",
            "instruction": "Determine a market team by its supervisor and confirmed brand portfolio, not visit region.",
        },
        "لاین داروخانه": {
            "team_split": "brand",
            "instruction": "Determine a pharmacy team by its supervisor and confirmed brand portfolio, not visit region.",
        },
        "لاین گالری": {
            "team_split": "region_or_customer",
            "instruction": "Do not use brand ownership to assign gallery teams; use supervisor, region, or customer assignment.",
        },
        "لاین زنجیره ای": {
            "team_split": "region_or_customer",
            "shared_supervisor": {"id": 716, "name": "امیر سلگی"},
            "instruction": "Do not use brand ownership to assign chain teams; use supervisor, region, or customer assignment.",
        },
        "لاین عمده فروشی": {
            "team_split": "region_or_customer",
            "shared_supervisor": {"id": 716, "name": "امیر سلگی"},
            "instruction": "Do not use brand ownership to assign wholesale teams; use supervisor, region, or customer assignment.",
        },
    },
}


def organization_reporting_policy() -> list[str]:
    """Return non-negotiable business rules for the agent runtime."""
    return [
        (
            "Confirmed Alborz structure: Market and Pharmacy teams are brand-partitioned. "
            "Gallery, Chain, and Wholesale teams are region/customer-partitioned, not brand-partitioned."
        ),
        (
            "In Alborz, Chain and Wholesale share supervisor ID 716 (Amir Selgi). "
            "Never infer a Gallery, Chain, or Wholesale team from its sold brands."
        ),
    ]
