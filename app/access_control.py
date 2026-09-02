from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlglot import exp, parse_one

from app.auth_service import user_profile
from app.config import Settings
from app.database import sqlite_connection
from app.reporting_policy import EXTERNAL_SALES_PERSON_IDS
from app.schema_catalog import SELLER_CUSTOMER_SOURCES, SELLER_REFERENCE_SOURCES
from app.schema_service import get_schema_object
from app.sql_guard import ValidatedSql


class DataAccessDenied(ValueError):
    """Raised when an authenticated principal requests data outside its policy."""


@dataclass(frozen=True)
class DataAccessPolicy:
    username: str
    role: str = ""
    branch: str = ""
    sales_line: str = ""
    personnel_id: int | None = None
    supervisor_personnel_id: int | None = None
    is_restricted_seller: bool = False
    is_admin: bool = False

    def trusted_context(self) -> dict[str, Any]:
        if self.is_admin:
            return {
                "principal": self.username,
                "role": self.role or "Admin",
                "mode": "admin_full_database_read",
                "database_scope": "all_catalogued_tables_and_views",
                "organization_definitions": "semantic_guidance_not_an_allowlist",
                "write_access": False,
                "planning_local_write_access": True,
            }
        if not self.is_restricted_seller:
            return {
                "principal": self.username,
                "mode": "internal_unrestricted",
            }
        return {
            "principal": self.username,
            "role": self.role,
            "mode": "seller_customer_scope",
            "authorized_customer_scope": {
                "branch_dimension": "CustomerLevelName",
                "branch": self.branch,
                "line_dimension": "CustomerCategoryName",
                "line": self.sales_line,
            },
            "own_salesperson_id": self.personnel_id,
            "team_supervisor_id": self.supervisor_personnel_id,
            "allowed": [
                "sales and invoices for customers in the same branch and sales line",
                "customer sales, returns and open invoices",
                "customer cardex and account activity",
                "customer receipts, settlements and balances",
                "customer-scoped NGT activity",
            ],
            "allowed_data_classes": [
                "customer_sales",
                "customer_collections",
                "customer_master",
                "product_reference",
            ],
            "preferred_sources": {
                "sales": ["dbo.SalesReviewFast", "dbo.SalesReturnReviewFast"],
                "invoices": ["Acc.vwRcvSaleReview", "dbo.vwReview_RcvAccountSale2"],
                "cardex": ["dbo.vwReview_RcvAccountCardex2", "dbo.CustomerCardex_Info"],
                "receipts": ["Acc.vwRcvPaymentsReview"],
                "settlements": ["dbo.vwReview_RcvAccountSettlement2"],
                "balances": ["Acc.vwCustomerBalance"],
                "ngt_customer": ["FRU.NGT_TourCustomerModel"],
            },
            "denied": [
                "purchase price and cost of goods",
                "profit and margin",
                "general finance, accounting, treasury, supplier and payroll data",
                "data outside the authorized customer branch and line",
            ],
            "enforcement": "server-side source rewriting and protected-field rejection",
        }


_SELLER_ROLE = "فروشنده"

_SAFE_CUSTOMER_SOURCES = set(SELLER_CUSTOMER_SOURCES)
"""Compatibility fallback for catalogs created before the access metadata existed."""
_LEGACY_SAFE_CUSTOMER_SOURCES = {
    "dbo.salesreviewfast",
    "dbo.salesreturnreviewfast",
    "dbo.customer",
    "dbo.customercardex_info",
    "dbo.vwtablethistory",
    "acc.vwrcvpaymentsreview",
    "acc.vwrcvsalereview",
    "acc.vwrcvsalereviewfast",
    "acc.vwrcvstatementreviewfast",
    "acc.vwrcvchequereview",
    "acc.vwrcvbankordersreview",
    "acc.vwrcvretchequereview",
    "acc.vwrcvretsalereview",
    "acc.vwcustomerbalance",
    "acc.vwpaymentsfast",
    "dbo.vwreview_rcvaccountsale2",
    "dbo.vwreview_rcvaccountpayment2",
    "dbo.vwreview_rcvaccountsettlement2",
    "dbo.vwreview_rcvaccountcardex2",
    "gnr.vwcust",
}

_SAFE_GLOBAL_REFERENCE_SOURCES = set(SELLER_REFERENCE_SOURCES)
_LEGACY_SAFE_GLOBAL_REFERENCE_SOURCES = {
    "gnr.tblbrand",
    "gnr.tblmanufacturer",
    "gnr.tblgoods",
    "gnr.tblgoodsgroup",
    "gnr.tblsalearea",
    "gnr.tblsalepath",
}

_CUSTOMER_SOURCE_PREFIXES = (
    "dbo.sales",
    "dbo.customer",
    "fru.ngt_",
    "fru.customercall",
)

_FORBIDDEN_SOURCE_MARKERS = (
    "treasury",
    "supplier",
    "supinvoice",
    "bankaccount",
    "expense",
    "stockacc",
    "buyreview",
    "purchase",
    "ledger",
    "journal",
    "payroll",
    "salary",
)

_FORBIDDEN_COLUMN_MARKERS = (
    "buy",
    "purchase",
    "cost",
    "ica",
    "profit",
    "margin",
    "cogs",
    "supplier",
    "password",
)

_CUSTOMER_ID_COLUMNS = (
    "customerid",
    "custid",
    "custref",
    "customerref",
    "pcustid",
    "filterid",
)

_CUSTOMER_UNIQUE_ID_COLUMNS = (
    "customeruniqueid",
    "custuniqueid",
)

_RESTRICTED_REQUEST_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"قیمت\s*خرید",
        r"بهای\s*(?:خرید|تمام[\s‌-]*شده)",
        r"حاشیه\s*سود",
        r"\bسود\b",
        r"\b(?:cost|cogs|purchase\s*price|profit|margin)\b",
        r"خزانه",
        r"موجودی\s*(?:کل\s*)?(?:بانک|صندوق)",
        r"حساب\s*بانکی\s*(?:شرکت|مجموعه)",
        r"دفتر\s*کل",
        r"ترازنامه",
        r"سود\s*و\s*زیان",
        r"حقوق\s*و\s*دستمزد",
        r"ت[اأ]مین[‌\s-]*کننده",
    )
)


def policy_for_user(settings: Settings, username: str | None) -> DataAccessPolicy:
    principal = str(username or "").strip()
    if not principal or principal in {"local", "action-api-key"}:
        return DataAccessPolicy(username=principal or "action-api-key")
    profile = user_profile(settings, principal)
    if not profile:
        return DataAccessPolicy(
            username=principal,
            is_admin=principal.casefold() == "admin",
        )
    role = str(profile.get("role") or "").strip()
    branch = str(profile.get("branch") or "").strip()
    sales_line = str(profile.get("sales_line") or "").strip()
    restricted = (
        settings.seller_data_restrictions_enabled
        and role.casefold() == _SELLER_ROLE.casefold()
    )
    resolved_username = str(profile.get("username") or principal)
    permissions = set(profile.get("permissions") or [])
    is_admin = "reports.full" in permissions or resolved_username.casefold() == "admin" or role.casefold() in {
        "admin",
        "administrator",
        "مدیر سیستم",
        "مدیر سامانه",
    }
    if restricted and (
        not branch or not sales_line or profile.get("personnel_id") is None
        or profile.get("supervisor_personnel_id") is None
    ):
        raise DataAccessDenied("Seller access profile is incomplete")
    return DataAccessPolicy(
        username=resolved_username,
        role=role,
        branch=branch,
        sales_line=sales_line,
        personnel_id=profile.get("personnel_id"),
        supervisor_personnel_id=profile.get("supervisor_personnel_id"),
        is_restricted_seller=restricted,
        is_admin=is_admin,
    )


def restricted_request_message(policy: DataAccessPolicy, message: str) -> str | None:
    if not policy.is_restricted_seller:
        return None
    if not any(pattern.search(message) for pattern in _RESTRICTED_REQUEST_PATTERNS):
        return None
    return (
        "شما به قیمت خرید، بهای تمام‌شده، سود و حاشیه سود یا گزارش‌های مالی و "
        "حسابداری عمومی دسترسی ندارید. گزارش‌های مشتریان "
        f"«{policy.branch} / {policy.sales_line}» شامل فروش، کاردکس، دریافتی و NGT "
        "در دسترس شماست."
    )


def _normalized_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _has_forbidden_column(name: str) -> bool:
    normalized = _normalized_identifier(name)
    return any(marker in normalized for marker in _FORBIDDEN_COLUMN_MARKERS)


def _source_key(schema: str, name: str) -> str:
    return f"{schema}.{name}".casefold()


def _is_customer_source(source: str) -> bool:
    if source in _SAFE_CUSTOMER_SOURCES or source in _LEGACY_SAFE_CUSTOMER_SOURCES:
        return True
    return source.startswith(_CUSTOMER_SOURCE_PREFIXES)


def _is_source_allowed(source: str) -> bool:
    if source in _SAFE_CUSTOMER_SOURCES or source in _SAFE_GLOBAL_REFERENCE_SOURCES or source in _LEGACY_SAFE_CUSTOMER_SOURCES or source in _LEGACY_SAFE_GLOBAL_REFERENCE_SOURCES:
        return True
    if any(marker in source for marker in _FORBIDDEN_SOURCE_MARKERS):
        return False
    return source.startswith(_CUSTOMER_SOURCE_PREFIXES)


def _catalog_seller_access(item: dict[str, Any]) -> str | None:
    value = (item.get("catalog") or {}).get("seller_access")
    return str(value) if value in {"restricted", "customer_scope", "reference"} else None


def _object_metadata(
    settings: Settings, schema: str, name: str
) -> tuple[str, str, list[dict[str, Any]]] | None:
    with sqlite_connection(settings.sqlite_path) as conn:
        if schema:
            row = conn.execute(
                """SELECT schema_name, object_name, details_json
                   FROM schema_objects
                   WHERE schema_name=? COLLATE NOCASE AND object_name=? COLLATE NOCASE""",
                (schema, name),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT schema_name, object_name, details_json
                   FROM schema_objects
                   WHERE object_name=? COLLATE NOCASE
                   ORDER BY CASE WHEN schema_name='dbo' THEN 0 ELSE 1 END, schema_name
                   LIMIT 1""",
                (name,),
            ).fetchone()
    if row is None:
        return None
    details = json.loads(row["details_json"])
    return (
        str(row["schema_name"]),
        str(row["object_name"]),
        list(details.get("columns") or []),
    )


def _customer_scope_column(
    schema: str, name: str, columns: list[dict[str, Any]]
) -> tuple[str, str] | None:
    by_normalized = {
        _normalized_identifier(str(column.get("name") or "")): column
        for column in columns
    }
    source = _source_key(schema, name)
    for candidate in _CUSTOMER_ID_COLUMNS:
        if candidate in by_normalized:
            column = by_normalized[candidate]
            data_type = str(column.get("data_type") or "").casefold()
            kind = "unique" if data_type == "uniqueidentifier" else "backoffice_numeric"
            return str(column.get("name") or ""), kind
    for candidate in _CUSTOMER_UNIQUE_ID_COLUMNS:
        if candidate in by_normalized:
            return str(by_normalized[candidate].get("name") or ""), "unique"
    if source == "gnr.vwcust" and "id" in by_normalized:
        return str(by_normalized["id"].get("name") or ""), "backoffice_numeric"
    if source == "fru.ngt_tourcustomermodel" and "backofficeid" in by_normalized:
        return str(by_normalized["backofficeid"].get("name") or ""), "backoffice_text"
    return None


def _quote_identifier(value: str) -> str:
    return "[" + value.replace("]", "]]") + "]"


def response_access_scope(policy: DataAccessPolicy) -> dict[str, str] | None:
    if not policy.is_restricted_seller:
        return None
    return {
        "mode": "seller_customer_scope",
        "branch": policy.branch,
        "sales_line": policy.sales_line,
    }


def response_scope_matches(
    policy: DataAccessPolicy, response: dict[str, Any]
) -> bool:
    if not policy.is_restricted_seller:
        return True
    return response.get("access_scope") == response_access_scope(policy)


def _quote_literal(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'"


def _text_storage_variants(value: str) -> list[str]:
    """Return the Unicode and legacy UTF-8-as-Latin-1 forms used by Negin views."""
    normalized_candidates = [value]
    for source, target in (("ی", "ي"), ("ي", "ی"), ("ک", "ك"), ("ك", "ک")):
        for candidate in list(normalized_candidates):
            normalized = candidate.replace(source, target)
            if normalized not in normalized_candidates:
                normalized_candidates.append(normalized)
    variants: list[str] = []
    for candidate in normalized_candidates:
        for stored in (candidate, candidate.encode("utf-8").decode("latin1")):
            if stored not in variants:
                variants.append(stored)
    return variants


def _text_scope_predicate(column: str, value: str) -> str:
    literals = ", ".join(_quote_literal(item) for item in _text_storage_variants(value))
    return f"{column} IN ({literals})"


def _scope_subquery(policy: DataAccessPolicy, kind: str) -> str:
    if kind == "unique":
        selected = "c.[CustGUID]"
    elif kind == "backoffice_text":
        selected = "CONVERT(varchar(50), c.[ID])"
    else:
        selected = "c.[ID]"
    return (
        f"SELECT DISTINCT {selected} FROM [GNR].[vwCust] AS c "
        f"WHERE {_text_scope_predicate('c.[CustLevelName]', policy.branch)} "
        f"AND {_text_scope_predicate('c.[CustCtgrName]', policy.sales_line)}"
    )


def _replacement_table(
    schema: str,
    name: str,
    alias: str,
    customer_column: str,
    scope_kind: str,
    policy: DataAccessPolicy,
    index: int,
    exclude_external_sales_identities: bool = False,
) -> exp.Expression:
    raw_alias = f"__acl_source_{index}"
    external_predicate = ""
    if exclude_external_sales_identities:
        ids = ", ".join(str(value) for value in sorted(EXTERNAL_SALES_PERSON_IDS))
        quoted_alias = _quote_identifier(raw_alias)
        external_predicate = (
            f" AND COALESCE({quoted_alias}.[DealerId], -1) NOT IN ({ids})"
            f" AND COALESCE({quoted_alias}.[SupervisorId], -1) NOT IN ({ids})"
        )
    fragment = (
        "(SELECT * FROM "
        f"{_quote_identifier(schema)}.{_quote_identifier(name)} AS {_quote_identifier(raw_alias)} "
        f"WHERE {_quote_identifier(raw_alias)}.{_quote_identifier(customer_column)} IN "
        f"({_scope_subquery(policy, scope_kind)}){external_predicate}) AS {_quote_identifier(alias)}"
    )
    parsed = parse_one(f"SELECT * FROM {fragment}", read="tsql")
    return parsed.args["from"].this


def enforce_sql_access(
    settings: Settings,
    policy: DataAccessPolicy,
    validated: ValidatedSql,
) -> ValidatedSql:
    if not policy.is_restricted_seller:
        return validated

    statement = parse_one(validated.sql, read="tsql")
    selected_columns = [column.name for column in statement.find_all(exp.Column)]
    if any(_has_forbidden_column(name) for name in selected_columns):
        raise DataAccessDenied("The requested metric is not available for this role")

    cte_names = {
        cte.alias_or_name.casefold()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }
    secured_sources = set(validated.sources)
    physical_tables = [
        table
        for table in statement.find_all(exp.Table)
        if table.db or table.name.casefold() not in cte_names
    ]
    if not physical_tables:
        return validated

    for index, table in enumerate(list(physical_tables), 1):
        metadata = _object_metadata(settings, table.db, table.name)
        if metadata is None:
            raise DataAccessDenied("The requested data source is not available for this role")
        schema, name, columns = metadata
        source = _source_key(schema, name)
        item = get_schema_object(settings, schema, name) or {}
        seller_access = _catalog_seller_access(item)
        if seller_access == "restricted" or (seller_access is None and not _is_source_allowed(source)):
            raise DataAccessDenied("The requested data source is not available for this role")
        if any(_has_forbidden_column(str(column.get("name") or "")) for column in columns):
            has_star = any(isinstance(node, exp.Star) for node in statement.walk())
            if has_star:
                raise DataAccessDenied("Select explicit permitted fields for this role")

        scope_column = _customer_scope_column(schema, name, columns)
        if seller_access == "customer_scope" or (seller_access is None and _is_customer_source(source)):
            if scope_column is None:
                raise DataAccessDenied("This source cannot be safely limited to the seller scope")
            alias = table.alias_or_name or name
            replacement = _replacement_table(
                schema,
                name,
                alias,
                scope_column[0],
                scope_column[1],
                policy,
                index,
                exclude_external_sales_identities=source in {
                    "dbo.salesreviewfast", "dbo.salesreturnreviewfast"
                },
            )
            table.replace(replacement)

    secured_sources.add("GNR.vwCust")
    return ValidatedSql(
        sql=statement.sql(dialect="tsql"),
        sources=sorted(secured_sources, key=str.casefold),
    )


def filter_schema_item(
    policy: DataAccessPolicy, item: dict[str, Any]
) -> dict[str, Any] | None:
    if not policy.is_restricted_seller:
        return item
    schema = str(item.get("schema") or "")
    name = str(item.get("name") or "")
    source = _source_key(schema, name)
    seller_access = _catalog_seller_access(item)
    if seller_access == "restricted" or (seller_access is None and not _is_source_allowed(source)):
        return None
    columns = list(item.get("columns") or [])
    if seller_access != "reference" and source not in _SAFE_GLOBAL_REFERENCE_SOURCES and _customer_scope_column(
        schema, name, columns
    ) is None:
        return None
    filtered = dict(item)
    filtered["columns"] = [
        column
        for column in columns
        if not _has_forbidden_column(str(column.get("name") or ""))
    ]
    return filtered


def schema_item_allowed(policy: DataAccessPolicy, item: dict[str, Any]) -> bool:
    return filter_schema_item(policy, item) is not None


def _source_allowed_in_catalog(
    settings: Settings, policy: DataAccessPolicy, source: str
) -> bool:
    parts = source.split(".", 1)
    if len(parts) != 2:
        return False
    item = get_schema_object(settings, parts[0], parts[1])
    return bool(item and filter_schema_item(policy, item) is not None)


def filter_schema_items(
    policy: DataAccessPolicy, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in items:
        visible = filter_schema_item(policy, item)
        if visible is not None:
            filtered.append(visible)
    return filtered


def filter_prepared_context(
    settings: Settings,
    policy: DataAccessPolicy,
    context: dict[str, Any],
) -> dict[str, Any]:
    if not policy.is_restricted_seller:
        return context
    filtered = dict(context)
    filtered["access_policy"] = policy.trusted_context()
    filtered["schema_candidates"] = [
        item
        for item in list(context.get("schema_candidates") or [])
        if filter_schema_item(policy, item) is not None
    ]
    safe_examples = []
    for example in list(context.get("successful_report_examples") or []):
        sources = [str(value) for value in example.get("sources") or []]
        if sources and all(_source_allowed_in_catalog(settings, policy, source) for source in sources):
            safe_examples.append(example)
    filtered["successful_report_examples"] = safe_examples
    filtered["known_source_failures"] = [
        item
        for item in list(context.get("known_source_failures") or [])
        if all(_source_allowed_in_catalog(settings, policy, str(source)) for source in item.get("sources") or [])
    ]
    return filtered
