from app.request_orchestration import plan_request


def test_greeting_stays_in_lightweight_conversation_mode():
    plan = plan_request("سلام، چطوری؟")

    assert plan.mode == "conversation"
    assert plan.needs_company_data is False


def test_company_report_enters_data_mode():
    plan = plan_request("فروش امروز من به تفکیک برند چقدر بوده؟")

    assert plan.mode == "company_data"
    assert plan.needs_company_data is True
    assert plan.needs_live_workspace is True


def test_short_followup_inherits_company_data_mode():
    history = [
        {"role": "user", "content": "فروش امروز را بده"},
        {"role": "assistant", "content": "گزارش آماده شد"},
    ]

    plan = plan_request("حالا به تفکیکش کن", history)

    assert plan.needs_company_data is True
    assert plan.reason == "short_followup_to_company_data"


def test_greeting_with_report_is_not_misclassified_as_small_talk():
    plan = plan_request("سلام، فروش امروز من چقدر بوده؟")

    assert plan.needs_company_data is True


def test_chat_does_not_eagerly_prepare_schema_for_small_talk(settings, monkeypatch):
    from dataclasses import replace

    from app.chat_service import AgentReply, chat

    class Result:
        final_output = AgentReply(answer="سلام!", evidence_status="not_required")

    monkeypatch.setattr(
        "app.chat_service.prepare_analysis_context",
        lambda *_args: (_ for _ in ()).throw(AssertionError("schema preload must stay lazy")),
    )
    monkeypatch.setattr("app.chat_service.Runner.run_sync", lambda *_args, **_kwargs: Result())

    response = chat(replace(settings, openai_api_key="test-key"), "سلام", "light-chat", "Admin")

    assert response["answer"] == "سلام!"


def test_chat_prepares_analysis_context_for_company_data(settings, monkeypatch):
    from dataclasses import replace

    from app.chat_service import AgentReply, chat

    calls = []

    class Result:
        final_output = AgentReply(
            answer="برای اجرای گزارش به داده زنده نیاز است.",
            clarification_required=True,
            evidence_status="clarification",
        )

    def fake_prepare(*_args):
        calls.append(True)
        return {"requires_live_database_evidence": True}

    monkeypatch.setattr("app.chat_service.prepare_analysis_context", fake_prepare)
    monkeypatch.setattr("app.chat_service.Runner.run_sync", lambda *_args, **_kwargs: Result())

    chat(
        replace(settings, openai_api_key="test-key"),
        "فروش امروز را بده",
        "data-chat",
        "Admin",
    )

    assert calls == [True]
