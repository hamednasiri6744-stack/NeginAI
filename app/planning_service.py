"""Versioned planning write-back store for NeginAI.

The source ERP remains read-only.  Budgets, forecasts, assumptions and their
audit trail live in the local planning store and can later be moved to a
dedicated SQL Server database without changing the public API.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any

from app.database import sqlite_connection


PERIOD_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")
SCENARIO_TYPES = {"budget", "forecast", "plan"}
PLANNING_METRICS = {
    "sales_amount": "فروش مبلغی",
    "sales_quantity": "فروش تعدادی",
    "gross_margin": "حاشیه سود",
    "collections": "وصول",
    "inventory_quantity": "موجودی تعدادی",
    "expense_amount": "هزینه",
    "headcount": "تعداد نیروی انسانی",
    "capex": "سرمایه‌گذاری ثابت",
}


class PlanningError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean(value: Any, limit: int = 200) -> str:
    return str(value or "").strip()[:limit]


def _decode_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _scenario_from_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["assumptions"] = _decode_json(item.pop("assumptions_json", "{}"), {})
    return item


def _validate_period(period: str, fiscal_year: int | None = None) -> str:
    match = PERIOD_RE.fullmatch(_clean(period, 7))
    if not match:
        raise PlanningError("دوره باید به شکل سال-ماه باشد؛ نمونه: 1405-01")
    if fiscal_year is not None and int(match.group("year")) != int(fiscal_year):
        raise PlanningError("سال دوره باید با سال مالی سناریو یکسان باشد")
    return match.group(0)


def _get_scenario(conn: Any, scenario_id: int) -> Any:
    row = conn.execute(
        "SELECT * FROM planning_scenarios WHERE id=?", (scenario_id,)
    ).fetchone()
    if row is None:
        raise PlanningError("سناریوی برنامه‌ریزی پیدا نشد")
    return row


def _audit(
    conn: Any,
    scenario_id: int,
    username: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """INSERT INTO planning_audit
           (scenario_id, username, action, details_json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            scenario_id,
            _clean(username, 100) or "unknown",
            action,
            json.dumps(details or {}, ensure_ascii=False, separators=(",", ":")),
            _now(),
        ),
    )


def create_scenario(
    settings: Any,
    username: str,
    *,
    code: str,
    name: str,
    scenario_type: str,
    fiscal_year: int,
    start_period: str,
    end_period: str,
    base_scenario_id: int | None = None,
    assumptions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code = _clean(code, 40)
    name = _clean(name, 200)
    scenario_type = _clean(scenario_type, 20).casefold()
    if not code or not name:
        raise PlanningError("کد و نام سناریو الزامی است")
    if scenario_type not in SCENARIO_TYPES:
        raise PlanningError("نوع سناریو باید budget، forecast یا plan باشد")
    if not 1300 <= int(fiscal_year) <= 2500:
        raise PlanningError("سال مالی معتبر نیست")
    start_period = _validate_period(start_period, fiscal_year)
    end_period = _validate_period(end_period, fiscal_year)
    if start_period > end_period:
        raise PlanningError("دوره شروع نمی‌تواند بعد از دوره پایان باشد")
    now = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        if base_scenario_id is not None:
            base = _get_scenario(conn, base_scenario_id)
            if int(base["fiscal_year"]) != int(fiscal_year):
                raise PlanningError("سناریوی مبنا باید از همان سال مالی باشد")
        try:
            cursor = conn.execute(
                """INSERT INTO planning_scenarios
                   (code, name, scenario_type, fiscal_year, start_period,
                    end_period, base_scenario_id, assumptions_json, created_by,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    name,
                    scenario_type,
                    fiscal_year,
                    start_period,
                    end_period,
                    base_scenario_id,
                    json.dumps(assumptions or {}, ensure_ascii=False),
                    _clean(username, 100),
                    now,
                    now,
                ),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise PlanningError("کد سناریو قبلاً استفاده شده است") from exc
            raise
        scenario_id = int(cursor.lastrowid)
        _audit(conn, scenario_id, username, "scenario_created")
        row = _get_scenario(conn, scenario_id)
    return _scenario_from_row(row)


def list_scenarios(
    settings: Any,
    *,
    fiscal_year: int | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if fiscal_year is not None:
        clauses.append("s.fiscal_year=?")
        params.append(fiscal_year)
    if not include_archived:
        clauses.append("s.status!='archived'")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            f"""SELECT s.*,
                       COUNT(v.id) AS value_count,
                       COALESCE(SUM(v.amount), 0) AS total_amount
                FROM planning_scenarios AS s
                LEFT JOIN planning_values AS v ON v.scenario_id=s.id
                {where}
                GROUP BY s.id
                ORDER BY s.fiscal_year DESC, s.id DESC""",
            params,
        ).fetchall()
    return [_scenario_from_row(row) for row in rows]


def get_scenario(settings: Any, scenario_id: int) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as conn:
        scenario = _scenario_from_row(_get_scenario(conn, scenario_id))
        totals = conn.execute(
            """SELECT metric, unit, COUNT(*) AS value_count,
                      COALESCE(SUM(amount), 0) AS total
               FROM planning_values WHERE scenario_id=?
               GROUP BY metric, unit ORDER BY metric, unit""",
            (scenario_id,),
        ).fetchall()
        audit_rows = conn.execute(
            """SELECT id, username, action, details_json, created_at
               FROM planning_audit WHERE scenario_id=? ORDER BY id DESC LIMIT 100""",
            (scenario_id,),
        ).fetchall()
    scenario["totals"] = [dict(row) for row in totals]
    scenario["audit"] = [
        {
            **{key: row[key] for key in ("id", "username", "action", "created_at")},
            "details": _decode_json(row["details_json"], {}),
        }
        for row in audit_rows
    ]
    return scenario


TRANSITIONS: dict[str, tuple[set[str], str]] = {
    "submit": ({"draft"}, "submitted"),
    "approve": ({"submitted"}, "approved"),
    "reject": ({"submitted"}, "draft"),
    "lock": ({"approved"}, "locked"),
    "reopen": ({"submitted", "approved", "locked"}, "draft"),
    "archive": ({"draft", "submitted", "approved", "locked"}, "archived"),
}


def transition_scenario(
    settings: Any, scenario_id: int, username: str, action: str, note: str = ""
) -> dict[str, Any]:
    action = _clean(action, 20).casefold()
    if action not in TRANSITIONS:
        raise PlanningError("عملیات وضعیت سناریو معتبر نیست")
    allowed, target = TRANSITIONS[action]
    now = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        current = _get_scenario(conn, scenario_id)
        if current["status"] not in allowed:
            raise PlanningError(
                f"عملیات {action} برای وضعیت {current['status']} مجاز نیست"
            )
        submitted_at = now if action == "submit" else current["submitted_at"]
        approved_by = _clean(username, 100) if action == "approve" else current["approved_by"]
        approved_at = now if action == "approve" else current["approved_at"]
        locked_at = now if action == "lock" else current["locked_at"]
        if target == "draft":
            submitted_at = approved_by = approved_at = locked_at = None
        conn.execute(
            """UPDATE planning_scenarios
               SET status=?, submitted_at=?, approved_by=?, approved_at=?,
                   locked_at=?, updated_at=? WHERE id=?""",
            (
                target,
                submitted_at,
                approved_by,
                approved_at,
                locked_at,
                now,
                scenario_id,
            ),
        )
        _audit(
            conn,
            scenario_id,
            username,
            f"scenario_{action}",
            {"from": current["status"], "to": target, "note": _clean(note, 1000)},
        )
        updated = _get_scenario(conn, scenario_id)
    return _scenario_from_row(updated)


DIMENSION_FIELDS = (
    "branch",
    "sales_line",
    "supervisor_id",
    "seller_id",
    "customer_id",
    "brand",
    "product_id",
)


def upsert_values(
    settings: Any,
    scenario_id: int,
    username: str,
    values: list[dict[str, Any]],
) -> dict[str, Any]:
    if not values:
        raise PlanningError("حداقل یک مقدار برنامه ارسال کنید")
    now = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        scenario = _get_scenario(conn, scenario_id)
        if scenario["status"] != "draft":
            raise PlanningError("فقط سناریوی پیش‌نویس قابل ویرایش است")
        prepared: list[tuple[Any, ...]] = []
        for value in values:
            period = _validate_period(value.get("period", ""), scenario["fiscal_year"])
            if not scenario["start_period"] <= period <= scenario["end_period"]:
                raise PlanningError("دوره مقدار خارج از بازه سناریو است")
            metric = _clean(value.get("metric"), 50).casefold()
            if metric not in PLANNING_METRICS:
                raise PlanningError(f"شاخص برنامه‌ریزی ناشناخته است: {metric}")
            try:
                amount = float(value.get("amount"))
            except (TypeError, ValueError) as exc:
                raise PlanningError("مقدار برنامه باید عدد باشد") from exc
            if not math.isfinite(amount) or abs(amount) > 1e18:
                raise PlanningError("مقدار برنامه معتبر نیست")
            dimensions = [_clean(value.get(field), 200) for field in DIMENSION_FIELDS]
            prepared.append(
                (
                    scenario_id,
                    period,
                    metric,
                    *dimensions,
                    amount,
                    _clean(value.get("unit"), 30) or "rial",
                    _clean(value.get("note"), 1000),
                    _clean(username, 100),
                    now,
                    now,
                )
            )
        conn.executemany(
            """INSERT INTO planning_values
               (scenario_id, period, metric, branch, sales_line,
                supervisor_id, seller_id, customer_id, brand, product_id,
                amount, unit, note, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(
                 scenario_id, period, metric, branch, sales_line,
                 supervisor_id, seller_id, customer_id, brand, product_id
               ) DO UPDATE SET amount=excluded.amount, unit=excluded.unit,
                 note=excluded.note, updated_at=excluded.updated_at""",
            prepared,
        )
        _audit(conn, scenario_id, username, "values_upserted", {"count": len(prepared)})
    return {"scenario_id": scenario_id, "upserted": len(prepared)}


def list_values(
    settings: Any,
    scenario_id: int,
    *,
    metric: str | None = None,
    period: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = ["scenario_id=?"]
    params: list[Any] = [scenario_id]
    if metric:
        clauses.append("metric=?")
        params.append(_clean(metric, 50).casefold())
    if period:
        clauses.append("period=?")
        params.append(_validate_period(period))
    where = " AND ".join(clauses)
    with sqlite_connection(settings.sqlite_path) as conn:
        _get_scenario(conn, scenario_id)
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM planning_values WHERE {where}", params
            ).fetchone()[0]
        )
        rows = conn.execute(
            f"""SELECT * FROM planning_values WHERE {where}
                ORDER BY period, metric, branch, sales_line, brand, product_id
                LIMIT ? OFFSET ?""",
            [*params, max(1, min(limit, 5000)), max(0, offset)],
        ).fetchall()
    return {"total": total, "items": [dict(row) for row in rows]}


def compare_scenarios(
    settings: Any, left_id: int, right_id: int, metric: str
) -> dict[str, Any]:
    metric = _clean(metric, 50).casefold()
    if metric not in PLANNING_METRICS:
        raise PlanningError("شاخص مقایسه معتبر نیست")
    with sqlite_connection(settings.sqlite_path) as conn:
        left = _scenario_from_row(_get_scenario(conn, left_id))
        right = _scenario_from_row(_get_scenario(conn, right_id))
        rows = conn.execute(
            """SELECT period,
                      COALESCE(SUM(CASE WHEN scenario_id=? THEN amount END), 0) AS left_amount,
                      COALESCE(SUM(CASE WHEN scenario_id=? THEN amount END), 0) AS right_amount
               FROM planning_values
               WHERE scenario_id IN (?, ?) AND metric=?
               GROUP BY period ORDER BY period""",
            (left_id, right_id, left_id, right_id, metric),
        ).fetchall()
    periods = []
    for row in rows:
        left_amount = float(row["left_amount"] or 0)
        right_amount = float(row["right_amount"] or 0)
        variance = left_amount - right_amount
        periods.append(
            {
                "period": row["period"],
                "left": left_amount,
                "right": right_amount,
                "variance": variance,
                "variance_percent": None
                if right_amount == 0
                else round(variance * 100 / abs(right_amount), 2),
            }
        )
    return {
        "metric": metric,
        "metric_label": PLANNING_METRICS[metric],
        "left_scenario": left,
        "right_scenario": right,
        "periods": periods,
    }

