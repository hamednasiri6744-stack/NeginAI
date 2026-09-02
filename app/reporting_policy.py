"""Company-specific reporting identities that are not internal sales teams."""

from __future__ import annotations


# These people can appear in the operational database because their companies
# sell directly through it. They must never be treated as Negin Pakhsh staff,
# supervisors, team members, or performance-report subjects.
EXTERNAL_SALES_PERSON_IDS = frozenset({7, 137, 192, 510})
EXTERNAL_SALES_PERSON_NAMES = frozenset({
    "محمد صادق نجف زاده",
    "ایمان شریف پور",
    "مسلم اعتمادی",
})


def external_sales_exclusion_sql(alias: str = "s") -> str:
    """Return the canonical-ID predicate for sales-report sources."""
    prefix = f"{alias}." if alias else ""
    ids = ", ".join(str(value) for value in sorted(EXTERNAL_SALES_PERSON_IDS))
    return (
        f"COALESCE({prefix}DealerId, -1) NOT IN ({ids}) "
        f"AND COALESCE({prefix}SupervisorId, -1) NOT IN ({ids})"
    )
