from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SqlQueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=100_000)


class SqlQueryResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time: float
    truncated: bool
    sources: list[str]


class DefinitionCreate(BaseModel):
    term: str = Field(min_length=1, max_length=200)
    definition: str = Field(min_length=1, max_length=10_000)
    rules: str = Field(default="", max_length=10_000)
    approved_sql: str | None = Field(default=None, max_length=100_000)
    related_objects: list[str] = Field(default_factory=list, max_length=100)


class DefinitionUpdate(DefinitionCreate):
    pass


class DefinitionOut(DefinitionCreate):
    id: int
    created_at: str
    updated_at: str


class ContextSearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=10, ge=1, le=50)


class SchemaCatalogUpdate(BaseModel):
    persian_name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2_000)
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    classification: str | None = Field(default=None, min_length=1, max_length=100)
    seller_access: str | None = Field(default=None, pattern=r"^(restricted|customer_scope|reference)$")
    aliases: list[str] | None = Field(default=None, max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    attachment_context: str | None = Field(default=None, max_length=20_000)
    attachment_name: str | None = Field(default=None, max_length=180)
    seller_coaching_start: bool = False
    seller_coaching_mode: bool = False
    day_route_mode: bool = False
    day_route_id: str | None = Field(default=None, max_length=64)
    conversation_id: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Stable id for this ChatGPT thread. Generate it once on the first action call, "
            "then reuse the exact returned conversation_id for every follow-up."
        ),
    )


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time: float | None = None
    truncated: bool = False
    sources: list[str] = Field(default_factory=list)
    sql: str | None = None
    clarification_required: bool = False
    report_context: dict[str, Any] | None = None
    presentation: dict[str, Any] | None = None
    total_available_rows: int | None = None


class ConversationCreateRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=100)


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    pinned: bool | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class AutomationCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    query_text: str = Field(min_length=1, max_length=4_000)
    condition_text: str | None = Field(default=None, max_length=2_000)
    schedule_kind: str
    interval_minutes: int | None = Field(default=None, ge=15, le=10_080)
    daily_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class NotificationReadRequest(BaseModel):
    notification_ids: list[int] = Field(min_length=1, max_length=100)


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class PushSubscriptionRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=4096)
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=4096)


class PrevisitVisitStartRequest(BaseModel):
    route_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100_000)


class PrevisitCustomerUpdateDraftRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=50)
    national_code: str | None = Field(default=None, max_length=20)
    economic_code: str | None = Field(default=None, max_length=50)
    store_name: str | None = Field(default=None, max_length=300)
    address: str | None = Field(default=None, max_length=1_000)
    mobile: str | None = Field(default=None, max_length=50)
    customer_activity_id: str | None = Field(default=None, max_length=36)
    state_id: str | None = Field(default=None, max_length=36)
    city_id: str | None = Field(default=None, max_length=36)
    county_id: str | None = Field(default=None, max_length=36)
    city_zone: int | None = Field(default=None, ge=0, le=2_147_483_647)
    customer_level_id: str | None = Field(default=None, max_length=36)
    customer_category_id: str | None = Field(default=None, max_length=36)
    owner_type_ref: int | None = Field(default=None, ge=0, le=2_147_483_647)
    postal_code: str | None = Field(default=None, max_length=20)
    customer_code: str | None = Field(default=None, max_length=50)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PrevisitCartLine(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0, le=1_000_000)
    unit_price: float = Field(ge=0)
    discount_amount: float = Field(default=0, ge=0)
    title: str = Field(default="", max_length=300)


class PrevisitDraftUpdateRequest(BaseModel):
    lines: list[PrevisitCartLine] = Field(default_factory=list, max_length=500)
    payment_type: str = Field(default="", max_length=100)
    order_type: str = Field(default="", max_length=100)
    warehouse_ref: int | None = Field(default=None, gt=0)
    warehouse_name: str = Field(default="", max_length=150)


class PrevisitSavedRequestUpsert(PrevisitDraftUpdateRequest):
    preview: dict[str, Any] = Field(default_factory=dict)


class PrevisitPreviewLine(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0, le=1_000_000)


class PrevisitPreviewRequest(BaseModel):
    route_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=100)
    order_type_ref: int = Field(gt=0)
    payment_usance_ref: str = Field(min_length=1, max_length=100)
    warehouse_ref: int | None = Field(default=None, gt=0)
    lines: list[PrevisitPreviewLine] = Field(min_length=1, max_length=500)


class PrevisitOutcomeRequest(BaseModel):
    outcome: str = Field(pattern=r"^(order|no_order|no_visit|skipped)$")
    reason_id: str | None = Field(default=None, max_length=36)
    reason: str = Field(default="", max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100_000)


class PlanningScenarioCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=200)
    scenario_type: str = Field(pattern=r"^(budget|forecast|plan)$")
    fiscal_year: int = Field(ge=1300, le=2500)
    start_period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    end_period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    base_scenario_id: int | None = Field(default=None, gt=0)
    assumptions: dict[str, Any] = Field(default_factory=dict)


class PlanningTransitionRequest(BaseModel):
    action: str = Field(pattern=r"^(submit|approve|reject|lock|reopen|archive)$")
    note: str = Field(default="", max_length=1_000)


class PlanningValueInput(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    metric: str = Field(min_length=1, max_length=50)
    amount: float = Field(ge=-1e18, le=1e18)
    unit: str = Field(default="rial", min_length=1, max_length=30)
    branch: str = Field(default="", max_length=200)
    sales_line: str = Field(default="", max_length=200)
    supervisor_id: str = Field(default="", max_length=200)
    seller_id: str = Field(default="", max_length=200)
    customer_id: str = Field(default="", max_length=200)
    brand: str = Field(default="", max_length=200)
    product_id: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=1_000)


class PlanningValuesUpsertRequest(BaseModel):
    values: list[PlanningValueInput] = Field(min_length=1, max_length=5_000)
