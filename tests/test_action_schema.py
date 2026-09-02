from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent


def test_custom_gpt_exposes_primary_chat_action():
    schema = yaml.safe_load((ROOT / "openapi-action.yaml").read_text(encoding="utf-8"))
    operation = schema["paths"]["/chat"]["post"]

    assert operation["operationId"] == "chatWithNeginAI"
    assert operation["x-openai-isConsequential"] is False
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ChatRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ChatResponse"
    }
    conversation = schema["components"]["schemas"]["ChatRequest"]["properties"]["conversation_id"]
    assert "Never generate a new id for a follow-up" in conversation["description"]
    message = schema["components"]["schemas"]["ChatRequest"]["properties"]["message"]
    assert "every day" in message["description"]
    assert "notify me when" in message["description"]
    assert "budgets" in message["description"]
    assert "Never claim that scheduling is unavailable" in operation["description"]
    assert "planning scenarios" in operation["description"]


def test_custom_gpt_instructions_require_internal_action_not_web_search():
    instructions = (ROOT / "docs" / "custom-gpt-instructions-fa.md").read_text(encoding="utf-8")

    assert "برای **هر** سؤال" in instructions
    assert "`chatWithNeginAI`" in instructions
    assert "هرگز از Web Search" in instructions
    assert "برای سؤال پیگیری هرگز شناسه تازه نساز" in instructions
    assert "### قانون اجباری اتوماسیون و اعلان" in instructions
    assert "هرگز نگو امکان زمان‌بندی" in instructions
    assert "موتور NeginAI این قابلیت را دارد" in instructions
    assert "### قانون اجباری برنامه‌ریزی و بودجه برای Admin" in instructions
    assert "عملکرد واقعی در برابر بودجه" in instructions
