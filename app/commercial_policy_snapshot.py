from __future__ import annotations

from typing import Any

from app.seller_workspace_service import _query_rows, _seller_profile


def seller_commercial_policy_snapshot(settings: Any, username: str) -> dict[str, Any]:
    """Read seller-scoped active price contracts and promotion definitions."""
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    products_sql = f"""
SELECT DISTINCT goods.ID AS ProductId, goods.GoodsCode, goods.GoodsName,
       brand.ID AS BrandRef, brand.BrandName
FROM NGT.Personnels AS personnel
LEFT JOIN NGT.VisitTemplates AS visit_template
  ON visit_template.Id = personnel.VisitTemplateUniqueId
 AND ISNULL(visit_template.IsRemoved, 0) = 0
INNER JOIN NGT.ProductTemplates AS product_template
  ON product_template.Id = COALESCE(personnel.ProductTemplateUniqueId, visit_template.ProductTemplateUniqueId)
INNER JOIN NGT.ProductTemplateDetails AS detail
  ON detail.ProductTemplateUniqueId = product_template.Id
INNER JOIN GNR.tblGoods AS goods ON goods.UniqueId = detail.ProductUniqueId
LEFT JOIN GNR.tblBrand AS brand ON brand.ID = goods.BrandRef
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(personnel.PersonnelIsActive, 1) = 1
  AND ISNULL(product_template.IsRemoved, 0) = 0
  AND ISNULL(detail.IsRemoved, 0) = 0
  AND ISNULL(goods.ShowInSale, 1) = 1
""".strip()
    product_rows = _query_rows(settings, products_sql)
    products = {
        str(int(row["ProductId"])): {
            "product_id": str(int(row["ProductId"])),
            "product_code": str(row.get("GoodsCode") or "").strip(),
            "product_name": str(row.get("GoodsName") or "").strip(),
            "brand_ref": int(row["BrandRef"]) if row.get("BrandRef") is not None else None,
            "brand_name": str(row.get("BrandName") or "").strip(),
        }
        for row in product_rows
    }
    if not products:
        return {
            "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
            "products": {}, "prices": {}, "promotions": {},
            "source": "NGT.ProductTemplateDetails",
        }

    order_types_sql = f"""
SELECT DISTINCT order_type.BackOfficeId, order_type.OrderTypeName
FROM NGT.Users AS app_user
INNER JOIN NGT.DeviceUsers AS device_user
  ON device_user.UserUniqueId = app_user.Id AND ISNULL(device_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceOrderTypes AS allowed
  ON allowed.DeviceSettingUniqueId = device_user.DeviceSettingUniqueId
 AND ISNULL(allowed.IsRemoved, 0) = 0
INNER JOIN NGT.OrderTypes AS order_type
  ON order_type.Id = allowed.OrderTypeUniqueId AND ISNULL(order_type.IsRemoved, 0) = 0
WHERE app_user.BackOfficePersonnelId = {personnel_id}
  AND ISNULL(app_user.IsRemoved, 0) = 0
ORDER BY order_type.BackOfficeId
""".strip()
    order_rows = _query_rows(settings, order_types_sql)
    order_types = {
        str(int(row["BackOfficeId"])): str(row.get("OrderTypeName") or "").strip()
        for row in order_rows if row.get("BackOfficeId") is not None
    }
    product_ids_sql = ",".join(products)
    order_ids_sql = ",".join(order_types) or "0"

    prices_sql = f"""
WITH ranked_price AS (
  SELECT TRY_CONVERT(int, history.GoodsRef) AS ProductId,
         TRY_CONVERT(int, history.OrderTypeRef) AS OrderTypeRef,
         history.SalePrice, history.UserPrice, history.StartDate, history.EndDate,
         ROW_NUMBER() OVER (
           PARTITION BY TRY_CONVERT(int, history.GoodsRef), TRY_CONVERT(int, history.OrderTypeRef)
           ORDER BY history.StartDate DESC, history.LastUpdate DESC
         ) AS PriceRank
  FROM NGT.ContractPrices AS history
  WHERE TRY_CONVERT(int, history.GoodsRef) IN ({product_ids_sql})
    AND TRY_CONVERT(int, history.OrderTypeRef) IN ({order_ids_sql})
    AND ISNULL(history.IsRemoved, 0) = 0
    AND history.StartDate <= FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR')
    AND (NULLIF(history.EndDate, '') IS NULL OR history.EndDate >= FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR'))
    AND (history.CustRef IS NULL OR history.CustRef = '')
    AND (history.CustCtgrRef IS NULL OR history.CustCtgrRef = '')
    AND (history.CustActRef IS NULL OR history.CustActRef = '')
    AND (history.CustLevelRef IS NULL OR history.CustLevelRef = '')
    AND (history.MainCustTypeRef IS NULL OR history.MainCustTypeRef = 0)
    AND (history.SubCustTypeRef IS NULL OR history.SubCustTypeRef = 0)
    AND (history.StateRef IS NULL OR history.StateRef = '')
    AND (history.CountyRef IS NULL OR history.CountyRef = '')
    AND (history.AreaRef IS NULL OR history.AreaRef = '')
    AND (history.BuyTypeRef IS NULL OR history.BuyTypeRef = '')
    AND (history.UsanceDay IS NULL OR history.UsanceDay = 0)
    AND (history.DealerCtgrRef IS NULL OR history.DealerCtgrRef = '')
    AND (history.DCRef IS NULL OR history.DCRef = '')
    AND (history.SaleOfficeRef IS NULL OR history.SaleOfficeRef = 0)
)
SELECT ProductId, OrderTypeRef, SalePrice, UserPrice, StartDate, EndDate
FROM ranked_price
WHERE PriceRank = 1
ORDER BY ProductId, OrderTypeRef
""".strip()
    prices: dict[str, dict[str, Any]] = {}
    for row in _query_rows(settings, prices_sql):
        product_id = str(int(row["ProductId"]))
        order_ref = str(int(row["OrderTypeRef"]))
        product = products[product_id]
        key = f"{product_id}:{order_ref}"
        prices[key] = {
            **product,
            "order_type_ref": int(order_ref),
            "order_type_name": order_types.get(order_ref, order_ref),
            "sale_price": float(row.get("SalePrice") or 0),
            "consumer_price": float(row.get("UserPrice") or 0),
            "start_date": str(row.get("StartDate") or ""),
            "end_date": str(row.get("EndDate") or ""),
        }
    promotions_sql = f"""
SELECT DISTINCT product.ID AS ProductId, discount.ID AS DiscountId,
       discount.Code, discount.DisGroup, discount.Priority, discount.PrizeType,
       discount.DisType, discount.DisAccRef,
       discount.StartDate, discount.EndDate, discount.MinQty, discount.MaxQty,
       discount.MinAmount, discount.MaxAmount, discount.PrizeQty, discount.PrizeRef,
       discount.PrizeStep, discount.PrizeUnit, discount.DisPerc, discount.DisPrice,
       discount.Comment, discount.IsSelfPrize, prize.GoodsName AS PrizeName
FROM GNR.tblGoods AS product
INNER JOIN SLE.tblDiscount AS discount ON 1 = 1
LEFT JOIN SLE.tblDiscountGoods AS discount_goods
  ON discount_goods.DiscountRef = discount.ID
 AND discount_goods.GoodsRef = product.ID
LEFT JOIN GNR.tblGoods AS prize ON prize.ID = discount.PrizeRef
WHERE product.ID IN ({product_ids_sql})
  AND ISNULL(discount.IsActive, 0) = 1
  AND discount.StartDate <= FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR')
  AND (NULLIF(discount.EndDate, '') IS NULL OR discount.EndDate >= FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR'))
  AND (
    discount_goods.ID IS NOT NULL
    OR discount.GoodsRefOld = product.ID
    OR discount.GoodsGroupRef = product.GoodsGroupRef
    OR discount.ManufacturerRef = product.ManufacturerRef
    OR discount.BrandRef = product.BrandRef
    OR EXISTS (
      SELECT 1 FROM GNR.tblGoodsMainSubType AS goods_type
      WHERE goods_type.GoodsRef = product.ID
        AND goods_type.MainTypeRef = discount.MainTypeRef
        AND (discount.SubTypeRef IS NULL OR goods_type.SubTypeRef = discount.SubTypeRef)
    )
  )
ORDER BY discount.ID, product.ID
""".strip()
    promotion_rows = _query_rows(settings, promotions_sql)
    rule_ids = sorted({int(row["DiscountId"]) for row in promotion_rows})
    conditions_by_rule: dict[int, list[dict[str, Any]]] = {}
    if rule_ids:
        condition_sql = f"""
SELECT DiscountRef, DCRef, CustCtgrRef, CustActRef, CustLevelRef,
       PayType, PaymentUsanceRef, OrderType, SaleOfficeRef, CustGroupRef,
       CustRef, OrderNo, StateRef, CountyRef, AreaRef, SaleZoneRef,
       MainCustTypeRef, SubCustTypeRef, OrderRef
FROM SLE.tblDiscountCondition
WHERE DiscountRef IN ({','.join(str(rule_id) for rule_id in rule_ids)})
ORDER BY DiscountRef
""".strip()
        for row in _query_rows(settings, condition_sql):
            rule_id = int(row["DiscountRef"])
            condition = {
                str(key): row.get(key)
                for key in (
                    "DCRef", "CustCtgrRef", "CustActRef", "CustLevelRef", "PayType",
                    "PaymentUsanceRef", "OrderType", "SaleOfficeRef", "CustGroupRef",
                    "CustRef", "OrderNo", "StateRef", "CountyRef", "AreaRef",
                    "SaleZoneRef", "MainCustTypeRef", "SubCustTypeRef", "OrderRef",
                )
                if row.get(key) not in (None, "", 0, False)
            }
            conditions_by_rule.setdefault(rule_id, []).append(condition)

    promotions: dict[str, dict[str, Any]] = {}
    for row in promotion_rows:
        rule_id = int(row["DiscountId"])
        product_id = str(int(row["ProductId"]))
        product = products[product_id]
        key = str(rule_id)
        item = promotions.get(key)
        if item is None:
            prize_qty = float(row.get("PrizeQty") or 0)
            kind = "prize" if prize_qty or int(row.get("PrizeType") or 0) == 1 else "discount"
            item = {
                "rule_id": rule_id,
                "rule_code": int(row.get("Code") or 0),
                "kind": kind,
                "title": str(row.get("Comment") or "").strip() or f"قانون {row.get('Code')}",
                "priority": int(row.get("Priority") or 0),
                "discount_group": int(row.get("DisGroup") or 0),
                "discount_type": int(row.get("DisType") or 0),
                "discount_account_ref": int(row.get("DisAccRef") or 0),
                "discount_percent": float(row.get("DisPerc") or 0),
                "discount_amount": float(row.get("DisPrice") or 0),
                "min_qty": float(row.get("MinQty") or 0),
                "max_qty": float(row.get("MaxQty") or 0),
                "min_amount": float(row.get("MinAmount") or 0),
                "max_amount": float(row.get("MaxAmount") or 0),
                "prize_quantity": prize_qty,
                "prize_product_id": str(row.get("PrizeRef") or ""),
                "prize_product_name": str(row.get("PrizeName") or "").strip(),
                "prize_step": float(row.get("PrizeStep") or 0),
                "prize_unit": float(row.get("PrizeUnit") or 0),
                "is_self_prize": bool(row.get("IsSelfPrize")),
                "start_date": str(row.get("StartDate") or ""),
                "end_date": str(row.get("EndDate") or ""),
                "products": [], "brands": [],
                "conditions": conditions_by_rule.get(rule_id, []),
            }
            promotions[key] = item
        product_ref = {
            "product_id": product_id,
            "product_code": product["product_code"],
            "product_name": product["product_name"],
            "brand_ref": product["brand_ref"],
            "brand_name": product["brand_name"],
        }
        if product_ref not in item["products"]:
            item["products"].append(product_ref)
        brand_name = product["brand_name"]
        if brand_name and brand_name not in item["brands"]:
            item["brands"].append(brand_name)

    for item in promotions.values():
        item["products"] = sorted(item["products"], key=lambda product: product["product_id"])
        item["brands"] = sorted(item["brands"])
        item["conditions"] = sorted(
            item["conditions"], key=lambda condition: str(sorted(condition.items()))
        )

    return {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "products": products,
        "prices": prices,
        "promotions": promotions,
        "sources": {
            "seller_scope": "NGT.ProductTemplateDetails",
            "prices": "NGT.ContractPrices (active generic base contracts)",
            "promotions": "SLE.tblDiscount + SLE.tblDiscountGoods + SLE.tblDiscountCondition",
            "official_final_price": "NGT EVC presale",
        },
        "read_only": True,
    }
