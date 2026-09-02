"""Extract Varanegar pricing, discount, and prize evidence safely.

This sixth information-base slice distinguishes simple price history, conditional
contract prices, discount rules, rule conditions, eligible products, prizes,
applied sale effects, and NGT projections.  It is read-only and persists only
schema, rule metadata, reference labels, and aggregate evidence; raw customer,
personnel, SQL-condition, or credential values are intentionally excluded.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _decode_fields,
    _json_default,
    _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "SLE.tblPrice", "role": "simple_product_price_history"},
    {"object": "SLE.tblCPrice", "role": "conditional_contract_price"},
    {"object": "SLE.tblDiscount", "role": "discount_and_prize_rule_header"},
    {"object": "SLE.tblDiscountCondition", "role": "customer_channel_rule_conditions"},
    {"object": "SLE.tblDiscountGoods", "role": "eligible_product_bridge"},
    {"object": "SLE.tblDiscountPrizeList", "role": "selectable_prize_product_bridge"},
    {"object": "SLE.tblDiscountStatus", "role": "derived_rule_status_labels"},
    {"object": "GNR.tblDiscountType", "role": "rule_purpose_type"},
    {"object": "SLE.tblDiscount_DeactivationLog", "role": "rule_activation_audit"},
    {"object": "SLE.tblPreventDiscountEvent", "role": "rule_prevention_event_bridge"},
    {"object": "SLE.tblDisSale", "role": "applied_sale_discount_or_addition"},
    {"object": "SLE.tblOrderPrize", "role": "order_prize_result"},
    {"object": "SLE.tblDisSalePrizePackage", "role": "applied_sale_prize_package"},
    {"object": "SLE.tblSaleVocherOrderPrize", "role": "voucher_snapshot_order_prize"},
    {"object": "SLE.tblSaleVocherDisSalePrizePackage", "role": "voucher_snapshot_prize_package"},
    {"object": "NGT.CustomerCallOrderLinePromotions", "role": "ngt_line_promotion_result"},
    {"object": "NGT.CustomerCallOrderPrizes", "role": "ngt_order_prize_result"},
    {"object": "NGT.CustomerCallSellPrizes", "role": "ngt_realized_sale_prize"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT fk.name AS constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
               OBJECT_NAME(fk.parent_object_id) AS parent_table,
               pc.name AS parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
               rc.name AS referenced_column,
               fk.delete_referential_action_desc AS on_delete,
               fk.update_referential_action_desc AS on_update,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys AS fk
        JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns AS pc
          ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({object_ids})
           OR fk.referenced_object_id IN ({object_ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,
                 fk.name,fkc.constraint_column_id
        """,
    )


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT DISTINCT
               OBJECT_SCHEMA_NAME(d.referencing_id) AS consumer_schema,
               OBJECT_NAME(d.referencing_id) AS consumer_name,
               o.type_desc AS consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) AS source_schema,
               OBJECT_NAME(d.referenced_id) AS source_table,
               d.is_schema_bound_reference,
               o.modify_date AS consumer_modify_date
        FROM sys.sql_expression_dependencies AS d
        JOIN sys.objects AS o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({object_ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
        """,
    )


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        WITH candidates AS (
            SELECT c.object_id,c.column_id,s.name AS schema_name,t.name AS table_name,
                   c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type
            FROM sys.columns AS c
            JOIN sys.tables AS t ON t.object_id=c.object_id
            JOIN sys.schemas AS s ON s.schema_id=t.schema_id
            WHERE LOWER(c.name) LIKE '%priceref%'
               OR LOWER(c.name) LIKE '%priceid%'
               OR LOWER(c.name) LIKE '%priceuniqueid%'
               OR LOWER(c.name) LIKE '%discountref%'
               OR LOWER(c.name) LIKE '%discountid%'
               OR LOWER(c.name) LIKE '%discountuniqueid%'
               OR LOWER(c.name) LIKE '%disref%'
               OR LOWER(c.name) LIKE '%promotion%'
               OR LOWER(c.name) LIKE '%prizeref%'
        )
        SELECT cc.schema_name,cc.table_name,cc.column_name,cc.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END AS has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) AS formal_target_table,
               rc.name AS formal_target_column
        FROM candidates AS cc
        LEFT JOIN sys.foreign_key_columns AS fkc
          ON fkc.parent_object_id=cc.object_id AND fkc.parent_column_id=cc.column_id
        LEFT JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE cc.object_id NOT IN ({object_ids})
        ORDER BY has_formal_fk,cc.schema_name,cc.table_name,cc.column_name
        """,
    )


def _reference_masters(cursor: Any) -> dict[str, Any]:
    discount_types = _rows(
        cursor,
        "SELECT ID,tblDiscountTypeTitle FROM GNR.tblDiscountType ORDER BY ID",
    )
    statuses = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,CONVERT(varbinary(max),StatusTitle) AS StatusTitle
            FROM SLE.tblDiscountStatus ORDER BY Id
            """,
        ),
        ("StatusTitle",),
    )
    prize_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,CONVERT(varbinary(max),Title) AS Title
            FROM SLE.vwDiscountPrizeType ORDER BY Id
            """,
        ),
        ("Title",),
    )
    step_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Code,CONVERT(varbinary(max),Title) AS Title
            FROM dbo.PrizeStepType ORDER BY Code
            """,
        ),
        ("Title",),
    )
    calc_methods = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Code,CONVERT(varbinary(max),Title) AS Title
            FROM GNR.tblLookup WHERE CodeType=73 ORDER BY Code
            """,
        ),
        ("Title",),
    )
    return {
        "discount_purpose_types": discount_types,
        "derived_status_labels": statuses,
        "prize_types": prize_types,
        "prize_step_types": step_types,
        "calculation_methods": calc_methods,
    }


def _price_history_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rows,COUNT(DISTINCT GoodsRef) AS goods,
               COUNT(DISTINCT UniqueId) AS distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) AS null_uuids,
               SUM(CASE WHEN DCRef IS NOT NULL THEN 1 ELSE 0 END) AS dc_specific_rows,
               SUM(CASE WHEN SalePrice<=0 THEN 1 ELSE 0 END) AS nonpositive_sale_price,
               SUM(CASE WHEN UserPrice<=0 THEN 1 ELSE 0 END) AS nonpositive_user_price,
               MIN(StartDate) AS minimum_start_date,MAX(StartDate) AS maximum_start_date,
               MIN(EndDate) AS minimum_end_date,MAX(EndDate) AS maximum_end_date
        FROM SLE.tblPrice
        """,
    )[0]
    effective = _rows(
        cursor,
        """
        SELECT cal.SolarDate AS as_of_business_date,COUNT_BIG(*) AS effective_rows,
               COUNT(DISTINCT p.GoodsRef) AS effective_goods,
               SUM(CASE WHEN p.DCRef IS NOT NULL THEN 1 ELSE 0 END) AS dc_specific_rows
        FROM SLE.tblPrice AS p
        CROSS JOIN (SELECT SolarDate FROM dbo.Calendar
                    WHERE Date=CAST(GETDATE() AS date)) AS cal
        WHERE p.StartDate<=cal.SolarDate
          AND (p.EndDate IS NULL OR p.EndDate>=cal.SolarDate)
        GROUP BY cal.SolarDate
        """,
    )[0]
    interval_shape = _rows(
        cursor,
        """
        SELECT SUM(CASE WHEN EndDate<StartDate THEN 1 ELSE 0 END) AS reverse_intervals,
               SUM(CASE WHEN EndDate IS NULL THEN 1 ELSE 0 END) AS open_ended_rows,
               SUM(CASE WHEN StartDate IS NULL THEN 1 ELSE 0 END) AS missing_start_date
        FROM SLE.tblPrice
        """,
    )[0]
    return {"population": population, "effective_snapshot": effective,
            "interval_shape": interval_shape}


def _contract_price_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rows,COUNT(DISTINCT GoodsRef) AS goods,
               COUNT(DISTINCT UniqueId) AS distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) AS null_uuids,
               SUM(CASE WHEN SalePrice<=0 THEN 1 ELSE 0 END) AS nonpositive_sale_price,
               SUM(CASE WHEN GoodsRef IS NULL THEN 1 ELSE 0 END) AS missing_goods,
               SUM(CASE WHEN MinQty>0 THEN 1 ELSE 0 END) AS positive_min_qty,
               SUM(CASE WHEN MaxQty IS NOT NULL THEN 1 ELSE 0 END) AS populated_max_qty,
               SUM(CASE WHEN EndDate<StartDate THEN 1 ELSE 0 END) AS reverse_intervals,
               SUM(CASE WHEN StartDate IS NULL THEN 1 ELSE 0 END) AS missing_start_date
        FROM SLE.tblCPrice
        """,
    )[0]
    type_distribution = _rows(
        cursor,
        """
        SELECT CPriceType,COUNT_BIG(*) AS price_rows,
               COUNT(DISTINCT GoodsRef) AS goods,
               MIN(StartDate) AS minimum_start_date,MAX(EndDate) AS maximum_end_date
        FROM SLE.tblCPrice GROUP BY CPriceType ORDER BY price_rows DESC
        """,
    )
    currency_shape = _rows(
        cursor,
        """
        SELECT CurrencyRef,ExchangeRate,COUNT_BIG(*) AS price_rows,
               COUNT(DISTINCT GoodsRef) AS goods
        FROM SLE.tblCPrice
        GROUP BY CurrencyRef,ExchangeRate ORDER BY price_rows DESC
        """,
    )
    effective_dimensions = _rows(
        cursor,
        """
        SELECT cal.SolarDate AS as_of_business_date,COUNT_BIG(*) AS effective_rows,
               COUNT(DISTINCT cp.GoodsRef) AS effective_goods,
               SUM(CASE WHEN CustRef IS NOT NULL THEN 1 ELSE 0 END) AS customer,
               SUM(CASE WHEN CustCtgrRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_category,
               SUM(CASE WHEN CustActRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_activity,
               SUM(CASE WHEN CustLevelRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_level,
               SUM(CASE WHEN MainCustTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_main_type,
               SUM(CASE WHEN SubCustTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_sub_type,
               SUM(CASE WHEN DCRef IS NOT NULL THEN 1 ELSE 0 END) AS distribution_center,
               SUM(CASE WHEN StateRef IS NOT NULL THEN 1 ELSE 0 END) AS state,
               SUM(CASE WHEN CountyRef IS NOT NULL THEN 1 ELSE 0 END) AS county,
               SUM(CASE WHEN AreaRef IS NOT NULL THEN 1 ELSE 0 END) AS area,
               SUM(CASE WHEN OrderTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS order_type,
               SUM(CASE WHEN BuyTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS payment_type,
               SUM(CASE WHEN UsanceDay IS NOT NULL THEN 1 ELSE 0 END) AS payment_usance,
               SUM(CASE WHEN DealerCtgrRef IS NOT NULL THEN 1 ELSE 0 END) AS dealer_category,
               SUM(CASE WHEN BatchNoRef IS NOT NULL OR BatchNoGroupRef IS NOT NULL THEN 1 ELSE 0 END) AS batch,
               SUM(CASE WHEN GoodsGroupRef IS NOT NULL THEN 1 ELSE 0 END) AS goods_group,
               SUM(CASE WHEN MainTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS goods_main_type,
               SUM(CASE WHEN SubTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS goods_sub_type,
               SUM(CASE WHEN SaleOfficeRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_office,
               SUM(CASE WHEN CustRef IS NULL AND CustCtgrRef IS NULL AND CustActRef IS NULL
                         AND CustLevelRef IS NULL AND MainCustTypeRef IS NULL
                         AND SubCustTypeRef IS NULL AND DCRef IS NULL AND StateRef IS NULL
                         AND CountyRef IS NULL AND AreaRef IS NULL AND OrderTypeRef IS NULL
                         AND BuyTypeRef IS NULL AND UsanceDay IS NULL AND DealerCtgrRef IS NULL
                         AND BatchNoRef IS NULL AND BatchNoGroupRef IS NULL
                         AND GoodsGroupRef IS NULL AND MainTypeRef IS NULL AND SubTypeRef IS NULL
                         AND SaleOfficeRef IS NULL THEN 1 ELSE 0 END) AS unrestricted_rows
        FROM SLE.tblCPrice AS cp
        CROSS JOIN (SELECT SolarDate FROM dbo.Calendar
                    WHERE Date=CAST(GETDATE() AS date)) AS cal
        WHERE cp.StartDate<=cal.SolarDate
          AND (cp.EndDate IS NULL OR cp.EndDate>=cal.SolarDate)
        GROUP BY cal.SolarDate
        """,
    )[0]
    public_projection = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS rows,COUNT(DISTINCT GoodsRef) AS goods,
               COUNT(DISTINCT Id) AS price_ids
        FROM dbo.WebService_PublicPrice
        """,
    )[0]
    return {
        "population": population,
        "type_distribution": type_distribution,
        "currency_exchange_shape": currency_shape,
        "effective_dimension_snapshot": effective_dimensions,
        "public_webservice_projection": public_projection,
    }


def _discount_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rules,COUNT(DISTINCT Code) AS distinct_codes,
               COUNT(DISTINCT UniqueId) AS distinct_uuids,
               COUNT(DISTINCT DisGroup) AS rule_groups,
               SUM(CASE WHEN IsActive=1 THEN 1 ELSE 0 END) AS active_flag,
               SUM(CASE WHEN IsActive<>1 OR IsActive IS NULL THEN 1 ELSE 0 END) AS no_effect_flag,
               SUM(CASE WHEN SqlCondition IS NOT NULL
                          AND LTRIM(RTRIM(SqlCondition))<>'' THEN 1 ELSE 0 END) AS advanced_sql_rules,
               SUM(CASE WHEN PrizeRef IS NOT NULL THEN 1 ELSE 0 END) AS single_prize_product,
               SUM(CASE WHEN PrizePackageRef IS NOT NULL THEN 1 ELSE 0 END) AS prize_package,
               SUM(CASE WHEN IsSelfPrize=1 THEN 1 ELSE 0 END) AS self_prize,
               SUM(CASE WHEN GoodsGroupRef IS NOT NULL THEN 1 ELSE 0 END) AS goods_group_selector,
               SUM(CASE WHEN ManufacturerRef IS NOT NULL THEN 1 ELSE 0 END) AS manufacturer_selector,
               SUM(CASE WHEN BrandRef IS NOT NULL THEN 1 ELSE 0 END) AS brand_selector,
               SUM(CASE WHEN MainTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS main_type_selector,
               SUM(CASE WHEN SubTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS sub_type_selector,
               MIN(StartDate) AS minimum_start_date,MAX(StartDate) AS maximum_start_date,
               MIN(EndDate) AS minimum_end_date,MAX(EndDate) AS maximum_end_date
        FROM SLE.tblDiscount
        """,
    )[0]
    status_snapshot = _rows(
        cursor,
        """
        SELECT cal.SolarDate AS as_of_business_date,
               SUM(CASE WHEN d.IsActive=1 AND d.StartDate<=cal.SolarDate
                          AND (d.EndDate IS NULL OR d.EndDate>=cal.SolarDate)
                        THEN 1 ELSE 0 END) AS effective,
               SUM(CASE WHEN d.IsActive=1 AND d.EndDate<cal.SolarDate
                        THEN 1 ELSE 0 END) AS active_flag_but_expired,
               SUM(CASE WHEN d.IsActive=1 AND d.StartDate>cal.SolarDate
                        THEN 1 ELSE 0 END) AS future_active_flag,
               SUM(CASE WHEN d.IsActive=0 THEN 1 ELSE 0 END) AS no_effect
        FROM SLE.tblDiscount AS d
        CROSS JOIN (SELECT SolarDate FROM dbo.Calendar
                    WHERE Date=CAST(GETDATE() AS date)) AS cal
        GROUP BY cal.SolarDate
        """,
    )[0]
    result_type_distribution = _rows(
        cursor,
        """
        SELECT DisType,PrizeType,DiscountTypeRef,IsSalePrize,IsSelfPrize,
               COUNT_BIG(*) AS rules,
               SUM(CASE WHEN IsActive=1 THEN 1 ELSE 0 END) AS active_flag
        FROM SLE.tblDiscount
        GROUP BY DisType,PrizeType,DiscountTypeRef,IsSalePrize,IsSelfPrize
        ORDER BY rules DESC
        """,
    )
    effective_result_distribution = _rows(
        cursor,
        """
        SELECT d.DisType,d.PrizeType,d.DiscountTypeRef,COUNT_BIG(*) AS rules
        FROM SLE.tblDiscount AS d
        CROSS JOIN (SELECT SolarDate FROM dbo.Calendar
                    WHERE Date=CAST(GETDATE() AS date)) AS cal
        WHERE d.IsActive=1 AND d.StartDate<=cal.SolarDate
          AND (d.EndDate IS NULL OR d.EndDate>=cal.SolarDate)
        GROUP BY d.DisType,d.PrizeType,d.DiscountTypeRef
        ORDER BY rules DESC
        """,
    )
    condition_dimensions = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS condition_rows,COUNT(DISTINCT DiscountRef) AS rules,
               SUM(CASE WHEN DCRef IS NOT NULL THEN 1 ELSE 0 END) AS distribution_center,
               SUM(CASE WHEN CustCtgrRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_category,
               SUM(CASE WHEN CustActRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_activity,
               SUM(CASE WHEN CustLevelRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_level,
               SUM(CASE WHEN CustRef IS NOT NULL THEN 1 ELSE 0 END) AS customer,
               SUM(CASE WHEN CustGroupRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_group,
               SUM(CASE WHEN PayType IS NOT NULL THEN 1 ELSE 0 END) AS payment_type,
               SUM(CASE WHEN PaymentUsanceRef IS NOT NULL THEN 1 ELSE 0 END) AS payment_usance,
               SUM(CASE WHEN OrderType IS NOT NULL THEN 1 ELSE 0 END) AS order_type,
               SUM(CASE WHEN SaleOfficeRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_office,
               SUM(CASE WHEN StateRef IS NOT NULL THEN 1 ELSE 0 END) AS state,
               SUM(CASE WHEN CountyRef IS NOT NULL THEN 1 ELSE 0 END) AS county,
               SUM(CASE WHEN AreaRef IS NOT NULL THEN 1 ELSE 0 END) AS area,
               SUM(CASE WHEN SaleZoneRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_zone,
               SUM(CASE WHEN MainCustTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_main_type,
               SUM(CASE WHEN SubCustTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS customer_sub_type,
               SUM(CASE WHEN OrderNo IS NOT NULL THEN 1 ELSE 0 END) AS order_number,
               SUM(CASE WHEN OrderRef IS NOT NULL THEN 1 ELSE 0 END) AS order_reference
        FROM SLE.tblDiscountCondition
        """,
    )[0]
    bridges = {
        "eligible_goods": _rows(
            cursor,
            """SELECT COUNT_BIG(*) AS rows,COUNT(DISTINCT DiscountRef) AS rules,
                      COUNT(DISTINCT GoodsRef) AS goods
                 FROM SLE.tblDiscountGoods""",
        )[0],
        "selectable_prize_goods": _rows(
            cursor,
            """SELECT COUNT_BIG(*) AS rows,COUNT(DISTINCT DiscountRef) AS rules,
                      COUNT(DISTINCT GoodsRef) AS goods,
                      SUM(CASE WHEN DiscountPrizeCount<=0 THEN 1 ELSE 0 END) AS nonpositive_count
                 FROM SLE.tblDiscountPrizeList""",
        )[0],
        "deactivation_audit": _rows(
            cursor,
            """SELECT IsActiveChangedTo,COUNT_BIG(*) AS rows,
                      MIN(ChangeDate) AS minimum_change,MAX(ChangeDate) AS maximum_change
                 FROM SLE.tblDiscount_DeactivationLog GROUP BY IsActiveChangedTo""",
        ),
    }
    return {
        "population": population,
        "effective_status_snapshot": status_snapshot,
        "result_type_distribution": result_type_distribution,
        "effective_result_distribution": effective_result_distribution,
        "condition_dimensions": condition_dimensions,
        "rule_bridges": bridges,
    }


def _business_window_usage(cursor: Any) -> dict[str, Any]:
    sale_prices = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) AS sale_lines,
               SUM(CASE WHEN i.PriceRef IS NOT NULL THEN 1 ELSE 0 END) AS with_price_ref,
               SUM(CASE WHEN i.CPriceRef IS NOT NULL THEN 1 ELSE 0 END) AS with_contract_price_ref,
               SUM(CASE WHEN i.PriceRef IS NOT NULL AND i.CPriceRef IS NOT NULL
                        THEN 1 ELSE 0 END) AS with_both,
               SUM(CASE WHEN i.PriceRef IS NULL AND i.CPriceRef IS NULL
                        THEN 1 ELSE 0 END) AS with_neither,
               COUNT(DISTINCT i.PriceRef) AS distinct_price_refs,
               COUNT(DISTINCT i.CPriceRef) AS distinct_contract_price_refs,
               COUNT(DISTINCT i.GoodsRef) AS goods,
               SUM(CASE WHEN ISNULL(i.Discount,0)<>0 OR ISNULL(i.Dis1,0)<>0
                          OR ISNULL(i.Dis2,0)<>0 OR ISNULL(i.Dis3,0)<>0
                          OR ISNULL(i.OtherDiscount,0)<>0 THEN 1 ELSE 0 END) AS lines_with_discount,
               SUM(CASE WHEN ISNULL(i.AddAmount,0)<>0 OR ISNULL(i.Add1,0)<>0
                          OR ISNULL(i.Add2,0)<>0 OR ISNULL(i.OtherAddition,0)<>0
                        THEN 1 ELSE 0 END) AS lines_with_addition,
               SUM(CASE WHEN ISNULL(i.PrizeType,0)<>0 THEN 1 ELSE 0 END) AS prize_lines
        FROM SLE.tblSaleItm AS i JOIN SLE.tblSaleHdr AS h ON h.ID=i.HdrRef
        WHERE h.SaleDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
          AND ISNULL(h.CancelFlag,0)=0 AND i.IsDeleted=0
        """,
    )[0]
    order_prices = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) AS order_lines,
               SUM(CASE WHEN i.CPriceRef IS NOT NULL THEN 1 ELSE 0 END) AS with_contract_price_ref,
               SUM(CASE WHEN i.CPriceRef IS NULL THEN 1 ELSE 0 END) AS without_contract_price_ref,
               COUNT(DISTINCT i.CPriceRef) AS distinct_contract_price_refs,
               COUNT(DISTINCT i.GoodsRef) AS goods
        FROM SLE.tblOrderItm AS i JOIN SLE.tblOrderHdr AS h ON h.ID=i.HdrRef
        WHERE h.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
          AND h.CancelFlag=0 AND i.IsDeleted=0
        """,
    )[0]
    applied_rules = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) AS applied_rows,COUNT(DISTINCT ds.HdrRef) AS sales,
               COUNT(DISTINCT ds.DisRef) AS rules,COUNT(DISTINCT ds.ItemRef) AS sale_items,
               SUM(CASE WHEN ISNULL(ds.Discount,0)<>0 THEN 1 ELSE 0 END) AS nonzero_discount,
               SUM(CASE WHEN ISNULL(ds.AddAmount,0)<>0 THEN 1 ELSE 0 END) AS nonzero_addition
        FROM SLE.tblDisSale AS ds JOIN SLE.tblSaleHdr AS h ON h.ID=ds.HdrRef
        WHERE h.SaleDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
          AND ISNULL(h.CancelFlag,0)=0
        """,
    )[0]
    order_prizes = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) AS prize_rows,COUNT(DISTINCT p.OrderRef) AS orders,
               COUNT(DISTINCT p.DiscountRef) AS rules,COUNT(DISTINCT p.GoodsRef) AS goods,
               SUM(CASE WHEN p.isdeleted=0 THEN 1 ELSE 0 END) AS active_rows,
               SUM(CASE WHEN p.IsAutomatic=1 THEN 1 ELSE 0 END) AS automatic_rows
        FROM SLE.tblOrderPrize AS p JOIN SLE.tblOrderHdr AS h ON h.ID=p.OrderRef
        WHERE h.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
          AND h.CancelFlag=0
        """,
    )[0]
    return {
        "basis": "Persian business dates; cancelled headers and deleted lines excluded",
        "from": BUSINESS_DATE_FROM,
        "to": BUSINESS_DATE_TO,
        "sale_price_usage": sale_prices,
        "order_price_usage": order_prices,
        "applied_sale_rules": applied_rules,
        "order_prizes": order_prizes,
    }


def _ngt_projection_quality(cursor: Any) -> dict[str, Any]:
    line_promotions = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rows,
               SUM(CASE WHEN p.IsRemoved=0 THEN 1 ELSE 0 END) AS active_rows,
               COUNT(DISTINCT p.CustomerCallOrderLineUniqueId) AS order_lines,
               SUM(CASE WHEN TRY_CONVERT(int,p.DiscountRef) IS NOT NULL THEN 1 ELSE 0 END) AS numeric_discount_refs,
               SUM(CASE WHEN d.ID IS NOT NULL THEN 1 ELSE 0 END) AS matched_discount_ids,
               SUM(CASE WHEN TRY_CONVERT(float,p.DiscountAmount) IS NOT NULL THEN 1 ELSE 0 END) AS parseable_amounts,
               SUM(CASE WHEN TRY_CONVERT(float,p.DiscountAmount) IS NULL
                          AND NULLIF(LTRIM(RTRIM(p.DiscountAmount)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) AS malformed_amounts
        FROM NGT.CustomerCallOrderLinePromotions AS p
        LEFT JOIN SLE.tblDiscount AS d ON d.ID=TRY_CONVERT(int,p.DiscountRef)
        """,
    )[0]
    order_prizes = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rows,
               SUM(CASE WHEN p.IsRemoved=0 THEN 1 ELSE 0 END) AS active_rows,
               COUNT(DISTINCT p.CustomerCallOrderUniqueId) AS orders,
               COUNT(DISTINCT p.DisRef) AS distinct_numeric_refs,
               COUNT(DISTINCT p.DiscountUniqueId) AS distinct_uuids,
               SUM(CASE WHEN di.ID IS NOT NULL THEN 1 ELSE 0 END) AS numeric_matches,
               SUM(CASE WHEN du.ID IS NOT NULL THEN 1 ELSE 0 END) AS uuid_matches,
               SUM(CASE WHEN di.ID=du.ID THEN 1 ELSE 0 END) AS numeric_uuid_agree,
               SUM(CASE WHEN p.DiscountUniqueId='00000000-0000-0000-0000-000000000000'
                        THEN 1 ELSE 0 END) AS zero_uuid_rows,
               SUM(CASE WHEN g.ID IS NOT NULL THEN 1 ELSE 0 END) AS product_uuid_matches
        FROM NGT.CustomerCallOrderPrizes AS p
        LEFT JOIN SLE.tblDiscount AS di ON di.ID=p.DisRef
        LEFT JOIN SLE.tblDiscount AS du ON du.UniqueId=p.DiscountUniqueId
        LEFT JOIN GNR.tblGoods AS g ON g.UniqueId=p.ProductUniqueId
        """,
    )[0]
    sell_prizes = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_rows,
               SUM(CASE WHEN p.IsRemoved=0 THEN 1 ELSE 0 END) AS active_rows,
               SUM(CASE WHEN d.ID IS NOT NULL THEN 1 ELSE 0 END) AS matched_discount,
               SUM(CASE WHEN g.ID IS NOT NULL THEN 1 ELSE 0 END) AS matched_prize_goods,
               SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) AS matched_sale
        FROM NGT.CustomerCallSellPrizes AS p
        LEFT JOIN SLE.tblDiscount AS d ON d.ID=p.DiscountRef
        LEFT JOIN GNR.tblGoods AS g ON g.ID=p.PrizeRef
        LEFT JOIN SLE.tblSaleHdr AS h ON h.ID=p.SaleRef
        """,
    )[0]
    window = _rows(
        cursor,
        f"""
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderLinePromotions p
           JOIN NGT.CustomerCallOrderLines l ON l.Id=p.CustomerCallOrderLineUniqueId
           JOIN NGT.CustomerCallOrders o ON o.Id=l.CustomerCallOrderUniqueId
           WHERE o.SalePDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
             AND p.IsRemoved=0 AND l.IsRemoved=0 AND o.IsRemoved=0) AS promotion_rows,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderPrizes p
           JOIN NGT.CustomerCallOrders o ON o.Id=p.CustomerCallOrderUniqueId
           WHERE o.SalePDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
             AND p.IsRemoved=0 AND o.IsRemoved=0) AS prize_rows,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallSellPrizes p
           JOIN NGT.CustomerCallOrders o ON o.Id=p.CustomerCallOrderUniqueId
           WHERE o.SalePDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
             AND p.IsRemoved=0 AND o.IsRemoved=0) AS realized_sale_prize_rows
        """,
    )[0]
    return {"line_promotions": line_promotions, "order_prizes": order_prizes,
            "realized_sale_prizes": sell_prizes, "business_window": window}


def _data_quality(cursor: Any) -> dict[str, Any]:
    referential = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblPrice p LEFT JOIN GNR.tblGoods g ON g.ID=p.GoodsRef
           WHERE g.ID IS NULL) AS orphan_price_goods,
          (SELECT COUNT_BIG(*) FROM SLE.tblCPrice p LEFT JOIN GNR.tblGoods g ON g.ID=p.GoodsRef
           WHERE p.GoodsRef IS NOT NULL AND g.ID IS NULL) AS orphan_contract_price_goods,
          (SELECT COUNT_BIG(*) FROM SLE.tblCPrice p LEFT JOIN GNR.tblUnit u ON u.ID=p.UnitRef
           WHERE u.ID IS NULL) AS orphan_contract_price_units,
          (SELECT COUNT_BIG(*) FROM SLE.tblDiscountCondition c LEFT JOIN SLE.tblDiscount d ON d.ID=c.DiscountRef
           WHERE d.ID IS NULL) AS orphan_discount_conditions,
          (SELECT COUNT_BIG(DISTINCT c.DiscountRef) FROM SLE.tblDiscountCondition c
           LEFT JOIN SLE.tblDiscount d ON d.ID=c.DiscountRef
           WHERE d.ID IS NULL) AS orphan_discount_condition_refs,
          (SELECT COUNT_BIG(*) FROM SLE.tblDiscountGoods x LEFT JOIN SLE.tblDiscount d ON d.ID=x.DiscountRef
           WHERE d.ID IS NULL) AS orphan_discount_goods_rules,
          (SELECT COUNT_BIG(*) FROM SLE.tblDiscountGoods x LEFT JOIN GNR.tblGoods g ON g.ID=x.GoodsRef
           WHERE g.ID IS NULL) AS orphan_discount_goods,
          (SELECT COUNT_BIG(*) FROM SLE.tblDiscountPrizeList x LEFT JOIN SLE.tblDiscount d ON d.ID=x.DiscountRef
           WHERE d.ID IS NULL) AS orphan_prize_list_rules,
          (SELECT COUNT_BIG(*) FROM SLE.tblDiscountPrizeList x LEFT JOIN GNR.tblGoods g ON g.ID=x.GoodsRef
           WHERE g.ID IS NULL) AS orphan_prize_list_goods
        """,
    )[0]
    duplicate_keys = _rows(
        cursor,
        """
        SELECT 'price_uuid' AS check_name,COUNT_BIG(*) AS duplicate_groups FROM (
          SELECT UniqueId FROM SLE.tblPrice WHERE UniqueId IS NOT NULL
          GROUP BY UniqueId HAVING COUNT_BIG(*)>1) x
        UNION ALL SELECT 'contract_price_uuid',COUNT_BIG(*) FROM (
          SELECT UniqueId FROM SLE.tblCPrice WHERE UniqueId IS NOT NULL
          GROUP BY UniqueId HAVING COUNT_BIG(*)>1) x
        UNION ALL SELECT 'discount_uuid',COUNT_BIG(*) FROM (
          SELECT UniqueId FROM SLE.tblDiscount WHERE UniqueId IS NOT NULL
          GROUP BY UniqueId HAVING COUNT_BIG(*)>1) x
        UNION ALL SELECT 'discount_code',COUNT_BIG(*) FROM (
          SELECT Code FROM SLE.tblDiscount GROUP BY Code HAVING COUNT_BIG(*)>1) x
        UNION ALL SELECT 'discount_goods_pair',COUNT_BIG(*) FROM (
          SELECT DiscountRef,GoodsRef FROM SLE.tblDiscountGoods
          GROUP BY DiscountRef,GoodsRef HAVING COUNT_BIG(*)>1) x
        UNION ALL SELECT 'discount_prize_pair',COUNT_BIG(*) FROM (
          SELECT DiscountRef,GoodsRef FROM SLE.tblDiscountPrizeList
          GROUP BY DiscountRef,GoodsRef HAVING COUNT_BIG(*)>1) x
        """,
    )
    coverage = _rows(
        cursor,
        """
        SELECT cal.SolarDate AS as_of_business_date,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g WHERE NOT EXISTS (
             SELECT 1 FROM SLE.tblPrice p WHERE p.GoodsRef=g.ID
               AND p.StartDate<=cal.SolarDate
               AND (p.EndDate IS NULL OR p.EndDate>=cal.SolarDate))) AS goods_without_effective_price_history,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g WHERE NOT EXISTS (
             SELECT 1 FROM SLE.tblCPrice p WHERE p.GoodsRef=g.ID
               AND p.StartDate<=cal.SolarDate
               AND (p.EndDate IS NULL OR p.EndDate>=cal.SolarDate))) AS goods_without_effective_contract_price
        FROM (SELECT SolarDate FROM dbo.Calendar
              WHERE Date=CAST(GETDATE() AS date)) AS cal
        """,
    )[0]
    return {"referential_integrity": referential,
            "duplicate_key_groups": duplicate_keys,
            "effective_goods_coverage": coverage}


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT s.name AS schema_name,o.name AS object_name,o.type_desc,
               m.definition,o.modify_date
        FROM sys.objects AS o JOIN sys.schemas AS s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules AS m ON m.object_id=o.object_id
        WHERE (s.name='SLE' AND o.name IN
              ('FindGoodsPriceRef','FindGoodsPrice','FindGoodsPriceWithDC',
               'vwDiscountPrizeType','vwDiscountGetList'))
           OR (s.name='GNR' AND o.name='ufn_GetCPriceRef')
           OR (s.name='dbo' AND o.name IN
              ('WebService_PublicPrice','PrizeStepType','NGT_GetDiscount',
               'usp_sdsnet_Order_Preview'))
           OR (s.name='FRU' AND o.name='DiscountCalcMethodModel')
        ORDER BY s.name,o.name
        """,
    )


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [_table_metadata(cursor, item["object"], item["role"])
                  for item in DOMAIN_TABLES]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "pricing_discounts_and_prizes",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata, rule shape, and aggregate evidence",
                "privacy_policy": "no customer/personnel rows, raw SQL conditions, or credentials",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "price_history": _price_history_profile(cursor),
            "conditional_contract_prices": _contract_price_profile(cursor),
            "discount_rules": _discount_profile(cursor),
            "business_window_usage": _business_window_usage(cursor),
            "ngt_projection_quality": _ngt_projection_quality(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() AS captured_at")[0],
            "evidence_limits": [
                "Rule SQL-condition values are intentionally excluded; only aggregate presence is persisted.",
                "IsActive alone is not an effective-date status; start and end dates are also required.",
                "Reverse price intervals are measured as a legacy close-previous-row convention, not automatically labelled corruption.",
                "CPriceType 1 and 5 are observed values, but their official labels remain unresolved.",
                "DisType 300 is evidenced as line-level; other code-family semantics require runtime tests before reimplementation.",
                "NGT prize history includes zero discount UUIDs and therefore retains numeric and UUID crosswalk evidence separately.",
                "Formal dependencies do not capture dynamic SQL or every Ref/Id/UUID convention.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
