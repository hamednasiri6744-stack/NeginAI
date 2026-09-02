from pathlib import Path

from app.chat_service import (
    AgentContext,
    AGENT_INSTRUCTIONS,
    _apply_temporal_context_note,
    _external_reporting_identity_policy_error,
    _named_exclusion_policy_error,
    _personnel_lookup_sql,
    _salesperson_lookup_sql,
)
from app.reporting_policy import external_sales_exclusion_sql
from app.sql_guard import validate_read_only_sql


def test_sales_questions_use_defaults_instead_of_routine_clarifications():
    assert "default sales total is unique sales" in AGENT_INSTRUCTIONS
    assert "never add invoice and voucher" in AGENT_INSTRUCTIONS
    assert "as تومان" in AGENT_INSTRUCTIONS
    assert "Never ask merely for" in AGENT_INSTRUCTIONS
    assert "most one short question at a time" in AGENT_INSTRUCTIONS
    assert "Do not repeat schema discovery" in AGENT_INSTRUCTIONS
    assert "means a top-10 ranking" in AGENT_INSTRUCTIONS
    assert "Follow-up questions inherit" in AGENT_INSTRUCTIONS
    assert "Resolve a missing time period in this order" in AGENT_INSTRUCTIONS
    assert "execute the report without asking" in AGENT_INSTRUCTIONS
    assert "call resolve_salesperson first" in AGENT_INSTRUCTIONS
    assert "call resolve_personnel" in AGENT_INSTRUCTIONS
    assert "Never answer a supervisor-specific request with an unfiltered branch/line total" in AGENT_INSTRUCTIONS
    assert "Do not use DayPaths or recent Tours to answer \"my routes\"" in AGENT_INSTRUCTIONS
    assert "Current customers on a seller route come from NGT.VisitTemplatePathCustomers" in AGENT_INSTRUCTIONS
    assert '"customer balance" means the overall cardex balance' in AGENT_INSTRUCTIONS
    assert "seller's own DealerId, deduplicated by SaleId" in AGENT_INSTRUCTIONS
    assert "This includes the seller's own customers, teammates' customers" in AGENT_INSTRUCTIONS
    assert "never customers in another branch or sales line" in AGENT_INSTRUCTIONS
    assert "Mandatory exception to the default-period rule" in AGENT_INSTRUCTIONS
    assert "do not assume today, do not execute SQL" in AGENT_INSTRUCTIONS
    assert "Do not answer \"my brands\" from a manually confirmed team portfolio" in AGENT_INSTRUCTIONS
    assert "Never exclude a person with DealerName/SalesManName NOT LIKE" in AGENT_INSTRUCTIONS
    assert 'using "به تفکیک", "همه", "تمام", or "کامل" is not a ranking' in AGENT_INSTRUCTIONS
    assert "State the combined حواله" in AGENT_INSTRUCTIONS
    assert "فاکتور basis" in AGENT_INSTRUCTIONS


def test_seller_coaching_instructions_use_brand_and_same_day_comparisons():
    assert "Seller performance coaching:" in AGENT_INSTRUCTIONS
    assert "Never compare a partial current month with a complete prior month." in AGENT_INSTRUCTIONS
    assert "geographic region or territory" in AGENT_INSTRUCTIONS
    assert "seller_coaching_session" in AGENT_INSTRUCTIONS
    assert "Never substitute a today-only report" in AGENT_INSTRUCTIONS


def test_seller_coaching_start_replaces_the_generic_summary_request():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert "Do not return a generic sales summary." in source
    assert "exactly three prioritized, practical recommendations" in source


def test_day_route_prompt_requires_customer_priority_and_ten_order_plan():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert "VIP segment from invoice frequency in the last 12 months" in source
    assert "realistic path to 10 orders" in source


def test_day_route_prompt_requires_a_ranked_customer_table():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert "Start the answer with one Markdown" in source
    assert "customer name, customer code, address" in source
    assert "12-month invoice count" in source
    assert "last recorded purchase date" in source


def test_day_route_id_is_added_only_after_the_agent_message_exists():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert source.index("agent_message = effective_message") < source.index("[Selected route id:")


def test_day_route_allows_enough_output_for_the_priority_table():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert "max_tokens=12000 if day_route_mode else 2200" in source


def test_day_route_prompt_adds_brand_columns_to_the_customer_table():
    source = (Path(__file__).parents[1] / "app" / "chat_service.py").read_text(encoding="utf-8")
    assert "Add two columns to this same customer table" in source
    assert "put those two brand lists into the two added columns" in source
    assert "COUNT(DISTINCT SellId)" in source
    assert "never by sales amount" in source
    assert "both brand columns must be per customer" in source
    assert "line_purchased_brands" in source
    assert "show every brand in each list" in source
    assert "visit_score descending" in source
    assert "Preserve that exact order" in source
    assert "Use visit_score as the final ranking field" in source
    assert "Do not include credit or collection risk yet" in source


def test_named_salesperson_exclusion_requires_canonical_id():
    unsafe = _named_exclusion_policy_error(
        "SELECT * FROM dbo.SalesReviewFast WHERE COALESCE(DealerName,N'') NOT LIKE N'%ايمان%'"
    )
    safe = _named_exclusion_policy_error(
        "SELECT * FROM dbo.SalesReviewFast WHERE DealerId <> ۱۲۳"
    )
    lookup = _salesperson_lookup_sql("ايمان شريف پور")

    assert unsafe and unsafe["error_type"] == "unsafe_named_entity_exclusion"
    assert safe is None
    assert "dbo.PDealer" in lookup
    assert "PDealerId AS DealerId" in lookup
    assert "REPLACE(REPLACE(REPLACE" in lookup


def test_external_company_sellers_require_the_canonical_report_filter(settings):
    context = AgentContext(
        settings=settings,
        prepared_context={"reporting_exclusions": {"person_ids": [7, 137, 192, 510]}},
    )
    incomplete = validate_read_only_sql("SELECT DealerId FROM dbo.SalesReviewFast")
    protected = validate_read_only_sql(
        "SELECT s.DealerId FROM dbo.SalesReviewFast AS s WHERE "
        + external_sales_exclusion_sql("s")
    )

    assert _external_reporting_identity_policy_error(context, incomplete)
    assert _external_reporting_identity_policy_error(context, protected) is None


def test_personnel_lookup_uses_the_canonical_directory_and_normalizes_names():
    lookup = _personnel_lookup_sql("حسین محبایی")

    assert "GNR.vwPersonnel" in lookup
    assert "PersCode AS PersonnelCode" in lookup
    assert "N'ي',N'ی'" in lookup


def test_inherited_temporal_scope_is_stated_without_asking():
    answer = _apply_temporal_context_note(
        "زهرا بیشترین دریافت را ثبت کرده است.",
        {
            "resolved_temporal_context": {
                "scope": "today",
                "matched_text": "امروز",
                "source": "previous_user_message",
            }
        },
        has_database_evidence=True,
    )

    assert answer.startswith("با توجه به گفت‌وگوی قبل، بازه را امروز در نظر گرفتم.")


def test_default_temporal_scope_is_stated_but_explicit_scope_is_not_duplicated():
    default_answer = _apply_temporal_context_note(
        "زهرا بیشترین دریافت را ثبت کرده است.",
        {
            "resolved_temporal_context": {
                "scope": "today",
                "matched_text": "امروز",
                "source": "default_current_business_date",
            }
        },
        has_database_evidence=True,
    )
    explicit_answer = _apply_temporal_context_note(
        "گزارش امروز آماده است.",
        {
            "resolved_temporal_context": {
                "scope": "today",
                "matched_text": "امروز",
                "source": "current_request",
            }
        },
        has_database_evidence=True,
    )

    assert default_answer.startswith("چون بازه‌ای مشخص نشده بود، بازه را امروز در نظر گرفتم.")
    assert explicit_answer == "گزارش امروز آماده است."
