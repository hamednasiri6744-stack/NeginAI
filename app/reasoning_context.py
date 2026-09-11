from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from app.business_time import jalali_business_date, tehran_now
from app.business_terms import expand_business_query
from app.config import Settings
from app.database import sqlite_connection
from app.definition_service import search_definitions
from app.reporting_policy import (
    EXTERNAL_SALES_PERSON_IDS,
    EXTERNAL_SALES_PERSON_NAMES,
    external_sales_exclusion_sql,
)
from app.organization_structure import ALBORZ_TEAM_STRUCTURE, organization_reporting_policy
from app.organization_structure_service import list_structure
from app.schema_service import (
    get_schema_object,
    schema_stats,
    search_schema,
    summarize_schema_results,
)
from app.varanegar_knowledge import (
    VaranegarRoute,
    detect_varanegar_route,
    get_varanegar_route,
    resolve_varanegar_route,
    route_definition,
)


_WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
_JALALI_OR_GREGORIAN_DATE_RE = re.compile(
    r"(?<!\d)(?:1[34]\d{2}|20\d{2})(?:[\-/]\d{1,2}(?:[\-/]\d{1,2})?)?(?!\d)"
)
_TEMPORAL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("today", (r"\bامروز\b", r"روز جاری", r"تاریخ جاری")),
    ("yesterday", (r"\bدیروز\b", r"روز قبل")),
    (
        "relative_days_ago",
        (
            r"\bپریروز\b",
            r"(?:یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|\d+)\s*روز\s*(?:پیش|قبل)",
        ),
    ),
    ("previous_week", (r"هفته (?:پیش|قبل)",)),
    ("previous_month", (r"ماه (?:پیش|قبل)",)),
    ("previous_year", (r"سال (?:پیش|قبل)",)),
    ("current_week", (r"این هفته", r"هفته جاری")),
    (
        "current_month_to_date",
        (
            r"از (?:ابتدا|اول) ماه(?: تا (?:امروز|الان))?",
            r"از (?:ابتدای|اولِ) این ماه(?: تا (?:امروز|الان))?",
        ),
    ),
    ("current_month", (r"این ماه", r"ماه جاری")),
    ("current_year", (r"\bامسال\b", r"سال جاری")),
    ("latest_business_date", (r"آخرین تاریخ کاری", r"آخرین روز کاری")),
    (
        "cumulative_to_date",
        (r"از ابتدا", r"از اول تا (?:الان|امروز)", r"تا به امروز", r"تا الان"),
    ),
)
_STOP_WORDS = {
    "از", "به", "با", "برای", "در", "را", "رو", "و", "یا", "که", "این", "آن",
    "من", "ما", "یک", "چه", "چی", "چیه", "بگو", "بده", "کن", "کنه", "است",
    "the", "a", "an", "of", "to", "for", "in", "and", "or", "is", "show", "give",
}

# This route is deliberately rule-based: routing a clear sales question must not
# require another model call.  It narrows the *preloaded* context only; the
# agent can still use its normal recovery flow if the approved sales sources do
# not contain the required field.
_SALES_INTENT_TERMS = frozenset({
    "\u0641\u0631\u0648\u0634", "\u0641\u0627\u06a9\u062a\u0648\u0631", "\u062d\u0648\u0627\u0644\u0647", "\u0645\u0631\u062c\u0648\u0639\u06cc", "\u0628\u0631\u06af\u0634\u062a\u06cc",
    "\u0645\u0634\u062a\u0631\u06cc", "\u0628\u0627\u0632\u0627\u0631\u06cc\u0627\u0628", "\u0641\u0631\u0648\u0634\u0646\u062f\u0647", "sale", "sales",
    "invoice", "factor", "voucher", "customer", "salesman",
})
_NON_SALES_QUALIFIERS = frozenset({"\u062e\u0631\u06cc\u062f", "\u062a\u0623\u0645\u06cc\u0646", "purchase", "supplier"})
_RECEIPT_TERMS = frozenset({"\u062f\u0631\u06cc\u0627\u0641\u062a", "\u0648\u0635\u0648\u0644", "receipt", "collection"})
_INITIAL_VIEW_CONTEXT_LIMIT = 6
_INITIAL_TABLE_CONTEXT_LIMIT = 10
_ADMIN_SCHEMA_CONTEXT_LIMIT = 30
_EXPLICIT_ALL_SCOPE_RE = re.compile(
    r"(?:^|\s)(?:"
    r"\u06a9\u0644(?:\u0634|\u0634\u0648|\u0627\u0634)?|"
    r"\u0647\u0645\u0634|\u0647\u0645\u0647(?:\u200c|\s)?(?:\u0634|\u0627\u0634)?|"
    r"\u062a\u0645\u0627\u0645(?:\u0634|\u0634\u0648|\u0627\u0634)?|"
    r"\u06a9\u0627\u0645\u0644(?:\u0634|\u0634\u0648|\u0627\u0634)?"
    r")(?:\s|$)"
)


def _has_explicit_all_scope(value: str) -> bool:
    return bool(_EXPLICIT_ALL_SCOPE_RE.search(normalize_text(value)))


def _is_sales_question(question: str) -> bool:
    """Identify clear sales/customer reports without spending an LLM call."""
    terms = _terms(question)
    if not terms.intersection(_SALES_INTENT_TERMS):
        return False
    # A purchase invoice is not a sales report merely because it contains the
    # generic word "invoice"/"factor".
    return not (
        terms.intersection(_NON_SALES_QUALIFIERS)
        and not terms.intersection({"\u0641\u0631\u0648\u0634", "sale", "sales", "\u0645\u0634\u062a\u0631\u06cc", "customer"})
    )


def _is_receipt_question(question: str) -> bool:
    """Detect customer-receipt reports, including short follow-up requests."""
    return bool(_terms(question).intersection(_RECEIPT_TERMS))


def _detect_temporal_scope(value: str) -> dict[str, str] | None:
    normalized = normalize_text(value)
    for scope, patterns in _TEMPORAL_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return {"scope": scope, "matched_text": match.group(0)}
    latest_record = re.search(
        "\\b(?:\u0622\u062e\u0631\u06cc\u0646|\u062c\u062f\u06cc\u062f\u062a\u0631\u06cc\u0646)\\b",
        normalized,
    )
    if latest_record:
        return {
            "scope": "all_time_latest_record",
            "matched_text": latest_record.group(0),
        }
    explicit_dates = _JALALI_OR_GREGORIAN_DATE_RE.findall(normalized)
    if explicit_dates:
        return {
            "scope": "explicit_date_or_range",
            "matched_text": "، ".join(explicit_dates[:4]),
        }
    return None


def customer_financial_period_clarification_required(question: str) -> bool:
    """Require an explicit all-time or dated choice for customer account reports."""
    normalized = normalize_text(question)
    if not normalized or _detect_temporal_scope(normalized):
        return False
    if _has_explicit_all_scope(normalized):
        return False

    inventory_context = any(
        marker in normalized
        for marker in ("\u06a9\u0627\u0644\u0627", "\u0627\u0646\u0628\u0627\u0631", "\u0645\u0648\u062c\u0648\u062f\u06cc \u06a9\u0627\u0644\u0627")
    )
    if inventory_context:
        return False

    route = detect_varanegar_route(normalized)
    if route and route.name in {"customer_cardex", "invoice_balance"}:
        return True

    has_cardex = any(
        marker in normalized
        for marker in ("\u06a9\u0627\u0631\u062f\u06a9\u0633", "\u06af\u0631\u062f\u0634 \u062d\u0633\u0627\u0628", "\u06af\u0631\u062f\u0634 \u0645\u0634\u062a\u0631\u06cc")
    )
    has_balance = "\u0645\u0627\u0646\u062f\u0647" in normalized
    return has_cardex or has_balance


def resolve_customer_financial_period_followup(
    question: str,
    history: list[dict[str, str]],
) -> dict[str, str] | None:
    """Bind a short period answer to the preceding customer-financial request.

    A reply such as ``کل کاردکس گفتم`` changes only the report period.  Keeping
    the previous customer request in trusted runtime context prevents the model
    from treating the reply as a new, customer-less request.
    """
    normalized = normalize_text(question)
    explicit_all = _has_explicit_all_scope(normalized)
    explicit_period = _detect_temporal_scope(normalized)
    if not explicit_all and not explicit_period:
        return None

    for item in reversed(history[-10:]):
        if item.get("role") != "user":
            continue
        previous = str(item.get("content") or "").strip()
        previous_normalized = normalize_text(previous)
        route = detect_varanegar_route(previous_normalized)
        is_customer_financial = bool(
            route and route.name in {"customer_cardex", "invoice_balance"}
        ) or any(
            marker in previous_normalized
            for marker in (
                "\u06a9\u0627\u0631\u062f\u06a9\u0633",
                "\u06af\u0631\u062f\u0634 \u062d\u0633\u0627\u0628",
                "\u0645\u0627\u0646\u062f\u0647 \u0641\u0627\u06a9\u062a\u0648\u0631",
                "\u0645\u0627\u0646\u062f\u0647 \u0645\u0634\u062a\u0631\u06cc",
            )
        )
        if not is_customer_financial:
            continue
        if route and route.name in {"customer_cardex", "invoice_balance"}:
            route_name = route.name
        elif "\u06a9\u0627\u0631\u062f\u06a9\u0633" in previous_normalized or "\u06af\u0631\u062f\u0634 \u062d\u0633\u0627\u0628" in previous_normalized:
            route_name = "customer_cardex"
        else:
            route_name = "invoice_balance"
        period = (
            {
                "scope": "all_available_records",
                "matched_text": "all records",
            }
            if explicit_all
            else explicit_period
        )
        return {
            "original_customer_request": previous,
            "period_scope": str((period or {}).get("scope") or ""),
            "period_text": str((period or {}).get("matched_text") or question),
            "route_name": route_name,
            "instruction": (
                "The current message is only a period correction/selection for the previous "
                "customer-financial request. Preserve the exact same customer identity and metric, "
                "apply the new period, and execute a fresh live query. Do not infer an access denial "
                "from an earlier empty result."
            ),
        }
    return None


def resolve_temporal_context(
    question: str,
    history: list[dict[str, str]],
) -> dict[str, str]:
    """Resolve a report period without forcing routine clarification questions."""
    current = _detect_temporal_scope(question)
    if current:
        return {
            **current,
            "source": "current_request",
            "instruction": "Use the period explicitly requested by the user.",
        }

    # An explicit all/complete request must not silently inherit "today" from
    # a previous turn. It is a complete data-set request unless a date was
    # stated in this same question (handled above).
    if _has_explicit_all_scope(question):
        return {
            "scope": "all_available_records",
            "matched_text": "all records",
            "source": "current_request",
            "instruction": (
                "Return the complete matching record set. Do not add a date filter "
                "unless the user explicitly supplied one."
            ),
        }

    recent = history[-8:]
    for preferred_role in ("user", "assistant"):
        for item in reversed(recent):
            if item.get("role") != preferred_role:
                continue
            detected = _detect_temporal_scope(item.get("content", ""))
            if detected:
                return {
                    **detected,
                    "source": f"previous_{preferred_role}_message",
                    "instruction": (
                        "Inherit this active conversation period, execute without asking, and "
                        "briefly state the inherited period in the answer."
                    ),
                }

    return {
        "scope": "today",
        "matched_text": "امروز",
        "source": "default_current_business_date",
        "instruction": (
            "For a time-dependent operational report, use the current business date without "
            "asking and briefly say that today was assumed."
        ),
    }


def normalize_text(value: str) -> str:
    return (
        value.replace("ي", "ی")
        .replace("ك", "ک")
        .replace("ۀ", "ه")
        .replace("ة", "ه")
        .translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        .casefold()
        .strip()
    )


def _terms(value: str) -> set[str]:
    expanded = expand_business_query(normalize_text(value))
    return {
        term
        for term in expanded
        if len(term) > 1 and term not in _STOP_WORDS
    }


def _bounded(value: Any, limit: int) -> str:
    return str(value or "")[:limit]


def find_successful_report_examples(
    settings: Settings,
    question: str,
    limit: int = 4,
    allowed_sources: set[str] | None = None,
    *,
    principal: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve report patterns only from conversations owned by ``principal``.

    Administrators intentionally receive no implicit cross-user memory bypass:
    database reporting authority does not grant access to another user's chat.
    """
    query_terms = _terms(question)
    owner = str(principal or "").strip()
    if not query_terms or not owner:
        return []
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT a.id, a.conversation_id, a.content AS answer, a.sql_text,
                      a.sources_json,
                      (SELECT u.content FROM chat_messages AS u
                       WHERE u.conversation_id = a.conversation_id
                         AND u.role = 'user' AND u.id < a.id
                       ORDER BY u.id DESC LIMIT 1) AS question
               FROM chat_messages AS a
               JOIN chat_conversations AS c ON c.id = a.conversation_id
               WHERE a.role = 'assistant' AND a.sql_text IS NOT NULL
                 AND c.username = ? COLLATE NOCASE
               ORDER BY a.id DESC LIMIT 300""",
            (owner,),
        ).fetchall()

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for row in rows:
        prior_question = _bounded(row["question"], 1000)
        answer = _bounded(row["answer"], 1200)
        sources = json.loads(row["sources_json"] or "[]")
        normalized_sources = {str(source).casefold() for source in sources}
        if allowed_sources and not normalized_sources.intersection(allowed_sources):
            continue
        question_overlap = query_terms & _terms(prior_question)
        evidence_overlap = query_terms & _terms(" ".join([answer, *map(str, sources)]))
        score = len(question_overlap) * 5 + len(evidence_overlap)
        normalized_question = normalize_text(question)
        normalized_prior = normalize_text(prior_question)
        if normalized_question and (
            normalized_question in normalized_prior or normalized_prior in normalized_question
        ):
            score += 12
        if score <= 0:
            continue
        ranked.append((score, int(row["id"]), {
            "prior_question": prior_question,
            "sql_pattern": _bounded(row["sql_text"], 8000),
            "sources": sources[:12],
            "guidance": "Reuse only the verified objects/joins; recalculate with the current request filters.",
        }))

    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [item[2] for item in ranked[: max(1, min(limit, 8))]]


def _definition_context(
    settings: Settings,
    question: str,
    route: VaranegarRoute | None = None,
) -> list[dict[str, Any]]:
    definitions = search_definitions(settings, question, 5)
    prepared = [
        {
            "term": _bounded(item.get("term"), 250),
            "definition": _bounded(item.get("definition"), 1200),
            "rules": _bounded(item.get("rules"), 1200),
            "approved_sql": _bounded(item.get("approved_sql"), 5000) or None,
            "related_objects": list(item.get("related_objects") or [])[:20],
        }
        for item in definitions
    ]
    if route is not None:
        operational = route_definition(route)
        if not any(normalize_text(str(item.get("term") or "")) == normalize_text(route.label) for item in prepared):
            prepared.insert(0, operational)
    return prepared[:6]


def _schema_context(
    settings: Settings,
    question: str,
    definitions: list[dict[str, Any]],
    *,
    admin_full_database: bool = False,
) -> list[dict[str, Any]]:
    # Reports are designed around Views: they already carry the business
    # joins, calculated fields and Varanegar captions.  Keep base Tables out
    # of the initial prompt whenever a relevant View exists.  Tables remain a
    # deliberate fallback for operational/raw-detail questions with no View.
    if admin_full_database:
        # Rank matches from the complete indexed catalog.  The prompt receives
        # a relevance shortlist only to keep tool/context transport bounded;
        # no table or view is excluded from discovery or later SQL inspection.
        raw = search_schema(settings, question, _ADMIN_SCHEMA_CONTEXT_LIMIT)
        seen = {(str(item.get("schema")), str(item.get("name"))) for item in raw}
        for definition in definitions:
            for reference in definition.get("related_objects", []):
                parts = str(reference).split(".")
                if len(parts) < 2 or (parts[0], parts[1]) in seen:
                    continue
                item = get_schema_object(settings, parts[0], parts[1])
                if item:
                    raw.append(item)
                    seen.add((parts[0], parts[1]))
        return summarize_schema_results(raw[:_ADMIN_SCHEMA_CONTEXT_LIMIT], question)

    raw = search_schema(settings, question, _INITIAL_VIEW_CONTEXT_LIMIT, object_type="VIEW")
    view_first = bool(raw)
    if not raw:
        raw = search_schema(settings, question, _INITIAL_TABLE_CONTEXT_LIMIT, object_type="TABLE")
    context_limit = _INITIAL_VIEW_CONTEXT_LIMIT if view_first else _INITIAL_TABLE_CONTEXT_LIMIT
    seen = {(str(item.get("schema")), str(item.get("name"))) for item in raw}
    for definition in definitions:
        for reference in definition.get("related_objects", []):
            parts = str(reference).split(".")
            if len(parts) < 2:
                continue
            key = (parts[0], parts[1])
            if key in seen:
                continue
            item = get_schema_object(settings, *key)
            if view_first and item and str(item.get("type") or "").upper() != "VIEW":
                continue
            if item:
                raw.append(item)
                seen.add(key)
            if len(raw) >= context_limit:
                break
    return summarize_schema_results(raw[:context_limit], question)


def _route_schema_context(
    settings: Settings,
    route: VaranegarRoute,
    question: str,
    *,
    admin_full_database: bool = False,
) -> list[dict[str, Any]]:
    """Load report Views by business concept, then add lexical matches.

    The old sales route sorted every question by one fixed global list before
    considering relevance. This loader starts with the exact report contract
    for the detected Varanegar concept and only then expands within Views.
    """
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    with sqlite_connection(settings.sqlite_path) as conn:
        for source in route.sources:
            schema, separator, name = source.partition(".")
            if not separator:
                continue
            row = conn.execute(
                """SELECT details_json FROM schema_objects
                   WHERE lower(schema_name) = lower(?) AND lower(object_name) = lower(?)
                   LIMIT 1""",
                (schema, name),
            ).fetchone()
            if not row:
                continue
            item = json.loads(row["details_json"])
            key = (str(item.get("schema") or "").casefold(), str(item.get("name") or "").casefold())
            if key not in seen:
                candidates.append(item)
                seen.add(key)

    # Lexical discovery is an expansion mechanism, not the primary ranking.
    # Keep it bounded to the same six-View budget when no curated source exists.
    lexical_type = None if admin_full_database else "VIEW"
    lexical_limit = _ADMIN_SCHEMA_CONTEXT_LIMIT if admin_full_database else 20
    for item in search_schema(settings, question, lexical_limit, object_type=lexical_type):
        key = (str(item.get("schema") or "").casefold(), str(item.get("name") or "").casefold())
        if key in seen:
            continue
        candidates.append(item)
        seen.add(key)
        candidate_limit = (
            _ADMIN_SCHEMA_CONTEXT_LIMIT
            if admin_full_database
            else max(_INITIAL_VIEW_CONTEXT_LIMIT, len(route.sources))
        )
        if len(candidates) >= candidate_limit:
            break

    limit = (
        _ADMIN_SCHEMA_CONTEXT_LIMIT
        if admin_full_database
        else max(_INITIAL_VIEW_CONTEXT_LIMIT, min(len(route.sources), 9))
    )
    return summarize_schema_results(candidates[:limit], question)


def _known_source_failures(
    settings: Settings,
    schema_candidates: list[dict[str, Any]],
    examples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relevant_sources = {
        f"{item.get('schema')}.{item.get('name')}".casefold()
        for item in schema_candidates
    }
    for example in examples:
        relevant_sources.update(str(source).casefold() for source in example.get("sources", []))
    if not relevant_sources:
        return []
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT sources_json, error_text, created_at
               FROM query_audit
               WHERE succeeded = 0 AND error_text IS NOT NULL
               ORDER BY id DESC LIMIT 150"""
        ).fetchall()
    warnings = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        sources = [str(value) for value in json.loads(row["sources_json"] or "[]")]
        matching = [source for source in sources if source.casefold() in relevant_sources]
        if not matching:
            continue
        error = _bounded(row["error_text"], 700)
        key = (",".join(sorted(matching)), error)
        if key in seen:
            continue
        seen.add(key)
        warnings.append({"sources": matching, "last_error": error})
        if len(warnings) >= 6:
            break
    return warnings


def prepare_analysis_context(
    settings: Settings,
    question: str,
    history: list[dict[str, str]],
    now: datetime | None = None,
    admin_full_database: bool = False,
    principal: str | None = None,
) -> dict[str, Any]:
    recent_context = " ".join(item.get("content", "") for item in history[-6:])
    retrieval_question = f"{recent_context}\n{question}".strip()
    customer_financial_followup = resolve_customer_financial_period_followup(
        question, history
    )
    route = (
        get_varanegar_route(customer_financial_followup["route_name"])
        if customer_financial_followup
        else resolve_varanegar_route(question, recent_context)
    )
    definitions = _definition_context(settings, question, route)
    receipt_policy = bool(route and route.name == "receipt") or _is_receipt_question(question)
    analysis_route = route.name if route else "general"
    if route is not None:
        schema_candidates = _route_schema_context(
            settings,
            route,
            retrieval_question,
            admin_full_database=admin_full_database,
        )
        # A missing/old schema cache must not make a report impossible.
        if not schema_candidates:
            schema_candidates = _schema_context(
                settings,
                retrieval_question,
                definitions,
                admin_full_database=admin_full_database,
            )
            analysis_route = f"{route.name}_catalog_fallback"
    else:
        schema_candidates = _schema_context(
            settings,
            retrieval_question,
            definitions,
            admin_full_database=admin_full_database,
        )
    schema_source_policy = "admin_all_database" if admin_full_database else (
        "view_first"
        if schema_candidates and all(str(item.get("type") or "").upper() == "VIEW" for item in schema_candidates)
        else "table_fallback"
    )
    allowed_sources = {
        f"{item.get('schema')}.{item.get('name')}".casefold()
        for item in schema_candidates
    }
    examples = find_successful_report_examples(
        settings, retrieval_question, 4,
        allowed_sources=(
            allowed_sources
            if route is not None and not admin_full_database
            else None
        ),
        principal=principal,
    )
    temporal_context = resolve_temporal_context(question, history)
    current_tehran = tehran_now(now)
    temporal_context.update({
        "current_tehran_datetime": current_tehran.isoformat(),
        "current_business_date": jalali_business_date(current_tehran),
    })
    required_result_columns = None
    if route is not None and route.name == "profit_last_purchase":
        groups = [
            ["BrandName"],
            ["COGSAtLastPurchasePrice", "CostAtLastPurchasePrice"],
            [
                "ProfitAtLastPurchasePrice",
                "GrossProfitAtLastPurchasePrice",
                "NetProfitAtLastPurchasePrice",
            ],
        ]
        if "تخف" in normalize_text(question):
            groups.append([
                "SettlementDiscountAmount",
                "AllocatedSettlementDiscount",
                "AllocatedSettlementDiscountAmount",
            ])
        required_result_columns = {
            "groups": groups,
            "instruction": (
                "The final non-empty SQL result must contain at least one column from every "
                "group. Price-coverage, row-count, or ambiguity diagnostics do not answer the request."
            ),
        }
    context = {
        "current_request": question,
        "runtime_policy": [
            "Current runtime policy overrides conflicting legacy definition text.",
            *organization_reporting_policy(),
            (
                "Company reporting exclusion: the external-company sellers "
                + ", ".join(sorted(EXTERNAL_SALES_PERSON_NAMES))
                + " are never internal salespeople, supervisors, team members, or report subjects. "
                "For every query using a sales/return report source, exclude their exact canonical IDs "
                + ", ".join(str(value) for value in sorted(EXTERNAL_SALES_PERSON_IDS))
                + " from both DealerId and SupervisorId. Use this predicate for alias s: "
                + external_sales_exclusion_sql("s")
                + ". Do not filter these identities by name."
            ),
            (
                "The verified Tehran business date is "
                f"{temporal_context['current_business_date']}. For scope=today, filter SQL on this "
                "exact date; never use MAX/MIN of database dates as a substitute for today."
            ),
            "For unspecified sales document basis, default to combined invoice and voucher reporting.",
            (
                "For customer receipt/collection reports, count PayAmount only when PayTypeName is an "
                "external instrument: cash, cheque, deposit, or its advance-payment variant. Filter "
                "PayTypeName in WHERE before summing; exclude discounts, credits, account transfers, "
                "settlements, return settlements, notices, and discrepancies."
                if receipt_policy else ""
            ),
            (
                "Admin has read-only discovery access to every catalogued SQL table and view. "
                "Varanegar routes, organization definitions, and preferred sources are semantic guidance, "
                "not an allowlist. Search and inspect any database object needed for an accurate answer."
                if admin_full_database
                else (
                    "Use the preloaded report Views first. Do not use base SQL Tables unless no relevant "
                    "View is available or the View lacks a required field."
                    if schema_source_policy == "view_first"
                    else "No relevant report View was found; base SQL Tables are the allowed fallback for this request."
                )
            ),
            "Successful examples are query patterns, not cached answers; always execute against live data.",
            "A zero-row result is provisional until filters, dates, and source choice are checked.",
            "Apply resolved_temporal_context to the SQL. Inherited or default periods are stated briefly, not asked as a follow-up question.",
        ],
        "resolved_temporal_context": temporal_context,
        "active_customer_financial_followup": customer_financial_followup,
        "requires_live_database_evidence": bool(customer_financial_followup)
        or bool(
            route
            and route.name in {"customer_cardex", "invoice_balance"}
            and not re.search(r"\b(?:\u062a\u0639\u0631\u06cc\u0641|\u0686\u06cc\u0633\u062a)\b", normalize_text(question))
        ),
        "analysis_route": analysis_route,
        "analysis_route_label": route.label if route else "تحلیل عمومی داده",
        "report_basis": route.report_basis if route else None,
        "route_guidance": list(route.guidance) if route else [],
        "operational_contract": (
            {
                "activity": route.activity,
                "risk_level": route.risk_level,
                "required_context": list(route.required_context),
                "guards": list(route.guards),
            }
            if route else None
        ),
        "schema_source_policy": schema_source_policy,
        "catalog_scope": (
            {
                **schema_stats(settings),
                "search_scope": "all_catalogued_tables_and_views",
                "candidate_transport": "relevance_shortlist_not_access_limit",
            }
            if admin_full_database
            else None
        ),
        "business_definitions": definitions,
        "receipt_policy": receipt_policy,
        "successful_report_examples": examples,
        "schema_candidates": schema_candidates,
        "known_source_failures": _known_source_failures(settings, schema_candidates, examples),
        "required_result_columns": required_result_columns,
        "reporting_exclusions": {
            "person_ids": sorted(EXTERNAL_SALES_PERSON_IDS),
            "applies_to": ["DealerId", "SupervisorId"],
            "purpose": "Exclude external-company sellers from every internal report and team structure.",
        },
        "organization_structure": {
            "alborz": ALBORZ_TEAM_STRUCTURE,
            "configured_rules": list_structure(settings),
            "usage": (
                "This is semantic guidance only: do not add these values as SQL filters, do not change "
                "Varanegar report calculations, and do not silently reassign sales. Use it to explain the "
                "meaning of branch, line, team and confirmed brand portfolios. If the requested team conflicts "
                "with this structure or contains an exceptional cross-team sale, state a short warning."
            ),
        },
    }
    return context


def has_relevant_analysis_context(context: dict[str, Any]) -> bool:
    return any(
        context.get(key)
        for key in ("business_definitions", "successful_report_examples", "schema_candidates")
    )
