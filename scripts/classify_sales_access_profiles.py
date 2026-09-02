"""Create read-only seller/supervisor branch and line assignments.

The primary assignment metric is distinct customers. Distinct sales documents
and recency are deterministic tie-breakers. This script creates review artifacts
only; it does not create users or change permissions.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR, get_settings
from app.database import sql_connection
from app.reporting_policy import EXTERNAL_SALES_PERSON_NAMES


START_DATE = "1405/05/01"
END_EXCLUSIVE = "1405/06/01"
OUTPUT_DIR = ROOT_DIR / "data" / "analysis" / "sales_access_classification"
ROLE_SELLER = "فروشنده"
ROLE_SUPERVISOR = "سرپرست"


ROLE_SQL = """
WITH People AS (
    SELECT N'فروشنده' AS RoleName,
           DealerId AS PersonId,
           MAX(DealerName) AS PersonName,
           COUNT(DISTINCT CustomerId) AS TotalCustomers,
           COUNT(DISTINCT SellId) AS TotalDocuments,
           MAX(SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND DealerId IS NOT NULL
    GROUP BY DealerId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       AND MAX(SellDate) >= ?

    UNION ALL

    SELECT N'سرپرست' AS RoleName,
           SupervisorId AS PersonId,
           MAX(SupervisorName) AS PersonName,
           COUNT(DISTINCT CustomerId) AS TotalCustomers,
           COUNT(DISTINCT SellId) AS TotalDocuments,
           MAX(SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND SupervisorId IS NOT NULL
    GROUP BY SupervisorId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
)
SELECT RoleName, PersonId, PersonName, TotalCustomers, TotalDocuments,
       LastActivityDate
FROM People
ORDER BY RoleName, PersonName
"""


BRANCH_SQL = """
WITH ActiveSellers AS (
    SELECT DealerId
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND DealerId IS NOT NULL
    GROUP BY DealerId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       AND MAX(SellDate) >= ?
), ActiveSupervisors AS (
    SELECT SupervisorId
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND SupervisorId IS NOT NULL
    GROUP BY SupervisorId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
), Stats AS (
    SELECT N'فروشنده' AS RoleName,
           s.DealerId AS PersonId,
           s.CustomerLevelId AS DimensionId,
           MAX(s.CustomerLevelName) AS DimensionName,
           COUNT(DISTINCT s.CustomerId) AS CustomerCount,
           COUNT(DISTINCT s.SellId) AS DocumentCount,
           MAX(s.SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast AS s
    INNER JOIN ActiveSellers AS a ON a.DealerId = s.DealerId
    WHERE s.ReportDate >= ? AND s.ReportDate < ?
    GROUP BY s.DealerId, s.CustomerLevelId

    UNION ALL

    SELECT N'سرپرست' AS RoleName,
           s.SupervisorId AS PersonId,
           s.CustomerLevelId AS DimensionId,
           MAX(s.CustomerLevelName) AS DimensionName,
           COUNT(DISTINCT s.CustomerId) AS CustomerCount,
           COUNT(DISTINCT s.SellId) AS DocumentCount,
           MAX(s.SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast AS s
    INNER JOIN ActiveSupervisors AS a ON a.SupervisorId = s.SupervisorId
    WHERE s.ReportDate >= ? AND s.ReportDate < ?
    GROUP BY s.SupervisorId, s.CustomerLevelId
)
SELECT RoleName, PersonId, DimensionId, DimensionName, CustomerCount,
       DocumentCount, LastActivityDate
FROM Stats
"""


LINE_SQL = """
WITH ActiveSellers AS (
    SELECT DealerId
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND DealerId IS NOT NULL
    GROUP BY DealerId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       AND MAX(SellDate) >= ?
), ActiveSupervisors AS (
    SELECT SupervisorId
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND SupervisorId IS NOT NULL
    GROUP BY SupervisorId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
), Stats AS (
    SELECT N'فروشنده' AS RoleName,
           s.DealerId AS PersonId,
           s.CustomerCategoryId AS DimensionId,
           MAX(s.CustomerCategoryName) AS DimensionName,
           COUNT(DISTINCT s.CustomerId) AS CustomerCount,
           COUNT(DISTINCT s.SellId) AS DocumentCount,
           MAX(s.SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast AS s
    INNER JOIN ActiveSellers AS a ON a.DealerId = s.DealerId
    WHERE s.ReportDate >= ? AND s.ReportDate < ?
    GROUP BY s.DealerId, s.CustomerCategoryId

    UNION ALL

    SELECT N'سرپرست' AS RoleName,
           s.SupervisorId AS PersonId,
           s.CustomerCategoryId AS DimensionId,
           MAX(s.CustomerCategoryName) AS DimensionName,
           COUNT(DISTINCT s.CustomerId) AS CustomerCount,
           COUNT(DISTINCT s.SellId) AS DocumentCount,
           MAX(s.SellDate) AS LastActivityDate
    FROM dbo.SalesReviewFast AS s
    INNER JOIN ActiveSupervisors AS a ON a.SupervisorId = s.SupervisorId
    WHERE s.ReportDate >= ? AND s.ReportDate < ?
    GROUP BY s.SupervisorId, s.CustomerCategoryId
)
SELECT RoleName, PersonId, DimensionId, DimensionName, CustomerCount,
       DocumentCount, LastActivityDate
FROM Stats
"""


RELATIONSHIP_SQL = """
WITH ActiveSellers AS (
    SELECT DealerId
    FROM dbo.SalesReviewFast
    WHERE ReportDate >= ? AND ReportDate < ? AND DealerId IS NOT NULL
    GROUP BY DealerId
    HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       AND MAX(SellDate) >= ?
)
SELECT s.DealerId AS SellerId,
       MAX(s.DealerName) AS SellerName,
       s.SupervisorId,
       MAX(s.SupervisorName) AS SupervisorName,
       COUNT(DISTINCT s.CustomerId) AS CustomerCount,
       COUNT(DISTINCT s.SellId) AS DocumentCount,
       MAX(s.SellDate) AS LastInvoiceDate
FROM dbo.SalesReviewFast AS s
INNER JOIN ActiveSellers AS a ON a.DealerId = s.DealerId
WHERE s.ReportDate >= ? AND s.ReportDate < ?
  AND s.SupervisorId IS NOT NULL
GROUP BY s.DealerId, s.SupervisorId
"""


QUALITY_SQL = """
SELECT MIN(ReportDate) AS MinDate,
       MAX(ReportDate) AS MaxDate,
       COUNT_BIG(*) AS TotalRows,
       COUNT(DISTINCT SellId) AS TotalDocuments,
       COUNT(DISTINCT DealerId) AS SellerCount,
       COUNT(DISTINCT SupervisorId) AS SupervisorCount,
       COUNT(DISTINCT CustomerId) AS CustomerCount,
       (SELECT COUNT(*) FROM (
            SELECT DealerId FROM dbo.SalesReviewFast
            WHERE ReportDate >= ? AND ReportDate < ? AND DealerId IS NOT NULL
            GROUP BY DealerId
            HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       ) AS PositiveSellers) AS PositiveSellerCount,
       (SELECT COUNT(*) FROM (
            SELECT SupervisorId FROM dbo.SalesReviewFast
            WHERE ReportDate >= ? AND ReportDate < ? AND SupervisorId IS NOT NULL
            GROUP BY SupervisorId
            HAVING SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) > 0
       ) AS PositiveSupervisors) AS PositiveSupervisorCount,
       SUM(CASE WHEN DealerId IS NULL OR LTRIM(RTRIM(COALESCE(DealerName, N''))) = N'' THEN 1 ELSE 0 END) AS MissingSellerRows,
       SUM(CASE WHEN SupervisorId IS NULL OR LTRIM(RTRIM(COALESCE(SupervisorName, N''))) = N'' THEN 1 ELSE 0 END) AS MissingSupervisorRows,
       SUM(CASE WHEN CustomerId IS NULL THEN 1 ELSE 0 END) AS MissingCustomerRows,
       SUM(CASE WHEN CustomerLevelId IS NULL OR LTRIM(RTRIM(COALESCE(CustomerLevelName, N''))) = N'' THEN 1 ELSE 0 END) AS MissingBranchRows,
       SUM(CASE WHEN CustomerCategoryId IS NULL OR LTRIM(RTRIM(COALESCE(CustomerCategoryName, N''))) = N'' THEN 1 ELSE 0 END) AS MissingLineRows
FROM dbo.SalesReviewFast
WHERE ReportDate >= ? AND ReportDate < ?
"""


@dataclass(frozen=True)
class DimensionAssignment:
    name: str
    dimension_id: int | None
    customers: int
    documents: int
    share_pct: float
    second_name: str
    second_customers: int
    margin_customers: int


def _rows(cursor: Any) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _normalize_fa(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ")
    return re.sub(r"\s+", " ", text)


def _jalali_subtract_days(date_text: str, days: int) -> str:
    year, month, day = (int(part) for part in date_text.split("/"))
    month_lengths = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    for _ in range(days):
        day -= 1
        if day > 0:
            continue
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        day = month_lengths[month - 1]
    return f"{year:04d}/{month:02d}/{day:02d}"


def _is_excluded_person(name: Any) -> bool:
    return _normalize_fa(name) in {
        _normalize_fa(item) for item in EXTERNAL_SALES_PERSON_NAMES
    }


def _rank_dimension(
    stats: dict[tuple[str, int], list[dict[str, Any]]],
    key: tuple[str, int],
) -> DimensionAssignment:
    options = sorted(
        stats[key],
        key=lambda row: (
            -int(row["CustomerCount"]),
            -int(row["DocumentCount"]),
            -int(str(row["LastActivityDate"] or "0").replace("/", "")),
            _normalize_fa(row["DimensionName"]),
        ),
    )
    winner = options[0]
    runner_up = options[1] if len(options) > 1 else None
    denominator = sum(int(row["CustomerCount"]) for row in options)
    winner_customers = int(winner["CustomerCount"])
    runner_customers = int(runner_up["CustomerCount"]) if runner_up else 0
    return DimensionAssignment(
        name=_normalize_fa(winner["DimensionName"] or "نامشخص"),
        dimension_id=winner["DimensionId"],
        customers=winner_customers,
        documents=int(winner["DocumentCount"]),
        share_pct=round(100.0 * winner_customers / denominator, 1) if denominator else 0.0,
        second_name=_normalize_fa(runner_up["DimensionName"] or "") if runner_up else "",
        second_customers=runner_customers,
        margin_customers=winner_customers - runner_customers,
    )


def _confidence(branch: DimensionAssignment, line: DimensionAssignment, customers: int) -> tuple[str, str]:
    reasons: list[str] = []
    if customers < 5:
        reasons.append("کمتر از ۵ مشتری")
    if branch.margin_customers == 0:
        reasons.append("تساوی شعبه")
    elif branch.share_pct < 55:
        reasons.append("غلبه ضعیف شعبه")
    if line.margin_customers == 0:
        reasons.append("تساوی لاین")
    elif line.share_pct < 55:
        reasons.append("غلبه ضعیف لاین")
    if reasons:
        return "نیازمند بررسی", "؛ ".join(reasons)
    if branch.share_pct >= 70 and line.share_pct >= 70 and customers >= 20:
        return "بالا", ""
    return "متوسط", ""


def _rank_supervisor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    options = sorted(
        rows,
        key=lambda row: (
            -int(row["CustomerCount"]),
            -int(row["DocumentCount"]),
            -int(str(row["LastInvoiceDate"] or "0").replace("/", "")),
            _normalize_fa(row["SupervisorName"]),
        ),
    )
    winner = options[0]
    runner_up = options[1] if len(options) > 1 else None
    denominator = sum(int(row["CustomerCount"]) for row in options)
    winner_customers = int(winner["CustomerCount"])
    return {
        "سرپرست مرتبط": _normalize_fa(winner["SupervisorName"]),
        "شناسه سرپرست": int(winner["SupervisorId"]),
        "تعداد مشتری با سرپرست": winner_customers,
        "سهم ارتباط سرپرست (%)": round(100.0 * winner_customers / denominator, 1) if denominator else 0.0,
        "سرپرست دوم": _normalize_fa(runner_up["SupervisorName"]) if runner_up else "",
        "شناسه سرپرست دوم": int(runner_up["SupervisorId"]) if runner_up else "",
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    with sql_connection(settings) as conn:
        cursor = conn.cursor()

        cursor.execute(
            QUALITY_SQL,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
        )
        quality = _rows(cursor)[0]
        end_date = str(quality["MaxDate"])
        recent_cutoff = _jalali_subtract_days(end_date, 9)

        cursor.execute(
            ROLE_SQL,
            START_DATE, END_EXCLUSIVE, recent_cutoff,
            START_DATE, END_EXCLUSIVE,
        )
        people = _rows(cursor)

        cursor.execute(
            BRANCH_SQL,
            START_DATE, END_EXCLUSIVE, recent_cutoff,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
        )
        branch_rows = _rows(cursor)

        cursor.execute(
            LINE_SQL,
            START_DATE, END_EXCLUSIVE, recent_cutoff,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
            START_DATE, END_EXCLUSIVE,
        )
        line_rows = _rows(cursor)

        cursor.execute(
            RELATIONSHIP_SQL,
            START_DATE, END_EXCLUSIVE, recent_cutoff,
            START_DATE, END_EXCLUSIVE,
        )
        relationship_rows = _rows(cursor)

    supervisor_names = {
        _normalize_fa(person["PersonName"])
        for person in people
        if str(person["RoleName"]) == ROLE_SUPERVISOR
    }
    people = [
        person
        for person in people
        if not _is_excluded_person(person["PersonName"])
        and not (
            str(person["RoleName"]) == ROLE_SELLER
            and _normalize_fa(person["PersonName"]) in supervisor_names
        )
    ]
    allowed_supervisor_names = {
        _normalize_fa(person["PersonName"])
        for person in people
        if str(person["RoleName"]) == ROLE_SUPERVISOR
    }
    relationships_by_seller: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in relationship_rows:
        supervisor_name = _normalize_fa(row["SupervisorName"])
        if supervisor_name in allowed_supervisor_names:
            relationships_by_seller[int(row["SellerId"])].append(row)

    branch_stats: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    line_stats: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in branch_rows:
        branch_stats[(str(row["RoleName"]), int(row["PersonId"]))].append(row)
    for row in line_rows:
        line_stats[(str(row["RoleName"]), int(row["PersonId"]))].append(row)

    assignments: list[dict[str, Any]] = []
    identities_by_name: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for person in people:
        identities_by_name[_normalize_fa(person["PersonName"])].add(
            (str(person["RoleName"]), int(person["PersonId"]))
        )

    for person in people:
        key = (str(person["RoleName"]), int(person["PersonId"]))
        branch = _rank_dimension(branch_stats, key)
        line = _rank_dimension(line_stats, key)
        total_customers = int(person["TotalCustomers"])
        confidence, review_reason = _confidence(branch, line, total_customers)
        person_name = _normalize_fa(person["PersonName"])
        same_name = identities_by_name[person_name]
        same_role_ids = sorted(person_id for role, person_id in same_name if role == key[0])
        recorded_roles = sorted({role for role, _ in same_name})
        if len(same_role_ids) > 1:
            duplicate_reason = "نام یکسان با چند شناسه در همین نقش"
            review_reason = "؛ ".join(item for item in [review_reason, duplicate_reason] if item)
            confidence = "نیازمند بررسی"
        relationship = {
            "سرپرست مرتبط": "",
            "شناسه سرپرست": "",
            "تعداد مشتری با سرپرست": "",
            "سهم ارتباط سرپرست (%)": "",
            "سرپرست دوم": "",
            "شناسه سرپرست دوم": "",
        }
        if key[0] == ROLE_SELLER and relationships_by_seller.get(key[1]):
            relationship = _rank_supervisor(relationships_by_seller[key[1]])
        assignments.append(
            {
                "نقش": key[0],
                "شناسه": key[1],
                "نام": person_name,
                "نقش‌های ثبت‌شده برای این نام": " + ".join(recorded_roles),
                "شناسه‌های هم‌نام در همین نقش": ", ".join(map(str, same_role_ids)) if len(same_role_ids) > 1 else "",
                "شعبه پیشنهادی": branch.name,
                "تعداد مشتری شعبه": branch.customers,
                "سهم شعبه (%)": branch.share_pct,
                "شعبه دوم": branch.second_name,
                "تعداد مشتری شعبه دوم": branch.second_customers,
                "لاین پیشنهادی": line.name,
                "تعداد مشتری لاین": line.customers,
                "سهم لاین (%)": line.share_pct,
                "لاین دوم": line.second_name,
                "تعداد مشتری لاین دوم": line.second_customers,
                "کل مشتری یکتا": total_customers,
                "کل اسناد فروش": int(person["TotalDocuments"]),
                "آخرین فعالیت": str(person["LastActivityDate"]),
                **relationship,
                "اطمینان": confidence,
                "دلیل بررسی": review_reason,
            }
        )

    assignments.sort(key=lambda row: (row["نقش"], row["شعبه پیشنهادی"], row["لاین پیشنهادی"], row["نام"]))
    detail_path = OUTPUT_DIR / f"sales_access_assignments_{end_date.replace('/', '-')}.csv"
    with detail_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(assignments[0]))
        writer.writeheader()
        writer.writerows(assignments)

    summary_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in assignments:
        summary_counts[(row["نقش"], row["شعبه پیشنهادی"], row["لاین پیشنهادی"])] += 1
    summary_rows = [
        {"نقش": role, "شعبه": branch, "لاین": line, "تعداد نفر": count}
        for (role, branch, line), count in sorted(summary_counts.items())
    ]
    summary_path = OUTPUT_DIR / f"sales_access_summary_{end_date.replace('/', '-')}.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    metadata = {
        "source": "dbo.SalesReviewFast",
        "period": {"start": START_DATE, "end": end_date},
        "assignment_rule": {
            "eligibility": "positive net turnover in 1405/05",
            "seller_recency_cutoff": recent_cutoff,
            "seller_recency_rule": "last invoice date must be newer than 10 elapsed days from latest business date",
            "excluded_people": sorted(EXTERNAL_SALES_PERSON_NAMES),
            "supervisors_removed_from_seller_list": True,
            "primary": "distinct customers",
            "tie_breakers": ["distinct sales documents", "latest activity", "dimension name"],
            "branch_field": "CustomerLevelName",
            "line_field": "CustomerCategoryName",
        },
        "quality": {key: _json_value(value) for key, value in quality.items()},
        "assignment_counts": {
            "total": len(assignments),
            "sellers": sum(row["نقش"] == "فروشنده" for row in assignments),
            "supervisors": sum(row["نقش"] == "سرپرست" for row in assignments),
            "high": sum(row["اطمینان"] == "بالا" for row in assignments),
            "medium": sum(row["اطمینان"] == "متوسط" for row in assignments),
            "review": sum(row["اطمینان"] == "نیازمند بررسی" for row in assignments),
            "linked_sellers": sum(bool(row["سرپرست مرتبط"]) for row in assignments if row["نقش"] == ROLE_SELLER),
            "unlinked_sellers": sum(not bool(row["سرپرست مرتبط"]) for row in assignments if row["نقش"] == ROLE_SELLER),
        },
    }
    metadata_path = OUTPUT_DIR / f"sales_access_metadata_{end_date.replace('/', '-')}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"detail={detail_path}")
    print(f"summary={summary_path}")
    print(f"metadata={metadata_path}")
    for row in assignments:
        if row["نام"] == "عارف کامران" and row["نقش"] == "فروشنده":
            print("example=" + json.dumps(row, ensure_ascii=True))


if __name__ == "__main__":
    main()
