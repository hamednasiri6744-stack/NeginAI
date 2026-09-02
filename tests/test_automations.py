from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
import subprocess
import json

import pytest

from app.automation_service import (
    AutomationRunTimeout,
    ConditionDecision,
    calculate_next_run,
    create_automation,
    delete_automation,
    list_automations,
    list_notifications,
    mark_notifications_read,
    run_due_automations,
    set_automation_active,
    _run_report_inline,
    _run_report_in_subprocess,
)
from app.database import sqlite_connection


def test_interval_and_daily_schedules_use_tehran_time():
    now = datetime(2026, 8, 9, 4, 0, tzinfo=timezone.utc)  # 07:30 Tehran

    interval = calculate_next_run("interval", 60, None, now)
    daily = calculate_next_run("daily", None, "09:00", now)

    assert interval == datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc)
    assert daily == datetime(2026, 8, 9, 5, 30, tzinfo=timezone.utc)


def test_new_daily_schedule_runs_in_current_minute_instead_of_skipping_a_day(settings):
    now = datetime(2026, 8, 9, 7, 4, 5, tzinfo=timezone.utc)  # 10:34:05 Tehran

    task = create_automation(
        settings,
        "Admin",
        "گزارش روزانه فروش ساعت ۱۰:۳۴",
        "فروش امروز را گزارش کن",
        "daily",
        daily_time="10:34",
        now=now,
    )

    assert task["next_run_at"] == "2026-08-09T07:04:00+00:00"
    assert calculate_next_run("daily", None, "10:34", now) == datetime(
        2026, 8, 10, 7, 4, tzinfo=timezone.utc
    )


def test_automations_are_owned_paused_and_soft_deleted_per_user(settings):
    task = create_automation(
        settings,
        "m.etemadi",
        "گزارش فروش ساعتی",
        "فروش یک ساعت اخیر را گزارش کن",
        "interval",
        interval_minutes=60,
    )

    assert [item["id"] for item in list_automations(settings, "m.etemadi")] == [task["id"]]
    assert list_automations(settings, "Admin") == []

    paused = set_automation_active(settings, "m.etemadi", task["id"], False)
    assert paused["active"] is False
    resumed = set_automation_active(settings, "m.etemadi", task["id"], True)
    assert resumed["active"] is True

    delete_automation(settings, "m.etemadi", task["id"])
    assert list_automations(settings, "m.etemadi") == []


def _make_due(settings, automation_id: int) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE automations SET next_run_at=?, locked_until=NULL WHERE id=?",
            ("2026-08-09T00:00:00+00:00", automation_id),
        )


def test_due_recurring_report_creates_user_notification(settings):
    task = create_automation(
        settings,
        "m.etemadi",
        "گزارش فروش",
        "فروش یک ساعت اخیر را گزارش کن",
        "interval",
        interval_minutes=60,
    )
    _make_due(settings, task["id"])

    result = run_due_automations(
        settings,
        now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
        report_runner=lambda _settings, _task: {
            "answer": "فروش یک ساعت اخیر ۱۲۳ بود.",
            "columns": ["Sales"],
            "rows": [[123]],
            "row_count": 1,
            "sources": ["dbo.SalesReviewFast"],
            "sql": "SELECT 123 AS Sales",
        },
    )

    assert result == {"claimed": 1, "completed": 1, "failed": 0, "notified": 1}
    notifications = list_notifications(settings, "m.etemadi", True)
    assert len(notifications) == 1
    assert notifications[0]["body"] == "فروش یک ساعت اخیر ۱۲۳ بود."
    assert mark_notifications_read(settings, "m.etemadi", [notifications[0]["id"]]) == 1
    assert list_notifications(settings, "m.etemadi", True) == []


def test_disabled_scheduler_does_not_claim_or_call_a_due_report(settings):
    task = create_automation(
        settings, "Admin", "report", "report today's sales", "interval", interval_minutes=60
    )
    _make_due(settings, task["id"])
    calls = []

    result = run_due_automations(
        replace(settings, automation_enabled=False),
        now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
        report_runner=lambda *_: calls.append(True),
    )

    assert result == {"claimed": 0, "completed": 0, "failed": 0, "notified": 0}
    assert calls == []


def test_due_report_sends_push_without_waiting_for_next_chat(settings):
    task = create_automation(
        settings,
        "m.etemadi",
        "گزارش فروش خودکار",
        "فروش امروز را گزارش کن",
        "interval",
        interval_minutes=60,
    )
    _make_due(settings, task["id"])
    pushes = []

    result = run_due_automations(
        settings,
        now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
        report_runner=lambda *_: {"answer": "فروش امروز ۱۲۳ بود."},
        push_sender=lambda settings, username, title, body, url: pushes.append(
            (username, title, body, url)
        ),
    )

    assert result["completed"] == 1
    assert pushes[0][:3] == (
        "m.etemadi",
        "گزارش فروش خودکار",
        "فروش امروز ۱۲۳ بود.",
    )
    assert pushes[0][3] == "/assistant?notification=1"


def test_automation_notification_opens_the_exact_item_in_the_app(client, settings):
    task = create_automation(
        settings,
        "Admin",
        "گزارش روزانه فروش",
        "فروش امروز را گزارش کن",
        "interval",
        interval_minutes=60,
    )
    _make_due(settings, task["id"])
    pushes = []

    run_due_automations(
        settings,
        now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
        report_runner=lambda *_: {"answer": "فروش خالص امروز ۱۲۳ میلیون تومان است."},
        push_sender=lambda *args: pushes.append(args),
    )

    report_url = pushes[0][4]
    response = client.get(report_url)
    notifications = list_notifications(settings, "Admin")

    assert response.status_code == 200
    assert report_url == "/assistant?notification=1"
    assert 'id="notificationsPanel"' in response.text
    assert notifications[0]["title"] == "گزارش روزانه فروش"
    assert notifications[0]["body"] == "فروش خالص امروز ۱۲۳ میلیون تومان است."


def test_push_failure_does_not_fail_a_completed_automation(settings):
    task = create_automation(
        settings, "Admin", "گزارش", "فروش را گزارش کن", "interval", interval_minutes=60
    )
    _make_due(settings, task["id"])

    def broken_push(*_):
        raise RuntimeError("push provider unavailable")

    result = run_due_automations(
        settings,
        now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
        report_runner=lambda *_: {"answer": "گزارش آماده است."},
        push_sender=broken_push,
    )

    assert result == {"claimed": 1, "completed": 1, "failed": 0, "notified": 1}
    assert len(list_notifications(settings, "Admin", True)) == 1


def test_automation_worker_timeout_is_bounded(settings, monkeypatch):
    def timed_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["automation-worker"], timeout=30)

    monkeypatch.setattr("app.automation_service.subprocess.run", timed_out)

    with pytest.raises(AutomationRunTimeout, match="30 seconds"):
        _run_report_in_subprocess(
            replace(settings, automation_run_timeout_seconds=30), {"id": 42}
        )


def test_automation_worker_returns_report_through_bounded_file(
    settings, monkeypatch, tmp_path
):
    from app.automation_worker import run_task

    task = create_automation(
        settings, "Admin", "گزارش", "فروش امروز", "interval", interval_minutes=60
    )
    output = tmp_path / "worker-result.json"
    monkeypatch.setattr("app.automation_worker.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.automation_worker._run_report_inline",
        lambda *_: {"answer": "گزارش آماده است.", "row_count": 1},
    )

    assert run_task(task["id"], output) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["response"]["answer"] == "گزارش آماده است."


def test_automation_report_runs_with_its_owner_access_policy(settings, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat_service.chat",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"answer": "ok"},
    )
    configured = replace(settings, openai_automation_api_key="automation-key")

    response = _run_report_inline(
        configured,
        {
            "id": 7,
            "username": "A.kamran",
            "query_text": "مجموع دریافتی مشتریان را گزارش کن",
        },
    )

    assert response == {"answer": "ok"}
    assert calls[0][0][3] == "A.kamran"


def test_condition_alert_notifies_only_on_false_to_true_transition(settings):
    task = create_automation(
        settings,
        "Admin",
        "هشدار فروش",
        "فروش امروز را بررسی کن",
        "interval",
        interval_minutes=60,
        condition_text="فروش از ۱۰۰ بیشتر شد",
    )
    response = {"answer": "فروش ۱۲۳ است", "row_count": 1, "rows": [[123]]}
    decisions = iter([True, True, False, True])

    def evaluate(_settings, _condition, _response):
        triggered = next(decisions)
        return ConditionDecision(triggered=triggered, reason="نتیجه شرط")

    totals = []
    for _ in range(4):
        _make_due(settings, task["id"])
        totals.append(
            run_due_automations(
                settings,
                now=datetime(2026, 8, 9, 1, 0, tzinfo=timezone.utc),
                report_runner=lambda _settings, _task: response,
                condition_evaluator=evaluate,
            )["notified"]
        )

    assert totals == [1, 0, 0, 1]
    assert len(list_notifications(settings, "Admin")) == 2


def test_automation_api_uses_authenticated_owner(client, auth):
    created = client.post(
        "/automations",
        headers=auth,
        json={
            "title": "گزارش روزانه",
            "query_text": "فروش امروز را گزارش کن",
            "schedule_kind": "daily",
            "daily_time": "09:00",
        },
    )
    assert created.status_code == 201
    listed = client.get("/automations", headers=auth)
    assert listed.status_code == 200
    assert listed.json()["automations"][0]["title"] == "گزارش روزانه"


def test_chat_agent_exposes_automation_management_tools(settings):
    from app.chat_service import _build_agent

    names = {tool.name for tool in _build_agent(settings).tools}
    assert {
        "create_recurring_automation",
        "list_my_automations",
        "set_my_automation_status",
        "delete_my_automation",
        "list_my_automation_notifications",
    } <= names


def test_unread_automation_notification_is_delivered_on_next_chat(
    settings, monkeypatch
):
    from app.chat_service import AgentReply, chat

    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO notifications
               (username, title, body, payload_json, created_at)
               VALUES ('m.etemadi', 'هشدار فروش', 'فروش از حد تعیین‌شده عبور کرد.', '{}', ?)""",
            (datetime.now(timezone.utc).isoformat(),),
        )

    class FakeResult:
        final_output = AgentReply(answer="پاسخ سؤال جدید", evidence_status="not_required")

    monkeypatch.setattr("app.chat_service.Runner.run_sync", lambda *_args, **_kwargs: FakeResult())
    monkeypatch.setattr("app.chat_service.prepare_analysis_context", lambda *_args: {})
    tuned = replace(settings, openai_api_key="test-key")

    response = chat(tuned, "سلام", "notification-chat", "m.etemadi")

    assert response["answer"].startswith("اعلان‌های خودکار جدید:")
    assert "فروش از حد تعیین‌شده عبور کرد" in response["answer"]
    assert list_notifications(settings, "m.etemadi", True) == []
