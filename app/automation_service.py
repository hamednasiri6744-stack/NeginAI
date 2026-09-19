from __future__ import annotations

import json
import hashlib
import hmac
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.config import ROOT_DIR, Settings
from app.database import sqlite_connection
from app.push_service import send_user_push


TEHRAN_TIMEZONE = "Asia/Tehran"
MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 7 * 24 * 60
LOCK_MINUTES = 15
REPORT_LINK_SECONDS = 30 * 24 * 60 * 60


class AutomationError(ValueError):
    pass


class AutomationRunTimeout(TimeoutError):
    pass


class ConditionDecision(BaseModel):
    triggered: bool
    reason: str = Field(max_length=1000)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    current = value or utc_now()
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _parse_daily_time(value: str | None) -> time:
    try:
        parsed = datetime.strptime(str(value or ""), "%H:%M")
    except ValueError as exc:
        raise AutomationError("daily_time must use HH:MM, for example 09:00") from exc
    return parsed.time()


def calculate_next_run(
    schedule_kind: Literal["interval", "daily"],
    interval_minutes: int | None,
    daily_time: str | None,
    now: datetime | None = None,
    timezone_name: str = TEHRAN_TIMEZONE,
    allow_current_minute: bool = False,
) -> datetime:
    current = _as_utc(now)
    if schedule_kind == "interval":
        minutes = int(interval_minutes or 0)
        if not MIN_INTERVAL_MINUTES <= minutes <= MAX_INTERVAL_MINUTES:
            raise AutomationError(
                f"interval_minutes must be between {MIN_INTERVAL_MINUTES} and {MAX_INTERVAL_MINUTES}"
            )
        return current + timedelta(minutes=minutes)
    if schedule_kind != "daily":
        raise AutomationError("schedule_kind must be interval or daily")
    target_time = _parse_daily_time(daily_time)
    local_zone = ZoneInfo(timezone_name)
    local_now = current.astimezone(local_zone)
    candidate = datetime.combine(local_now.date(), target_time, local_zone)
    if candidate <= local_now:
        within_current_minute = local_now - candidate < timedelta(minutes=1)
        if not (allow_current_minute and within_current_minute):
            candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _public_automation(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "title": str(row["title"]),
        "query_text": str(row["query_text"]),
        "condition_text": row["condition_text"],
        "schedule_kind": str(row["schedule_kind"]),
        "interval_minutes": row["interval_minutes"],
        "daily_time": row["daily_time"],
        "timezone": str(row["timezone"]),
        "active": bool(row["active"]),
        "next_run_at": str(row["next_run_at"]),
        "last_run_at": row["last_run_at"],
        "last_status": row["last_status"],
        "last_error": row["last_error"],
        "created_at": str(row["created_at"]),
    }


def create_automation(
    settings: Settings,
    username: str,
    title: str,
    query_text: str,
    schedule_kind: Literal["interval", "daily"],
    interval_minutes: int | None = None,
    daily_time: str | None = None,
    condition_text: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    owner = username.strip()
    clean_title = title.strip()
    clean_query = query_text.strip()
    clean_condition = (condition_text or "").strip() or None
    if not owner:
        raise AutomationError("authenticated username is required")
    if not clean_title or len(clean_title) > 200:
        raise AutomationError("title must contain 1 to 200 characters")
    if not clean_query or len(clean_query) > 4000:
        raise AutomationError("query_text must contain 1 to 4000 characters")
    if clean_condition and len(clean_condition) > 2000:
        raise AutomationError("condition_text cannot exceed 2000 characters")
    current = _as_utc(now)
    next_run = calculate_next_run(
        schedule_kind,
        interval_minutes,
        daily_time,
        current,
        allow_current_minute=True,
    )
    created_at = current.isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            """INSERT INTO automations
               (username, title, query_text, condition_text, schedule_kind,
                interval_minutes, daily_time, timezone, active, next_run_at,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
            (
                owner,
                clean_title,
                clean_query,
                clean_condition,
                schedule_kind,
                interval_minutes if schedule_kind == "interval" else None,
                daily_time if schedule_kind == "daily" else None,
                TEHRAN_TIMEZONE,
                next_run.isoformat(),
                created_at,
                created_at,
            ),
        )
        row = conn.execute(
            "SELECT * FROM automations WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
    return _public_automation(row)


def list_automations(
    settings: Settings, username: str, include_inactive: bool = True
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM automations WHERE username=? AND deleted_at IS NULL"
    params: list[Any] = [username]
    if not include_inactive:
        sql += " AND active=1"
    sql += " ORDER BY active DESC, id DESC"
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_public_automation(row) for row in rows]


def set_automation_active(
    settings: Settings,
    username: str,
    automation_id: int,
    active: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _as_utc(now)
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT * FROM automations WHERE id=? AND username=? AND deleted_at IS NULL",
            (automation_id, username),
        ).fetchone()
        if row is None:
            raise AutomationError("automation not found")
        next_run = row["next_run_at"]
        if active:
            next_run = calculate_next_run(
                row["schedule_kind"],
                row["interval_minutes"],
                row["daily_time"],
                current,
                allow_current_minute=True,
            ).isoformat()
        conn.execute(
            """UPDATE automations
               SET active=?, next_run_at=?, locked_until=NULL, updated_at=?
               WHERE id=? AND username=?""",
            (int(active), next_run, current.isoformat(), automation_id, username),
        )
        updated = conn.execute(
            "SELECT * FROM automations WHERE id=?", (automation_id,)
        ).fetchone()
    return _public_automation(updated)


def delete_automation(settings: Settings, username: str, automation_id: int) -> None:
    stamp = utc_now().isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            """UPDATE automations
               SET active=0, deleted_at=?, locked_until=NULL, updated_at=?
               WHERE id=? AND username=? AND deleted_at IS NULL""",
            (stamp, stamp, automation_id, username),
        )
        if cursor.rowcount != 1:
            raise AutomationError("automation not found")


def list_notifications(
    settings: Settings,
    username: str,
    unread_only: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM notifications WHERE username=?"
    params: list[Any] = [username]
    if unread_only:
        sql += " AND read_at IS NULL"
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(limit, 100)))
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": int(row["id"]),
            "automation_id": row["automation_id"],
            "title": str(row["title"]),
            "body": str(row["body"]),
            "source": str(row["source"] or "automation"),
            "category": str(row["category"] or "general"),
            "severity": str(row["severity"] or "info"),
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "action_path": row["action_path"],
            "requires_ack": bool(row["requires_ack"]),
            "acknowledged": row["acknowledged_at"] is not None,
            "occurred_at": str(row["occurred_at"] or row["created_at"]),
            "read": row["read_at"] is not None,
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def mark_notifications_read(
    settings: Settings, username: str, notification_ids: list[int]
) -> int:
    ids = sorted({int(value) for value in notification_ids if int(value) > 0})[:100]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            f"UPDATE notifications SET read_at=? WHERE username=? AND read_at IS NULL AND id IN ({placeholders})",
            [utc_now().isoformat(), username, *ids],
        )
    return int(cursor.rowcount)


def acknowledge_notifications(
    settings: Settings, username: str, notification_ids: list[int]
) -> int:
    ids = sorted({int(value) for value in notification_ids if int(value) > 0})[:100]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    stamp = utc_now().isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            f"UPDATE notifications SET acknowledged_at=?, read_at=COALESCE(read_at, ?) WHERE username=? AND requires_ack=1 AND acknowledged_at IS NULL AND id IN ({placeholders})",
            [stamp, stamp, username, *ids],
        )
    return int(cursor.rowcount)


def create_notification_report_token(
    settings: Settings,
    notification_id: int,
    username: str,
    now: datetime | None = None,
) -> str:
    expires_at = int(_as_utc(now).timestamp()) + REPORT_LINK_SECONDS
    payload = f"{int(notification_id)}|{username}|{expires_at}"
    signature = hmac.new(
        settings.action_api_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{expires_at}.{signature}"


def get_notification_report(
    settings: Settings,
    notification_id: int,
    token: str,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if not settings.action_api_key:
        return None
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE id=?",
            (int(notification_id),),
        ).fetchone()
    if row is None:
        return None
    try:
        expires_text, supplied_signature = token.split(".", 1)
        expires_at = int(expires_text)
    except (TypeError, ValueError):
        return None
    if expires_at < int(_as_utc(now).timestamp()):
        return None
    payload = f"{int(notification_id)}|{row['username']}|{expires_at}"
    expected_signature = hmac.new(
        settings.action_api_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        report_payload = json.loads(str(row["payload_json"] or "{}"))
    except json.JSONDecodeError:
        report_payload = {}
    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "automation_id": row["automation_id"],
        "title": str(row["title"]),
        "body": str(row["body"]),
        "created_at": str(row["created_at"]),
        "payload": report_payload,
    }


def _claim_due(
    settings: Settings, now: datetime, limit: int
) -> list[dict[str, Any]]:
    stamp = now.isoformat()
    lock_until = (now + timedelta(minutes=LOCK_MINUTES)).isoformat()
    claimed: list[dict[str, Any]] = []
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """SELECT * FROM automations
               WHERE active=1 AND deleted_at IS NULL AND next_run_at<=?
                 AND (locked_until IS NULL OR locked_until<?)
               ORDER BY next_run_at, id LIMIT ?""",
            (stamp, stamp, max(1, min(limit, 10))),
        ).fetchall()
        for row in rows:
            updated = conn.execute(
                """UPDATE automations SET locked_until=?, updated_at=?
                   WHERE id=? AND (locked_until IS NULL OR locked_until<?)""",
                (lock_until, stamp, row["id"], stamp),
            )
            if updated.rowcount == 1:
                claimed.append(dict(row))
    return claimed


def _run_report_inline(settings: Settings, task: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_automation_api_key:
        raise RuntimeError("OPENAI_AUTOMATION_API_KEY is not configured")
    from app.chat_service import chat

    task_settings = replace(
        settings, openai_api_key=settings.openai_automation_api_key
    )
    local_time = utc_now().astimezone(ZoneInfo(TEHRAN_TIMEZONE)).isoformat()
    prompt = (
        "این یک اجرای خودکار پس‌زمینه است؛ اتوماسیون جدید نساز و فقط گزارش زنده را اجرا کن.\n"
        f"زمان اجرای تهران: {local_time}\n"
        f"درخواست گزارش: {task['query_text']}"
    )
    return chat(
        task_settings,
        prompt,
        f"automation-run-{task['id']}-{uuid4()}",
        str(task["username"]),
    )


def _run_report_in_subprocess(settings: Settings, task: dict[str, Any]) -> dict[str, Any]:
    """Run the agent outside the scheduler process so a hung run can be terminated."""
    python = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    executable = str(python if python.exists() else Path(sys.executable))
    fd, output_name = tempfile.mkstemp(prefix="neginai-automation-", suffix=".json")
    os.close(fd)
    output_path = Path(output_name)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        try:
            completed = subprocess.run(
                [
                    executable,
                    "-m",
                    "app.automation_worker",
                    str(int(task["id"])),
                    str(output_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                timeout=settings.automation_run_timeout_seconds,
                creationflags=creationflags,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AutomationRunTimeout(
                f"automation report exceeded {settings.automation_run_timeout_seconds} seconds"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or "automation worker failed")[-1000:].strip()
            raise RuntimeError(detail)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or "automation worker failed")[:2000])
        response = payload.get("response")
        if not isinstance(response, dict):
            raise RuntimeError("automation worker returned an invalid response")
        return response
    finally:
        output_path.unlink(missing_ok=True)


def _default_report_runner(settings: Settings, task: dict[str, Any]) -> dict[str, Any]:
    return _run_report_in_subprocess(settings, task)


def _default_condition_evaluator(
    settings: Settings, condition_text: str, response: dict[str, Any]
) -> ConditionDecision:
    # Heavy OpenAI/Agents imports stay off the API startup path.
    from agents import Agent, ModelSettings, OpenAIProvider, RunConfig, Runner
    from openai.types.shared import Reasoning

    if not settings.openai_automation_api_key:
        raise RuntimeError("OPENAI_AUTOMATION_API_KEY is not configured")
    evidence = {
        "answer": str(response.get("answer") or "")[:6000],
        "columns": list(response.get("columns") or [])[:30],
        "rows": list(response.get("rows") or [])[:50],
        "row_count": int(response.get("row_count") or 0),
    }
    agent = Agent(
        name="NeginAI automation condition evaluator",
        instructions=(
            "Evaluate the Persian alert condition only from the supplied live report evidence. "
            "Return triggered=true only when the evidence clearly proves the condition. "
            "If evidence is missing or ambiguous, return false. Write the reason in Persian."
        ),
        model=settings.openai_model,
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="low"), verbosity="low", max_tokens=500
        ),
        output_type=ConditionDecision,
    )
    result = Runner.run_sync(
        agent,
        input=json.dumps(
            {"condition": condition_text, "live_report_evidence": evidence},
            ensure_ascii=False,
            default=str,
        ),
        max_turns=3,
        run_config=RunConfig(
            workflow_name="NeginAI automation condition evaluation",
            trace_include_sensitive_data=False,
            model_provider=OpenAIProvider(api_key=settings.openai_automation_api_key),
        ),
    )
    if isinstance(result.final_output, ConditionDecision):
        return result.final_output
    raise RuntimeError("condition evaluator returned an invalid result")


def _safe_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": str(response.get("answer") or "")[:12000],
        "columns": list(response.get("columns") or [])[:50],
        "rows": list(response.get("rows") or [])[:100],
        "row_count": int(response.get("row_count") or 0),
        "sources": list(response.get("sources") or [])[:30],
        "sql": str(response.get("sql") or "")[:20000] or None,
    }


def run_due_automations(
    settings: Settings,
    limit: int = 3,
    now: datetime | None = None,
    report_runner: Callable[[Settings, dict[str, Any]], dict[str, Any]] | None = None,
    condition_evaluator: Callable[[Settings, str, dict[str, Any]], ConditionDecision]
    | None = None,
    push_sender: Callable[[Settings, str, str, str, str], Any] | None = None,
) -> dict[str, int]:
    # The scheduler must be explicitly enabled.  This prevents a retained API
    # key or a stale active row from creating any background model usage.
    if not settings.automation_enabled:
        return {"claimed": 0, "completed": 0, "failed": 0, "notified": 0}
    current = _as_utc(now)
    tasks = _claim_due(settings, current, limit)
    report_runner = report_runner or _default_report_runner
    condition_evaluator = condition_evaluator or _default_condition_evaluator
    push_sender = push_sender or send_user_push
    completed = failed = notified = 0
    for task in tasks:
        started_at = utc_now()
        scheduled_for = str(task["next_run_at"])
        try:
            push_message: tuple[str, str, str, str] | None = None
            response = report_runner(settings, task)
            safe_response = _safe_response(response)
            condition = str(task.get("condition_text") or "").strip()
            decision = (
                condition_evaluator(settings, condition, safe_response)
                if condition
                else ConditionDecision(triggered=True, reason="گزارش زمان‌بندی‌شده اجرا شد.")
            )
            previous_triggered = (
                None if task.get("last_triggered") is None else bool(task["last_triggered"])
            )
            should_notify = not condition or (decision.triggered and previous_triggered is not True)
            finished_at = utc_now()
            next_run = calculate_next_run(
                task["schedule_kind"], task["interval_minutes"], task["daily_time"], finished_at
            )
            with sqlite_connection(settings.sqlite_path) as conn:
                conn.execute(
                    """INSERT INTO automation_runs
                       (automation_id, username, scheduled_for, started_at, finished_at,
                        status, triggered, answer, response_json)
                       VALUES (?, ?, ?, ?, ?, 'success', ?, ?, ?)""",
                    (
                        task["id"], task["username"], scheduled_for, started_at.isoformat(),
                        finished_at.isoformat(), int(decision.triggered),
                        safe_response["answer"], json.dumps(safe_response, ensure_ascii=False, default=str),
                    ),
                )
                if should_notify:
                    body = safe_response["answer"]
                    if condition:
                        body = f"{decision.reason}\n\n{body}".strip()
                    notification_cursor = conn.execute(
                        """INSERT INTO notifications
                           (username, automation_id, title, body, payload_json, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            task["username"], task["id"], task["title"], body[:12000],
                            json.dumps(safe_response, ensure_ascii=False, default=str),
                            finished_at.isoformat(),
                        ),
                    )
                    notification_id = int(notification_cursor.lastrowid)
                    report_url = f"/assistant?notification={notification_id}"
                    notified += 1
                    push_message = (
                        str(task["username"]),
                        str(task["title"]),
                        body[:12000],
                        report_url,
                    )
                conn.execute(
                    """UPDATE automations
                       SET next_run_at=?, last_run_at=?, last_status='success', last_error=NULL,
                           last_triggered=?, locked_until=NULL, updated_at=?
                       WHERE id=?""",
                    (
                        next_run.isoformat(), finished_at.isoformat(), int(decision.triggered),
                        finished_at.isoformat(), task["id"],
                    ),
                )
            if push_message is not None:
                try:
                    push_sender(settings, *push_message)
                except Exception:
                    # Push is best-effort. The durable in-app notification remains available.
                    pass
            completed += 1
        except Exception as exc:
            finished_at = utc_now()
            try:
                next_run = calculate_next_run(
                    task["schedule_kind"], task["interval_minutes"], task["daily_time"], finished_at
                )
            except Exception:
                next_run = finished_at + timedelta(hours=1)
            with sqlite_connection(settings.sqlite_path) as conn:
                conn.execute(
                    """INSERT INTO automation_runs
                       (automation_id, username, scheduled_for, started_at, finished_at,
                        status, error_text)
                       VALUES (?, ?, ?, ?, ?, 'failed', ?)""",
                    (
                        task["id"], task["username"], scheduled_for, started_at.isoformat(),
                        finished_at.isoformat(), str(exc)[:2000],
                    ),
                )
                conn.execute(
                    """UPDATE automations
                       SET next_run_at=?, last_run_at=?, last_status='failed', last_error=?,
                           locked_until=NULL, updated_at=? WHERE id=?""",
                    (
                        next_run.isoformat(), finished_at.isoformat(), str(exc)[:2000],
                        finished_at.isoformat(), task["id"],
                    ),
                )
            failed += 1
    return {"claimed": len(tasks), "completed": completed, "failed": failed, "notified": notified}
