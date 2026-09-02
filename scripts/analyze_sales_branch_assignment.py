"""Build a read-only salesperson-to-branch recommendation from NeginPakhsh."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from app.config import ROOT_DIR, get_settings
from app.database import execute_query
from app.sql_guard import validate_read_only_sql


START_DATE = "1404/05/12"
ACTIVE_SINCE = "1405/02/12"
END_DATE = "1405/05/12"

SQL = f"""
WITH RecentSellers AS (
  SELECT DISTINCT DealerId
  FROM dbo.SalesReviewFast
  WHERE SellDate BETWEEN '{ACTIVE_SINCE}' AND '{END_DATE}' AND DealerId IS NOT NULL
), Portfolio AS (
  SELECT s.DealerId, MAX(s.DealerName) AS DealerName,
         s.CustomerLevelId, MAX(s.CustomerLevelName) AS BranchName,
         COUNT(DISTINCT s.CustomerId) AS CustomerCount,
         COUNT(DISTINCT s.SellId) AS InvoiceCount,
         SUM(COALESCE(s.SellNetAmount, 0) - COALESCE(s.SellReturnNetAmount, 0)) AS NetSales
  FROM dbo.SalesReviewFast AS s
  INNER JOIN RecentSellers AS r ON r.DealerId = s.DealerId
  WHERE s.SellDate BETWEEN '{START_DATE}' AND '{END_DATE}'
    AND s.CustomerLevelId IN (1, 2, 3, 4)
  GROUP BY s.DealerId, s.CustomerLevelId
), Ranked AS (
  SELECT *,
         SUM(CustomerCount) OVER (PARTITION BY DealerId) AS TotalCustomers,
         ROW_NUMBER() OVER (
           PARTITION BY DealerId ORDER BY CustomerCount DESC, NetSales DESC
         ) AS BranchRank
  FROM Portfolio
)
SELECT DealerId, DealerName, BranchName, CustomerCount, TotalCustomers,
       CAST(100.0 * CustomerCount / NULLIF(TotalCustomers, 0) AS decimal(5, 1)) AS DominantSharePct,
       InvoiceCount, CAST(NetSales AS decimal(38, 0)) AS NetSales
FROM Ranked
WHERE BranchRank = 1
ORDER BY BranchName, DealerName
"""


def main() -> None:
    result = execute_query(get_settings(), validate_read_only_sql(SQL))
    output_dir = ROOT_DIR / "data" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = output_dir / "sales_personnel_branch_assignment_1405-05-12.csv"
    rows = []
    for source in result["rows"]:
        row = dict(zip(result["columns"], source))
        customer_count = int(row["TotalCustomers"])
        share = float(row["DominantSharePct"])
        row["OperationalSalesperson"] = "بله" if customer_count >= 20 else "نیازمند بررسی"
        row["Confidence"] = "بالا" if share >= 70 else "متوسط" if share >= 55 else "پایین"
        rows.append(row)

    fields = result["columns"] + ["OperationalSalesperson", "Confidence"]
    with detail_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    all_counts = Counter(row["BranchName"] for row in rows)
    core_counts = Counter(
        row["BranchName"] for row in rows if row["OperationalSalesperson"] == "بله"
    )
    summary_path = output_dir / "sales_personnel_branch_summary_1405-05-12.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["BranchName", "ActiveCodes", "OperationalSalespeople"])
        for branch in sorted(all_counts):
            writer.writerow([branch, all_counts[branch], core_counts[branch]])

    print(f"detail={detail_path}")
    print(f"summary={summary_path}")
    print(f"active_codes={len(rows)}")
    print(f"operational={sum(core_counts.values())}")
    for branch in sorted(all_counts):
        print(branch, all_counts[branch], core_counts[branch])


if __name__ == "__main__":
    main()
