from __future__ import annotations

import asyncio
import json

from agents.tool_context import ToolContext

from app.access_control import DataAccessPolicy
from app.chat_service import (
    AgentContext,
    _build_agent,
    compare_admin_planning_scenarios,
    create_admin_planning_scenario,
    list_admin_planning_scenarios,
    transition_admin_planning_scenario,
    upsert_admin_planning_values,
)
from app.request_orchestration import plan_request


def _invoke(tool, context: AgentContext, arguments: dict):
    serialized = json.dumps(arguments, ensure_ascii=False)
    tool_context = ToolContext(
        context=context,
        tool_name=tool.name,
        tool_call_id="planning-test-call",
        tool_arguments=serialized,
    )
    return json.loads(
        asyncio.run(tool.on_invoke_tool(tool_context, serialized))
    )


def _admin_context(settings) -> AgentContext:
    return AgentContext(
        settings=settings,
        username="Admin",
        access_policy=DataAccessPolicy(username="Admin", is_admin=True),
    )


def test_chat_agent_exposes_complete_admin_planning_toolset(settings):
    names = {tool.name for tool in _build_agent(settings).tools}

    assert {
        "list_admin_planning_scenarios",
        "get_admin_planning_scenario",
        "list_admin_planning_values",
        "compare_admin_planning_scenarios",
        "create_admin_planning_scenario",
        "upsert_admin_planning_values",
        "transition_admin_planning_scenario",
    } <= names


def test_planning_phrases_are_routed_as_company_data():
    for message in (
        "بودجه فروش ۱۴۰۵ را نشان بده",
        "پیش‌بینی را با سناریوی مبنا مقایسه کن",
        "انحراف هدف فروش چقدر است؟",
        "show me the forecast scenario",
    ):
        plan = plan_request(message)
        assert plan.needs_company_data is True


def test_non_admin_chat_tool_cannot_read_or_write_planning(settings):
    context = AgentContext(
        settings=settings,
        username="seller.user",
        access_policy=DataAccessPolicy(
            username="seller.user", role="فروشنده", is_restricted_seller=True
        ),
    )

    listed = _invoke(list_admin_planning_scenarios, context, {})
    created = _invoke(
        create_admin_planning_scenario,
        context,
        {
            "code": "DENIED-1405",
            "name": "نباید ساخته شود",
            "scenario_type": "budget",
            "fiscal_year": 1405,
            "start_period": "1405-01",
            "end_period": "1405-12",
        },
    )

    assert listed["error_type"] == "admin_required"
    assert created["error_type"] == "admin_required"


def test_admin_chat_can_create_fill_compare_and_submit_planning(settings):
    context = _admin_context(settings)
    budget = _invoke(
        create_admin_planning_scenario,
        context,
        {
            "code": "CHAT-BUD-1405",
            "name": "بودجه فروش چت",
            "scenario_type": "budget",
            "fiscal_year": 1405,
            "start_period": "1405-01",
            "end_period": "1405-12",
            "price_growth_percent": 10,
        },
    )["scenario"]
    forecast = _invoke(
        create_admin_planning_scenario,
        context,
        {
            "code": "CHAT-FC-1405",
            "name": "پیش‌بینی فروش چت",
            "scenario_type": "forecast",
            "fiscal_year": 1405,
            "start_period": "1405-01",
            "end_period": "1405-12",
            "base_scenario_id": budget["id"],
        },
    )["scenario"]

    for scenario_id, amount in ((budget["id"], 1_000_000), (forecast["id"], 900_000)):
        saved = _invoke(
            upsert_admin_planning_values,
            context,
            {
                "scenario_id": scenario_id,
                "values": [
                    {
                        "period": "1405-01",
                        "metric": "sales_amount",
                        "amount": amount,
                        "unit": "rial",
                        "brand": "Misswake",
                    }
                ],
            },
        )
        assert saved["upserted"] == 1

    comparison = _invoke(
        compare_admin_planning_scenarios,
        context,
        {
            "left_scenario_id": forecast["id"],
            "right_scenario_id": budget["id"],
            "metric": "sales_amount",
        },
    )
    submitted = _invoke(
        transition_admin_planning_scenario,
        context,
        {"scenario_id": budget["id"], "action": "submit", "note": "تأیید چت"},
    )

    assert comparison["periods"][0]["variance"] == -100_000
    assert comparison["periods"][0]["variance_percent"] == -10
    assert submitted["scenario"]["status"] == "submitted"
    assert context.last_action_result["action"] == "planning_scenario_submit"

