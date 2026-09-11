"""Provider-neutral, fail-closed intent gateway for NeginAI.

The gateway is deliberately unable to execute SQL, tools, calculations or
business commands.  A remote model may only translate a bounded user message
into the strict :class:`IntentEnvelope`; authoritative work stays in NeginAI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_INTENT_INPUT_CHARS = 4_000
DEFAULT_CONFIDENCE_THRESHOLD = 0.65


class IntentTimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="unspecified", min_length=1, max_length=50)
    start: str | None = Field(default=None, max_length=40)
    end: str | None = Field(default=None, max_length=40)


class IntentEnvelope(BaseModel):
    """The only model-authored contract accepted by the application."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    entities: dict[str, str] = Field(default_factory=dict)
    time_range: IntentTimeRange = Field(default_factory=IntentTimeRange)
    requested_metrics: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0, le=1)
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=500)

    @field_validator("entities")
    @classmethod
    def validate_entities(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("at most 20 entities are allowed")
        normalized: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key).strip()
            item = str(raw_value).strip()
            if not key or len(key) > 80 or not item or len(item) > 300:
                raise ValueError("entity keys and values must be bounded and non-empty")
            normalized[key] = item
        return normalized

    @field_validator("requested_metrics")
    @classmethod
    def normalize_metrics(cls, value: list[str]) -> list[str]:
        normalized = [str(item).strip().casefold() for item in value]
        if any(not item or len(item) > 80 for item in normalized):
            raise ValueError("metric names must be bounded and non-empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("metric names must be unique")
        return normalized


class IntentProvider(Protocol):
    provider_name: str
    model_name: str

    def extract(self, *, instructions: str, message: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class IntentGatewayResult:
    envelope: IntentEnvelope
    provider: str
    model: str


class IntentGatewayError(RuntimeError):
    """Safe gateway failure that does not expose provider credentials or payloads."""


def _bounded_message(message: str) -> str:
    normalized = " ".join(str(message or "").split())
    if not normalized:
        raise IntentGatewayError("intent input is empty")
    if len(normalized) > MAX_INTENT_INPUT_CHARS:
        raise IntentGatewayError("intent input exceeds the application limit")
    return normalized


def _instructions(allowed_intents: Sequence[str], allowed_metrics: Sequence[str]) -> str:
    intents = ", ".join(sorted(allowed_intents))
    metrics = ", ".join(sorted(allowed_metrics)) or "none"
    return (
        "Translate the Persian or English request into one JSON intent envelope. "
        "Do not answer the request, calculate values, write SQL, choose permissions, "
        "or create commands. Use only these intents: "
        f"{intents}. Allowed metric identifiers: {metrics}. "
        "When the request is ambiguous, set needs_clarification=true and provide "
        "one short clarification_question."
    )


class IntentGateway:
    def __init__(
        self,
        provider: IntentProvider,
        *,
        allowed_intents: Sequence[str],
        allowed_metrics: Sequence[str] = (),
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.provider = provider
        self.allowed_intents = frozenset(str(item).strip() for item in allowed_intents)
        self.allowed_metrics = frozenset(str(item).strip().casefold() for item in allowed_metrics)
        self.confidence_threshold = confidence_threshold
        if not self.allowed_intents:
            raise ValueError("at least one allowed intent is required")
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence threshold must be between zero and one")

    def extract(self, message: str) -> IntentGatewayResult:
        bounded = _bounded_message(message)
        try:
            raw = self.provider.extract(
                instructions=_instructions(self.allowed_intents, self.allowed_metrics),
                message=bounded,
            )
            envelope = IntentEnvelope.model_validate(raw)
        except IntentGatewayError:
            raise
        except Exception as exc:
            raise IntentGatewayError("intent provider returned an invalid envelope") from exc

        if envelope.intent not in self.allowed_intents:
            raise IntentGatewayError("intent is not allowed by the application")
        unknown_metrics = set(envelope.requested_metrics) - self.allowed_metrics
        if unknown_metrics:
            raise IntentGatewayError("one or more requested metrics are not allowed")
        if envelope.confidence < self.confidence_threshold:
            if not envelope.clarification_question:
                raise IntentGatewayError("low-confidence intent requires clarification")
            envelope = envelope.model_copy(update={"needs_clarification": True})
        if envelope.needs_clarification and not envelope.clarification_question:
            raise IntentGatewayError("clarification question is required")
        return IntentGatewayResult(
            envelope=envelope,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
        )


class OpenAICompatibleIntentProvider:
    """Thin adapter for Iranian gateways exposing the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 20,
        provider_name: str = "openai-compatible",
    ) -> None:
        if not api_key.strip() or not model.strip():
            raise ValueError("provider api key and model are required")
        self.provider_name = provider_name.strip() or "openai-compatible"
        self.model_name = model.strip()
        self._client = OpenAI(
            api_key=api_key.strip(),
            base_url=base_url.strip().rstrip("/") if base_url else None,
            timeout=timeout_seconds,
        )

    def extract(self, *, instructions: str, message: str) -> dict[str, Any]:
        response = self._client.responses.create(
            model=self.model_name,
            instructions=instructions,
            input=message,
            max_output_tokens=500,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "neginai_intent_envelope",
                    "strict": True,
                    "schema": IntentEnvelope.model_json_schema(),
                }
            },
        )
        try:
            payload = json.loads(response.output_text)
        except (AttributeError, TypeError, json.JSONDecodeError) as exc:
            raise IntentGatewayError("intent provider did not return valid JSON") from exc
        if not isinstance(payload, dict):
            raise IntentGatewayError("intent provider returned a non-object payload")
        return payload
