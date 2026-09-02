from dataclasses import replace

from app.chat_service import chat


def test_chat_asks_for_all_or_date_range_before_customer_cardex(settings):
    configured = replace(settings, openai_api_key="test-key")

    response = chat(
        configured,
        "کاردکس و مانده مشتری را بده",
        conversation_id="cardex-period-choice",
        username="action-api-key",
    )

    assert response["clarification_required"] is True
    assert "کل کاردکس" in response["answer"]
    assert "بازهٔ تاریخی" in response["answer"]
    assert response["report_context"]["period_source"] == "clarification_required"
    assert response["report_context"]["resolved_request"]["standalone_request"] == (
        "کاردکس و مانده مشتری را بده"
    )
    assert response["report_context"]["resolved_request"]["is_followup"] is False
    assert "sql" not in response
