from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.config import get_settings
from app.database import sql_connection


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis_result.json"
HISTORICAL_MONTHS = ["1405/02", "1405/03", "1405/04", "1405/05"]
BUCKETS = ["01-05", "06-10", "11-15", "16-20", "21-end"]
EXPECTED_WORKDAYS_1405_06 = {
    "01-05": 5,
    "06-10": 3,
    "11-15": 4,
    "16-20": 4,
    "21-end": 9,
}


DAILY_SQL = """
SET NOCOUNT ON;
SELECT
    ReportDate,
    COUNT_BIG(*) AS LineRows,
    COUNT(DISTINCT SellDetailID) AS DistinctDetailIds,
    COUNT(DISTINCT SellId) AS Documents,
    SUM(COALESCE(SellNetAmount, 0) - COALESCE(SellReturnNetAmount, 0)) AS NetRial,
    SUM(COALESCE(SellReturnNetAmount, 0)) AS ReturnRial
FROM dbo.SalesReviewFast
WHERE ReportDate >= '1405/02/01' AND ReportDate <= '1405/06/03'
GROUP BY ReportDate
ORDER BY ReportDate;
"""


QUALITY_SQL = """
SET NOCOUNT ON;
SELECT
    CONVERT(varchar(19), GETDATE(), 120) AS ServerTime,
    COUNT_BIG(*) AS LineRows,
    COUNT(DISTINCT SellDetailID) AS DistinctDetailIds,
    SUM(CASE WHEN ReportDate IS NULL THEN 1 ELSE 0 END) AS NullReportDates,
    SUM(CASE WHEN SellId IS NULL THEN 1 ELSE 0 END) AS NullSellIds,
    SUM(COALESCE(SellReturnNetAmount, 0)) AS ReturnRial
FROM dbo.SalesReviewFast
WHERE ReportDate >= '1405/02/01' AND ReportDate <= '1405/06/03';
"""


def bucket_for_day(day: int) -> str:
    if day <= 5:
        return "01-05"
    if day <= 10:
        return "06-10"
    if day <= 15:
        return "11-15"
    if day <= 20:
        return "16-20"
    return "21-end"


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def main() -> None:
    settings = get_settings()
    with sql_connection(settings) as conn:
        cursor = conn.cursor()
        cursor.execute(DAILY_SQL)
        columns = [column[0] for column in cursor.description]
        daily_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.execute(QUALITY_SQL)
        quality_columns = [column[0] for column in cursor.description]
        quality = dict(zip(quality_columns, cursor.fetchone()))

    for row in daily_rows:
        row["month"] = str(row["ReportDate"])[:7]
        row["day"] = int(str(row["ReportDate"])[-2:])
        row["bucket"] = bucket_for_day(row["day"])
        row["net_toman"] = float(Decimal(str(row["NetRial"])) / Decimal(10))
        row["return_toman"] = float(Decimal(str(row["ReturnRial"])) / Decimal(10))

    month_stats: dict[str, dict] = {}
    for month in HISTORICAL_MONTHS:
        month_rows = [row for row in daily_rows if row["month"] == month]
        median_documents = statistics.median(row["Documents"] for row in month_rows)
        # Tiny end-of-process or partial-posting dates are not full selling days.
        # A relative threshold avoids hard-coding a document count across months.
        document_cutoff = median_documents * 0.20
        qualified = [row for row in month_rows if row["Documents"] >= document_cutoff]
        excluded = [row for row in month_rows if row["Documents"] < document_cutoff]

        bucket_stats: dict[str, dict] = {}
        for bucket in BUCKETS:
            values = [row["net_toman"] for row in qualified if row["bucket"] == bucket]
            bucket_stats[bucket] = {
                "qualified_days": len(values),
                "average_daily_toman": sum(values) / len(values) if values else None,
                "total_toman": sum(values),
            }

        early_average = bucket_stats["01-05"]["average_daily_toman"]
        if not early_average:
            raise RuntimeError(f"No usable early-month baseline for {month}")
        for value in bucket_stats.values():
            value["multiplier_vs_early"] = (
                value["average_daily_toman"] / early_average
                if value["average_daily_toman"] is not None
                else None
            )

        month_stats[month] = {
            "median_documents": median_documents,
            "document_cutoff": document_cutoff,
            "qualified_days": len(qualified),
            "excluded_dates": [
                {
                    "date": str(row["ReportDate"]),
                    "documents": row["Documents"],
                    "net_toman": row["net_toman"],
                }
                for row in excluded
            ],
            "buckets": bucket_stats,
            "all_sales_toman": sum(row["net_toman"] for row in month_rows),
            "qualified_sales_toman": sum(row["net_toman"] for row in qualified),
        }

    model_months = [
        month
        for month in HISTORICAL_MONTHS
        if month_stats[month]["buckets"]["01-05"]["qualified_days"] >= 3
    ]

    uplift_curve = []
    for bucket in BUCKETS:
        values = [
            month_stats[month]["buckets"][bucket]["multiplier_vs_early"]
            for month in model_months
        ]
        uplift_curve.append(
            {
                "bucket": bucket,
                "median_multiplier": statistics.median(values),
                "mean_multiplier": statistics.mean(values),
                "q25_multiplier": quantile(values, 0.25),
                "q75_multiplier": quantile(values, 0.75),
                "minimum_multiplier": min(values),
                "maximum_multiplier": max(values),
                "month_multipliers": {
                    month: month_stats[month]["buckets"][bucket]["multiplier_vs_early"]
                    for month in model_months
                },
            }
        )

    current_rows = [row for row in daily_rows if row["month"] == "1405/06"]
    current_baseline = statistics.mean(row["net_toman"] for row in current_rows)
    median_multiplier_by_bucket = {
        row["bucket"]: row["median_multiplier"] for row in uplift_curve
    }

    forecast_parts = []
    for bucket in BUCKETS:
        daily_forecast = current_baseline * median_multiplier_by_bucket[bucket]
        forecast_parts.append(
            {
                "bucket": bucket,
                "expected_workdays": EXPECTED_WORKDAYS_1405_06[bucket],
                "multiplier": median_multiplier_by_bucket[bucket],
                "forecast_daily_toman": daily_forecast,
                "forecast_bucket_toman": daily_forecast
                * EXPECTED_WORKDAYS_1405_06[bucket],
            }
        )

    curve_scenarios = []
    for source_month in model_months:
        total = 0.0
        for bucket in BUCKETS:
            multiplier = month_stats[source_month]["buckets"][bucket][
                "multiplier_vs_early"
            ]
            total += (
                current_baseline
                * multiplier
                * EXPECTED_WORKDAYS_1405_06[bucket]
            )
        curve_scenarios.append({"source_month": source_month, "forecast_toman": total})

    forecast_values = [row["forecast_toman"] for row in curve_scenarios]
    central_forecast = sum(row["forecast_bucket_toman"] for row in forecast_parts)

    # Leave-one-month-out check: estimate each historical month from its own
    # early-month pace and the median shape of the other three months.
    backtests = []
    for target_month in model_months:
        peer_months = [month for month in model_months if month != target_month]
        target_early = month_stats[target_month]["buckets"]["01-05"][
            "average_daily_toman"
        ]
        predicted = 0.0
        for bucket in BUCKETS:
            peer_multipliers = [
                month_stats[month]["buckets"][bucket]["multiplier_vs_early"]
                for month in peer_months
            ]
            predicted += (
                target_early
                * statistics.median(peer_multipliers)
                * month_stats[target_month]["buckets"][bucket]["qualified_days"]
            )
        actual = month_stats[target_month]["qualified_sales_toman"]
        backtests.append(
            {
                "month": target_month,
                "predicted_toman": predicted,
                "actual_toman": actual,
                "error_percent": (predicted / actual - 1) * 100,
            }
        )

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_snapshot": {
            "server_time": str(quality["ServerTime"]),
            "source": "SQL Server 192.168.1.171 / NeginPakhsh / dbo.SalesReviewFast",
            "date_range": "1405/02/01..1405/06/03",
            "metric": "sum(SellNetAmount - SellReturnNetAmount), divided by 10 to toman",
        },
        "quality": {
            "line_rows": int(quality["LineRows"]),
            "distinct_detail_ids": int(quality["DistinctDetailIds"]),
            "duplicate_detail_rows": int(quality["LineRows"])
            - int(quality["DistinctDetailIds"]),
            "null_report_dates": int(quality["NullReportDates"]),
            "null_sell_ids": int(quality["NullSellIds"]),
            "return_toman": float(Decimal(str(quality["ReturnRial"])) / Decimal(10)),
            "partial_day_rule": "exclude dates with documents below 20% of that month's median",
        },
        "historical_months": month_stats,
        "model_months": model_months,
        "excluded_model_months": [
            month for month in HISTORICAL_MONTHS if month not in model_months
        ],
        "uplift_curve": uplift_curve,
        "current": {
            "observed_dates": [str(row["ReportDate"]) for row in current_rows],
            "documents": sum(row["Documents"] for row in current_rows),
            "sales_toman": sum(row["net_toman"] for row in current_rows),
            "baseline_daily_toman": current_baseline,
        },
        "expected_workdays": EXPECTED_WORKDAYS_1405_06,
        "forecast_parts": forecast_parts,
        "curve_scenarios": curve_scenarios,
        "forecast": {
            "central_toman": central_forecast,
            "scenario_min_toman": min(forecast_values),
            "scenario_max_toman": max(forecast_values),
            "scenario_median_toman": statistics.median(forecast_values),
        },
        "backtests": backtests,
        "daily_preview": [
            {
                "date": str(row["ReportDate"]),
                "documents": row["Documents"],
                "net_toman": row["net_toman"],
            }
            for row in daily_rows[:10]
        ],
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
