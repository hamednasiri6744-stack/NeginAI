"""Seller target pulse built from local planning targets and read-only Varanegar actuals."""

from __future__ import annotations

from typing import Any

from app.database import sql_connection, sqlite_connection
from app.seller_workspace_service import _seller_profile, _seller_work_calendar_summary


TARGET_METRIC = "sales_amount"
TARGET_CONTRACT = "NEGIN_TARGET_PULSE_V1"
TARGET_SEMANTIC_STATUS = "NEEDS_VALIDATION"


def _target_rial(amount: Any, unit: str) -> float:
    value = float(amount or 0)
    normalized = str(unit or "rial").strip().casefold()
    if normalized in {"toman", "tomans"}:
        return value * 10.0
    return value


def seller_target_pulse(settings: Any, username: str) -> dict[str, Any]:
    profile = _seller_profile(settings, username)
    seller_id = int(profile["personnel_id"])
    work_calendar = _seller_work_calendar_summary(settings, seller_id) or {}
    month = str(work_calendar.get("month") or "").strip()
    if len(month) != 7 or month[4] != "/":
        return {
            "configured": False,
            "seller_id": seller_id,
            "period": "",
            "actual_sales_rial": 0.0,
            "actual_invoice_count": 0,
            "target_rial": None,
            "achievement_percent": None,
            "expected_pace_percent": None,
            "pace_gap_percent": None,
            "remaining_target_rial": None,
            "daily_required_rial": None,
            "status": "unavailable",
            "contract": TARGET_CONTRACT,
            "semantic_status": TARGET_SEMANTIC_STATUS,
        }

    period = month.replace("/", "-")
    target_row = None
    with sqlite_connection(settings.sqlite_path) as connection:
        target_row = connection.execute(
            """
            SELECT s.id AS scenario_id, s.code AS scenario_code, s.name AS scenario_name,
                   s.status, v.amount, v.unit
            FROM planning_values AS v
            INNER JOIN planning_scenarios AS s ON s.id = v.scenario_id
            WHERE v.period = ?
              AND v.metric = ?
              AND v.seller_id = ?
              AND s.status IN ('locked', 'approved')
            ORDER BY CASE s.status WHEN 'locked' THEN 0 ELSE 1 END, s.id DESC
            LIMIT 1
            """,
            (period, TARGET_METRIC, str(seller_id)),
        ).fetchone()

    start_date = f"{month}/01"
    end_date = f"{month}/31"
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(DISTINCT H.ID) AS InvoiceCount,
                   COALESCE(SUM(CONVERT(money, I.AmountNut)), 0) AS ActualSales
            FROM SLE.tblSaleHdr AS H
            INNER JOIN SLE.tblSaleItm AS I ON I.HdrRef = H.ID
            WHERE H.DealerRef = ?
              AND H.CancelFlag = 0
              AND I.IsDeleted = 0
              AND ISNULL(I.PrizeType, 0) = 0
              AND H.SaleDate BETWEEN ? AND ?
            """,
            (seller_id, start_date, end_date),
        )
        row = cursor.fetchone()

    invoice_count = int(row[0] or 0) if row else 0
    actual_rial = float(row[1] or 0) if row else 0.0
    total_days = int(work_calendar.get("total_working_days") or 0)
    elapsed_days = int(work_calendar.get("elapsed_working_days") or 0)
    remaining_days = int(work_calendar.get("remaining_working_days") or 0)
    expected_pace = (elapsed_days / total_days * 100.0) if total_days > 0 else None

    if target_row is None:
        return {
            "configured": False,
            "seller_id": seller_id,
            "period": period,
            "actual_sales_rial": actual_rial,
            "actual_invoice_count": invoice_count,
            "target_rial": None,
            "achievement_percent": None,
            "expected_pace_percent": round(expected_pace, 2) if expected_pace is not None else None,
            "pace_gap_percent": None,
            "remaining_target_rial": None,
            "daily_required_rial": None,
            "remaining_working_days": remaining_days,
            "status": "unconfigured",
            "contract": TARGET_CONTRACT,
            "semantic_status": TARGET_SEMANTIC_STATUS,
            "actual_source": "dbo.TargetAndSale logic: SLE.tblSaleHdr + SLE.tblSaleItm.AmountNut",
            "target_source": "NeginAI planning_values",
        }

    target_rial = _target_rial(target_row["amount"], str(target_row["unit"] or "rial"))
    achievement = (actual_rial / target_rial * 100.0) if target_rial > 0 else 0.0
    remaining = max(target_rial - actual_rial, 0.0)
    daily_required = remaining / remaining_days if remaining_days > 0 else remaining
    pace_gap = achievement - expected_pace if expected_pace is not None else None
    if pace_gap is None:
        status = "configured"
    elif pace_gap > 1.0:
        status = "ahead"
    elif pace_gap < -1.0:
        status = "behind"
    else:
        status = "on_track"

    return {
        "configured": True,
        "seller_id": seller_id,
        "period": period,
        "actual_sales_rial": actual_rial,
        "actual_invoice_count": invoice_count,
        "target_rial": target_rial,
        "achievement_percent": round(achievement, 2),
        "expected_pace_percent": round(expected_pace, 2) if expected_pace is not None else None,
        "pace_gap_percent": round(pace_gap, 2) if pace_gap is not None else None,
        "remaining_target_rial": remaining,
        "daily_required_rial": daily_required,
        "remaining_working_days": remaining_days,
        "status": status,
        "scenario": {
            "id": int(target_row["scenario_id"]),
            "code": str(target_row["scenario_code"]),
            "name": str(target_row["scenario_name"]),
            "status": str(target_row["status"]),
        },
        "contract": TARGET_CONTRACT,
        "semantic_status": TARGET_SEMANTIC_STATUS,
        "actual_source": "dbo.TargetAndSale logic: SLE.tblSaleHdr + SLE.tblSaleItm.AmountNut",
        "target_source": "NeginAI planning_values",
    }
