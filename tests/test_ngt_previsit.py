from dataclasses import replace
from datetime import date
from concurrent.futures import ThreadPoolExecutor
import json
from time import sleep
from urllib.parse import parse_qs
from uuid import UUID

import pytest

from app.models import PrevisitPreviewRequest
from app.ngt_previsit_service import (
    _calculate_ngt_credit_control,
    _catalog_sale_units,
    _device_warehouse_ids,
    _evaluate_promotion_conditions,
    _grouped_catalogs,
    build_previsit_voice_vocabulary,
    _normalise_evc,
    _post_evc,
    _token,
    previsit_context,
    preview_previsit,
    validate_order_draft,
    warm_previsit_route,
    catalog_image,
)


def test_previsit_voice_vocabulary_prioritizes_real_order_language_and_in_stock_skus():
    products = [
        {
            "name": "خمیر دندان لمینت میسویک",
            "brand": "میسویک",
            "group": "خمیر دندان",
            "manufacturer": "سیلانه سبز",
            "description": "ضد زردی و سفید کننده",
            "available_qty": 24,
        },
        {
            "name": "دستمال مرطوب کودک ۲۰ عددی دافی",
            "brand": "دافی",
            "group": "دستمال مرطوب کودک",
            "manufacturer": "آریان کیمیا تک",
            "description": "مناسب پوست حساس",
            "available_qty": 0,
        },
    ]

    vocabulary = build_previsit_voice_vocabulary(products, max_chars=2_400)

    assert len(vocabulary) <= 2_400
    assert "دونه یا تا" in vocabulary
    assert "پک" in vocabulary
    assert "کارتون یا کرتن" in vocabulary
    assert "برندهای مجاز" in vocabulary
    assert "میسویک" in vocabulary
    assert "دافی" in vocabulary
    assert "نام کامل کالاهای مجاز" in vocabulary
    assert "خمیر دندان لمینت میسویک" in vocabulary
    assert vocabulary.index("خمیر دندان لمینت میسویک") < vocabulary.index("دستمال مرطوب کودک 20 عددی دافی")
    assert "واژه‌های شاخص کالا" in vocabulary


def test_previsit_voice_vocabulary_is_bounded_and_strips_prompt_delimiters():
    products = [{
        "name": "کالای [ویژه] <آزمایشی>",
        "brand": "برند؛نمونه",
        "group": "گروه:بهداشت",
        "description": "توضیح کنترل‌شده",
        "available_qty": 1,
    }]

    vocabulary = build_previsit_voice_vocabulary(products, max_chars=800)

    assert len(vocabulary) <= 800
    assert "[" not in vocabulary
    assert "]" not in vocabulary
    assert "<" not in vocabulary
    assert ">" not in vocabulary
    assert "کالای ویژه آزمایشی" in vocabulary


def test_grouped_catalogs_keep_only_products_allowed_for_the_seller(settings, monkeypatch):
    products = [
        {"id": "4032", "unique_id": "11111111-1111-1111-1111-111111111111", "brand": "Brand A", "group_id": "7"},
        {"id": "4033", "unique_id": "22222222-2222-2222-2222-222222222222", "brand": "Brand A", "group_id": "8"},
    ]
    monkeypatch.setattr(
        "app.ngt_previsit_service._rows",
        lambda *_args: [
            {
                "CatalogId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "CatalogName": "Grouped product",
                "ProductMainGroupUniqueId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "CatalogOrder": 3,
                "ImageName": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jpg",
                "ProductUniqueId": "11111111-1111-1111-1111-111111111111",
                "ProductOrder": 2,
            },
            {
                "CatalogId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "CatalogName": "Grouped product",
                "ProductMainGroupUniqueId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "CatalogOrder": 3,
                "ImageName": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jpg",
                "ProductUniqueId": "99999999-9999-9999-9999-999999999999",
                "ProductOrder": 1,
            },
        ],
    )

    grouped = _grouped_catalogs(settings, products)

    assert grouped == [{
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "name": "Grouped product",
        "main_group_unique_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "row_index": 3,
        "image_url": "/seller-workspace/previsit/catalog-images/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jpg?size=thumb",
        "product_ids": ["4032"],
        "brands": ["Brand A"],
        "group_ids": ["7"],
    }]


def test_catalog_image_accepts_upstream_uppercase_jpg_extension(settings, monkeypatch):
    class FakeHeaders:
        @staticmethod
        def get_content_type():
            return "image/jpeg"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        @staticmethod
        def read():
            return b"image"

    captured = {}
    monkeypatch.setattr(
        "app.ngt_previsit_service.urlopen",
        lambda request, timeout: captured.update(url=request.full_url, timeout=timeout) or FakeResponse(),
    )
    settings = replace(settings, ngt_api_base_url="http://ngt.internal")

    content, content_type = catalog_image(
        settings,
        "91f5c672-85e1-4115-ab16-fa7fcb60bc64",
        "91f5c672-85e1-4115-ab16-fa7fcb60bc64.JPG",
        "thumb",
    )

    assert content == b"image"
    assert content_type == "image/jpeg"
    assert captured["timeout"] == 20
    assert "/100x100/91f5c672-85e1-4115-ab16-fa7fcb60bc64/91f5c672-85e1-4115-ab16-fa7fcb60bc64.JPG" in captured["url"]


def _context():
    return {
        "seller": {"personnel_id": 293, "full_name": "Seller"},
        "route": {"id": "11111111-1111-1111-1111-111111111111", "title": "Route"},
        "customer": {"id": 196},
        "order_types": [{"id": 2, "name": "Pre-sale"}],
        "payment_types": [{"id": "401", "name": "Cash", "buy_type_ref": 3, "check_credit": True, "check_debit": True}],
        "products": [{"id": "4032", "name": "Product", "indicative_price": 1_930_000, "stock_ref": "1"}],
        "warehouses": [
            {"id": "b66abfeb-134a-4c80-adfd-f687bbcf650d", "ref": 1, "name": "Stock 1"},
            {"id": "763834b8-a4e3-4ad0-8983-e1576f7511d9", "ref": 3, "name": "Stock 3"},
        ],
        "warehouse_selection": {"enabled": True, "default_ref": 1},
        "_bridge": {"sale_office_ref": 1, "dc_ref": 1, "subsystem_type_unique_id": "subsystem-id"},
    }


def test_ngt_device_warehouse_list_is_ordered_deduplicated_and_validated():
    result = _device_warehouse_ids({
        "ListOfStockPreSale": (
            "b66abfeb-134a-4c80-adfd-f687bbcf650d, invalid, "
            "763834b8-a4e3-4ad0-8983-e1576f7511d9, "
            "b66abfeb-134a-4c80-adfd-f687bbcf650d"
        ),
    })

    assert result == [
        "b66abfeb-134a-4c80-adfd-f687bbcf650d",
        "763834b8-a4e3-4ad0-8983-e1576f7511d9",
    ]


def test_catalog_sale_units_use_real_factors_and_only_authoritative_fallbacks():
    row = {
        "BaseUnitRef": 3,
        "UnitName": "عدد",
        "sdpmsCartonQty": 600,
        "UseBatchPackage": True,
        "SaleUnitsJson": json.dumps(
            [
                {"ref": 1, "name": "کارتن 1", "factor": 600, "is_default": True},
                {"ref": 4, "name": "بسته", "factor": 12, "is_default": False},
                {"ref": 3, "name": "عدد", "factor": 1, "is_default": False},
            ],
            ensure_ascii=False,
        ),
    }

    units = _catalog_sale_units(row)

    assert [unit["factor"] for unit in units] == [1, 12, 600]
    assert [unit["name"] for unit in units] == ["عدد", "بسته", "کارتن 1"]

    fallback = _catalog_sale_units(
        {
            "BaseUnitRef": 3,
            "UnitName": "عدد",
            "sdpmsCartonQty": 96,
            "UseBatchPackage": True,
            "SaleUnitsJson": "[]",
        }
    )
    assert [unit["name"] for unit in fallback] == ["عدد", "کارتن"]
    assert [unit["factor"] for unit in fallback] == [1, 96]


def test_ngt_preview_rejects_warehouse_outside_seller_device_settings(settings, monkeypatch):
    monkeypatch.setattr("app.ngt_previsit_service.previsit_context", lambda *_args, **_kwargs: _context())
    request = PrevisitPreviewRequest(
        route_id="11111111-1111-1111-1111-111111111111",
        customer_id="196",
        order_type_ref=2,
        payment_usance_ref="401",
        warehouse_ref=99,
        lines=[{"product_id": "4032", "quantity": 1}],
    )

    with pytest.raises(ValueError, match="انبار انتخاب‌شده"):
        preview_previsit(settings, "seller", request)


def test_ngt_preview_rejects_quantity_above_selected_warehouse_inventory(settings, monkeypatch):
    context = _context()
    context["products"][0].update({
        "available_qty": 200,
        "warehouse_inventory": {
            "1": {"available_qty": 1},
            "3": {"available_qty": 200},
        },
    })
    monkeypatch.setattr("app.ngt_previsit_service.previsit_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(
        "app.ngt_previsit_service._post_evc",
        lambda *_args, **_kwargs: pytest.fail("سفارش بیشتر از موجودی نباید به سرویس ارسال شود"),
    )
    request = PrevisitPreviewRequest(
        route_id="11111111-1111-1111-1111-111111111111",
        customer_id="196",
        order_type_ref=2,
        payment_usance_ref="401",
        warehouse_ref=1,
        lines=[{"product_id": "4032", "quantity": 63}],
    )

    with pytest.raises(ValueError, match="فقط 1 عدد"):
        preview_previsit(settings, "seller", request)


def test_route_warmup_primes_seller_context_without_returning_catalog(settings, monkeypatch):
    monkeypatch.setattr(
        "app.ngt_previsit_service.seller_route_customers",
        lambda *_args: {"customers": [{"id": 196}]},
    )
    monkeypatch.setattr(
        "app.ngt_previsit_service.previsit_context",
        lambda *_args, **_kwargs: {
            "catalog_count": 505,
            "warehouses": [{"ref": 1}, {"ref": 3}],
            "order_types": [{"id": 2}, {"id": 3}, {"id": 12}],
            "payment_types": [{"id": 384}],
            "products": [{"id": "1200"}],
        },
    )

    result = warm_previsit_route(settings, "A.kamran", "route-id")

    assert result == {
        "ready": True,
        "route_id": "route-id",
        "catalog_count": 505,
        "warehouse_count": 2,
        "order_type_count": 3,
        "payment_type_count": 1,
        "cache_seconds": 300,
        "source": "NGT seller context warmup",
    }
    assert "products" not in result


def test_previsit_catalog_is_shared_between_customers_of_same_seller(settings, monkeypatch):
    import app.ngt_previsit_service as service

    service._context_cache.clear()
    service._seller_context_cache.clear()
    service._seller_context_load_locks.clear()
    catalog_calls = 0

    def fake_assignment(_settings, _username, path_id, customer_id):
        return {
            "path_id": path_id,
            "route": {"route": {"title": "Route"}},
            "customer": {"id": str(customer_id), "name": f"Customer {customer_id}"},
        }

    def fake_context_rows(_settings, _personnel_id):
        return (
            {
                "ShowStockLevel": True,
                "OnlineRefreshStockLevel": True,
                "ApplyCurrentOrdersInInventory": False,
                "CustomerAdvancedCreditControl": True,
                "AllowCashWithoutAdvancedCreditControl": False,
                "SaleOfficeRef": 1,
                "DcRef": 1,
                "SubSystemTypeUniqueId": "subsystem-id",
            },
            [{"BackOfficeId": 2, "OrderTypeName": "Pre-sale"}],
            [{
                "BackOfficeId": 401,
                "PaymentTypeOrderName": "Cash",
                "BuyTypeRef": 3,
                "PaymentDeadLine": 0,
                "PaymentTime": 0,
                "IsCash": True,
                "CheckCredit": True,
                "CheckDebit": True,
            }],
        )

    def fake_rows(_settings, _sql):
        nonlocal catalog_calls
        catalog_calls += 1
        sleep(0.05)
        if "SELECT GoodsRef, OrderTypeRef, SalePrice" in _sql:
            return [{
                "GoodsRef": 4032,
                "OrderTypeRef": 2,
                "SalePrice": 1_930_000,
                "UserPrice": 2_100_000,
                "ManufacturerPrice": 1_800_000,
            }]
        return [{
            "GoodsRef": 4032,
            "ProductUniqueId": "product-id",
            "GoodsCode": "4032",
            "GoodsName": "Product",
            "BrandName": "Brand",
            "GoodsGroupRef": 7,
            "GoodsGroupName": "Leaf Group",
            "ParentGoodsGroupRef": 3,
            "ParentGoodsGroupName": "Parent Group",
        }]

    monkeypatch.setattr("app.ngt_previsit_service._validate_assignment", fake_assignment)
    monkeypatch.setattr(
        "app.ngt_previsit_service._seller_profile",
        lambda *_args: {"personnel_id": 293, "full_name": "Seller"},
    )
    monkeypatch.setattr("app.ngt_previsit_service._context_rows", fake_context_rows)
    monkeypatch.setattr("app.ngt_previsit_service._rows", fake_rows)
    monkeypatch.setattr("app.ngt_previsit_service.jalali_business_date", lambda: "1405/06/01")

    def load(customer_id):
        return previsit_context(
            settings,
            "seller",
            "11111111-1111-1111-1111-111111111111",
            customer_id,
            limit=1000,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.map(load, ("196", "2445"))

    # Catalogue, order-type price matrix and grouped-catalogue links are each
    # loaded once, then shared between customers of the same seller.
    assert catalog_calls == 3
    assert first["customer"]["id"] == "196"
    assert second["customer"]["id"] == "2445"
    assert first["products"] == second["products"]
    assert first["products"] is not second["products"]
    assert first["products"][0]["group_parent_id"] == "3"
    assert first["products"][0]["group_parent"] == "Parent Group"
    assert first["products"][0]["smallest_group_id"] == "7"
    assert first["products"][0]["smallest_group"] == "Leaf Group"


def test_ngt_preview_sends_zero_client_price_and_uses_official_result(settings, monkeypatch):
    captured = {}
    def fake_context(*args, **kwargs):
        captured["context_limit"] = kwargs.get("limit")
        return _context()

    monkeypatch.setattr("app.ngt_previsit_service.previsit_context", fake_context)
    monkeypatch.setattr(
        "app.ngt_previsit_service._candidate_promotion_rules",
        lambda *_args, **_kwargs: [{
            "product_id": "4032", "rule_id": 77, "rule_code": "R-1",
            "title": "Rule", "details": "10 percent", "condition_summary": "",
            "eligibility_status": "ineligible", "eligible": False,
            "eligibility_reasons": ["نوع سفارش منطبق نیست"],
            "applied": False,
        }],
    )

    def fake_post(_settings, payload, subsystem_id):
        captured["payload"] = payload
        captured["subsystem_id"] = subsystem_id
        return {
            "ErrorCode": 0,
            "Message": "ok",
            "Items": [{
                "GoodsRef": "4032", "TotalQty": 2, "CustPrice": 2_000_000,
                "Discount": 100_000, "Tax": 20_000, "Charge": 0,
                "AmountNut": 3_920_000, "RuleNo": "R-1",
            }],
            "OrderPrize": [{"GoodsRef": "99", "TotalQty": 1}],
        }

    monkeypatch.setattr("app.ngt_previsit_service._post_evc", fake_post)
    monkeypatch.setattr(
        "app.ngt_previsit_service._live_customer_credit_control",
        lambda *_args, **_kwargs: {"allowed": True, "message": "ok"},
    )
    request = PrevisitPreviewRequest(
        route_id="11111111-1111-1111-1111-111111111111",
        customer_id="196",
        order_type_ref=2,
        payment_usance_ref="401",
        lines=[{"product_id": "4032", "quantity": 2}],
    )

    result = preview_previsit(settings, "M.flsfi", request)

    sent = captured["payload"]
    assert sent["DealerRef"] == 293
    assert captured["context_limit"] == 1000
    assert sent["CustRef"] == "196"
    assert "UnitPrice" not in sent["PreSaleEvcDetails"][0]
    assert "PriceRef" not in sent["PreSaleEvcDetails"][0]
    assert sent["OrderDate"] == ""
    assert sent["PreSaleEvcDetails"][0]["OrderDate"] == date.today().strftime("%Y/%m/%d")
    assert UUID(sent["PreSaleEvcDetails"][0]["OrderId"])
    assert sent["PreSaleEvcDetails"][0]["OrderId"] != "00000000-0000-0000-0000-000000000000"
    assert "OrderPrizeList" not in sent
    assert "OrderRef" not in sent
    assert captured["subsystem_id"] == "subsystem-id"
    assert result["items"][0]["unit_price"] == 2_000_000
    assert result["totals"] == {
        "gross": 4_000_000.0,
        "discount": 100_000.0,
        "tax": 20_000.0,
        "charge": 0.0,
        "net": 3_920_000.0,
    }
    assert result["related_rules"][0]["applied"] is True
    assert result["related_rules"][0]["eligibility_status"] == "eligible"
    assert result["related_rules"][0]["eligible"] is True
    assert result["related_rules"][0]["eligibility_reasons"] == []
    assert result["gift_lines"] == [{
        "product_id": "99",
        "parent_product_id": "4032",
        "title": "کالای اشانتیون 99",
        "quantity": 1.0,
        "unit_price": 0.0,
        "gross_amount": 0.0,
        "discount_amount": 0.0,
        "discount_percent": 100.0,
        "net_amount": 0.0,
        "source": "NGT official prize",
    }]
    assert result["creates_order"] is False
    assert result["credit_control"]["allowed"] is True


def test_ngt_credit_control_combines_balances_for_payment_that_checks_both():
    result = _calculate_ngt_credit_control(
        {"InitCredit": 1, "RemainCredit": 700, "InitDebit": 1, "RemainDebit": 500},
        {"CheckCredit": True, "CheckDebit": True},
        order_total=1_000,
        pending_order_total=100,
        order_asn_limit=2,
        order_bed_limit=2,
    )

    assert result["allowed"] is True
    assert result["mode"] == "combined"
    assert result["available_amount"] == 1_200
    assert result["evaluated_total"] == 1_100


def test_ngt_credit_control_blocks_credit_only_payment_with_exact_deficit():
    result = _calculate_ngt_credit_control(
        {"InitCredit": 5_000, "RemainCredit": 800, "InitDebit": 9_000, "RemainDebit": 9_000},
        {"CheckCredit": True, "CheckDebit": False},
        order_total=1_000,
        order_asn_limit=2,
        order_bed_limit=2,
    )

    assert result["allowed"] is False
    assert result["blocking"] is True
    assert result["mode"] == "credit"
    assert result["deficit"] == 200


def test_ngt_credit_control_uses_debit_branch_and_respects_disabled_flags():
    debit = _calculate_ngt_credit_control(
        {"InitCredit": 1, "RemainCredit": 10, "InitDebit": 1, "RemainDebit": 600},
        {"CheckCredit": False, "CheckDebit": True},
        order_total=700,
        order_asn_limit=2,
        order_bed_limit=2,
    )
    unchecked = _calculate_ngt_credit_control(
        {"InitCredit": 1, "RemainCredit": 0, "InitDebit": 1, "RemainDebit": 0},
        {"CheckCredit": False, "CheckDebit": False},
        order_total=999_999,
        order_asn_limit=2,
        order_bed_limit=2,
    )

    assert debit["mode"] == "debit"
    assert debit["allowed"] is False
    assert unchecked["mode"] == "none"
    assert unchecked["allowed"] is True


def test_saved_order_is_repriced_and_credit_checked_before_completion(settings, monkeypatch):
    monkeypatch.setattr(
        "app.ngt_previsit_service.get_visit_draft",
        lambda *_args: {
            "visit_status": "active",
            "route_id": "11111111-1111-1111-1111-111111111111",
            "customer_id": "196",
            "payment_type": "Cash",
            "order_type": "Pre-sale",
            "lines": [{"product_id": "4032", "quantity": 2}],
        },
    )
    monkeypatch.setattr("app.ngt_previsit_service.previsit_context", lambda *_args, **_kwargs: _context())
    captured = {}

    def fake_preview(_settings, _username, payload):
        captured["payload"] = payload
        return {"ok": True, "totals": {"net": 10}, "credit_control": {"allowed": True}}

    monkeypatch.setattr("app.ngt_previsit_service.preview_previsit", fake_preview)

    result = validate_order_draft(settings, "seller", "visit-id")

    assert result["credit_control"]["allowed"] is True
    assert captured["payload"].payment_usance_ref == "401"
    assert captured["payload"].lines[0].quantity == 2


def test_saved_order_cannot_complete_when_live_credit_is_rejected(settings, monkeypatch):
    monkeypatch.setattr(
        "app.ngt_previsit_service.get_visit_draft",
        lambda *_args: {
            "visit_status": "active",
            "route_id": "11111111-1111-1111-1111-111111111111",
            "customer_id": "196",
            "payment_type": "Cash",
            "order_type": "Pre-sale",
            "lines": [{"product_id": "4032", "quantity": 2}],
        },
    )
    monkeypatch.setattr("app.ngt_previsit_service.previsit_context", lambda *_args, **_kwargs: _context())
    monkeypatch.setattr(
        "app.ngt_previsit_service.preview_previsit",
        lambda *_args: {
            "ok": False,
            "message": "",
            "credit_control": {"allowed": False, "message": "credit deficit"},
        },
    )

    with pytest.raises(ValueError, match="credit deficit"):
        validate_order_draft(settings, "seller", "visit-id")


def test_promotion_conditions_explain_customer_and_new_order_mismatches():
    labels = {
        "CustCtgrRef": "گروه مشتری",
        "OrderType": "نوع سفارش",
        "OrderNo": "سفارش مرجع",
    }
    status, reasons = _evaluate_promotion_conditions(
        [
            {"CustCtgrRef": 6},
            {"OrderType": 13},
            {"OrderNo": 54237},
        ],
        {"CustCtgrRef": {"2"}, "OrderType": 2, "OrderNo": None},
        labels,
    )

    assert status == "ineligible"
    assert "گروه مشتری موردنیاز 6؛ مقدار فعلی 2" in reasons
    assert "نوع سفارش موردنیاز 13؛ مقدار فعلی 2" in reasons
    assert "مخصوص سفارش 54237؛ سفارش فعلی جدید است" in reasons


def test_promotion_conditions_accept_alternative_customer_mapping():
    status, reasons = _evaluate_promotion_conditions(
        [{"MainCustTypeRef": 2}, {"MainCustTypeRef": 4}, {"OrderType": 2}],
        {"MainCustTypeRef": {"4", "9"}, "OrderType": 2},
        {"MainCustTypeRef": "نوع اصلی مشتری", "OrderType": "نوع سفارش"},
    )

    assert status == "eligible"
    assert reasons == []


def test_promotion_condition_rows_are_alternative_ngt_paths():
    status, reasons = _evaluate_promotion_conditions(
        [{"CustCtgrRef": 4}, {"OrderType": 13}],
        {"CustCtgrRef": {"4"}, "OrderType": 2},
        {"CustCtgrRef": "گروه مشتری", "OrderType": "نوع سفارش"},
    )

    assert status == "eligible"
    assert reasons == []


def test_ngt_tax_rule_add_amount_is_reported_as_tax_and_charges():
    result = _normalise_evc(
        {
            "items": [{
                "goodsRef": 4040,
                "unitQty": 1,
                "custPrice": 4_345_455,
                "discount": 1_086_363,
                "tax": 0,
                "charge": 0,
                "addAmount": 325_909,
                "evcItemAdd1": 325_909,
                "amountNut": 3_585_001,
            }],
        },
        [{"product_id": "4040", "quantity": 1}],
    )

    assert result["items"][0]["tax_amount"] == 325_909
    assert result["items"][0]["gross_amount"] == 4_345_455
    assert result["items"][0]["discount_percent"] == 25
    assert result["items"][0]["tax_and_charge_amount"] == 325_909
    assert result["items"][0]["discount_breakdown"]["unclassified"] == {
        "amount": 1_086_363.0,
        "percent": 25.0,
    }
    assert result["totals"]["tax"] == 325_909
    assert result["totals"]["charge"] == 0
    assert result["totals"]["net"] == 3_585_001


def test_ngt_discount_accounts_are_reported_separately_with_effective_percentages():
    result = _normalise_evc(
        {
            "items": [{
                "goodsRef": 4040,
                "unitQty": 2,
                "custPrice": 500_000,
                "discount": 360_000,
                "evcItemDis1": 50_000,
                "evcItemDis2": 100_000,
                "evcItemDis3": 200_000,
                "evcItemOtherDiscount": 10_000,
                "amountNut": 640_000,
            }],
        },
        [{"product_id": "4040", "quantity": 2}],
    )

    breakdown = result["items"][0]["discount_breakdown"]
    assert breakdown["cash"] == {"amount": 50_000.0, "percent": 5.0}
    assert breakdown["volume"] == {"amount": 100_000.0, "percent": 10.0}
    assert breakdown["goods"] == {"amount": 200_000.0, "percent": 20.0}
    assert breakdown["other"] == {"amount": 10_000.0, "percent": 1.0}
    assert breakdown["unclassified"] == {"amount": 0.0, "percent": 0.0}


def test_previsit_ui_calls_catalog_and_official_ngt_preview():
    source = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/assistant.css", encoding="utf-8").read()

    assert "/seller-workspace/previsit/context" in source
    assert "/seller-workspace/previsit/preview" in source
    assert "UnitPrice" not in source
    assert "previsitPreviewResult" in source
    assert "startButton.classList.add('is-loading')" in source
    assert "startButton.textContent = 'در حال دریافت کالا، موجودی و قیمت‌ها…'" in source
    assert "startButton.classList.remove('is-loading')" in source
    assert "#startPrevisit.is-loading::before" in styles
    assert 'data-field="discount_percent"' in source
    assert 'data-field="cash_discount_percent"' in source
    assert 'data-field="volume_discount_percent"' in source
    assert 'data-field="goods_discount_percent"' in source
    assert "discount_breakdown" in source
    assert "previsit-invoice-head" in source
    assert "previsit-invoice-scroll" in source
    assert "جزئیات قوانین مرتبط" not in source
    invoice_header = source[source.index('class="previsit-invoice-head"'):source.index('class="previsit-lines"')]
    assert invoice_header.index("کالایی") < invoice_header.index("حجمی") < invoice_header.index("نقدی")
    assert "--invoice-areas:" in styles
    assert "width:max(100%,1120px)" in styles
    assert "grid-template-columns:var(--invoice-cols)!important" in styles
    assert "gap:0!important" in styles
    assert ".is-goods{grid-area:goods}" in styles
    assert ".is-volume{grid-area:volume}" in styles
    assert ".is-cash{grid-area:cash}" in styles
    assert 'data-field="gross_amount"' in source
    assert 'data-field="tax_and_charge_amount"' in source
    assert 'data-field="net_amount"' in source
    assert "previsit-line-formula" in source
    assert ".previsit-panel{min-height:0;overflow:hidden}" in styles
    assert "height:100%;min-height:0;margin:0 auto;overflow-x:hidden;overflow-y:auto" in styles
    assert "previsitCatalogGrid" in source
    assert "previsitBrandFilter" in source
    assert "previsitGroupFilter" in source
    assert "previsitQuickGroupFilter" in source
    assert "previsitQuickBrandFilter" in source
    assert "renderPrevisitQuickFilterOptions" in source
    assert "renderPrevisitListFilters" in source
    assert "currentPrevisitListProducts" in source
    assert "previsitListState.brand" in source
    assert "previsitListState.group" in source
    assert "همه گروه‌های این برند" in source
    assert "(!previsitListState.brand || item.brand === previsitListState.brand) && item.group" in source
    assert 'data-previsit-list-unit-increase' in source
    assert 'data-previsit-list-unit-decrease' in source
    assert 'data-previsit-list-unit-quantity' in source
    assert 'parsePrevisitUnitQuantity' in source
    assert "replace(/[۰-۹]/g" in source
    assert "replace(/[٠-٩]/g" in source
    assert "addEventListener('input', (event) =>" in source
    assert 'data-previsit-list-unit-summary' in source
    assert 'data-previsit-catalog-unit-increase' in source
    assert 'data-previsit-catalog-unit-decrease' in source
    assert 'data-previsit-catalog-unit-quantity' in source
    assert 'data-previsit-catalog-unit-summary' in source
    assert 'updatePrevisitCatalogUnitFeedback' in source
    assert 'previsitListStockToggle' in source
    assert '!previsitListState.inStock || Number(product.available_qty) > 0' in source
    assert 'class="previsit-list-unit-rows"' in source
    assert 'previsitProductUnitQuantities' in source
    assert 'changePrevisitListUnitQuantity' in source
    assert 'quantities[previsitUnitKey(unit)] * unit.factor' in source
    assert ".join(' + ')" in source
    assert 'previsitCatalogUnitRows' in source
    assert 'previsitCatalogTextCompare' in source
    assert "previsitCatalogTextCompare(a.brand || a.manufacturer, b.brand || b.manufacturer)" in source
    assert "a.group_parent || a.group" in source
    assert "a.smallest_group || a.group" in source
    assert source.index("const brandOrder") < source.index("const parentGroupOrder")
    assert source.index("const parentGroupOrder") < source.index("const smallestGroupOrder")
    assert "previsitCatalogTextCompare(a.code || a.id, b.code || b.id)" in source
    assert "if (!leftText && rightText) return 1" in source
    assert "withinGroup = 'code'" in source
    assert "sort: 'code'" in source
    assert '<option value="code">' in source
    assert "previsitProductHierarchyCompare(a, b, previsitCatalogState.sort)" in source
    assert "previsitProductHierarchyCompare(a, b)" in source
    assert "previsitProductUnitSelections" in source
    assert "Number(unitDelta || 0) * factor" in source
    assert "Number(unitQuantity || 0) * factor" in source
    assert "تعداد در کارتن" in source
    assert "قیمت پایه با ${taxPercent.toLocaleString" in source
    list_styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()
    assert ".previsit-product-list-view" in list_styles
    assert "grid-template-columns:repeat(auto-fit,minmax(82px,1fr))" in list_styles
    assert ".previsit-order-common{position:sticky" in list_styles
    assert "top:var(--previsit-order-sticky-top" in list_styles
    assert ".previsit-product-unit-grid" in list_styles
    assert "function renderPrevisitCatalogFilterOptions()" in source
    assert "ابتدا برند را انتخاب کنید" in source
    assert ".filter((item) => !previsitQuickFilterState.brand || item.brand === previsitQuickFilterState.brand)" in source
    assert ".filter((item) => !previsitCatalogState.brand || item.brand === previsitCatalogState.brand)" in source
    assert "previsitWarehouse" in source
    assert "warehouse_ref: Number($('#previsitWarehouse').value)" in source
    active_selector = source[source.rindex("function fillPrevisitContextSelectors()") :]
    assert "const warehouse = $('#previsitWarehouse')" in active_selector
    assert "warehouse.innerHTML = warehouses.length" in active_selector
    assert "warehouse.value = defaultWarehouseRef" in active_selector
    assert "warehouse.disabled = !warehouses.length" in active_selector
    assert "renderPrevisitProductOptions(); renderPrevisitProductList(); renderPrevisitGroupedCatalogFilters(); renderPrevisitGroupedCatalogs(); updatePrevisitPriceContextNote();" in source
    assert "warmPrevisitRouteContext(routeId)" in source
    assert "/seller-workspace/previsit/warmup" in source
    assert "orderCommon.append(orderConditions, assistant)" in source
    assert "previsit-mobile-dock" in source
    assert "previsitDockQuantity" in source
    assert "previsitDockTotalLabel" in source
    assert "ناخالص فعلی" in source
    assert "Number(row.dataset.officialPrice || 0) > 0" in source
    assert "Number(row.dataset.indicativePrice || 0)" in source
    assert "renderPrevisitGiftLines" in source
    assert "previsit-gift-line" in source
    assert "۱۰۰٪ تخفیف" in source
    assert ".previsit-mobile-dock{position:fixed!important" in styles
    assert ".previsit-invoice-scroll .previsit-gift-line" in styles
    assert "previsit-invoice-navigation" not in source
    assert "positionPrevisitInvoice" in source
    assert "settlePrevisitInvoiceEdge" in source
    assert "scroller.scrollLeft = 0" in source
    assert "overflow-x:scroll!important" in styles
    assert "touch-action:pan-x pan-y" in styles
    assert "--previsit-invoice-edge-gutter" in styles
    assert ".previsit-line-rules,.previsit-line-formula,.previsit-line-unclassified{display:none!important}" in styles
    assert "previsit-remove-line" in source
    assert "<svg viewBox=\"0 0 24 24\"" in source
    assert "data-previsit-add-product" in source
    assert "data-previsit-catalog-unit-decrease" in source
    assert "changePrevisitProductQuantity" in source
    assert "previsit-product-unit-grid" in source
    assert "previsitInvoiceTotals" in source
    assert 'data-total="quantity"' in source
    assert 'data-total="gross"' in source
    assert 'data-total="goods"' in source
    assert 'data-total="volume"' in source
    assert 'data-total="cash"' in source
    assert 'data-total="tax"' in source
    assert 'data-total="net"' in source
    assert ".previsit-invoice-totals" in styles
    assert "grid-template-areas:var(--invoice-areas)!important" in styles
    assert "previsitTableMode" in source
    assert "previsitTableOverlay" in source
    assert "openPrevisitTableMode" in source
    assert "renderPrevisitTableProduct" in source
    assert "changePrevisitTableQuantity" in source
    assert "previsitTableSwipeStart" in source
    assert "beginPrevisitTableSwipe" in source
    assert "finishPrevisitTableSwipe" in source
    assert "tablePrice(product.manufacturer_price)" in source
    assert "tablePrice(product.consumer_price)" in source
    assert "requestFullscreen" in source
    assert "previsit-table-customer" in styles
    assert "transform:rotate(180deg)" in styles
    assert "previsit-table-controls" in styles
    assert "previsit-table-page-next" in styles
    assert "touch-action:pan-y" in styles
    assert "grid-template-areas:\"product product\" \"quantity quantity\"" in styles
    assert ".previsit-invoice-scroll .previsit-line-discount-columns .is-goods{grid-area:goods" in styles
    assert "Keep the shopping basket invoice-shaped on phones" in styles
    assert "product.manufacturer_price" in source
    assert "product.consumer_price" in source
    assert "previsit-line-producer" in source
    assert "previsit-line-consumer" in source
    assert "grid-area:producer" in styles
    assert "grid-area:consumer" in styles
    assert "previsit-credit-warning" in source
    assert "credit.allowed === false" in source
    assert "previsit-restrictions" not in source
    assert "credit_control?.allowed" in source
    assert "validate_order_draft" in open("app/routes/seller_workspace.py", encoding="utf-8").read()
    assert ".previsit-credit-warning" in styles


def test_ngt_catalog_reads_all_contract_price_types():
    source = open("app/ngt_previsit_service.py", encoding="utf-8").read()

    assert "WITH ranked_price AS" in source
    assert "ROW_NUMBER() OVER (" in source
    assert "price.PriceRank = 1" in source
    assert source.count("FROM NGT.ContractPrices AS history") == 2
    assert "def _product_order_type_prices(" in source
    assert '"indicative_prices"' in source
    assert "history.SalePrice" in source
    assert "history.UserPrice" in source
    assert "source_price.ManufacturerPrice" in source
    assert "source_price.UniqueId = history.Id" in source
    assert '"consumer_price"' in source
    assert '"manufacturer_price"' in source
    assert '"catalog_tax_percent"' in source
    assert '"catalog_tax_inclusive_price"' in source
    assert "tax_main_type.LookUpId = 501" in source
    assert "TRY_CONVERT(decimal(9, 4), tax_subtype.SubName)" in source
    assert '"catalog_tax_main_type_ref"' in source
    assert '"catalog_tax_sub_type_ref"' in source
    assert "discount.Code = 5014" not in source[source.index("def previsit_context"):source.index("def _promotion_customer_context")]


def test_catalog_tax_display_does_not_replace_official_invoice_price():
    source = open("app/static/assistant.js", encoding="utf-8").read()

    assert "product.catalog_tax_inclusive_price" in source
    assert "is-tax-inclusive" in source
    assert "displayedBasePrice" in source
    assert "row.dataset.indicativePrice = String(line.unit_price || product.indicative_price || 0)" in source
    assert "product.catalog_tax_inclusive_price || product.indicative_price" not in source


def test_ngt_token_sends_required_three_part_scope(settings, monkeypatch):
    configured = replace(
        settings,
        ngt_api_base_url="http://ngt.test",
        ngt_api_username="seller",
        ngt_api_password="secret",
        ngt_api_scope="owner,data-owner,center",
    )
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"access_token":"issued-token"}'

    def fake_urlopen(request, timeout):
        captured["body"] = parse_qs(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.ngt_previsit_service.urlopen", fake_urlopen)

    assert _token(configured) == "issued-token"
    assert captured["body"]["scope"] == ["owner,data-owner,center"]
    assert captured["timeout"] == 20


def test_ngt_evc_sends_required_owner_headers(settings, monkeypatch):
    owner_keys = (
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    )
    configured = replace(
        settings,
        ngt_api_base_url="http://ngt.test",
        ngt_api_scope=",".join(owner_keys),
    )
    captured = {}

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"items": []}'

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["query"] = parse_qs(request.full_url.split("?", 1)[1])
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.ngt_previsit_service._token", lambda _settings: "issued-token")
    monkeypatch.setattr("app.ngt_previsit_service.urlopen", fake_urlopen)

    assert _post_evc(configured, {}, "subsystem-id") == {"items": []}
    folded = {key.casefold(): value for key, value in captured["headers"].items()}
    assert folded["ownerkey"] == owner_keys[0]
    assert folded["dataownerkey"] == owner_keys[1]
    assert folded["dataownercenterkey"] == owner_keys[2]
    assert folded["authorization"] == "Bearer issued-token"
    assert captured["query"]["calcDiscount"] == ["true"]
    assert captured["query"]["calcSaleRestriction"] == ["false"]
    assert captured["query"]["calcPaymentType"] == ["false"]
    assert captured["timeout"] == 30
