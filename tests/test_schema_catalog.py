from __future__ import annotations

import json
from datetime import datetime

from app.access_control import filter_schema_item, policy_for_user
from app.database import sqlite_connection
from app.schema_catalog import account_name_context_label, sync_schema_catalog, update_catalog_entry


def _object(settings, schema: str, name: str, columns: list[str]) -> None:
    data = {
        "schema": schema,
        "name": name,
        "type": "VIEW",
        "columns": [{"name": column, "data_type": "int"} for column in columns],
        "foreign_keys": [],
        "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES (?, ?, 'VIEW', ?, ?)""",
            (schema, name, json.dumps(data), datetime.utcnow().isoformat()),
        )


def test_catalog_adds_persian_aliases_and_conservative_access(settings):
    _object(settings, "dbo", "CustomerCardex_Info", ["CustId", "BuyAmount"])
    _object(settings, "dbo", "SalesSecret", ["CustId"])

    result = sync_schema_catalog(settings)

    assert result == {"cataloged_objects": 2, "automatic_labels": 2}
    with sqlite_connection(settings.sqlite_path) as conn:
        customer = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='CustomerCardex_Info'"
        ).fetchone()["details_json"])
        secret = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='SalesSecret'"
        ).fetchone()["details_json"])
    assert customer["catalog"]["persian_name"] == "گردش حساب مشتری"
    assert customer["catalog"]["seller_access"] == "customer_scope"
    assert customer["columns"][0]["persian_name"] == "شناسه مشتری"
    assert secret["catalog"]["seller_access"] == "restricted"


def test_catalog_uses_curated_sales_name_and_access(settings):
    _object(settings, "dbo", "SalesReviewFast", ["CustomerId", "SellNetAmount"])

    sync_schema_catalog(settings)

    with sqlite_connection(settings.sqlite_path) as conn:
        item = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='SalesReviewFast'"
        ).fetchone()["details_json"])
    assert item["catalog"]["persian_name"] == "گزارش سریع فروش مشتریان"
    assert item["catalog"]["seller_access"] == "customer_scope"
    assert "فروش خالص" in item["catalog"]["aliases"]


def test_financial_column_dictionary_uses_exact_business_meanings(settings):
    _object(
        settings, "Acc", "vwCustomerBalance",
        ["ID", "DcRef", "CustRef", "AccYear", "ud_Id", "DateOf", "BedAmount", "BesAmount", "Balance"],
    )
    sync_schema_catalog(settings)

    with sqlite_connection(settings.sqlite_path) as conn:
        item = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='vwCustomerBalance'"
        ).fetchone()["details_json"])
    labels = {column["name"]: column["persian_name"] for column in item["columns"]}
    statuses = {column["name"]: column["translation_status"] for column in item["columns"]}
    assert labels == {
        "ID": "شناسه رکورد",
        "DcRef": "شناسه مرکز توزیع",
        "CustRef": "شناسه مشتری",
        "AccYear": "سال مالی",
        "ud_Id": "شناسه یکتا",
        "DateOf": "تاریخ",
        "BedAmount": "مبلغ بدهکار",
        "BesAmount": "مبلغ بستانکار",
        "Balance": "مانده حساب",
    }
    assert set(statuses.values()) == {"verified"}


def test_unknown_column_is_saved_for_review_and_safe_names_are_inferred(settings):
    _object(settings, "dbo", "Example", ["GoodsCode", "MysteryXYZ"])
    sync_schema_catalog(settings)

    with sqlite_connection(settings.sqlite_path) as conn:
        item = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='Example'"
        ).fetchone()["details_json"])
        review = conn.execute(
            "SELECT occurrence_count FROM schema_translation_review WHERE column_name='MysteryXYZ'"
        ).fetchone()
    fields = {column["name"]: column for column in item["columns"]}
    assert fields["GoodsCode"]["persian_name"] == "کد کالا"
    assert fields["GoodsCode"]["translation_status"] == "inferred"
    assert fields["MysteryXYZ"]["persian_name"] == "MysteryXYZ"
    assert fields["MysteryXYZ"]["translation_status"] == "needs_review"
    assert review["occurrence_count"] == 1


def test_account_name_uses_bank_or_accounting_context_not_global_resource_label():
    bank = {
        "schema": "dbo", "name": "vwReview_RcvAccountBankAccount2", "type": "VIEW",
        "referenced_tables": [{"schema": "dbo", "name": "tblReview_RcvAccountBankAccount"}],
    }
    accounting = {"schema": "Acc", "name": "vwExpenseAccount", "type": "VIEW", "referenced_tables": []}

    assert account_name_context_label(bank, "AccountName") == (
        "نام صاحب حساب", "verified", "varanegar_review_grid"
    )
    assert account_name_context_label(accounting, "AccountName") == (
        "نام حساب", "inferred", "accounting_object_context"
    )


def test_conflicting_varanegar_captions_are_not_resolved_by_majority_vote(settings):
    _object(settings, "dbo", "ContextFreeExample", ["MultiMeaning"])
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.executemany(
            """INSERT INTO varanegar_column_labels (resource_name, technical_name, persian_name)
               VALUES (?, ?, ?)""",
            [
                ("ReviewResource.SalesResources.fa.resources", "MultiMeaning", "معنی فروش"),
                ("ReviewResource.StockResources.fa.resources", "MultiMeaning", "معنی انبار"),
            ],
        )

    sync_schema_catalog(settings)

    with sqlite_connection(settings.sqlite_path) as conn:
        item = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='ContextFreeExample'"
        ).fetchone()["details_json"])
    field = item["columns"][0]
    assert field["persian_name"] == "MultiMeaning"
    assert field["translation_status"] == "needs_review"


def test_manual_catalog_access_override_is_used_by_seller_filter(settings):
    _object(settings, "dbo", "CustomerCardex_Info", ["CustId", "BesAmount"])
    sync_schema_catalog(settings)
    update_catalog_entry(
        settings,
        "dbo",
        "CustomerCardex_Info",
        {"persian_name": "گردش مشتری", "seller_access": "restricted"},
    )
    with sqlite_connection(settings.sqlite_path) as conn:
        item = json.loads(conn.execute(
            "SELECT details_json FROM schema_objects WHERE object_name='CustomerCardex_Info'"
        ).fetchone()["details_json"])

    seller = policy_for_user(settings, "seller-without-profile")
    seller = seller.__class__(username="seller", is_restricted_seller=True, branch="شعبه", sales_line="لاین")
    assert filter_schema_item(seller, item) is None
