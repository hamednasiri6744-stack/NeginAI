import pytest

from app.ai_gateway import IntentEnvelope
from app.intelligence_kernel import (
    DeterministicIntelligenceKernel,
    IntelligencePolicyError,
    PrincipalCapabilities,
)


def _intent(name: str, *, metrics: list[str] | None = None) -> IntentEnvelope:
    return IntentEnvelope.model_validate(
        {
            "intent": name,
            "entities": {"customer_id": "C-100"},
            "time_range": {"kind": "current_month"},
            "requested_metrics": metrics or [],
            "confidence": 0.95,
            "needs_clarification": False,
        }
    )


def test_kernel_selects_the_internal_tool_not_a_model_supplied_function():
    kernel = DeterministicIntelligenceKernel()
    principal = PrincipalCapabilities("seller-7", frozenset({"sales:read"}))

    plan = kernel.compile(
        _intent("customer_sales_summary", metrics=["net_sales"]), principal
    )

    assert plan.tool_name == "get_customer_sales"
    assert plan.subject == "seller-7"
    assert plan.mutating is False
    assert "command_id" not in plan.arguments


def test_kernel_denies_intent_when_principal_lacks_application_permission():
    kernel = DeterministicIntelligenceKernel()
    principal = PrincipalCapabilities("seller-7", frozenset({"inventory:read"}))

    with pytest.raises(IntelligencePolicyError, match="not allowed"):
        kernel.compile(_intent("customer_sales_summary"), principal)


def test_kernel_denies_metric_not_owned_by_selected_tool():
    kernel = DeterministicIntelligenceKernel()
    principal = PrincipalCapabilities("seller-7", frozenset({"sales:read"}))

    with pytest.raises(IntelligencePolicyError, match="outside the tool contract"):
        kernel.compile(
            _intent("customer_sales_summary", metrics=["available_quantity"]),
            principal,
        )


def test_mutating_plan_gets_application_owned_command_id_and_confirmation_gate():
    kernel = DeterministicIntelligenceKernel()
    principal = PrincipalCapabilities("seller-7", frozenset({"orders:submit"}))

    plan = kernel.compile(_intent("order_submit"), principal)

    assert plan.tool_name == "enqueue_validated_order"
    assert plan.mutating is True
    assert plan.requires_confirmation is True
    assert plan.arguments["command_id"]


def test_clarification_never_compiles_to_a_tool_plan():
    kernel = DeterministicIntelligenceKernel()
    principal = PrincipalCapabilities("seller-7", frozenset({"inventory:read"}))
    envelope = _intent("inventory_lookup").model_copy(
        update={
            "needs_clarification": True,
            "clarification_question": "کدام کالا؟",
        }
    )

    with pytest.raises(IntelligencePolicyError, match="clarification"):
        kernel.compile(envelope, principal)
