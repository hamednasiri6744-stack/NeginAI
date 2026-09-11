"""Deterministic planning kernel between model intent and application tools.

The kernel owns tool selection and authorization.  Model output is treated as
untrusted structured input and can never name a function, SQL statement or
permission directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from app.ai_gateway import IntentEnvelope


class IntelligencePolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    required_permission: str
    allowed_metrics: frozenset[str] = frozenset()
    mutating: bool = False


@dataclass(frozen=True)
class PrincipalCapabilities:
    subject: str
    permissions: frozenset[str]


@dataclass(frozen=True)
class ExecutionPlan:
    trace_id: str
    subject: str
    intent: str
    tool_name: str
    arguments: Mapping[str, Any]
    mutating: bool
    requires_confirmation: bool


DEFAULT_TOOL_REGISTRY: Mapping[str, ToolSpec] = MappingProxyType(
    {
        "customer_sales_summary": ToolSpec(
            name="get_customer_sales",
            required_permission="sales:read",
            allowed_metrics=frozenset({"net_sales", "sales_quantity"}),
        ),
        "inventory_lookup": ToolSpec(
            name="get_inventory_availability",
            required_permission="inventory:read",
            allowed_metrics=frozenset({"available_quantity"}),
        ),
        "order_draft": ToolSpec(
            name="prepare_order_draft",
            required_permission="orders:draft",
            allowed_metrics=frozenset(),
            mutating=True,
        ),
        "order_submit": ToolSpec(
            name="enqueue_validated_order",
            required_permission="orders:submit",
            allowed_metrics=frozenset(),
            mutating=True,
        ),
    }
)


class DeterministicIntelligenceKernel:
    def __init__(self, registry: Mapping[str, ToolSpec] = DEFAULT_TOOL_REGISTRY) -> None:
        self._registry = MappingProxyType(dict(registry))
        if not self._registry:
            raise ValueError("tool registry cannot be empty")

    @property
    def allowed_intents(self) -> tuple[str, ...]:
        return tuple(sorted(self._registry))

    @property
    def allowed_metrics(self) -> tuple[str, ...]:
        metrics = {metric for spec in self._registry.values() for metric in spec.allowed_metrics}
        return tuple(sorted(metrics))

    def compile(
        self,
        envelope: IntentEnvelope,
        principal: PrincipalCapabilities,
    ) -> ExecutionPlan:
        spec = self._registry.get(envelope.intent)
        if spec is None:
            raise IntelligencePolicyError("intent has no application-owned tool mapping")
        if spec.required_permission not in principal.permissions:
            raise IntelligencePolicyError("principal is not allowed to execute this intent")
        unknown_metrics = set(envelope.requested_metrics) - spec.allowed_metrics
        if unknown_metrics:
            raise IntelligencePolicyError("intent requested metrics outside the tool contract")
        if envelope.needs_clarification:
            raise IntelligencePolicyError("clarification must be resolved before planning")

        arguments: dict[str, Any] = {
            "entities": dict(envelope.entities),
            "time_range": envelope.time_range.model_dump(mode="json"),
            "metrics": list(envelope.requested_metrics),
        }
        # Mutation identity is created locally. It is never accepted from the
        # model envelope, so retries and audit records use an application-owned
        # command identity.
        if spec.mutating:
            arguments["command_id"] = str(uuid4())

        return ExecutionPlan(
            trace_id=str(uuid4()),
            subject=principal.subject,
            intent=envelope.intent,
            tool_name=spec.name,
            arguments=MappingProxyType(arguments),
            mutating=spec.mutating,
            requires_confirmation=spec.mutating,
        )
