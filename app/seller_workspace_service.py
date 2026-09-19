"""Seller-facing current routes and sellable catalog brands from NGT."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID
from zoneinfo import ZoneInfo

from app.auth_service import user_profile
from app.database import sql_connection, sqlite_connection


class SellerWorkspaceError(ValueError):
    pass


class SellerRouteNotFound(SellerWorkspaceError):
    pass


class SellerDayRouteMismatch(SellerWorkspaceError):
    pass


def _coordinate(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number and abs(number) <= 180 else None


def _seller_profile(settings: Any, username: str) -> dict[str, Any]:
    profile = user_profile(settings, username)
    if not profile or str(profile.get("role") or "").casefold() != "\u0641\u0631\u0648\u0634\u0646\u062f\u0647":
        raise SellerWorkspaceError("Seller account is required")
    if profile.get("personnel_id") is None or profile.get("supervisor_personnel_id") is None:
        raise SellerWorkspaceError("Seller organization profile is incomplete")
    return profile


def _query_rows(settings: Any, sql: str) -> list[dict[str, Any]]:
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        columns = [str(item[0]) for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _resolve_seller_day_route(settings: Any, personnel_id: int) -> dict[str, Any] | None:
    """Resolve the same path NGT uses when it creates today's seller tour.

    NGT first keeps an already-created tour, then honours an explicit active
    DayPath, and otherwise rotates VisitTemplatePaths from VisitPlans while
    excluding calendar weekends/holidays/vacations.  This query is read-only;
    it never creates an NGT tour.
    """
    sql = f"""
WITH SellerContext AS (
  SELECT TOP 1 personnel.Id AS PersonnelUniqueId,
         visit_template.Id AS VisitTemplateUniqueId,
         visit_template.CalendarTemplateUniqueId,
         CONVERT(date, GETDATE()) AS Today,
         FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR') AS TodayPDate
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS visit_template
    ON visit_template.Id = personnel.VisitTemplateUniqueId
  WHERE personnel.BackOfficeId = N'{int(personnel_id)}'
    AND ISNULL(personnel.IsRemoved, 0) = 0
    AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(visit_template.IsRemoved, 0) = 0
), PathStats AS (
  SELECT context.PersonnelUniqueId, context.VisitTemplateUniqueId,
         context.CalendarTemplateUniqueId, context.Today, context.TodayPDate,
         COUNT(path.Id) AS PathCount
  FROM SellerContext AS context
  LEFT JOIN NGT.VisitTemplatePaths AS path
    ON path.VisitTemplateUniqueId = context.VisitTemplateUniqueId
   AND ISNULL(path.IsRemoved, 0) = 0
  GROUP BY context.PersonnelUniqueId, context.VisitTemplateUniqueId,
           context.CalendarTemplateUniqueId, context.Today, context.TodayPDate
)
SELECT resolved.PathId, path.PathTitle, context.TodayPDate AS RoutePDate,
       resolved.RouteSource
FROM PathStats AS context
OUTER APPLY (
  SELECT TOP 1 tour.VisitTemplatePathUniqueId AS PathId
  FROM NGT.Tours AS tour
  WHERE tour.AgentUniqueId = context.PersonnelUniqueId
    AND tour.TourPDate = context.TodayPDate
    AND tour.VisitTemplatePathUniqueId IS NOT NULL
    AND ISNULL(tour.IsRemoved, 0) = 0
  ORDER BY CASE WHEN tour.EndTime IS NULL THEN 0 ELSE 1 END,
           tour.StartTime DESC, tour.LastUpdate DESC
) AS existing_tour
OUTER APPLY (
  SELECT TOP 1 day_path.VisitTemplatePathUniqueId AS PathId
  FROM NGT.DayPaths AS day_path
  WHERE day_path.PersonnelUniqueId = context.PersonnelUniqueId
    AND day_path.ActivePDate = context.TodayPDate
    AND ISNULL(day_path.IsActive, 0) = 1
    AND ISNULL(day_path.IsRemoved, 0) = 0
  ORDER BY day_path.LastUpdate DESC, day_path.CreatedDate DESC
) AS explicit_day_path
OUTER APPLY (
  SELECT TOP 1 visit_plan.Id, CONVERT(date, visit_plan.StartDate) AS StartDate
  FROM NGT.VisitPlans AS visit_plan
  WHERE visit_plan.PersonnelUniqueId = context.PersonnelUniqueId
    AND ISNULL(visit_plan.IsRemoved, 0) = 0
  ORDER BY visit_plan.LastUpdate DESC, visit_plan.CreatedDate DESC
) AS visit_plan
LEFT JOIN NGT.CalendarTemplates AS calendar_template
  ON calendar_template.Id = context.CalendarTemplateUniqueId
 AND ISNULL(calendar_template.IsRemoved, 0) = 0
OUTER APPLY (
  SELECT TOP 1 ISNULL(app_setting.HolidayShiftEnabled, 0) AS HolidayShiftEnabled
  FROM NGT.AppSettings AS app_setting
  WHERE ISNULL(app_setting.IsRemoved, 0) = 0
  ORDER BY app_setting.LastUpdate DESC, app_setting.CreatedDate DESC
) AS settings
OUTER APPLY (
  SELECT CASE ((DATEDIFF(DAY, CONVERT(date, '19000107'), context.Today) % 7) + 7) % 7
           WHEN 0 THEN ISNULL(calendar_template.Sunday, 0)
           WHEN 1 THEN ISNULL(calendar_template.Monday, 0)
           WHEN 2 THEN ISNULL(calendar_template.Tuesday, 0)
           WHEN 3 THEN ISNULL(calendar_template.Wednesday, 0)
           WHEN 4 THEN ISNULL(calendar_template.Thursday, 0)
           WHEN 5 THEN ISNULL(calendar_template.Friday, 0)
           WHEN 6 THEN ISNULL(calendar_template.Saturday, 0)
         END AS IsCalendarOff,
         CASE WHEN ISNULL(settings.HolidayShiftEnabled, 0) = 1 AND (
           EXISTS (
             SELECT 1 FROM NGT.CalendarTemplateHolidays AS holiday
             WHERE holiday.CalendarTemplateUniqueId = context.CalendarTemplateUniqueId
               AND CONVERT(date, holiday.HolidayDate) = context.Today
               AND ISNULL(holiday.IsRemoved, 0) = 0
           ) OR EXISTS (
             SELECT 1 FROM NGT.VisitPlanVacations AS vacation
             WHERE vacation.VisitPlanUniqueId = visit_plan.Id
               AND CONVERT(date, vacation.VacationDate) = context.Today
               AND ISNULL(vacation.IsRemoved, 0) = 0
           )
         ) THEN 1 ELSE 0 END AS IsShiftOff
) AS today_status
OUTER APPLY (
  SELECT COUNT(*) AS WorkingDayCount
  FROM (
    SELECT DATEADD(DAY, number.RowNo - 1, visit_plan.StartDate) AS WorkDate
    FROM (
      SELECT ROW_NUMBER() OVER (ORDER BY first_object.object_id, second_object.object_id) AS RowNo
      FROM sys.all_objects AS first_object
      CROSS JOIN sys.all_objects AS second_object
    ) AS number
    WHERE visit_plan.StartDate IS NOT NULL
      AND number.RowNo <= DATEDIFF(DAY, visit_plan.StartDate, context.Today) + 1
  ) AS work_day
  WHERE CASE ((DATEDIFF(DAY, CONVERT(date, '19000107'), work_day.WorkDate) % 7) + 7) % 7
          WHEN 0 THEN ISNULL(calendar_template.Sunday, 0)
          WHEN 1 THEN ISNULL(calendar_template.Monday, 0)
          WHEN 2 THEN ISNULL(calendar_template.Tuesday, 0)
          WHEN 3 THEN ISNULL(calendar_template.Wednesday, 0)
          WHEN 4 THEN ISNULL(calendar_template.Thursday, 0)
          WHEN 5 THEN ISNULL(calendar_template.Friday, 0)
          WHEN 6 THEN ISNULL(calendar_template.Saturday, 0)
        END = 0
    AND NOT (
      ISNULL(settings.HolidayShiftEnabled, 0) = 1 AND (
        EXISTS (
          SELECT 1 FROM NGT.CalendarTemplateHolidays AS holiday
          WHERE holiday.CalendarTemplateUniqueId = context.CalendarTemplateUniqueId
            AND CONVERT(date, holiday.HolidayDate) = CONVERT(date, work_day.WorkDate)
            AND ISNULL(holiday.IsRemoved, 0) = 0
        ) OR EXISTS (
          SELECT 1 FROM NGT.VisitPlanVacations AS vacation
          WHERE vacation.VisitPlanUniqueId = visit_plan.Id
            AND CONVERT(date, vacation.VacationDate) = CONVERT(date, work_day.WorkDate)
            AND ISNULL(vacation.IsRemoved, 0) = 0
        )
      )
    )
) AS working_days
OUTER APPLY (
  SELECT TOP 1 scheduled_path.Id AS PathId
  FROM NGT.VisitTemplatePaths AS scheduled_path
  WHERE scheduled_path.VisitTemplateUniqueId = context.VisitTemplateUniqueId
    AND scheduled_path.RowIndex = 1 + ((working_days.WorkingDayCount - 1) % NULLIF(context.PathCount, 0))
    AND visit_plan.StartDate <= context.Today
    AND working_days.WorkingDayCount > 0
    AND ISNULL(today_status.IsCalendarOff, 0) = 0
    AND ISNULL(today_status.IsShiftOff, 0) = 0
    AND ISNULL(scheduled_path.IsRemoved, 0) = 0
) AS scheduled_path
CROSS APPLY (
  SELECT COALESCE(existing_tour.PathId, explicit_day_path.PathId, scheduled_path.PathId) AS PathId,
         CASE
           WHEN existing_tour.PathId IS NOT NULL THEN N'NGT.Tours'
           WHEN explicit_day_path.PathId IS NOT NULL THEN N'NGT.DayPaths'
           WHEN scheduled_path.PathId IS NOT NULL THEN N'NGT.VisitPlans'
           ELSE NULL
         END AS RouteSource
) AS resolved
LEFT JOIN NGT.VisitTemplatePaths AS path ON path.Id = resolved.PathId
WHERE resolved.PathId IS NOT NULL
""".strip()
    rows = _query_rows(settings, sql)
    if not rows or not rows[0].get("PathId"):
        return None
    row = rows[0]
    return {
        "id": str(row["PathId"]),
        "title": str(row.get("PathTitle") or "").strip(),
        "date": str(row.get("RoutePDate") or "").strip(),
        "source": str(row.get("RouteSource") or "").strip(),
    }


def _resolve_seller_location_policy(settings: Any, personnel_id: int) -> dict[str, Any]:
    """Read the effective NGT visit controls for this seller and device."""
    sql = f"""
SELECT TOP 1
       ISNULL(device_settings.CheckDistance, 0) AS CheckDistance,
       device_settings.MaxDistance,
       COALESCE(base_value.BaseValueName, public_value.PublicValueName, N'') AS CheckDistanceTypeName,
       ISNULL(public_value.PublicValueName, N'') AS CheckDistanceTypeCode,
       ISNULL(device_settings.EnableGPS, 0) AS EnableGPS,
       ISNULL(device_settings.SetCustomerLocation, 0) AS SetCustomerLocation,
       ISNULL(device_settings.AllowRegisterNewCustomer, 0) AS AllowRegisterNewCustomer,
       ISNULL(device_settings.ViewCustomerInvoicesReport, 0) AS ViewCustomerInvoicesReport,
       ISNULL(device_settings.ViewCustomerCardexReport, 0) AS ViewCustomerCardexReport,
       ISNULL(device_settings.ViewCustomerOpenInvoicesReport, 0) AS ViewCustomerOpenInvoicesReport,
       ISNULL(device_settings.ViewCustomerSaleHistoryReport, 0) AS ViewCustomerSaleHistoryReport,
       ISNULL(device_settings.ViewCustomerFinanceData, 0) AS ViewCustomerFinanceData,
       ISNULL(app_setting.AllowEditCustomer, 0) AS AllowEditCustomer,
       ISNULL(device_settings.MandatoryCustomerVisit, ISNULL(app_setting.MandatoryCustomerVisit, 0)) AS MandatoryCustomerVisit,
       app_setting.EditCustomerFields,
       app_setting.InsertCustomerFields
FROM NGT.Users AS users
INNER JOIN NGT.DeviceUsers AS device_user
  ON device_user.UserUniqueId = users.Id
 AND ISNULL(device_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceSettings AS device_settings
  ON device_settings.Id = device_user.DeviceSettingUniqueId
 AND ISNULL(device_settings.IsRemoved, 0) = 0
LEFT JOIN NGT.BaseValues AS base_value
  ON base_value.Id = device_settings.CheckDistanceTypeUniqueId
 AND ISNULL(base_value.IsRemoved, 0) = 0
LEFT JOIN NGT.PublicValues AS public_value
  ON public_value.Id = device_settings.CheckDistanceTypeUniqueId
OUTER APPLY (
  SELECT TOP 1 current_setting.AllowEditCustomer, current_setting.MandatoryCustomerVisit,
         current_setting.EditCustomerFields, current_setting.InsertCustomerFields
  FROM NGT.AppSettings AS current_setting
  WHERE ISNULL(current_setting.IsRemoved, 0) = 0
  ORDER BY current_setting.LastUpdate DESC, current_setting.CreatedDate DESC
) AS app_setting
WHERE users.BackOfficePersonnelId = {int(personnel_id)}
  AND ISNULL(users.IsRemoved, 0) = 0
  AND ISNULL(users.IsActive, 1) = 1
ORDER BY device_user.LastUpdate DESC, device_settings.LastUpdate DESC
""".strip()
    rows = _query_rows(settings, sql)
    row = rows[0] if rows else {}
    required_fields = _configured_customer_fields(row.get("EditCustomerFields"))
    ngt_distance_enabled = bool(row.get("CheckDistance"))
    start_distance_enforced = ngt_distance_enabled and bool(
        getattr(settings, "previsit_start_distance_check_enabled", False)
    )
    return {
        # `enabled` preserves the live NGT rule. `enforced` reports whether
        # NeginAI currently applies that rule at the start-visit boundary.
        "enabled": ngt_distance_enabled,
        "max_distance_meters": int(row["MaxDistance"]) if row.get("MaxDistance") is not None else None,
        "scope": str(row.get("CheckDistanceTypeName") or "").strip(),
        "scope_code": str(row.get("CheckDistanceTypeCode") or "").strip(),
        "enforced": start_distance_enforced,
        "mode": (
            "enforced_at_start" if start_distance_enforced
            else "suspended_for_testing" if ngt_distance_enabled
            else "disabled"
        ),
        "enforcement_stage": "start" if start_distance_enforced else "disabled",
        "gps_enabled": bool(row.get("EnableGPS")) or start_distance_enforced,
        "set_customer_location": bool(row.get("SetCustomerLocation")),
        "allow_register_new_customer": bool(row.get("AllowRegisterNewCustomer")),
        "allow_edit_customer": bool(row.get("AllowEditCustomer")),
        "mandatory_customer_visit": bool(row.get("MandatoryCustomerVisit")),
        "required_customer_fields": required_fields,
        "insert_customer_fields": _configured_customer_fields(row.get("InsertCustomerFields")),
        "reports": {
            "invoices": bool(row.get("ViewCustomerInvoicesReport")),
            "cardex": bool(row.get("ViewCustomerCardexReport")),
            "open_invoices": bool(row.get("ViewCustomerOpenInvoicesReport")),
            "sale_history": bool(row.get("ViewCustomerSaleHistoryReport")),
            "finance": bool(row.get("ViewCustomerFinanceData")),
        },
        "source": "NGT.DeviceUsers -> NGT.DeviceSettings + NGT.AppSettings",
    }


def _configured_customer_fields(value: Any) -> list[str]:
    """Normalize NGT's JSON/comma-delimited mandatory customer-field setting."""
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        values = value
    else:
        text = str(value).strip()
        try:
            decoded = json.loads(text)
            values = decoded if isinstance(decoded, list) else [decoded]
        except (json.JSONDecodeError, TypeError):
            values = text.replace(";", ",").replace("|", ",").split(",")
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _ngt_visit_outcome_data(settings: Any) -> dict[str, Any]:
    rows = _query_rows(settings, """
SELECT CONVERT(varchar(36), reason.Id) AS ReasonId,
       reason.NoSaleReasonName AS ReasonName,
       CONVERT(varchar(36), reason.NoSaleReasonTypeUniqueId) AS ReasonTypeId,
       COALESCE(public_type.PublicValueName, base_type.BaseValueName, N'') AS ReasonTypeName
FROM NGT.NoSaleReasons AS reason
LEFT JOIN NGT.BaseValues AS base_type
  ON base_type.Id = reason.NoSaleReasonTypeUniqueId
 AND ISNULL(base_type.IsRemoved, 0) = 0
LEFT JOIN NGT.PublicValues AS public_type
  ON public_type.Id = reason.NoSaleReasonTypeUniqueId
WHERE ISNULL(reason.IsRemoved, 0) = 0
  AND ISNULL(reason.ShowForNgt, 0) = 1
ORDER BY COALESCE(public_type.PublicValueName, base_type.BaseValueName, N''), reason.NoSaleReasonName
""".strip())
    statuses = _query_rows(settings, """
SELECT CONVERT(varchar(36), status.Id) AS VisitStatusId,
       status.BaseValueName AS VisitStatusName,
       public_status.PublicValueName AS VisitStatusCode
FROM NGT.BaseValues AS status
INNER JOIN NGT.PublicValues AS public_status ON public_status.Id = status.Id
WHERE ISNULL(status.IsRemoved, 0) = 0
  AND public_status.PublicValueName IN (
      N'VisitStatusTypes.NoOrder', N'VisitStatusTypes.NoVisit',
      N'VisitStatusTypes.Determind', N'VisitStatusTypes.Undetermind'
  )
""".strip())
    status_by_code = {
        str(row.get("VisitStatusCode") or "").strip(): str(row.get("VisitStatusId") or "")
        for row in statuses
    }
    reasons = {"no_order": [], "no_visit": []}
    for row in rows:
        type_name = str(row.get("ReasonTypeName") or "").strip()
        outcome = "no_visit" if type_name.endswith(".NoVisit") or "ظˆغŒط²غŒطھ" in type_name else "no_order"
        reasons[outcome].append({
            "id": str(row.get("ReasonId") or ""),
            "title": str(row.get("ReasonName") or "").strip(),
            "type_id": str(row.get("ReasonTypeId") or ""),
        })
    return {
        "reasons": reasons,
        "visit_status_ids": {
            "order": status_by_code.get("VisitStatusTypes.Determind") or status_by_code.get("VisitStatusTypes.Undetermind") or "",
            "no_order": status_by_code.get("VisitStatusTypes.NoOrder") or "",
            "no_visit": status_by_code.get("VisitStatusTypes.NoVisit") or "",
        },
    }


def seller_visit_policy(settings: Any, username: str, path_id: str, customer_id: str) -> dict[str, Any]:
    route, customer = _assigned_route_customer(settings, username, path_id, customer_id)
    policy = route.get("visit_location_policy") or {}
    outcome_data = _ngt_visit_outcome_data(settings)
    effective_customer = dict(customer)
    with sqlite_connection(settings.sqlite_path) as connection:
        draft_row = connection.execute(
            "SELECT update_json FROM previsit_customer_update_drafts WHERE username = ? AND route_id = ? AND customer_id = ?",
            (username, str(route["route"]["id"]), str(customer["id"])),
        ).fetchone()
    if draft_row:
        draft = json.loads(str(draft_row["update_json"] or "{}"))
        draft_to_customer = {"customer_code": "code"}
        for key, value in draft.items():
            effective_customer[draft_to_customer.get(key, key)] = value
    missing = []
    aliases = {
        "phone": "phone", "mobile": "mobile", "store_name": "store_name", "storename": "store_name",
        "address": "address", "customer_code": "code", "customercode": "code",
        "latitude": "latitude", "longitude": "longitude",
    }
    for configured in policy.get("required_customer_fields") or []:
        key = aliases.get(str(configured).replace(" ", "").replace("-", "_").casefold())
        if key and effective_customer.get(key) in (None, ""):
            missing.append(configured)
    blockers = []
    order_blockers = []
    if missing:
        order_blockers.append("ط§ط·ظ„ط§ط¹ط§طھ ط§ط¬ط¨ط§ط±غŒ ظ…ط´طھط±غŒ ط¨ط§غŒط¯ ظ¾غŒط´ ط§ط² ط³ظپط§ط±ط´â€Œع¯غŒط±غŒ طھع©ظ…غŒظ„ ط´ظˆط¯")
    if policy.get("enforced") and not effective_customer.get("location_check_exempt") and (
        effective_customer.get("latitude") is None or effective_customer.get("longitude") is None
    ):
        blockers.append("ظ…ظˆظ‚ط¹غŒطھ ظ…ط´طھط±غŒ ط¨ط±ط§غŒ ع©ظ†طھط±ظ„ ظپط§طµظ„ظ‡ ط«ط¨طھ ظ†ط´ط¯ظ‡ ط§ط³طھ")
        order_blockers.append("ظ…ظˆظ‚ط¹غŒطھ ظ…ط´طھط±غŒ ط¨ط±ط§غŒ ع©ظ†طھط±ظ„ ظپط§طµظ„ظ‡ ط«ط¨طھ ظ†ط´ط¯ظ‡ ط§ط³طھ")
    return {
        "route": route["route"],
        "customer": {
            "id": customer["id"], "name": customer.get("name"), "store_name": customer.get("store_name"),
            "has_location": effective_customer.get("latitude") is not None and effective_customer.get("longitude") is not None,
            "location_check_exempt": bool(customer.get("location_check_exempt")),
        },
        "controls": policy,
        "missing_required_fields": missing,
        "start_blockers": blockers,
        "order_blockers": order_blockers,
        "can_start_visit": not blockers,
        **outcome_data,
        "source": "live NGT seller, device, app and no-sale settings",
    }


def resolve_ngt_visit_outcome(
    settings: Any, username: str, path_id: str, customer_id: str, outcome: str, reason_id: str,
) -> dict[str, Any]:
    policy = seller_visit_policy(settings, username, path_id, customer_id)
    reason = next(
        (item for item in policy["reasons"].get(outcome, []) if item["id"].casefold() == str(reason_id).casefold()),
        None,
    )
    if reason is None:
        raise SellerWorkspaceError("ط¯ظ„غŒظ„ ط§ظ†طھط®ط§ط¨â€Œط´ط¯ظ‡ ط¯ط± NGT ظپط¹ط§ظ„ ظ†غŒط³طھ غŒط§ ط¨ظ‡ ط§غŒظ† ظ†ظˆط¹ ظ†طھغŒط¬ظ‡ ظˆغŒط²غŒطھ طھط¹ظ„ظ‚ ظ†ط¯ط§ط±ط¯")
    return {
        "reason_id": reason["id"],
        "reason": reason["title"],
        "visit_status_id": policy["visit_status_ids"].get(outcome) or None,
    }


def _seller_all_routes_test_override_enabled(
    settings: Any,
    username: str,
    *,
    now: datetime | None = None,
) -> bool:
    configured_username = str(
        getattr(settings, "previsit_test_all_routes_username", "") or ""
    ).strip()
    expires_at_text = str(
        getattr(settings, "previsit_test_all_routes_until", "") or ""
    ).strip()
    if (
        not configured_username
        or configured_username.casefold() != str(username or "").strip().casefold()
        or not expires_at_text
    ):
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_text)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc) <= expires_at.astimezone(timezone.utc)


def require_seller_day_route(settings: Any, username: str, path_id: str) -> dict[str, Any]:
    profile = _seller_profile(settings, username)
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerDayRouteMismatch("ظ…ط³غŒط± ط§ظ†طھط®ط§ط¨â€Œط´ط¯ظ‡ ظ…ط¹طھط¨ط± ظ†غŒط³طھ") from exc
    if _seller_all_routes_test_override_enabled(settings, username):
        assigned_route = next(
            (
                route
                for route in seller_routes(settings, username).get("routes", [])
                if str(route.get("id") or "").casefold() == clean_path_id.casefold()
            ),
            None,
        )
        if not assigned_route:
            raise SellerDayRouteMismatch("ظ…ط³غŒط± ط§ظ†طھط®ط§ط¨â€Œط´ط¯ظ‡ ط¬ط²ظˆ ظ…ط³غŒط±ظ‡ط§غŒ طھط®طµغŒطµâ€ŒغŒط§ظپطھظ‡ ظپط±ظˆط´ظ†ط¯ظ‡ ظ†غŒط³طھ")
        return {
            "id": assigned_route["id"],
            "title": assigned_route["title"],
            "date": "",
            "source": "temporary_test_override",
        }
    assignment = _resolve_seller_day_route(settings, int(profile["personnel_id"]))
    if not assignment:
        raise SellerDayRouteMismatch("ط¨ط±ط§غŒ ط§ظ…ط±ظˆط² ظ…ط³غŒط± ط±ظˆط² ظپط¹ط§ظ„غŒ ط¯ط± NGT طھط¹غŒغŒظ† ظ†ط´ط¯ظ‡ ط§ط³طھ")
    if str(assignment["id"]).casefold() != clean_path_id.casefold():
        title = str(assignment.get("title") or "ظ…ط³غŒط± طھط¹غŒغŒظ†â€Œط´ط¯ظ‡")
        raise SellerDayRouteMismatch(f"ظپظ‚ط· ظ…ط³غŒط± ط±ظˆط² NGT ظ‚ط§ط¨ظ„ ط´ط±ظˆط¹ ط§ط³طھ: {title}")
    return assignment


def _seller_work_calendar_summary(settings: Any, personnel_id: int) -> dict[str, Any] | None:
    """Return current Persian-month workday counts from NGT calendar semantics used by route rotation."""
    sql = f"""
WITH SellerContext AS (
  SELECT TOP 1 personnel.Id AS PersonnelUniqueId,
         visit_template.CalendarTemplateUniqueId,
         CONVERT(date, GETDATE()) AS Today,
         FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR') AS TodayPDate,
         LEFT(FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR'), 7) AS MonthKey
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS visit_template
    ON visit_template.Id = personnel.VisitTemplateUniqueId
  WHERE personnel.BackOfficeId = N'{int(personnel_id)}'
    AND ISNULL(personnel.IsRemoved, 0) = 0
    AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(visit_template.IsRemoved, 0) = 0
)
SELECT context.TodayPDate,
       context.MonthKey,
       context.CalendarTemplateUniqueId,
       ISNULL(workdays.TotalWorkingDays, 0) AS TotalWorkingDays,
       ISNULL(workdays.ElapsedWorkingDays, 0) AS ElapsedWorkingDays,
       ISNULL(workdays.RemainingWorkingDays, 0) AS RemainingWorkingDays,
       ISNULL(workdays.IsWorkingDay, 0) AS IsWorkingDay
FROM SellerContext AS context
LEFT JOIN NGT.CalendarTemplates AS calendar_template
  ON calendar_template.Id = context.CalendarTemplateUniqueId
 AND ISNULL(calendar_template.IsRemoved, 0) = 0
OUTER APPLY (
  SELECT TOP 1 visit_plan.Id
  FROM NGT.VisitPlans AS visit_plan
  WHERE visit_plan.PersonnelUniqueId = context.PersonnelUniqueId
    AND ISNULL(visit_plan.IsRemoved, 0) = 0
  ORDER BY visit_plan.LastUpdate DESC, visit_plan.CreatedDate DESC
) AS visit_plan
OUTER APPLY (
  SELECT TOP 1 ISNULL(app_setting.HolidayShiftEnabled, 0) AS HolidayShiftEnabled
  FROM NGT.AppSettings AS app_setting
  WHERE ISNULL(app_setting.IsRemoved, 0) = 0
  ORDER BY app_setting.LastUpdate DESC, app_setting.CreatedDate DESC
) AS settings
OUTER APPLY (
  SELECT COUNT(*) AS TotalWorkingDays,
         SUM(CASE WHEN work_day.WorkDate <= work_day.TodayDate THEN 1 ELSE 0 END) AS ElapsedWorkingDays,
         SUM(CASE WHEN work_day.WorkDate > work_day.TodayDate THEN 1 ELSE 0 END) AS RemainingWorkingDays,
         SUM(CASE WHEN work_day.WorkDate = work_day.TodayDate THEN 1 ELSE 0 END) AS IsWorkingDay
  FROM (
    SELECT DATEADD(DAY, numbers.OffsetDay, context.Today) AS WorkDate,
           context.Today AS TodayDate
    FROM (
      SELECT TOP (81)
             ROW_NUMBER() OVER (ORDER BY first_object.object_id, second_object.object_id) - 41 AS OffsetDay
      FROM sys.all_objects AS first_object
      CROSS JOIN sys.all_objects AS second_object
    ) AS numbers
  ) AS work_day
  WHERE LEFT(FORMAT(work_day.WorkDate, 'yyyy/MM/dd', 'fa-IR'), 7) = context.MonthKey
    AND CASE ((DATEDIFF(DAY, CONVERT(date, '19000107'), work_day.WorkDate) % 7) + 7) % 7
          WHEN 0 THEN ISNULL(calendar_template.Sunday, 0)
          WHEN 1 THEN ISNULL(calendar_template.Monday, 0)
          WHEN 2 THEN ISNULL(calendar_template.Tuesday, 0)
          WHEN 3 THEN ISNULL(calendar_template.Wednesday, 0)
          WHEN 4 THEN ISNULL(calendar_template.Thursday, 0)
          WHEN 5 THEN ISNULL(calendar_template.Friday, 0)
          WHEN 6 THEN ISNULL(calendar_template.Saturday, 0)
        END = 0
    AND NOT (
      ISNULL(settings.HolidayShiftEnabled, 0) = 1 AND (
        EXISTS (
          SELECT 1
          FROM NGT.CalendarTemplateHolidays AS holiday
          WHERE holiday.CalendarTemplateUniqueId = context.CalendarTemplateUniqueId
            AND CONVERT(date, holiday.HolidayDate) = CONVERT(date, work_day.WorkDate)
            AND ISNULL(holiday.IsRemoved, 0) = 0
        )
        OR EXISTS (
          SELECT 1
          FROM NGT.VisitPlanVacations AS vacation
          WHERE vacation.VisitPlanUniqueId = visit_plan.Id
            AND CONVERT(date, vacation.VacationDate) = CONVERT(date, work_day.WorkDate)
            AND ISNULL(vacation.IsRemoved, 0) = 0
        )
      )
    )
) AS workdays
""".strip()
    rows = _query_rows(settings, sql)
    if not rows or rows[0].get("CalendarTemplateUniqueId") is None:
        return None
    row = rows[0]
    return {
        "date": str(row.get("TodayPDate") or "").strip(),
        "month": str(row.get("MonthKey") or "").strip(),
        "elapsed_working_days": int(row.get("ElapsedWorkingDays") or 0),
        "remaining_working_days": int(row.get("RemainingWorkingDays") or 0),
        "total_working_days": int(row.get("TotalWorkingDays") or 0),
        "is_working_day": bool(row.get("IsWorkingDay")),
        "source": "NGT.CalendarTemplates+CalendarTemplateHolidays+VisitPlanVacations",
    }



def seller_routes(settings: Any, username: str) -> dict[str, Any]:
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    current_assignment_sql = f"""
SELECT vt.VisitTemplateName, vtp.Id AS PathId, vtp.PathTitle, vtp.RowIndex, vtp.LastUpdate,
       ISNULL(customer_stats.CustomerCount, 0) AS CustomerCount
FROM NGT.Personnels AS p
INNER JOIN NGT.VisitTemplates AS vt ON vt.Id = p.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS vtp ON vtp.VisitTemplateUniqueId = vt.Id
OUTER APPLY (
  SELECT COUNT(*) AS CustomerCount
  FROM (
    SELECT primary_link.CustomerUniqueId
    FROM NGT.VisitTemplatePathCustomers AS primary_link
    INNER JOIN NGT.Customers AS primary_customer
      ON primary_customer.Id = primary_link.CustomerUniqueId
    WHERE primary_link.VisitTemplatePathUniqueId = vtp.Id
      AND ISNULL(primary_link.IsRemoved, 0) = 0
      AND ISNULL(primary_customer.IsRemoved, 0) = 0
      AND ISNULL(primary_customer.IsActive, 1) = 1
    UNION
    SELECT secondary_link.CustomerUniqueId
    FROM NGT.VisitTemplatePathSecondaryCustomers AS secondary_link
    INNER JOIN NGT.Customers AS secondary_customer
      ON secondary_customer.Id = secondary_link.CustomerUniqueId
    WHERE secondary_link.VisitTemplatePathUniqueId = vtp.Id
      AND ISNULL(secondary_link.IsRemoved, 0) = 0
      AND ISNULL(secondary_customer.IsRemoved, 0) = 0
      AND ISNULL(secondary_customer.IsActive, 1) = 1
  ) AS assigned_customer
) AS customer_stats
WHERE p.BackOfficeId = N'{personnel_id}'
  AND ISNULL(p.IsRemoved, 0) = 0
  AND ISNULL(p.PersonnelIsActive, 1) = 1
  AND ISNULL(vt.IsRemoved, 0) = 0
  AND ISNULL(vtp.IsRemoved, 0) = 0
ORDER BY vtp.RowIndex, vtp.PathTitle
""".strip()
    assigned = _query_rows(settings, current_assignment_sql)
    resolved_day_route = _resolve_seller_day_route(settings, personnel_id)
    work_calendar = _seller_work_calendar_summary(settings, personnel_id)
    location_policy = _resolve_seller_location_policy(settings, personnel_id)
    test_all_routes_override = _seller_all_routes_test_override_enabled(settings, username)
    resolved_day_route_id = str((resolved_day_route or {}).get("id") or "").casefold()
    routes = [
        {
            "id": str(row["PathId"]),
            "title": str(row["PathTitle"] or "").strip(),
            "row_index": row["RowIndex"],
            "updated_at": str(row["LastUpdate"] or ""),
            "customer_count": int(row["CustomerCount"] or 0),
            "source": "current_visit_template",
            "is_day_route": str(row["PathId"]).casefold() == resolved_day_route_id,
            "can_start_day_route": test_all_routes_override or str(row["PathId"]).casefold() == resolved_day_route_id,
            "can_start_visit": test_all_routes_override or str(row["PathId"]).casefold() == resolved_day_route_id,
        }
        for row in assigned if str(row["PathTitle"] or "").strip()
    ]
    day_route = next((route for route in routes if route["is_day_route"]), None)
    if day_route and resolved_day_route:
        resolved_day_route = {
            **resolved_day_route,
            "title": day_route["title"],
        }
    else:
        resolved_day_route = None
    result = {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "visit_template": str(assigned[0]["VisitTemplateName"] or "") if assigned else "",
        "routes": routes,
        "day_route": resolved_day_route,
        "work_calendar": work_calendar,
        "day_route_status": (
            "temporary_all_routes"
            if test_all_routes_override
            else "assigned" if resolved_day_route else "not_assigned"
        ),
        "test_all_routes_override": test_all_routes_override,
        "visit_location_policy": location_policy,
        "source": "NGT.Personnels.VisitTemplateUniqueId",
        "live_assignment": True,
    }
    try:
        from app.operational_notification_service import enqueue_route_assignment_observation
        enqueue_route_assignment_observation(settings, username, result)
    except Exception:
        # Alerting must never block the seller workspace.
        pass
    return result


def _route_visit_resolutions(settings: Any, username: str, path_id: str) -> dict[str, dict[str, Any]]:
    """Return today's latest completed visit for every customer in one route."""
    today = datetime.now(ZoneInfo("Asia/Tehran")).date()
    with sqlite_connection(settings.sqlite_path) as connection:
        rows = connection.execute(
            """SELECT visits.id, visits.customer_id, visits.status, visits.started_at, visits.ended_at,
                      drafts.outcome, drafts.outcome_reason,
                      (SELECT COUNT(*) FROM previsit_saved_requests AS saved
                       WHERE saved.visit_id = visits.id AND saved.username = visits.username) AS saved_request_count
               FROM previsit_visits AS visits
               INNER JOIN previsit_drafts AS drafts ON drafts.visit_id = visits.id AND drafts.username = visits.username
               WHERE visits.username = ? AND visits.route_id = ? AND visits.status = 'completed'
               ORDER BY visits.started_at DESC""",
            (username, str(path_id)),
        ).fetchall()
    resolutions: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        try:
            started_at = datetime.fromisoformat(str(row["started_at"]).replace("Z", "+00:00"))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if started_at.astimezone(ZoneInfo("Asia/Tehran")).date() != today:
                continue
        except (TypeError, ValueError):
            continue
        customer_id = str(row["customer_id"])
        if customer_id in resolutions:
            continue
        resolutions[customer_id] = {
            "status": "completed",
            "outcome": str(row.get("outcome") or ""),
            "outcome_reason": str(row.get("outcome_reason") or ""),
            "saved_request_count": int(row.get("saved_request_count") or 0),
            "ended_at": str(row.get("ended_at") or ""),
        }
    return resolutions


def seller_route_customers(settings: Any, username: str, path_id: str) -> dict[str, Any]:
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerRouteNotFound("Current seller route was not found") from exc

    customers_sql = f"""
SELECT path.Id AS PathId, path.PathTitle, assigned.RowIndex,
       customer.BackOfficeId, customer.CustomerCode, customer.CustomerName,
       customer.StoreName, customer.Address, customer.Phone, customer.Mobile,
       customer.Latitude, customer.Longitude, customer.IgnoreLocation, customer.Alarm,
       backoffice_customer.BedCredit, backoffice_customer.AsnCredit,
       backoffice_customer.HasBedCredit, backoffice_customer.HasAsnCredit,
       COALESCE(credit_snapshot.RemBedCredit, backoffice_customer.BedCredit) AS RemBedCredit,
       COALESCE(credit_snapshot.RemAsnCredit, backoffice_customer.AsnCredit) AS RemAsnCredit,
       credit_snapshot.RemAmount AS CustomerRemaining,
       credit_snapshot.OpenChequeCount, credit_snapshot.OpenChequeAmount,
       credit_snapshot.ReturnChequeCount, credit_snapshot.ReturnChequeAmount,
       credit_snapshot.DcRef AS CreditDcRef, credit_snapshot.LastUpdate AS CreditLastUpdate,
       ISNULL(cardex.CustomerCardexBalance, 0) AS CustomerCardexBalance,
       ISNULL(open_invoices.OpenInvoiceRemaining, 0) AS OpenInvoiceRemaining,
       ISNULL(open_invoices.OpenInvoiceCount, 0) AS OpenInvoiceCount
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
INNER JOIN (
  SELECT VisitTemplatePathUniqueId, CustomerUniqueId, MIN(RowIndex) AS RowIndex
  FROM (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex
    FROM NGT.VisitTemplatePathCustomers
    WHERE ISNULL(IsRemoved, 0) = 0
    UNION ALL
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex
    FROM NGT.VisitTemplatePathSecondaryCustomers
    WHERE ISNULL(IsRemoved, 0) = 0
  ) AS all_links
  GROUP BY VisitTemplatePathUniqueId, CustomerUniqueId
) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
LEFT JOIN GNR.tblCust AS backoffice_customer
  ON backoffice_customer.ID = TRY_CONVERT(int, customer.BackOfficeId)
OUTER APPLY (
  SELECT TOP 1 order_header.DcRefSDS
  FROM NGT.CustomerCallOrders AS order_header
  WHERE TRY_CONVERT(int, order_header.DealerRefSDS) = {personnel_id}
    AND order_header.DcRefSDS IS NOT NULL
    AND ISNULL(order_header.IsRemoved, 0) = 0
  ORDER BY order_header.LastUpdate DESC
) AS recent_order_context
OUTER APPLY (
  SELECT TOP 1 info.RemAmount, info.RemBedCredit, info.RemAsnCredit,
         info.OpenChequeCount, info.OpenChequeAmount,
         info.ReturnChequeCount, info.ReturnChequeAmount,
         info.DcRef, info.LastUpdate
  FROM Acc.tblCustRemInfo AS info
  WHERE info.CustRef = TRY_CONVERT(int, customer.BackOfficeId)
  ORDER BY CASE WHEN info.DcRef = recent_order_context.DcRefSDS THEN 0 ELSE 1 END,
           info.LastUpdate DESC, info.DcRef
) AS credit_snapshot
OUTER APPLY (
  SELECT SUM(balance.Balance) AS CustomerCardexBalance
  FROM Acc.vwCustomerBalance AS balance
  WHERE balance.CustRef = TRY_CONVERT(int, customer.BackOfficeId)
) AS cardex
OUTER APPLY (
  SELECT SUM(invoice.RemainingAmount) AS OpenInvoiceRemaining,
         COUNT(*) AS OpenInvoiceCount
  FROM (
    SELECT sale.SaleId, MAX(sale.RemainingAmount) AS RemainingAmount
    FROM Acc.vwRcvSaleReview AS sale
    WHERE sale.CustId = TRY_CONVERT(int, customer.BackOfficeId)
      AND sale.DealerId = {personnel_id}
      AND sale.RemainingAmount > 0
    GROUP BY sale.SaleId
  ) AS invoice
) AS open_invoices
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(template.IsRemoved, 0) = 0
  AND ISNULL(path.IsRemoved, 0) = 0
  AND ISNULL(customer.IsRemoved, 0) = 0
  AND ISNULL(customer.IsActive, 1) = 1
ORDER BY assigned.RowIndex, customer.StoreName, customer.CustomerName
""".strip()
    assigned = _query_rows(settings, customers_sql)
    if not assigned:
        route_check_sql = f"""
SELECT path.Id AS PathId, path.PathTitle
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(template.IsRemoved, 0) = 0
  AND ISNULL(path.IsRemoved, 0) = 0
""".strip()
        route = _query_rows(settings, route_check_sql)
        if not route:
            raise SellerRouteNotFound("Current seller route was not found")
        path_title = str(route[0]["PathTitle"] or "").strip()
    else:
        path_title = str(assigned[0]["PathTitle"] or "").strip()

    with sqlite_connection(settings.sqlite_path) as connection:
        saved_locations = {
            str(item["customer_id"]): dict(item)
            for item in connection.execute("SELECT customer_id, latitude, longitude, source FROM customer_geo_locations")
        }
    visit_resolutions = _route_visit_resolutions(settings, username, clean_path_id)
    customers = [
        {
            "id": int(row["BackOfficeId"]) if str(row["BackOfficeId"] or "").isdigit() else str(row["BackOfficeId"] or ""),
            "code": str(row["CustomerCode"] or "").strip(),
            "name": str(row["CustomerName"] or "").strip(),
            "store_name": str(row["StoreName"] or "").strip(),
            "address": str(row["Address"] or "").strip(),
            "latitude": _coordinate(saved_locations.get(str(row["BackOfficeId"]), {}).get("latitude")) or _coordinate(row["Latitude"]),
            "longitude": _coordinate(saved_locations.get(str(row["BackOfficeId"]), {}).get("longitude")) or _coordinate(row["Longitude"]),
            "location_source": str(saved_locations.get(str(row["BackOfficeId"]), {}).get("source") or ("erp" if _coordinate(row["Latitude"]) and _coordinate(row["Longitude"]) else "")),
            "location_check_exempt": bool(row.get("IgnoreLocation")),
            "alarm": str(row.get("Alarm") or "").strip(),
            "phone": str(row["Phone"] or "").strip(),
            "mobile": str(row["Mobile"] or "").strip(),
            "visit_resolution": visit_resolutions.get(str(row["BackOfficeId"])),
            "cardex_balance": float(row["CustomerCardexBalance"] or 0),
            "open_invoice_remaining": float(row["OpenInvoiceRemaining"] or 0),
            "open_invoice_count": int(row["OpenInvoiceCount"] or 0),
            "financial_snapshot": {
                "bed_credit": float(row.get("BedCredit") or 0),
                "remaining_bed_credit": float(row.get("RemBedCredit") or 0),
                "asn_credit": float(row.get("AsnCredit") or 0),
                "remaining_asn_credit": float(row.get("RemAsnCredit") or 0),
                "has_bed_credit": bool(row.get("HasBedCredit")),
                "has_asn_credit": bool(row.get("HasAsnCredit")),
                "combined_remaining": float(row.get("RemBedCredit") or 0) + float(row.get("RemAsnCredit") or 0),
                "customer_remaining": float(row.get("CustomerRemaining") or 0),
                "open_cheque_count": int(row.get("OpenChequeCount") or 0),
                "open_cheque_amount": float(row.get("OpenChequeAmount") or 0),
                "returned_cheque_count": int(row.get("ReturnChequeCount") or 0),
                "returned_cheque_amount": float(row.get("ReturnChequeAmount") or 0),
                "dc_ref": int(row["CreditDcRef"]) if row.get("CreditDcRef") is not None else None,
                "updated_at": str(row.get("CreditLastUpdate") or ""),
                "source": "GNR.tblCust + Acc.tblCustRemInfo",
            },
        }
        for row in assigned
    ]
    return {
        "route": {"id": clean_path_id, "title": path_title},
        "customer_count": len(customers),
        "customers": customers,
        "visit_location_policy": _resolve_seller_location_policy(settings, personnel_id),
        "source": "NGT.VisitTemplatePathCustomers",
        "live_assignment": True,
    }


def seller_route_customers_basic(settings: Any, username: str, path_id: str) -> dict[str, Any]:
    # Fast route payload for Home/Route/Orders. Keeps identity/location,
    # visit state and lightweight credit data; expensive finance aggregates
    # stay on the existing full seller_route_customers path.
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerRouteNotFound("Current seller route was not found") from exc

    customers_sql = f"""
SELECT path.Id AS PathId, path.PathTitle, assigned.RowIndex,
       customer.BackOfficeId, customer.CustomerCode, customer.CustomerName,
       customer.StoreName, customer.Address, customer.Phone, customer.Mobile,
       customer.Latitude, customer.Longitude, customer.IgnoreLocation, customer.Alarm,
       backoffice_customer.BedCredit, backoffice_customer.AsnCredit,
       backoffice_customer.HasBedCredit, backoffice_customer.HasAsnCredit,
       COALESCE(credit_snapshot.RemBedCredit, backoffice_customer.BedCredit) AS RemBedCredit,
       COALESCE(credit_snapshot.RemAsnCredit, backoffice_customer.AsnCredit) AS RemAsnCredit,
       credit_snapshot.RemAmount AS CustomerRemaining,
       credit_snapshot.OpenChequeCount, credit_snapshot.OpenChequeAmount,
       credit_snapshot.ReturnChequeCount, credit_snapshot.ReturnChequeAmount,
       credit_snapshot.DcRef AS CreditDcRef, credit_snapshot.LastUpdate AS CreditLastUpdate,
       CAST(0 AS float) AS CustomerCardexBalance,
       CAST(0 AS float) AS OpenInvoiceRemaining,
       CAST(0 AS int) AS OpenInvoiceCount
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
INNER JOIN (
  SELECT VisitTemplatePathUniqueId, CustomerUniqueId, MIN(RowIndex) AS RowIndex
  FROM (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex
    FROM NGT.VisitTemplatePathCustomers
    WHERE ISNULL(IsRemoved, 0) = 0
    UNION ALL
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex
    FROM NGT.VisitTemplatePathSecondaryCustomers
    WHERE ISNULL(IsRemoved, 0) = 0
  ) AS all_links
  GROUP BY VisitTemplatePathUniqueId, CustomerUniqueId
) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
LEFT JOIN GNR.tblCust AS backoffice_customer
  ON backoffice_customer.ID = TRY_CONVERT(int, customer.BackOfficeId)
OUTER APPLY (
  SELECT TOP 1 order_header.DcRefSDS
  FROM NGT.CustomerCallOrders AS order_header
  WHERE TRY_CONVERT(int, order_header.DealerRefSDS) = {personnel_id}
    AND order_header.DcRefSDS IS NOT NULL
    AND ISNULL(order_header.IsRemoved, 0) = 0
  ORDER BY order_header.LastUpdate DESC
) AS recent_order_context
OUTER APPLY (
  SELECT TOP 1 info.RemAmount, info.RemBedCredit, info.RemAsnCredit,
         info.OpenChequeCount, info.OpenChequeAmount,
         info.ReturnChequeCount, info.ReturnChequeAmount,
         info.DcRef, info.LastUpdate
  FROM Acc.tblCustRemInfo AS info
  WHERE info.CustRef = TRY_CONVERT(int, customer.BackOfficeId)
  ORDER BY CASE WHEN info.DcRef = recent_order_context.DcRefSDS THEN 0 ELSE 1 END,
           info.LastUpdate DESC, info.DcRef
) AS credit_snapshot
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(template.IsRemoved, 0) = 0
  AND ISNULL(path.IsRemoved, 0) = 0
  AND ISNULL(customer.IsRemoved, 0) = 0
  AND ISNULL(customer.IsActive, 1) = 1
ORDER BY assigned.RowIndex, customer.StoreName, customer.CustomerName
""".strip()
    assigned = _query_rows(settings, customers_sql)
    if not assigned:
        route_check_sql = f"""
SELECT path.Id AS PathId, path.PathTitle
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(template.IsRemoved, 0) = 0
  AND ISNULL(path.IsRemoved, 0) = 0
""".strip()
        route = _query_rows(settings, route_check_sql)
        if not route:
            raise SellerRouteNotFound("Current seller route was not found")
        path_title = str(route[0]["PathTitle"] or "").strip()
    else:
        path_title = str(assigned[0]["PathTitle"] or "").strip()

    with sqlite_connection(settings.sqlite_path) as connection:
        saved_locations = {
            str(item["customer_id"]): dict(item)
            for item in connection.execute(
                "SELECT customer_id, latitude, longitude, source FROM customer_geo_locations"
            )
        }
    visit_resolutions = _route_visit_resolutions(settings, username, clean_path_id)
    customers = [
        {
            "id": int(row["BackOfficeId"]) if str(row["BackOfficeId"] or "").isdigit() else str(row["BackOfficeId"] or ""),
            "code": str(row["CustomerCode"] or "").strip(),
            "name": str(row["CustomerName"] or "").strip(),
            "store_name": str(row["StoreName"] or "").strip(),
            "address": str(row["Address"] or "").strip(),
            "latitude": _coordinate(saved_locations.get(str(row["BackOfficeId"]), {}).get("latitude")) or _coordinate(row["Latitude"]),
            "longitude": _coordinate(saved_locations.get(str(row["BackOfficeId"]), {}).get("longitude")) or _coordinate(row["Longitude"]),
            "location_source": str(saved_locations.get(str(row["BackOfficeId"]), {}).get("source") or ("erp" if _coordinate(row["Latitude"]) and _coordinate(row["Longitude"]) else "")),
            "location_check_exempt": bool(row.get("IgnoreLocation")),
            "alarm": str(row.get("Alarm") or "").strip(),
            "phone": str(row["Phone"] or "").strip(),
            "mobile": str(row["Mobile"] or "").strip(),
            "visit_resolution": visit_resolutions.get(str(row["BackOfficeId"])),
            "cardex_balance": 0.0,
            "open_invoice_remaining": 0.0,
            "open_invoice_count": 0,
            "financial_snapshot": {
                "bed_credit": float(row.get("BedCredit") or 0),
                "remaining_bed_credit": float(row.get("RemBedCredit") or 0),
                "asn_credit": float(row.get("AsnCredit") or 0),
                "remaining_asn_credit": float(row.get("RemAsnCredit") or 0),
                "has_bed_credit": bool(row.get("HasBedCredit")),
                "has_asn_credit": bool(row.get("HasAsnCredit")),
                "combined_remaining": float(row.get("RemBedCredit") or 0) + float(row.get("RemAsnCredit") or 0),
                "customer_remaining": float(row.get("CustomerRemaining") or 0),
                "open_cheque_count": int(row.get("OpenChequeCount") or 0),
                "open_cheque_amount": float(row.get("OpenChequeAmount") or 0),
                "returned_cheque_count": int(row.get("ReturnChequeCount") or 0),
                "returned_cheque_amount": float(row.get("ReturnChequeAmount") or 0),
                "dc_ref": int(row["CreditDcRef"]) if row.get("CreditDcRef") is not None else None,
                "updated_at": str(row.get("CreditLastUpdate") or ""),
                "source": "GNR.tblCust + Acc.tblCustRemInfo",
            },
        }
        for row in assigned
    ]
    return {
        "route": {"id": clean_path_id, "title": path_title},
        "customer_count": len(customers),
        "customers": customers,
        "visit_location_policy": _resolve_seller_location_policy(settings, personnel_id),
        "source": "NGT.VisitTemplatePathCustomers",
        "live_assignment": True,
        "detail": "basic",
    }


_CUSTOMER_UPDATE_FIELD_NAMES = (
    "phone", "national_code", "economic_code", "store_name", "address", "mobile",
    "customer_activity_id", "state_id", "city_id", "county_id", "city_zone",
    "customer_level_id", "customer_category_id", "owner_type_ref", "postal_code",
    "customer_code", "latitude", "longitude",
)

_CUSTOMER_UPDATE_FIELD_ALIASES = {
    "phone": "phone", "nationalcode": "national_code", "economiccode": "economic_code",
    "storename": "store_name", "address": "address", "mobile": "mobile",
    "customeractivityid": "customer_activity_id", "customeractivityuniqueid": "customer_activity_id",
    "stateid": "state_id", "stateuniqueid": "state_id", "cityid": "city_id", "cityuniqueid": "city_id",
    "countyid": "county_id", "countyuniqueid": "county_id", "cityzone": "city_zone",
    "customerlevelid": "customer_level_id", "customerleveluniqueid": "customer_level_id",
    "customercategoryid": "customer_category_id", "customercategoryuniqueid": "customer_category_id",
    "ownertyperef": "owner_type_ref", "postalcode": "postal_code", "postcode": "postal_code",
    "customercode": "customer_code", "latitude": "latitude", "longitude": "longitude",
}


def _active_customer_update_fields(policy: dict[str, Any]) -> list[str]:
    active = list(_CUSTOMER_UPDATE_FIELD_NAMES) if policy.get("allow_edit_customer") else []
    for item in policy.get("required_customer_fields") or []:
        normalized = str(item).replace("_", "").replace("-", "").replace(" ", "").casefold()
        field = _CUSTOMER_UPDATE_FIELD_ALIASES.get(normalized)
        if field and field not in active:
            active.append(field)
    if policy.get("set_customer_location"):
        for field in ("latitude", "longitude"):
            if field not in active:
                active.append(field)
    return active


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sql_text(value: Any) -> str:
    return str(value or "").replace("'", "''")


def _assigned_route_customer(settings: Any, username: str, path_id: str, customer_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    route = seller_route_customers(settings, username, path_id)
    customer = next((item for item in route["customers"] if str(item["id"]) == str(customer_id)), None)
    if customer is None:
        raise SellerRouteNotFound("Customer is not assigned to this seller route")
    return route, customer


def seller_customer_profile_any_route(settings: Any, username: str, customer_id: str) -> dict[str, Any]:
    """Read one assigned customer profile without claiming a day route is active."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    safe_customer_id = _sql_text(customer_id)
    rows = _query_rows(settings, f"""
SELECT TOP 1 CONVERT(varchar(36), path.Id) AS PathId
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
INNER JOIN (
  SELECT VisitTemplatePathUniqueId, CustomerUniqueId, MIN(RowIndex) AS RowIndex
  FROM (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex FROM NGT.VisitTemplatePathCustomers WHERE ISNULL(IsRemoved,0)=0
    UNION ALL
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId, RowIndex FROM NGT.VisitTemplatePathSecondaryCustomers WHERE ISNULL(IsRemoved,0)=0
  ) AS links GROUP BY VisitTemplatePathUniqueId, CustomerUniqueId
) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND customer.BackOfficeId = N'{safe_customer_id}'
  AND ISNULL(personnel.IsRemoved,0)=0 AND ISNULL(personnel.PersonnelIsActive,1)=1
  AND ISNULL(template.IsRemoved,0)=0 AND ISNULL(path.IsRemoved,0)=0
  AND ISNULL(customer.IsRemoved,0)=0 AND ISNULL(customer.IsActive,1)=1
ORDER BY path.RowIndex, assigned.RowIndex
""".strip())
    if not rows:
        raise SellerRouteNotFound("Customer is not assigned to this seller")
    result = seller_route_customer_profile(settings, username, str(rows[0]["PathId"]), customer_id)
    result["browse_context"] = {"mode": "assigned_route_read_only", "day_route_active": False}
    return result


def _customer_profile_lookups(settings: Any) -> dict[str, list[dict[str, Any]]]:
    rows = _query_rows(settings, """
SELECT 'activity' AS LookupKind, CONVERT(varchar(36), Id) AS Id,
       CustomerActivityName AS Title, NULL AS ParentId, TRY_CONVERT(int, BackOfficeId) AS Ref
FROM NGT.CustomerActivities WHERE ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'category', CONVERT(varchar(36), Id), CustomerCategoryName, NULL, TRY_CONVERT(int, BackOfficeId)
FROM NGT.CustomerCategories WHERE ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'level', CONVERT(varchar(36), Id), CustomerLevelName, NULL, TRY_CONVERT(int, BackOfficeId)
FROM NGT.CustomerLevels WHERE ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'owner_type', CONVERT(varchar(20), TRY_CONVERT(int, BackOfficeId)), CustomerOwnerTypeName, NULL, TRY_CONVERT(int, BackOfficeId)
FROM NGT.CustomerOwnerTypes WHERE ISNULL(IsRemoved, 0) = 0 AND TRY_CONVERT(int, BackOfficeId) IS NOT NULL
UNION ALL
SELECT 'state', CONVERT(varchar(36), Id), StateName, NULL, TRY_CONVERT(int, BackOfficeId)
FROM NGT.States WHERE ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'city', CONVERT(varchar(36), Id), CityName, CONVERT(varchar(36), StateUniqueId), TRY_CONVERT(int, BackOfficeId)
FROM NGT.Cities WHERE ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'county', CONVERT(varchar(36), Id), CountyName, NULL, TRY_CONVERT(int, BackOfficeId)
FROM NGT.Counties WHERE ISNULL(IsRemoved, 0) = 0
ORDER BY LookupKind, Title
""".strip())
    result: dict[str, list[dict[str, Any]]] = {
        "activity": [], "category": [], "level": [], "owner_type": [],
        "state": [], "city": [], "county": [],
    }
    for row in rows:
        kind = str(row["LookupKind"])
        result.setdefault(kind, []).append({
            "id": str(row["Id"] or ""),
            "title": str(row["Title"] or "").strip(),
            "parent_id": str(row["ParentId"] or ""),
            "ref": int(row["Ref"]) if row.get("Ref") is not None else None,
        })
    return result


def seller_route_customer_profile(settings: Any, username: str, path_id: str, customer_id: str) -> dict[str, Any]:
    route, route_customer = _assigned_route_customer(settings, username, path_id, customer_id)
    safe_customer_id = _sql_text(route_customer["id"])
    rows = _query_rows(settings, f"""
SELECT CONVERT(varchar(36), customer.Id) AS CustomerUniqueId,
       customer.BackOfficeId, customer.CustomerCode, customer.CustomerName,
       customer.StoreName, customer.Address, customer.Phone, customer.Mobile,
       customer.NationalCode, customer.EconomicCode, customer.PostCode,
       customer.CityZone, customer.Latitude, customer.Longitude, customer.Alarm,
       CONVERT(varchar(36), customer.CustomerActivityUniqueId) AS CustomerActivityId,
       activity.CustomerActivityName,
       CONVERT(varchar(36), customer.CustomerCategoryUniqueId) AS CustomerCategoryId,
       category.CustomerCategoryName,
       CONVERT(varchar(36), customer.CustomerLevelUniqueId) AS CustomerLevelId,
       level_info.CustomerLevelName,
       owner_info.BackOfficeId AS OwnerTypeRef, owner_info.CustomerOwnerTypeName,
       CONVERT(varchar(36), customer.StateUniqueId) AS StateId, state_info.StateName,
       CONVERT(varchar(36), customer.CityUniqueId) AS CityId, city_info.CityName,
       CONVERT(varchar(36), customer.CountyUniqueId) AS CountyId, county_info.CountyName,
       customer.VisitCount, customer.OrderCount, customer.OrderLineCount,
       customer.SumOrderAmount, customer.AvgSuccessfulVisit, customer.LastUpdate
FROM NGT.Customers AS customer
LEFT JOIN NGT.CustomerActivities AS activity ON activity.Id = customer.CustomerActivityUniqueId
LEFT JOIN NGT.CustomerCategories AS category ON category.Id = customer.CustomerCategoryUniqueId
LEFT JOIN NGT.CustomerLevels AS level_info ON level_info.Id = customer.CustomerLevelUniqueId
LEFT JOIN NGT.CustomerOwnerTypes AS owner_info ON owner_info.Id = customer.OwnerTypeUniqueId
LEFT JOIN NGT.States AS state_info ON state_info.Id = customer.StateUniqueId
LEFT JOIN NGT.Cities AS city_info ON city_info.Id = customer.CityUniqueId
LEFT JOIN NGT.Counties AS county_info ON county_info.Id = customer.CountyUniqueId
WHERE customer.BackOfficeId = N'{safe_customer_id}'
  AND ISNULL(customer.IsRemoved, 0) = 0
""".strip())
    if not rows:
        raise SellerRouteNotFound("Customer profile was not found in NGT")
    row = rows[0]
    with sqlite_connection(settings.sqlite_path) as connection:
        draft_row = connection.execute(
            "SELECT update_json, updated_at FROM previsit_customer_update_drafts WHERE username = ? AND route_id = ? AND customer_id = ?",
            (username, str(route["route"]["id"]), str(route_customer["id"])),
        ).fetchone()
    draft = json.loads(str(draft_row["update_json"])) if draft_row else None
    editable = {
        "phone": str(row["Phone"] or "").strip(),
        "national_code": str(row["NationalCode"] or "").strip(),
        "economic_code": str(row["EconomicCode"] or "").strip(),
        "store_name": str(row["StoreName"] or "").strip(),
        "address": str(row["Address"] or "").strip(),
        "mobile": str(row["Mobile"] or "").strip(),
        "customer_activity_id": str(row["CustomerActivityId"] or ""),
        "state_id": str(row["StateId"] or ""),
        "city_id": str(row["CityId"] or ""),
        "county_id": str(row["CountyId"] or ""),
        "city_zone": int(row["CityZone"]) if row.get("CityZone") is not None else None,
        "customer_level_id": str(row["CustomerLevelId"] or ""),
        "customer_category_id": str(row["CustomerCategoryId"] or ""),
        "owner_type_ref": int(row["OwnerTypeRef"]) if row.get("OwnerTypeRef") is not None and str(row["OwnerTypeRef"]).isdigit() else None,
        "postal_code": str(row["PostCode"] or "").strip(),
        "customer_code": str(row["CustomerCode"] or "").strip(),
        "latitude": _coordinate(route_customer.get("latitude")),
        "longitude": _coordinate(route_customer.get("longitude")),
    }
    return {
        "route": route["route"],
        "customer": {
            **route_customer,
            "unique_id": str(row["CustomerUniqueId"] or ""),
            "name": str(row["CustomerName"] or "").strip(),
            "alarm": str(row["Alarm"] or "").strip(),
            "activity_name": str(row["CustomerActivityName"] or "").strip(),
            "category_name": str(row["CustomerCategoryName"] or "").strip(),
            "level_name": str(row["CustomerLevelName"] or "").strip(),
            "owner_type_name": str(row["CustomerOwnerTypeName"] or "").strip(),
            "state_name": str(row["StateName"] or "").strip(),
            "city_name": str(row["CityName"] or "").strip(),
            "county_name": str(row["CountyName"] or "").strip(),
            "visit_count": int(row["VisitCount"] or 0),
            "order_count": int(row["OrderCount"] or 0),
            "order_line_count": int(row["OrderLineCount"] or 0),
            "sum_order_amount": float(row["SumOrderAmount"] or 0),
            "avg_successful_visit": float(row["AvgSuccessfulVisit"] or 0),
            "ngt_updated_at": str(row["LastUpdate"] or ""),
            "editable": editable,
        },
        "lookups": _customer_profile_lookups(settings),
        "draft": draft,
        "draft_updated_at": str(draft_row["updated_at"]) if draft_row else None,
        "visit_controls": route.get("visit_location_policy") or {},
        "editable_contract": {
            "fields": list(_CUSTOMER_UPDATE_FIELD_NAMES),
            "active_fields": _active_customer_update_fields(route.get("visit_location_policy") or {}),
            "source": "NGT 5.9.0.170 SyncGetCustomerUpdateDataViewModel + SyncGetCustomerUpdateLocationViewModel",
            "write_mode": "local_draft_only",
        },
    }


def save_seller_route_customer_profile_draft(
    settings: Any,
    username: str,
    path_id: str,
    customer_id: str,
    update: dict[str, Any],
) -> dict[str, Any]:
    profile = seller_route_customer_profile(settings, username, path_id, customer_id)
    lookups = profile["lookups"]
    allowed_ids = {
        "customer_activity_id": {item["id"] for item in lookups["activity"]},
        "customer_category_id": {item["id"] for item in lookups["category"]},
        "customer_level_id": {item["id"] for item in lookups["level"]},
        "state_id": {item["id"] for item in lookups["state"]},
        "city_id": {item["id"] for item in lookups["city"]},
        "county_id": {item["id"] for item in lookups["county"]},
    }
    active_fields = set(profile["editable_contract"]["active_fields"])
    normalized: dict[str, Any] = dict(profile["customer"]["editable"])
    for field in active_fields:
        value = update.get(field, normalized.get(field))
        if isinstance(value, str):
            value = value.strip()
        if field in allowed_ids and value and value not in allowed_ids[field]:
            raise SellerWorkspaceError(f"Invalid NGT lookup value for {field}")
        normalized[field] = value if value not in ("â€‹",) else ""
    owner_refs = {item["ref"] for item in lookups["owner_type"]}
    if normalized["owner_type_ref"] is not None and normalized["owner_type_ref"] not in owner_refs:
        raise SellerWorkspaceError("Invalid NGT lookup value for owner_type_ref")
    now = _utc_now()
    route_id = str(profile["route"]["id"])
    resolved_customer_id = str(profile["customer"]["id"])
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """
            INSERT INTO previsit_customer_update_drafts
              (username, route_id, customer_id, update_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username, route_id, customer_id) DO UPDATE SET
              update_json = excluded.update_json,
              updated_at = excluded.updated_at
            """,
            (username, route_id, resolved_customer_id, json.dumps(normalized, ensure_ascii=False), now, now),
        )
        latitude = normalized.get("latitude")
        longitude = normalized.get("longitude")
        if latitude is not None and longitude is not None:
            connection.execute(
                """
                INSERT INTO customer_geo_locations
                  (customer_id, latitude, longitude, source, updated_by, updated_at)
                VALUES (?, ?, ?, 'salesperson_pinned', ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                  latitude = excluded.latitude,
                  longitude = excluded.longitude,
                  source = excluded.source,
                  updated_by = excluded.updated_by,
                  updated_at = excluded.updated_at
                """,
                (resolved_customer_id, float(latitude), float(longitude), username, now),
            )
    return {
        "route_id": route_id,
        "customer_id": resolved_customer_id,
        "draft": normalized,
        "updated_at": now,
        "write_mode": "local_draft_only",
        "location_available_for_visit": normalized.get("latitude") is not None and normalized.get("longitude") is not None,
        "message": "Customer changes were saved locally and were not sent to NGT or Varanegar.",
    }


def _neshan_get(url: str, api_key: str, params: dict[str, Any]) -> dict[str, Any]:
    request = Request(f"{url}?{urlencode(params)}", headers={"Api-Key": api_key})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SellerWorkspaceError("Neshan route service is unavailable") from exc


def _neshan_direction(settings: Any, origin_latitude: float, origin_longitude: float, destination_latitude: float, destination_longitude: float) -> dict[str, Any]:
    direction = _neshan_get("https://api.neshan.org/v4/direction", settings.neshan_service_api_key, {
        "type": "car", "origin": f"{origin_latitude},{origin_longitude}",
        "destination": f"{destination_latitude},{destination_longitude}",
    })
    route_info = (direction.get("routes") or [{}])[0]
    return {
        "polyline": str((route_info.get("overview_polyline") or {}).get("points") or ""),
        "leg": (route_info.get("legs") or [None])[0],
    }


def seller_route_map_plan(
    settings: Any, username: str, path_id: str, origin_latitude: float | None, origin_longitude: float | None,
    route_mode: str = "sales_priority",
    *, require_day_route: bool = False,
) -> dict[str, Any]:
    if require_day_route:
        require_seller_day_route(settings, username, path_id)
    if not settings.neshan_service_api_key:
        raise SellerWorkspaceError("Neshan route service is not configured")
    # Navigation only needs route identity, customer coordinates and visit state.
    # Avoid the full financial customer payload here; visit intelligence is loaded
    # separately when the seller opens a customer.
    route = seller_route_customers_basic(settings, username, path_id)
    analytics_available = True
    analytics_settings = replace(settings, sql_query_timeout=min(int(settings.sql_query_timeout), 5))
    try:
        analytics = _seller_route_visit_scores_fast(analytics_settings, username, path_id)
    except (TimeoutError, OSError):
        # Route customers and navigation are operational data; purchase
        # analytics only enriches their priority and must never block the day.
        analytics = {"customers": []}
        analytics_available = False
    analytics_by_customer = {str(item["id"]): item for item in analytics.get("customers") or []}
    selected_mode = route_mode if route_mode in {"sales_priority", "shortest"} else "sales_priority"
    all_customers = [
        {**item, "visit_score": int(analytics_by_customer.get(str(item["id"]), {}).get("visit_score") or 0),
         "analysis": analytics_by_customer.get(str(item["id"]), {})}
        for item in route["customers"]
    ]
    candidates = [
        item for item in all_customers if item["latitude"] is not None and item["longitude"] is not None
    ]
    candidates.sort(key=lambda item: (-item["visit_score"], str(item["name"] or item["store_name"])))
    max_score = max((int(item["visit_score"] or 0) for item in candidates), default=1)
    for item in all_customers:
        score = int(item["visit_score"] or 0)
        item["priority_tier"] = "high" if score >= max_score * .67 else ("medium" if score >= max_score * .34 else "low")
    if not candidates:
        return {"route": route["route"], "customers": all_customers, "missing_location_count": route["customer_count"], "ordered_customers": [], "unlocated_customers": all_customers, "polyline": "", "initial_leg": None, "route_mode": selected_mode, "visit_location_policy": route.get("visit_location_policy"), "analytics_available": analytics_available}
    has_origin = origin_latitude is not None and origin_longitude is not None
    origin = {"id": "origin", "latitude": origin_latitude, "longitude": origin_longitude} if has_origin else None
    if selected_mode == "sales_priority":
        ordered_customers: list[dict[str, Any]] = []
        cursor = origin
        # Optimize each commercial tier geographically, while never allowing a
        # low-probability stop to be put ahead of high/medium-probability work.
        for tier in ("high", "medium", "low"):
            group = [item for item in candidates if item["priority_tier"] == tier]
            if not group:
                continue
            ordered_group = _optimize_route_group(settings, cursor, group)
            ordered_customers.extend(ordered_group)
            cursor = ordered_group[-1] if ordered_group else cursor
        origin = origin or (ordered_customers[0] if ordered_customers else None)
    else:
        ordered_customers = _optimize_route_group(settings, origin, candidates)
        origin = origin or (ordered_customers[0] if ordered_customers else None)
    # A later priority group starts from the final point of the previous group.
    # Neshan returns that starting point too; keep every customer only once.
    seen_customer_ids: set[str] = set()
    ordered_customers = [
        item for item in ordered_customers
        if not (str(item["id"]) in seen_customer_ids or seen_customer_ids.add(str(item["id"])))
    ]
    if origin is None:
        ordered_customers = candidates
        origin = ordered_customers[0]
    # The map is a live stop-by-stop navigator, not a whole-day line.  Asking
    # Neshan for every waypoint here makes the first displayed route end at the
    # last customer and is confusing for a seller.  Only return the leg to the
    # first customer; after a visit/skip the client asks ``map-leg`` again for
    # the next active customer from the seller's current GPS position.
    initial_direction: dict[str, Any] = {}
    if has_origin and ordered_customers:
        first_customer = ordered_customers[0]
        initial_direction = _neshan_direction(
            settings,
            float(origin_latitude),
            float(origin_longitude),
            float(first_customer["latitude"]),
            float(first_customer["longitude"]),
        )
    return {
        "route": route["route"], "customers": all_customers, "missing_location_count": route["customer_count"] - len(candidates),
        "ordered_customers": ordered_customers, "unlocated_customers": [item for item in all_customers if item["latitude"] is None or item["longitude"] is None],
        "has_origin": has_origin, "polyline": initial_direction.get("polyline") or "",
        "legs": [], "initial_leg": initial_direction.get("leg"), "route_mode": selected_mode,
        "visit_location_policy": route.get("visit_location_policy"),
        "analytics_available": analytics_available,
    }


def _optimize_route_group(settings: Any, origin: dict[str, Any] | None, customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return Neshan's shortest order for one priority group, preserving its tier."""
    if len(customers) <= 1:
        return customers
    points = ([origin] if origin else []) + customers
    trip = _neshan_get("https://api.neshan.org/v3/trip", settings.neshan_service_api_key, {
        "waypoints": "|".join(f"{item['latitude']},{item['longitude']}" for item in points),
        "roundTrip": "false", "sourceIsAnyPoint": "false", "lastIsAnyPoint": "true",
    })
    indexes = [int(point["index"]) for point in trip.get("points") or [] if str(point.get("index", "")).isdigit()]
    ordered = [
        points[index] for index in indexes
        if 0 <= index < len(points) and not (origin is not None and index == 0)
    ]
    return ordered or customers


def _seller_route_destination_location(
    settings: Any, username: str, path_id: str, destination_id: str
) -> tuple[float, float]:
    """Resolve one assigned route destination without financial enrichment."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerRouteNotFound("Current seller route was not found") from exc
    clean_destination_id = _sql_text(destination_id)
    destination_sql = f"""
SELECT TOP 1 customer.BackOfficeId, customer.Latitude, customer.Longitude
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
INNER JOIN (
  SELECT VisitTemplatePathUniqueId, CustomerUniqueId
  FROM NGT.VisitTemplatePathCustomers
  WHERE ISNULL(IsRemoved, 0) = 0
  UNION
  SELECT VisitTemplatePathUniqueId, CustomerUniqueId
  FROM NGT.VisitTemplatePathSecondaryCustomers
  WHERE ISNULL(IsRemoved, 0) = 0
) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
  AND CONVERT(nvarchar(100), customer.BackOfficeId) = N'{clean_destination_id}'
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(template.IsRemoved, 0) = 0
  AND ISNULL(path.IsRemoved, 0) = 0
  AND ISNULL(customer.IsRemoved, 0) = 0
  AND ISNULL(customer.IsActive, 1) = 1
""".strip()
    rows = _query_rows(settings, destination_sql)
    if not rows:
        raise SellerRouteNotFound("Current seller route destination was not found")
    row = rows[0]
    customer_id = str(row.get("BackOfficeId") or destination_id)
    with sqlite_connection(settings.sqlite_path) as connection:
        saved = connection.execute(
            "SELECT latitude, longitude FROM customer_geo_locations WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
    saved_latitude = _coordinate(saved["latitude"]) if saved is not None else None
    saved_longitude = _coordinate(saved["longitude"]) if saved is not None else None
    latitude = saved_latitude or _coordinate(row.get("Latitude"))
    longitude = saved_longitude or _coordinate(row.get("Longitude"))
    if latitude is None or longitude is None:
        raise SellerRouteNotFound("Current seller route destination was not found")
    return latitude, longitude


def seller_route_map_leg(
    settings: Any, username: str, path_id: str, destination_id: str, origin_latitude: float, origin_longitude: float
) -> dict[str, Any]:
    if not settings.neshan_service_api_key:
        raise SellerWorkspaceError("Neshan route service is not configured")
    destination_latitude, destination_longitude = _seller_route_destination_location(
        settings, username, path_id, destination_id
    )
    return _neshan_direction(
        settings, origin_latitude, origin_longitude, destination_latitude, destination_longitude
    )


def _sales_month_serial(value: Any) -> int | None:
    parts = str(value or "").replace("-", "/").split("/")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]) * 12 + int(parts[1])


def _visit_score_components(
    months: list[int],
    *,
    all_brand_purchase_score: int,
    line_brand_purchase_score: int,
    line_brand_count: int,
    active_line_brand_count: int,
    current_month: int,
) -> tuple[int, dict[str, int]]:
    invoice_time_score = sum(
        9 if current_month - month <= 2 else 6 if 4 <= current_month - month <= 6 else 1
        for month in months
    )
    regularity_score = min(len(set(months)), 6)
    cross_sell_score = (
        min(max(active_line_brand_count - line_brand_count, 0), 5)
        if line_brand_count
        else 0
    )
    newly_active_score = 3 if months and min(months) >= current_month - 2 else 0
    recent_months = sum(1 for month in months if current_month - month <= 2)
    previous_months = sum(1 for month in months if 3 <= current_month - month <= 4)
    reengagement_score = 3 if previous_months > recent_months else 0
    breakdown = {
        "invoice_time": invoice_time_score,
        "all_brand_purchases": int(all_brand_purchase_score),
        "line_brand_purchase_bonus": int(line_brand_purchase_score),
        "line_brand_breadth": int(line_brand_count),
        "purchase_regularity": regularity_score,
        "cross_sell_opportunity": cross_sell_score,
        "newly_active": newly_active_score,
        "reengagement_opportunity": reengagement_score,
    }
    return sum(breakdown.values()), breakdown


def _seller_route_visit_scores_fast(
    settings: Any,
    username: str,
    path_id: str,
) -> dict[str, Any]:
    """Return score-only route analytics for map ordering.

    The full visit workspace still uses seller_route_day_analytics. This path
    intentionally omits brand/line detail that the map never renders.
    """
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerRouteNotFound("Current seller route was not found") from exc

    route_cte = f"""
WITH RouteCustomers AS (
  SELECT DISTINCT TRY_CONVERT(int, customer.BackOfficeId) AS CustomerId
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
  INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
  INNER JOIN (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId
    FROM NGT.VisitTemplatePathCustomers WHERE ISNULL(IsRemoved, 0) = 0
    UNION
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId
    FROM NGT.VisitTemplatePathSecondaryCustomers WHERE ISNULL(IsRemoved, 0) = 0
  ) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
  INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
    AND ISNULL(personnel.IsRemoved, 0) = 0
    AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(template.IsRemoved, 0) = 0
    AND ISNULL(path.IsRemoved, 0) = 0
    AND ISNULL(customer.IsRemoved, 0) = 0
    AND ISNULL(customer.IsActive, 1) = 1
)
""".strip()

    brand_sql = route_cte + f""",
SellerBrands AS (
  SELECT DISTINCT goods.BrandRef
  FROM NGT.Personnels AS personnel
  LEFT JOIN NGT.VisitTemplates AS visit_template
    ON visit_template.Id = personnel.VisitTemplateUniqueId
   AND ISNULL(visit_template.IsRemoved, 0) = 0
  INNER JOIN NGT.ProductTemplates AS product_template
    ON product_template.Id = COALESCE(
      personnel.ProductTemplateUniqueId,
      visit_template.ProductTemplateUniqueId
    )
  INNER JOIN NGT.ProductTemplateDetails AS detail
    ON detail.ProductTemplateUniqueId = product_template.Id
  INNER JOIN GNR.tblGoods AS goods ON goods.UniqueId = detail.ProductUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND ISNULL(personnel.IsRemoved, 0) = 0
    AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(product_template.IsRemoved, 0) = 0
    AND ISNULL(detail.IsRemoved, 0) = 0
),
SaleBrandInvoice AS (
  SELECT sale.CustomerId, goods.BrandRef, sale.SellId,
         MAX(CASE WHEN seller_brand.BrandRef IS NULL THEN 0 ELSE 1 END)
           AS IsSellerLineBrand
  FROM dbo.SalesReviewFast AS sale
  INNER JOIN RouteCustomers AS route ON route.CustomerId = sale.CustomerId
  INNER JOIN GNR.tblGoods AS goods ON goods.id = sale.GoodsId
  LEFT JOIN SellerBrands AS seller_brand ON seller_brand.BrandRef = goods.BrandRef
  WHERE sale.ReportDate >= FORMAT(
    DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR'
  )
  GROUP BY sale.CustomerId, goods.BrandRef, sale.SellId
),
BrandRollup AS (
  SELECT CustomerId, BrandRef,
         MAX(IsSellerLineBrand) AS IsSellerLineBrand,
         COUNT(*) AS InvoiceCount
  FROM SaleBrandInvoice
  GROUP BY CustomerId, BrandRef
)
SELECT CustomerId,
       SUM(InvoiceCount) AS AllBrandPurchaseScore,
       SUM(CASE WHEN IsSellerLineBrand = 1 THEN InvoiceCount ELSE 0 END)
         AS LineBrandPurchaseScore,
       SUM(CASE WHEN IsSellerLineBrand = 1 THEN 1 ELSE 0 END) AS LineBrandCount,
       (SELECT COUNT(*) FROM SellerBrands) AS ActiveLineBrandCount
FROM BrandRollup
GROUP BY CustomerId
""".strip()

    invoice_sql = route_cte + "\n" + """
SELECT sale.CustomerId, sale.SellId, MAX(sale.ReportDate) AS ReportDate
FROM dbo.SalesReviewFast AS sale
INNER JOIN RouteCustomers AS route ON route.CustomerId = sale.CustomerId
WHERE sale.ReportDate >= FORMAT(
  DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR'
)
GROUP BY sale.CustomerId, sale.SellId
""".strip()

    brand_rows = _query_rows(settings, brand_sql)
    invoice_rows = _query_rows(settings, invoice_sql)
    brand_by_customer = {str(row["CustomerId"] or ""): row for row in brand_rows}
    invoice_months: dict[str, list[int]] = {}
    for row in invoice_rows:
        month = _sales_month_serial(row.get("ReportDate"))
        if month is not None:
            invoice_months.setdefault(str(row["CustomerId"] or ""), []).append(month)
    current_month = max(
        (month for months in invoice_months.values() for month in months),
        default=0,
    )
    customers: list[dict[str, Any]] = []
    for customer_id in set(brand_by_customer) | set(invoice_months):
        brand = brand_by_customer.get(customer_id, {})
        score, breakdown = _visit_score_components(
            invoice_months.get(customer_id, []),
            all_brand_purchase_score=int(brand.get("AllBrandPurchaseScore") or 0),
            line_brand_purchase_score=int(brand.get("LineBrandPurchaseScore") or 0),
            line_brand_count=int(brand.get("LineBrandCount") or 0),
            active_line_brand_count=int(brand.get("ActiveLineBrandCount") or 0),
            current_month=current_month,
        )
        customers.append({
            "id": int(customer_id) if customer_id.isdigit() else customer_id,
            "visit_score": score,
            "score_breakdown": breakdown,
        })
    return {
        "customers": customers,
        "source": "dbo.SalesReviewFast lightweight route scoring",
        "live_assignment": True,
    }


def seller_route_day_analytics(settings: Any, username: str, path_id: str) -> dict[str, Any]:
    """Return fixed, read-only purchase signals for customers in one current seller route."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SellerRouteNotFound("Current seller route was not found") from exc

    analytics_sql = f"""
WITH RouteCustomers AS (
  SELECT path.Id AS PathId, path.PathTitle, customer.BackOfficeId, customer.CustomerCode,
         customer.CustomerName, customer.StoreName
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
  INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
  INNER JOIN (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId
    FROM NGT.VisitTemplatePathCustomers WHERE ISNULL(IsRemoved, 0) = 0
    UNION
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId
    FROM NGT.VisitTemplatePathSecondaryCustomers WHERE ISNULL(IsRemoved, 0) = 0
  ) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
  INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
    AND ISNULL(personnel.IsRemoved, 0) = 0 AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(template.IsRemoved, 0) = 0 AND ISNULL(path.IsRemoved, 0) = 0
    AND ISNULL(customer.IsRemoved, 0) = 0 AND ISNULL(customer.IsActive, 1) = 1
)
SELECT route.PathId, route.PathTitle, route.BackOfficeId, route.CustomerCode,
       route.CustomerName, route.StoreName,
       ISNULL(company.InvoiceCount, 0) AS CompanyInvoiceCount12M,
       ISNULL(company.NetSales, 0) AS CompanyNetSales12M,
       company.LastInvoiceDate,
       ISNULL(mine.InvoiceCount, 0) AS SellerInvoiceCount12M,
       ISNULL(mine.NetSales, 0) AS SellerNetSales12M
FROM RouteCustomers AS route
OUTER APPLY (
  SELECT COUNT(*) AS InvoiceCount, SUM(invoice.InvoiceAmount) AS NetSales,
         MAX(invoice.InvoiceDate) AS LastInvoiceDate
  FROM (
    SELECT sale.SaleId, MAX(sale.SalesNetAmount) AS InvoiceAmount,
           MAX(COALESCE(sale.SaleDate, sale.SaleVocherDate, sale.ReportDate)) AS InvoiceDate
    FROM Acc.vwRcvSaleReview AS sale
    WHERE sale.CustId = TRY_CONVERT(int, route.BackOfficeId)
      AND (TRY_CONVERT(date, sale.SaleDate) >= DATEADD(YEAR, -1, CONVERT(date, GETDATE()))
           OR TRY_CONVERT(date, sale.SaleVocherDate) >= DATEADD(YEAR, -1, CONVERT(date, GETDATE()))
           OR sale.ReportDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR'))
    GROUP BY sale.SaleId
  ) AS invoice
) AS company
OUTER APPLY (
  SELECT COUNT(*) AS InvoiceCount, SUM(invoice.InvoiceAmount) AS NetSales
  FROM (
    SELECT sale.SaleId, MAX(sale.SalesNetAmount) AS InvoiceAmount
    FROM Acc.vwRcvSaleReview AS sale
    WHERE sale.CustId = TRY_CONVERT(int, route.BackOfficeId) AND sale.DealerId = {personnel_id}
      AND (TRY_CONVERT(date, sale.SaleDate) >= DATEADD(YEAR, -1, CONVERT(date, GETDATE()))
           OR TRY_CONVERT(date, sale.SaleVocherDate) >= DATEADD(YEAR, -1, CONVERT(date, GETDATE()))
           OR sale.ReportDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR'))
    GROUP BY sale.SaleId
  ) AS invoice
) AS mine
ORDER BY ISNULL(company.InvoiceCount, 0) DESC, company.LastInvoiceDate DESC, route.StoreName, route.CustomerName
""".strip()
    rows = _query_rows(settings, analytics_sql)
    brand_sql = f"""
WITH SellerBrands AS (
  SELECT DISTINCT goods.BrandRef
  FROM NGT.Personnels AS personnel
  LEFT JOIN NGT.VisitTemplates AS visit_template
    ON visit_template.Id = personnel.VisitTemplateUniqueId AND ISNULL(visit_template.IsRemoved, 0) = 0
  INNER JOIN NGT.ProductTemplates AS product_template
    ON product_template.Id = COALESCE(personnel.ProductTemplateUniqueId, visit_template.ProductTemplateUniqueId)
  INNER JOIN NGT.ProductTemplateDetails AS detail ON detail.ProductTemplateUniqueId = product_template.Id
  INNER JOIN GNR.tblGoods AS goods ON goods.UniqueId = detail.ProductUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND ISNULL(personnel.IsRemoved, 0) = 0 AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(product_template.IsRemoved, 0) = 0 AND ISNULL(detail.IsRemoved, 0) = 0
)
SELECT brand.BrandName, COUNT(DISTINCT sale.SellId) AS InvoiceCount
FROM dbo.SalesReviewFast AS sale
INNER JOIN GNR.tblGoods AS goods ON goods.id = sale.GoodsId
INNER JOIN SellerBrands AS seller_brand ON seller_brand.BrandRef = goods.BrandRef
INNER JOIN GNR.tblBrand AS brand ON brand.id = goods.BrandRef
WHERE sale.DealerId = {personnel_id}
  AND sale.ReportDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
GROUP BY brand.BrandName
ORDER BY COUNT(DISTINCT sale.SellId) DESC, brand.BrandName
""".strip()
    brand_rows = _query_rows(settings, brand_sql)
    brand_invoice_presence = [
        {"name": str(row["BrandName"] or "").strip(), "invoice_count": int(row["InvoiceCount"] or 0)}
        for row in brand_rows if str(row["BrandName"] or "").strip()
    ]
    customer_brand_sql = f"""
WITH RouteCustomers AS (
  SELECT DISTINCT customer.BackOfficeId
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
  INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
  INNER JOIN (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId FROM NGT.VisitTemplatePathCustomers WHERE ISNULL(IsRemoved, 0) = 0
    UNION
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId FROM NGT.VisitTemplatePathSecondaryCustomers WHERE ISNULL(IsRemoved, 0) = 0
  ) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
  INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
    AND ISNULL(personnel.IsRemoved, 0) = 0 AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(template.IsRemoved, 0) = 0 AND ISNULL(path.IsRemoved, 0) = 0
    AND ISNULL(customer.IsRemoved, 0) = 0 AND ISNULL(customer.IsActive, 1) = 1
), SellerBrands AS (
  SELECT DISTINCT goods.BrandRef
  FROM NGT.Personnels AS personnel
  LEFT JOIN NGT.VisitTemplates AS visit_template
    ON visit_template.Id = personnel.VisitTemplateUniqueId AND ISNULL(visit_template.IsRemoved, 0) = 0
  INNER JOIN NGT.ProductTemplates AS product_template
    ON product_template.Id = COALESCE(personnel.ProductTemplateUniqueId, visit_template.ProductTemplateUniqueId)
  INNER JOIN NGT.ProductTemplateDetails AS detail ON detail.ProductTemplateUniqueId = product_template.Id
  INNER JOIN GNR.tblGoods AS goods ON goods.UniqueId = detail.ProductUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND ISNULL(personnel.IsRemoved, 0) = 0 AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(product_template.IsRemoved, 0) = 0 AND ISNULL(detail.IsRemoved, 0) = 0
), SaleDetails AS (
  SELECT sale.CustomerId, brand.id AS BrandRef, brand.BrandName,
         sale.SellId, sale.SellDetailID,
         MAX(sale.ReportDate) AS ReportDate,
         MAX(sale.DealerId) AS DealerId,
         MAX(LTRIM(RTRIM(ISNULL(sale.DealerName, N'')))) AS DealerName,
         MAX(LTRIM(RTRIM(ISNULL(sale.CustomerCategoryName, N'')))) AS SalesLine,
         MAX(LTRIM(RTRIM(ISNULL(sale.CustomerLevelName, N'')))) AS BranchName,
         MAX(CASE WHEN seller_brand.BrandRef IS NULL THEN 0 ELSE 1 END) AS IsSellerLineBrand,
         MAX(ISNULL(sale.SellNetAmount, 0)) - MAX(ISNULL(sale.SellReturnNetAmount, 0)) AS NetSales
  FROM dbo.SalesReviewFast AS sale
  INNER JOIN RouteCustomers AS route ON TRY_CONVERT(int, route.BackOfficeId) = sale.CustomerId
  INNER JOIN GNR.tblGoods AS goods ON goods.id = sale.GoodsId
  INNER JOIN GNR.tblBrand AS brand ON brand.id = goods.BrandRef
  LEFT JOIN SellerBrands AS seller_brand ON seller_brand.BrandRef = goods.BrandRef
  WHERE sale.ReportDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
  GROUP BY sale.CustomerId, brand.id, brand.BrandName, sale.SellId, sale.SellDetailID
), BrandRollup AS (
  SELECT CustomerId, BrandRef, BrandName, COUNT(DISTINCT SellId) AS InvoiceCount,
         SUM(NetSales) AS NetSales, MAX(ReportDate) AS LastPurchaseDate,
         MAX(IsSellerLineBrand) AS IsSellerLineBrand
  FROM SaleDetails
  GROUP BY CustomerId, BrandRef, BrandName
), LineRollup AS (
  SELECT CustomerId, SalesLine, BranchName, COUNT(DISTINCT SellId) AS InvoiceCount,
         SUM(NetSales) AS NetSales, MAX(ReportDate) AS LastPurchaseDate
  FROM SaleDetails
  GROUP BY CustomerId, SalesLine, BranchName
)
SELECT N'brand' AS RecordKind, rollup.CustomerId, rollup.BrandName,
       rollup.InvoiceCount, rollup.NetSales, rollup.LastPurchaseDate,
       rollup.IsSellerLineBrand, latest.SalesLine, latest.BranchName,
       latest.DealerId AS LastSellerId, latest.DealerName AS LastSellerName,
       latest.DealerMobile AS LastSellerMobile
FROM BrandRollup AS rollup
OUTER APPLY (
  SELECT TOP 1 detail.SalesLine, detail.BranchName, detail.DealerId, detail.DealerName,
         COALESCE(NULLIF(LTRIM(RTRIM(contact.Mobile)), N''),
                  NULLIF(LTRIM(RTRIM(contact.Mobile2)), N'')) AS DealerMobile
  FROM SaleDetails AS detail
  LEFT JOIN dbo.Personnel AS personnel ON personnel.PersonnelId = detail.DealerId
  LEFT JOIN dbo.Contact AS contact ON contact.ContactId = personnel.ContactId
  WHERE detail.CustomerId = rollup.CustomerId AND detail.BrandRef = rollup.BrandRef
  ORDER BY detail.ReportDate DESC, detail.SellId DESC, detail.SellDetailID DESC
) AS latest
UNION ALL
SELECT N'line' AS RecordKind, rollup.CustomerId, N'' AS BrandName,
       rollup.InvoiceCount, rollup.NetSales, rollup.LastPurchaseDate,
       0 AS IsSellerLineBrand, rollup.SalesLine, rollup.BranchName,
       latest.DealerId AS LastSellerId, latest.DealerName AS LastSellerName,
       latest.DealerMobile AS LastSellerMobile
FROM LineRollup AS rollup
OUTER APPLY (
  SELECT TOP 1 detail.DealerId, detail.DealerName,
         COALESCE(NULLIF(LTRIM(RTRIM(contact.Mobile)), N''),
                  NULLIF(LTRIM(RTRIM(contact.Mobile2)), N'')) AS DealerMobile
  FROM SaleDetails AS detail
  LEFT JOIN dbo.Personnel AS personnel ON personnel.PersonnelId = detail.DealerId
  LEFT JOIN dbo.Contact AS contact ON contact.ContactId = personnel.ContactId
  WHERE detail.CustomerId = rollup.CustomerId
    AND detail.SalesLine = rollup.SalesLine
    AND detail.BranchName = rollup.BranchName
  ORDER BY detail.ReportDate DESC, detail.SellId DESC, detail.SellDetailID DESC
) AS latest
ORDER BY CustomerId, RecordKind, InvoiceCount DESC, BrandName
""".strip()
    customer_brand_rows = _query_rows(settings, customer_brand_sql)
    customer_brand_presence: dict[str, list[dict[str, Any]]] = {}
    customer_line_brand_presence: dict[str, list[dict[str, Any]]] = {}
    customer_line_purchase_summary: dict[str, list[dict[str, Any]]] = {}
    for row in customer_brand_rows:
        customer_id = str(row["CustomerId"] or "")
        if str(row.get("RecordKind") or "brand") == "line":
            customer_line_purchase_summary.setdefault(customer_id, []).append({
                "name": str(row.get("SalesLine") or "").strip() or "ظ„ط§غŒظ† ظ†ط§ظ…ط´ط®طµ",
                "branch": str(row.get("BranchName") or "").strip(),
                "invoice_count": int(row.get("InvoiceCount") or 0),
                "net_sales": float(row.get("NetSales") or 0),
                "last_purchase_date": str(row.get("LastPurchaseDate") or ""),
                "last_seller_id": int(row["LastSellerId"]) if row.get("LastSellerId") is not None else None,
                "last_seller_name": str(row.get("LastSellerName") or "").strip(),
                "last_seller_mobile": str(row.get("LastSellerMobile") or "").strip(),
            })
            continue
        brand = {
            "name": str(row["BrandName"] or "").strip(),
            "invoice_count": int(row["InvoiceCount"] or 0),
            "net_sales": float(row.get("NetSales") or 0),
            "last_purchase_date": str(row.get("LastPurchaseDate") or ""),
            "sales_line": str(row.get("SalesLine") or "").strip(),
            "branch": str(row.get("BranchName") or "").strip(),
            "last_seller_id": int(row["LastSellerId"]) if row.get("LastSellerId") is not None else None,
            "last_seller_name": str(row.get("LastSellerName") or "").strip(),
            "last_seller_mobile": str(row.get("LastSellerMobile") or "").strip(),
        }
        if not brand["name"]:
            continue
        customer_brand_presence.setdefault(customer_id, []).append(brand)
        if int(row["IsSellerLineBrand"] or 0):
            customer_line_brand_presence.setdefault(customer_id, []).append(brand)
    invoice_timing_sql = f"""
WITH RouteCustomers AS (
  SELECT DISTINCT customer.BackOfficeId
  FROM NGT.Personnels AS personnel
  INNER JOIN NGT.VisitTemplates AS template ON template.Id = personnel.VisitTemplateUniqueId
  INNER JOIN NGT.VisitTemplatePaths AS path ON path.VisitTemplateUniqueId = template.Id
  INNER JOIN (
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId FROM NGT.VisitTemplatePathCustomers WHERE ISNULL(IsRemoved, 0) = 0
    UNION
    SELECT VisitTemplatePathUniqueId, CustomerUniqueId FROM NGT.VisitTemplatePathSecondaryCustomers WHERE ISNULL(IsRemoved, 0) = 0
  ) AS assigned ON assigned.VisitTemplatePathUniqueId = path.Id
  INNER JOIN NGT.Customers AS customer ON customer.Id = assigned.CustomerUniqueId
  WHERE personnel.BackOfficeId = N'{personnel_id}'
    AND path.Id = CAST(N'{clean_path_id}' AS uniqueidentifier)
    AND ISNULL(personnel.IsRemoved, 0) = 0 AND ISNULL(personnel.PersonnelIsActive, 1) = 1
    AND ISNULL(template.IsRemoved, 0) = 0 AND ISNULL(path.IsRemoved, 0) = 0
    AND ISNULL(customer.IsRemoved, 0) = 0 AND ISNULL(customer.IsActive, 1) = 1
)
SELECT sale.CustomerId, sale.SellId, MAX(sale.ReportDate) AS ReportDate
FROM dbo.SalesReviewFast AS sale
INNER JOIN RouteCustomers AS route ON TRY_CONVERT(int, route.BackOfficeId) = sale.CustomerId
WHERE sale.ReportDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
GROUP BY sale.CustomerId, sale.SellId
""".strip()
    invoice_rows = _query_rows(settings, invoice_timing_sql)

    invoice_months: dict[str, list[int]] = {}
    for row in invoice_rows:
        month = _sales_month_serial(row["ReportDate"])
        if month is not None:
            invoice_months.setdefault(str(row["CustomerId"] or ""), []).append(month)
    current_month = max((month for months in invoice_months.values() for month in months), default=0)
    active_line_brand_count = len(seller_brands(settings, username).get("brand_details") or [])
    if not rows:
        # Keep the ownership check separate so an empty route is not mistaken for an unauthorized route.
        route = seller_route_customers(settings, username, clean_path_id)
        return {"route": route["route"], "customer_count": 0, "customers": [], "brand_invoice_presence": brand_invoice_presence, "source": "Acc.vwRcvSaleReview + dbo.SalesReviewFast", "live_assignment": True}
    customers = []
    for row in rows:
        customer_id = str(row["BackOfficeId"] or "")
        purchased_brands = customer_brand_presence.get(customer_id, [])
        line_purchased_brands = customer_line_brand_presence.get(customer_id, [])
        months = invoice_months.get(customer_id, [])
        all_brand_purchase_score = sum(brand["invoice_count"] for brand in purchased_brands)
        line_brand_purchase_score = sum(brand["invoice_count"] for brand in line_purchased_brands)
        visit_score, score_breakdown = _visit_score_components(
            months,
            all_brand_purchase_score=all_brand_purchase_score,
            line_brand_purchase_score=line_brand_purchase_score,
            line_brand_count=len(line_purchased_brands),
            active_line_brand_count=active_line_brand_count,
            current_month=current_month,
        )
        customers.append({
            "id": int(customer_id) if customer_id.isdigit() else customer_id,
            "code": str(row["CustomerCode"] or "").strip(),
            "name": str(row["CustomerName"] or "").strip(),
            "store_name": str(row["StoreName"] or "").strip(),
            "company_invoice_count_12m": int(row["CompanyInvoiceCount12M"] or 0),
            "company_net_sales_12m": float(row["CompanyNetSales12M"] or 0),
            "last_invoice_date": str(row["LastInvoiceDate"] or ""),
            "seller_invoice_count_12m": int(row["SellerInvoiceCount12M"] or 0),
            "seller_net_sales_12m": float(row["SellerNetSales12M"] or 0),
            "purchased_brands": purchased_brands,
            "line_purchased_brands": line_purchased_brands,
            "line_purchase_summary": customer_line_purchase_summary.get(customer_id, []),
            "line_brand_count": len(line_purchased_brands),
            "purchased_brand_count": len(purchased_brands),
            "visit_score": visit_score,
            "score_breakdown": score_breakdown,
        })
    def priority_key(customer: dict[str, Any]) -> tuple[int, int, int]:
        compact_date = customer["last_invoice_date"].replace("/", "").replace("-", "")
        return (
        -customer["visit_score"],
        -customer["line_brand_count"],
            -int(compact_date) if compact_date.isdigit() else 0,
        )

    customers.sort(key=priority_key)
    return {
        "route": {"id": clean_path_id, "title": str(rows[0]["PathTitle"] or "").strip()},
        "customer_count": len(customers), "customers": customers,
        "brand_invoice_presence": brand_invoice_presence,
        "source": "Acc.vwRcvSaleReview + dbo.SalesReviewFast (seller-scoped)", "live_assignment": True,
    }


def seller_open_invoices(settings: Any, username: str) -> dict[str, Any]:
    """List every open invoice owned by the authenticated seller, regardless of current assignment."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    invoices_sql = f"""
SELECT customer.BackOfficeId, customer.CustomerCode, customer.CustomerName,
       customer.StoreName, customer.Address, customer.Phone, customer.Mobile,
       ISNULL(returned_cheques.ReturnChequeCount, 0) AS ReturnChequeCount,
       ISNULL(returned_cheques.ReturnChequeAmount, 0) AS ReturnChequeAmount,
       ISNULL(cardex.CustomerCardexBalance, 0) AS CustomerCardexBalance,
       ISNULL(open_invoices.OpenInvoiceRemaining, 0) AS OpenInvoiceRemaining,
       ISNULL(open_invoices.OpenInvoiceCount, 0) AS OpenInvoiceCount,
       open_invoices.OldestOpenInvoiceDate
FROM NGT.Customers AS customer
OUTER APPLY (
  SELECT SUM(balance.Balance) AS CustomerCardexBalance
  FROM Acc.vwCustomerBalance AS balance
  WHERE balance.CustRef = TRY_CONVERT(int, customer.BackOfficeId)
) AS cardex
OUTER APPLY (
  SELECT SUM(info.ReturnChequeCount) AS ReturnChequeCount,
         SUM(info.ReturnChequeAmount) AS ReturnChequeAmount
  FROM Acc.tblCustRemInfo AS info
  WHERE info.CustRef = TRY_CONVERT(int, customer.BackOfficeId)
) AS returned_cheques
INNER JOIN (
  SELECT invoice.CustId, SUM(invoice.RemainingAmount) AS OpenInvoiceRemaining,
         COUNT(*) AS OpenInvoiceCount, MIN(invoice.InvoiceDate) AS OldestOpenInvoiceDate
  FROM (
    SELECT sale.CustId, sale.SaleId, MAX(sale.RemainingAmount) AS RemainingAmount,
           COALESCE(MIN(sale.SaleDate), MIN(sale.SaleVocherDate), MIN(sale.ReportDate)) AS InvoiceDate
    FROM Acc.vwRcvSaleReview AS sale
    WHERE sale.DealerId = {personnel_id}
      AND sale.RemainingAmount > 0
    GROUP BY sale.CustId, sale.SaleId
  ) AS invoice
  GROUP BY invoice.CustId
) AS open_invoices ON open_invoices.CustId = TRY_CONVERT(int, customer.BackOfficeId)
WHERE open_invoices.OpenInvoiceRemaining > 0
ORDER BY open_invoices.OldestOpenInvoiceDate, customer.StoreName, customer.CustomerName
""".strip()
    rows = _query_rows(settings, invoices_sql)
    customers = [
        {
            "id": int(row["BackOfficeId"]) if str(row["BackOfficeId"] or "").isdigit() else str(row["BackOfficeId"] or ""),
            "code": str(row["CustomerCode"] or "").strip(),
            "name": str(row["CustomerName"] or "").strip(),
            "store_name": str(row["StoreName"] or "").strip(),
            "address": str(row["Address"] or "").strip(),
            "phone": str(row["Phone"] or "").strip(),
            "mobile": str(row["Mobile"] or "").strip(),
            "return_cheque_count": int(row["ReturnChequeCount"] or 0),
            "return_cheque_amount": float(row["ReturnChequeAmount"] or 0),
            "cardex_balance": float(row["CustomerCardexBalance"] or 0),
            "open_invoice_remaining": float(row["OpenInvoiceRemaining"] or 0),
            "open_invoice_count": int(row["OpenInvoiceCount"] or 0),
            "oldest_open_invoice_date": str(row["OldestOpenInvoiceDate"] or ""),
        }
        for row in rows
    ]
    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "customer_count": len(customers),
        "open_invoice_remaining": sum(customer["open_invoice_remaining"] for customer in customers),
        "customers": customers,
        "source": "Acc.vwRcvSaleReview",
        "live_assignment": True,
    }


def seller_customer_open_invoices(settings: Any, username: str, customer_id: str) -> dict[str, Any]:
    """List the authenticated seller's open invoices for one customer."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    try:
        clean_customer_id = int(customer_id)
    except (TypeError, ValueError) as exc:
        raise SellerWorkspaceError("Customer was not found") from exc

    invoices_sql = f"""
SELECT sale.SaleId, MAX(sale.SaleNo) AS InvoiceNumber,
       COALESCE(MIN(sale.SaleDate), MIN(sale.SaleVocherDate), MIN(sale.ReportDate)) AS InvoiceDate,
       MAX(sale.SalesNetAmount) AS InvoiceAmount,
       MAX(sale.RemainingAmount) AS RemainingAmount
FROM Acc.vwRcvSaleReview AS sale
WHERE sale.CustId = {clean_customer_id}
  AND sale.DealerId = {personnel_id}
  AND sale.RemainingAmount > 0
GROUP BY sale.SaleId
ORDER BY COALESCE(MIN(sale.SaleDate), MIN(sale.SaleVocherDate), MIN(sale.ReportDate)), sale.SaleId
""".strip()
    rows = _query_rows(settings, invoices_sql)
    invoices = [
        {
            "id": int(row["SaleId"]),
            "number": str(row["InvoiceNumber"] or "").strip(),
            "date": str(row["InvoiceDate"] or ""),
            "amount": float(row["InvoiceAmount"] or 0),
            "remaining_amount": float(row["RemainingAmount"] or 0),
        }
        for row in rows
    ]
    return {
        "customer_id": clean_customer_id,
        "invoice_count": len(invoices),
        "invoices": invoices,
        "source": "Acc.vwRcvSaleReview",
    }


def _customer_cheque_intelligence(settings: Any, customer_id: str) -> dict[str, Any]:
    """Read stable customer cheque status/history without changing Varanegar."""
    try:
        clean_customer_id = int(customer_id)
    except (TypeError, ValueError) as exc:
        raise SellerWorkspaceError("Customer was not found") from exc

    summary_sql = f"""
WITH HistoryFlags AS (
  SELECT history.RChequeId,
         MAX(CASE WHEN history.RChequeStatusId = 4 THEN 1 ELSE 0 END) AS HadReturn
  FROM dbo.RChequeHistory AS history
  GROUP BY history.RChequeId
), Settled AS (
  SELECT settlement.RetChequeRef AS RChequeId,
         SUM(ISNULL(settlement.SettlementAmount, 0)) AS SettledAmount,
         MAX(settlement.SettlementDate) AS LastSettlementDate
  FROM dbo.Settlement2 AS settlement
  WHERE settlement.RetChequeRef IS NOT NULL
  GROUP BY settlement.RetChequeRef
)
SELECT
  COUNT(DISTINCT CASE WHEN cheque.RChequeStatusId = 3
       AND cheque.LastStatusDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
       THEN cheque.RChequeId END) AS PaidChequeCount12M,
  SUM(CASE WHEN cheque.RChequeStatusId = 3
       AND cheque.LastStatusDate >= FORMAT(DATEADD(YEAR, -1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
       THEN ISNULL(cheque.RChequeAmount, 0) ELSE 0 END) AS PaidChequeAmount12M,
  COUNT(DISTINCT CASE WHEN cheque.RChequeStatusId = 4 THEN cheque.RChequeId END) AS ActiveReturnedCount,
  SUM(CASE WHEN cheque.RChequeStatusId = 4 THEN ISNULL(cheque.RChequeAmount, 0) ELSE 0 END) AS ActiveReturnedAmount,
  COUNT(DISTINCT CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 3 THEN cheque.RChequeId END) AS CollectedAfterReturnCount,
  SUM(CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 3 THEN ISNULL(cheque.RChequeAmount, 0) ELSE 0 END) AS CollectedAfterReturnAmount,
  COUNT(DISTINCT CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 5 THEN cheque.RChequeId END) AS RefundedAfterReturnCount,
  SUM(CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 5 THEN ISNULL(cheque.RChequeAmount, 0) ELSE 0 END) AS RefundedAfterReturnAmount,
  COUNT(DISTINCT CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 9 THEN cheque.RChequeId END) AS LegalReturnedCount,
  SUM(CASE WHEN flags.HadReturn = 1 AND cheque.RChequeStatusId = 9 THEN ISNULL(cheque.RChequeAmount, 0) ELSE 0 END) AS LegalReturnedAmount,
  COUNT(DISTINCT CASE WHEN flags.HadReturn = 1
       AND ISNULL(settled.SettledAmount, 0) >= ISNULL(cheque.RChequeAmount, 0)
       AND ISNULL(cheque.RChequeAmount, 0) > 0 THEN cheque.RChequeId END) AS FullySettledReturnedCount,
  SUM(CASE WHEN flags.HadReturn = 1 THEN
       CASE WHEN ISNULL(settled.SettledAmount, 0) > ISNULL(cheque.RChequeAmount, 0)
            THEN ISNULL(cheque.RChequeAmount, 0) ELSE ISNULL(settled.SettledAmount, 0) END
       ELSE 0 END) AS ReturnedSettlementAmount
FROM dbo.RCheque2 AS cheque
LEFT JOIN HistoryFlags AS flags ON flags.RChequeId = cheque.RChequeId
LEFT JOIN Settled AS settled ON settled.RChequeId = cheque.RChequeId
WHERE cheque.CustomerId = {clean_customer_id}
""".strip()
    summary_rows = _query_rows(settings, summary_sql)
    row = summary_rows[0] if summary_rows else {}

    details_sql = f"""
WITH HistoryFlags AS (
  SELECT history.RChequeId,
         MAX(CASE WHEN history.RChequeStatusId = 4 THEN 1 ELSE 0 END) AS HadReturn,
         MIN(CASE WHEN history.RChequeStatusId = 4 THEN history.StatusDate END) AS FirstReturnDate
  FROM dbo.RChequeHistory AS history
  GROUP BY history.RChequeId
), Settled AS (
  SELECT settlement.RetChequeRef AS RChequeId,
         SUM(ISNULL(settlement.SettlementAmount, 0)) AS SettledAmount,
         MAX(settlement.SettlementDate) AS LastSettlementDate
  FROM dbo.Settlement2 AS settlement
  WHERE settlement.RetChequeRef IS NOT NULL
  GROUP BY settlement.RetChequeRef
)
SELECT TOP 50 cheque.RChequeId, cheque.RChequeNo, cheque.RChequeDate,
       cheque.RChequeAmount, cheque.BankName, cheque.RChequeBranchName,
       cheque.RChequeStatusId, cheque.RChequeStatusName, cheque.LastStatusDate,
       flags.FirstReturnDate, ISNULL(settled.SettledAmount, 0) AS SettledAmount,
       settled.LastSettlementDate
FROM dbo.RCheque2 AS cheque
INNER JOIN HistoryFlags AS flags ON flags.RChequeId = cheque.RChequeId AND flags.HadReturn = 1
LEFT JOIN Settled AS settled ON settled.RChequeId = cheque.RChequeId
WHERE cheque.CustomerId = {clean_customer_id}
  AND cheque.RChequeStatusId IN (3, 4, 5, 9)
ORDER BY cheque.LastStatusDate DESC, cheque.RChequeId DESC
""".strip()
    detail_rows = _query_rows(settings, details_sql)
    lifecycle = {
        3: "collected_after_return",
        4: "active_returned",
        5: "refunded_after_return",
        9: "legal_returned",
    }
    cheques = []
    for item in detail_rows:
        amount = float(item.get("RChequeAmount") or 0)
        settled_amount = min(float(item.get("SettledAmount") or 0), amount) if amount > 0 else 0.0
        status_id = int(item.get("RChequeStatusId") or 0)
        cheques.append({
            "id": int(item["RChequeId"]),
            "number": str(item.get("RChequeNo") or "").strip(),
            "date": str(item.get("RChequeDate") or ""),
            "amount": amount,
            "bank": str(item.get("BankName") or "").strip(),
            "branch": str(item.get("RChequeBranchName") or "").strip(),
            "status_id": status_id,
            "status": str(item.get("RChequeStatusName") or "").strip(),
            "status_date": str(item.get("LastStatusDate") or ""),
            "first_return_date": str(item.get("FirstReturnDate") or ""),
            "settled_amount": settled_amount,
            "last_settlement_date": str(item.get("LastSettlementDate") or ""),
            "lifecycle": lifecycle.get(status_id, "returned_history"),
            "fully_settled": amount > 0 and settled_amount >= amount,
        })

    summary = {
        "paid_12m_count": int(row.get("PaidChequeCount12M") or 0),
        "paid_12m_amount": float(row.get("PaidChequeAmount12M") or 0),
        "active_returned_count": int(row.get("ActiveReturnedCount") or 0),
        "active_returned_amount": float(row.get("ActiveReturnedAmount") or 0),
        "collected_after_return_count": int(row.get("CollectedAfterReturnCount") or 0),
        "collected_after_return_amount": float(row.get("CollectedAfterReturnAmount") or 0),
        "refunded_after_return_count": int(row.get("RefundedAfterReturnCount") or 0),
        "refunded_after_return_amount": float(row.get("RefundedAfterReturnAmount") or 0),
        "legal_returned_count": int(row.get("LegalReturnedCount") or 0),
        "legal_returned_amount": float(row.get("LegalReturnedAmount") or 0),
        "fully_settled_returned_count": int(row.get("FullySettledReturnedCount") or 0),
        "returned_settlement_amount": float(row.get("ReturnedSettlementAmount") or 0),
    }
    return {
        "customer_id": clean_customer_id,
        "summary": summary,
        "cheques": cheques,
        "source": "dbo.RCheque2 + dbo.RChequeHistory + dbo.Settlement2",
        "classification": {
            "paid": "current_status_3",
            "active_returned": "current_status_4",
            "refunded_after_return": "history_status_4_then_current_status_5",
            "fully_settled": "settlement_total_gte_cheque_amount",
        },
    }


def seller_customer_visit_workspace(
    settings: Any,
    username: str,
    path_id: str,
    customer_id: str,
) -> dict[str, Any]:
    """Build the read-only customer intelligence used inside one seller visit."""
    profile = seller_route_customer_profile(settings, username, path_id, customer_id)
    resolved_customer_id = str(profile["customer"]["id"])
    # These three read-only datasets are independent once the customer has
    # been resolved. Running them concurrently removes avoidable serial SQL
    # latency from the first visit workspace load.
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="seller-visit") as executor:
        analytics_future = executor.submit(
            seller_route_day_analytics, settings, username, path_id
        )
        invoices_future = executor.submit(
            seller_customer_open_invoices, settings, username, resolved_customer_id
        )
        cheques_future = executor.submit(
            _customer_cheque_intelligence, settings, resolved_customer_id
        )
        route_analytics = analytics_future.result()
        open_invoices = invoices_future.result()
        cheque_intelligence = cheques_future.result()
    customer_analytics = next(
        (
            item
            for item in route_analytics.get("customers") or []
            if str(item.get("id")) == resolved_customer_id
        ),
        {},
    )
    return {
        "route": profile["route"],
        "customer": profile["customer"],
        "analytics": customer_analytics,
        "open_invoices": open_invoices,
        "cheques": cheque_intelligence,
        "sources": {
            "profile": "NGT.Customers + current seller route assignment",
            "purchase_intelligence": route_analytics.get("source"),
            "open_invoices": open_invoices.get("source"),
            "cheques": cheque_intelligence.get("source"),
        },
        "read_only": True,
    }


def seller_returned_cheques(settings: Any, username: str) -> dict[str, Any]:
    """List returned cheques allocated to the authenticated seller's invoices."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    sql = f"""
SELECT cheque.ChequeId, cheque.ChequeNo, cheque.ChequeDate, cheque.ChequeAmount,
       cheque.BankName, cheque.BranchName, cheque.CustId, cheque.CustCode,
       cheque.CustFullName, cheque.CustStoreName, cheque.LastStatusName,
       cheque.LastStatusDate, cheque.AccountName, customer.Phone AS CustomerPhone,
       customer.Mobile AS CustomerMobile, allocation.SellerShare,
       ISNULL(settlement.SettledAmount, 0) AS SettledAmount
FROM (
  SELECT returned.ChequeId, MAX(returned.ChequeNo) AS ChequeNo,
         MAX(returned.ChequeDate) AS ChequeDate, MAX(returned.ChequeAmount) AS ChequeAmount,
         MAX(returned.BankName) AS BankName, MAX(returned.BranchName) AS BranchName,
         MAX(returned.CustId) AS CustId, MAX(returned.CustCode) AS CustCode,
         MAX(returned.CustFullName) AS CustFullName, MAX(returned.CustStoreName) AS CustStoreName,
         MAX(returned.LastStatusName) AS LastStatusName, MAX(returned.LastStatusDate) AS LastStatusDate,
         MAX(returned.AccountName) AS AccountName
  FROM Acc.vwRcvRetChequeReview AS returned
  GROUP BY returned.ChequeId
) AS cheque
INNER JOIN (
  SELECT payment.ChequeId, SUM(payment.PayAmount) AS SellerShare
  FROM Acc.vwRcvPaymentsReview AS payment
  WHERE payment.DealerId = {personnel_id}
    AND payment.ChequeId IS NOT NULL
  GROUP BY payment.ChequeId
) AS allocation ON allocation.ChequeId = cheque.ChequeId
LEFT JOIN NGT.Customers AS customer ON TRY_CONVERT(int, customer.BackOfficeId) = cheque.CustId
OUTER APPLY (
  SELECT SUM(item.SettlementAmount) AS SettledAmount
  FROM dbo.Settlement2 AS item
  WHERE item.RetChequeRef = cheque.ChequeId
) AS settlement
WHERE allocation.SellerShare > 0
ORDER BY cheque.LastStatusDate DESC, cheque.ChequeDate DESC, cheque.ChequeId DESC
""".strip()
    rows = _query_rows(settings, sql)
    cheques = [
        {
            "id": int(row["ChequeId"]), "number": str(row["ChequeNo"] or "").strip(),
            "date": str(row["ChequeDate"] or ""), "amount": float(row["ChequeAmount"] or 0),
            "bank": str(row["BankName"] or "").strip(), "branch": str(row["BranchName"] or "").strip(),
            "customer_id": int(row["CustId"]) if row["CustId"] is not None else None,
            "customer_code": str(row["CustCode"] or "").strip(),
            "customer_name": str(row["CustFullName"] or "").strip(),
            "customer_store": str(row["CustStoreName"] or "").strip(),
            "account_name": str(row["AccountName"] or "").strip(),
            "customer_phone": str(row["CustomerPhone"] or "").strip(),
            "customer_mobile": str(row["CustomerMobile"] or "").strip(),
            "status": str(row["LastStatusName"] or "").strip(),
            "status_date": str(row["LastStatusDate"] or ""),
            "seller_share": float(row["SellerShare"] or 0),
            "settled_amount": float(row["SettledAmount"] or 0),
        }
        for row in rows
    ]
    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "cheque_count": len(cheques),
        "cheque_amount": sum(item["amount"] for item in cheques),
        "seller_share": sum(item["seller_share"] for item in cheques),
        "settled_amount": sum(item["settled_amount"] for item in cheques),
        "cheques": cheques,
        "source": "Acc.vwRcvRetChequeReview",
    }


def seller_distribution_in_progress(settings: Any, username: str) -> dict[str, Any]:
    """List the seller's dispatched invoices for today and distributions scheduled for tomorrow."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    sql = f"""
SELECT sale.ID AS SaleId, sale.SaleNo, sale.SaleVocherNo, sale.SaleDate,
       sale.TotalAmount, customer.CustomerCode, customer.CustomerName, customer.StoreName,
       dist.DistNo, dist.DistDate, dist.SendDate,
       driver.ContactName AS DriverName, driver.Mobile AS DriverMobile
FROM SLE.tblSaleHdr AS sale
INNER JOIN SLE.tblDist AS dist ON dist.ID = sale.DistRef
LEFT JOIN NGT.Customers AS customer ON TRY_CONVERT(int, customer.BackOfficeId) = sale.CustRef
LEFT JOIN dbo.Personnel AS driver_personnel ON driver_personnel.PersonnelId = dist.DriverRef
LEFT JOIN dbo.Contact AS driver ON driver.ContactId = driver_personnel.ContactId
WHERE sale.DealerRef = {personnel_id}
  AND ISNULL(sale.CancelFlag, 0) = 0
  AND dist.DistDate IN (
      FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR'),
      FORMAT(DATEADD(DAY, 1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
  )
  AND (
      dist.SendDate IS NOT NULL
      OR dist.DistDate = FORMAT(DATEADD(DAY, 1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')
  )
  AND (dist.ReturnDate IS NULL OR CONVERT(date, dist.ReturnDate) <= CONVERT(date, '19000101'))
ORDER BY dist.DistDate, dist.SendDate, dist.DistNo, sale.ID
""".strip()
    rows = _query_rows(settings, sql)
    invoices = [
        {
            "id": int(row["SaleId"]),
            "number": str(row["SaleNo"] or row["SaleVocherNo"] or row["SaleId"]),
            "sale_date": str(row["SaleDate"] or ""),
            "amount": float(row["TotalAmount"] or 0),
            "customer_code": str(row["CustomerCode"] or "").strip(),
            "customer_name": str(row["CustomerName"] or "").strip(),
            "customer_store": str(row["StoreName"] or "").strip(),
            "distribution_number": str(row["DistNo"] or "").strip(),
            "distribution_date": str(row["DistDate"] or ""),
            "sent_at": str(row["SendDate"] or ""),
            "driver_name": str(row["DriverName"] or "").strip(),
            "driver_mobile": str(row["DriverMobile"] or "").strip(),
        }
        for row in rows
    ]
    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "distribution_date": str(rows[0]["DistDate"] or "") if rows else "",
        "distribution_dates": list(dict.fromkeys(str(row["DistDate"] or "") for row in rows if row["DistDate"])),
        "invoice_count": len(invoices),
        "invoices": invoices,
        "source": "SLE.tblSaleHdr + SLE.tblDist",
    }


def seller_voucher_return_report(settings: Any, username: str) -> dict[str, Any]:
    """Summarize the current Persian-calendar month's seller vouchers and returns."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    sql = f"""
SELECT MAX(FORMAT(GETDATE(), 'yyyy/MM', 'fa-IR')) AS ReportMonth,
       COUNT(DISTINCT voucher.ID) AS VoucherCount,
       COUNT(DISTINCT CASE WHEN ISNULL(sale.CancelFlag, 0) = 0
                                  AND NULLIF(LTRIM(RTRIM(sale.SaleNo)), '') IS NOT NULL
                           THEN voucher.ID END) AS InvoicedCount,
       COUNT(DISTINCT CASE WHEN ISNULL(sale.CancelFlag, 0) = 1 THEN voucher.ID END) AS FullReturnedCount,
       COUNT(DISTINCT CASE WHEN ISNULL(sale.CancelFlag, 0) = 0
                                  AND NULLIF(LTRIM(RTRIM(sale.SaleNo)), '') IS NULL
                           THEN voucher.ID END) AS UndistributedCount
FROM SLE.tblSaleVocherHdr AS voucher
LEFT JOIN SLE.tblSaleHdr AS sale ON sale.ID = voucher.SaleRef
WHERE voucher.DealerRef = {personnel_id}
  AND voucher.SaleVocherDate LIKE FORMAT(GETDATE(), 'yyyy/MM', 'fa-IR') + '/%'
""".strip()
    row = _query_rows(settings, sql)[0]
    vouchers = int(row["VoucherCount"] or 0)
    full_returned = int(row["FullReturnedCount"] or 0)
    invoiced = int(row["InvoicedCount"] or 0)
    undistributed = int(row["UndistributedCount"] or 0)
    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "report_month": str(row["ReportMonth"] or ""),
        "voucher_count": vouchers,
        "invoiced_count": invoiced,
        "full_returned_count": full_returned,
        "undistributed_count": undistributed,
        "returned_count": full_returned,
        "reconciled_voucher_count": invoiced + full_returned + undistributed,
        "return_percentage": round((full_returned / vouchers * 100) if vouchers else 0, 2),
        "source": "SLE.tblSaleVocherHdr",
    }


def seller_brands(settings: Any, username: str) -> dict[str, Any]:
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    supervisor_id = int(profile["supervisor_personnel_id"])
    catalog_sql = f"""
SELECT pt.ProductTemplateName, brand.id AS BrandRef, brand.BrandName,
       COUNT(DISTINCT detail.ProductUniqueId) AS ProductCount
FROM NGT.Personnels AS personnel
LEFT JOIN NGT.VisitTemplates AS visit_template
  ON visit_template.Id = personnel.VisitTemplateUniqueId
 AND ISNULL(visit_template.IsRemoved, 0) = 0
INNER JOIN NGT.ProductTemplates AS pt
  ON pt.Id = COALESCE(
    personnel.ProductTemplateUniqueId, visit_template.ProductTemplateUniqueId
  )
INNER JOIN NGT.ProductTemplateDetails AS detail
  ON detail.ProductTemplateUniqueId = pt.Id
INNER JOIN GNR.tblGoods AS goods ON goods.UniqueId = detail.ProductUniqueId
INNER JOIN GNR.tblBrand AS brand ON brand.id = goods.BrandRef
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(pt.IsRemoved, 0) = 0
  AND ISNULL(detail.IsRemoved, 0) = 0
  AND NULLIF(LTRIM(RTRIM(brand.BrandName)), '') IS NOT NULL
GROUP BY pt.ProductTemplateName, brand.id, brand.BrandName
ORDER BY brand.BrandName
""".strip()
    assigned = _query_rows(settings, catalog_sql)
    brand_details = [
        {
            "id": int(row["BrandRef"]),
            "name": str(row["BrandName"] or "").strip(),
            "product_count": int(row["ProductCount"] or 0),
        }
        for row in assigned if str(row["BrandName"] or "").strip()
    ]
    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "supervisor": {"personnel_id": supervisor_id},
        "branch": profile["branch"],
        "sales_line": profile["sales_line"],
        "product_template": str(assigned[0]["ProductTemplateName"] or "") if assigned else "",
        "brands": [brand["name"] for brand in brand_details],
        "brand_details": brand_details,
        "configured": bool(assigned),
        "source": "NGT.ProductTemplateDetails",
        "live_assignment": True,
    }
