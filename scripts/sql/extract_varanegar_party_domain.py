"""Extract Varanegar party/customer/supplier/personnel evidence safely.

This fifth information-base slice establishes the shared Contact master and its
customer, supplier, personnel, application-user, job, and NGT-principal roles.
It intentionally emits no names, phones, addresses, national identifiers,
usernames, password values, password hashes, or security stamps.  Only schema,
non-personal reference labels, and aggregate completeness/quality evidence are
persisted.
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
    {"object": "dbo.Contact", "role": "shared_party_contact_master"},
    {"object": "dbo.ContactType", "role": "contact_type"},
    {"object": "dbo.ContactTitle", "role": "contact_title"},
    {"object": "dbo.LegalPersonType", "role": "legal_registration_type"},
    {"object": "GNR.tblCust", "role": "customer_master"},
    {"object": "GNR.tblCustGroup", "role": "customer_group_tree"},
    {"object": "GNR.tblCustAct", "role": "customer_activity_type"},
    {"object": "GNR.tblCustlevel", "role": "customer_level"},
    {"object": "SLE.tblCustCtgrSle", "role": "sales_customer_category"},
    {"object": "GNR.tblMainCustType", "role": "legacy_customer_main_type"},
    {"object": "GNR.tblSubCustType", "role": "legacy_customer_sub_type"},
    {"object": "GNR.tblCustMainSubType", "role": "customer_classification_bridge"},
    {"object": "GNR.tblSupplier", "role": "supplier_master"},
    {"object": "dbo.Personnel", "role": "personnel_and_sales_agent_master"},
    {"object": "dbo.PersonnelType", "role": "personnel_type"},
    {"object": "dbo.PersonnelInfoStatusType", "role": "personnel_information_status"},
    {"object": "dbo.Job", "role": "job_type"},
    {"object": "dbo.PersonnelJob", "role": "personnel_job_history_and_hierarchy"},
    {"object": "dbo.AppUser", "role": "legacy_application_user"},
    {"object": "NGT.Principals", "role": "ngt_identity_principal"},
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
            WHERE LOWER(c.name) LIKE '%contactid%'
               OR LOWER(c.name) LIKE '%custref%'
               OR LOWER(c.name) LIKE '%customerid%'
               OR LOWER(c.name) LIKE '%customeruniqueid%'
               OR LOWER(c.name) LIKE '%supplierref%'
               OR LOWER(c.name) LIKE '%personnelid%'
               OR LOWER(c.name) LIKE '%dealerref%'
               OR LOWER(c.name) LIKE '%supervisorref%'
               OR LOWER(c.name) LIKE '%principalid%'
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
    customer_lookup_rows = _decode_fields(
        _rows(
            cursor,
            """
            SELECT CodeType,Code,CONVERT(varbinary(max),Title) AS Title,Value1
            FROM GNR.tblLookup WHERE CodeType IN (8,9,24)
            ORDER BY CodeType,Code
            """,
        ),
        ("Title",),
    )
    contact_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ContactTypeId,
                   CONVERT(varbinary(max),ContactTypeName) AS ContactTypeName
            FROM dbo.ContactType ORDER BY ContactTypeId
            """,
        ),
        ("ContactTypeName",),
    )
    contact_titles = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ContactTitleId,
                   CONVERT(varbinary(max),ContactTitleName) AS ContactTitleName,
                   ContactTypeId
            FROM dbo.ContactTitle ORDER BY ContactTitleId
            """,
        ),
        ("ContactTitleName",),
    )
    legal_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT LegalPersonTypeId,
                   CONVERT(varbinary(max),LegalPersonType) AS LegalPersonType
            FROM dbo.LegalPersonType ORDER BY LegalPersonTypeId
            """,
        ),
        ("LegalPersonType",),
    )
    customer_groups = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,ParentRef,
                   CONVERT(varbinary(max),CustGroupName) AS CustGroupName,
                   NLeft,NRight,NLevel
            FROM GNR.tblCustGroup ORDER BY NLeft,ID
            """,
        ),
        ("CustGroupName",),
    )
    customer_activities = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CustActCode,
                   CONVERT(varbinary(max),CustActName) AS CustActName,UniqueId
            FROM GNR.tblCustAct ORDER BY ID
            """,
        ),
        ("CustActName",),
    )
    customer_levels = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,Code,CONVERT(varbinary(max),Title) AS Title,UniqueId
            FROM GNR.tblCustlevel ORDER BY ID
            """,
        ),
        ("Title",),
    )
    customer_categories = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CustCtgrCode,
                   CONVERT(varbinary(max),CustCtgrName) AS CustCtgrName,CustCtgrGUID
            FROM SLE.tblCustCtgrSle ORDER BY ID
            """,
        ),
        ("CustCtgrName",),
    )
    main_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,MainCode,CONVERT(varbinary(max),MainName) AS MainName,LookUpId
            FROM GNR.tblMainCustType ORDER BY ID
            """,
        ),
        ("MainName",),
    )
    sub_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,SubCode,CONVERT(varbinary(max),SubName) AS SubName,MainTypeRef
            FROM GNR.tblSubCustType ORDER BY MainTypeRef,ID
            """,
        ),
        ("SubName",),
    )
    personnel_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT PersonnelTypeId,
                   CONVERT(varbinary(max),PersonnelTypeName) AS PersonnelTypeName
            FROM dbo.PersonnelType ORDER BY PersonnelTypeId
            """,
        ),
        ("PersonnelTypeName",),
    )
    personnel_statuses = _decode_fields(
        _rows(
            cursor,
            """
            SELECT PersonnelInfoStatusTypeId,
                   CONVERT(varbinary(max),PersonnelInfoStatusTypeName) AS PersonnelInfoStatusTypeName
            FROM dbo.PersonnelInfoStatusType ORDER BY PersonnelInfoStatusTypeId
            """,
        ),
        ("PersonnelInfoStatusTypeName",),
    )
    jobs = _decode_fields(
        _rows(
            cursor,
            """
            SELECT JobId,CONVERT(varbinary(max),JobName) AS JobName,
                   IsUsedInSDS,IsUsedInFRU
            FROM dbo.Job ORDER BY JobId
            """,
        ),
        ("JobName",),
    )
    return {
        "contact_types": contact_types,
        "contact_titles": contact_titles,
        "legal_person_types": legal_types,
        "customer_status_type_registration_lookups": customer_lookup_rows,
        "customer_groups": customer_groups,
        "customer_activities": customer_activities,
        "customer_levels": customer_levels,
        "customer_categories": customer_categories,
        "customer_main_types": main_types,
        "customer_sub_types": sub_types,
        "personnel_types": personnel_types,
        "personnel_information_statuses": personnel_statuses,
        "jobs": jobs,
    }


def _contact_role_summary(cursor: Any) -> dict[str, Any]:
    return {
        "population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_contacts,
                   SUM(CASE WHEN IsCust=1 THEN 1 ELSE 0 END) AS flagged_customer,
                   SUM(CASE WHEN IsSupplier=1 THEN 1 ELSE 0 END) AS flagged_supplier,
                   SUM(CASE WHEN IsPersonnel=1 THEN 1 ELSE 0 END) AS flagged_personnel,
                   SUM(CASE WHEN IsReceivable=1 THEN 1 ELSE 0 END) AS receivable,
                   SUM(CASE WHEN IsPayable=1 THEN 1 ELSE 0 END) AS payable,
                   SUM(CASE WHEN NationalIDNo IS NOT NULL AND LTRIM(RTRIM(NationalIDNo))<>'' THEN 1 ELSE 0 END) AS national_id_populated,
                   SUM(CASE WHEN Mobile IS NOT NULL AND LTRIM(RTRIM(Mobile))<>'' THEN 1 ELSE 0 END) AS mobile_populated,
                   SUM(CASE WHEN Email1 IS NOT NULL AND LTRIM(RTRIM(Email1))<>'' THEN 1 ELSE 0 END) AS email_populated
            FROM dbo.Contact
            """,
        )[0],
        "actual_role_links": _rows(
            cursor,
            """
            WITH roles AS (
              SELECT ContactId,'customer' AS role_name FROM GNR.tblCust WHERE ContactId IS NOT NULL
              UNION ALL SELECT ContactId,'supplier' FROM GNR.tblSupplier WHERE ContactId IS NOT NULL
              UNION ALL SELECT ContactId,'personnel' FROM dbo.Personnel
            ), per_contact AS (
              SELECT ContactId,COUNT(DISTINCT role_name) AS role_count
              FROM roles GROUP BY ContactId
            )
            SELECT
              (SELECT COUNT_BIG(*) FROM GNR.tblCust WHERE ContactId IS NOT NULL) AS customer_links,
              (SELECT COUNT(DISTINCT ContactId) FROM GNR.tblCust WHERE ContactId IS NOT NULL) AS distinct_customer_contacts,
              (SELECT COUNT_BIG(*) FROM GNR.tblSupplier WHERE ContactId IS NOT NULL) AS supplier_links,
              (SELECT COUNT(DISTINCT ContactId) FROM GNR.tblSupplier WHERE ContactId IS NOT NULL) AS distinct_supplier_contacts,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel) AS personnel_links,
              (SELECT COUNT(DISTINCT ContactId) FROM dbo.Personnel) AS distinct_personnel_contacts,
              (SELECT COUNT_BIG(*) FROM per_contact WHERE role_count=1) AS contacts_with_one_role,
              (SELECT COUNT_BIG(*) FROM per_contact WHERE role_count=2) AS contacts_with_two_roles,
              (SELECT COUNT_BIG(*) FROM per_contact WHERE role_count=3) AS contacts_with_three_roles,
              (SELECT COUNT_BIG(*) FROM dbo.Contact c LEFT JOIN per_contact r ON r.ContactId=c.ContactId
                 WHERE r.ContactId IS NULL) AS contacts_without_actual_role
            """,
        )[0],
        "flag_link_mismatches": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x JOIN dbo.Contact c ON c.ContactId=x.ContactId
                 WHERE ISNULL(c.IsCust,0)<>1) AS customer_links_not_flagged_customer,
              (SELECT COUNT_BIG(*) FROM GNR.tblSupplier x JOIN dbo.Contact c ON c.ContactId=x.ContactId
                 WHERE ISNULL(c.IsSupplier,0)<>1) AS supplier_links_not_flagged_supplier,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel x JOIN dbo.Contact c ON c.ContactId=x.ContactId
                 WHERE ISNULL(c.IsPersonnel,0)<>1) AS personnel_links_not_flagged_personnel,
              (SELECT COUNT_BIG(*) FROM dbo.Contact c LEFT JOIN GNR.tblCust x ON x.ContactId=c.ContactId
                 WHERE c.IsCust=1 AND x.ID IS NULL) AS flagged_customer_without_customer_link,
              (SELECT COUNT_BIG(*) FROM dbo.Contact c LEFT JOIN GNR.tblSupplier x ON x.ContactId=c.ContactId
                 WHERE c.IsSupplier=1 AND x.Id IS NULL) AS flagged_supplier_without_supplier_link,
              (SELECT COUNT_BIG(*) FROM dbo.Contact c LEFT JOIN dbo.Personnel x ON x.ContactId=c.ContactId
                 WHERE c.IsPersonnel=1 AND x.PersonnelId IS NULL) AS flagged_personnel_without_personnel_link
            """,
        )[0],
        "sensitive_field_duplicate_groups": _rows(
            cursor,
            """
            SELECT 'contact_national_id' AS field_name,COUNT_BIG(*) AS duplicate_groups FROM (
              SELECT LTRIM(RTRIM(NationalIDNo)) normalized_value FROM dbo.Contact
              WHERE NationalIDNo IS NOT NULL AND LTRIM(RTRIM(NationalIDNo)) NOT IN ('','0')
              GROUP BY LTRIM(RTRIM(NationalIDNo)) HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'contact_mobile',COUNT_BIG(*) FROM (
              SELECT LTRIM(RTRIM(Mobile)) normalized_value FROM dbo.Contact
              WHERE Mobile IS NOT NULL AND LTRIM(RTRIM(Mobile)) NOT IN ('','0')
              GROUP BY LTRIM(RTRIM(Mobile)) HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'customer_national_code',COUNT_BIG(*) FROM (
              SELECT LTRIM(RTRIM(NationalCode)) normalized_value FROM GNR.tblCust
              WHERE NationalCode IS NOT NULL AND LTRIM(RTRIM(NationalCode)) NOT IN ('','0')
              GROUP BY LTRIM(RTRIM(NationalCode)) HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'customer_mobile',COUNT_BIG(*) FROM (
              SELECT LTRIM(RTRIM(Mobile)) normalized_value FROM GNR.tblCust
              WHERE Mobile IS NOT NULL AND LTRIM(RTRIM(Mobile)) NOT IN ('','0')
              GROUP BY LTRIM(RTRIM(Mobile)) HAVING COUNT_BIG(*)>1
            ) d
            """,
        ),
    }


def _customer_profile(cursor: Any) -> dict[str, Any]:
    return {
        "population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_customers,
                   SUM(CASE WHEN CustGUID IS NOT NULL THEN 1 ELSE 0 END) AS guid_populated,
                   SUM(CASE WHEN ContactId IS NOT NULL THEN 1 ELSE 0 END) AS contact_populated,
                   SUM(CASE WHEN Mobile IS NOT NULL AND LTRIM(RTRIM(Mobile))<>'' THEN 1 ELSE 0 END) AS mobile_populated,
                   SUM(CASE WHEN NationalCode IS NOT NULL AND LTRIM(RTRIM(NationalCode))<>'' THEN 1 ELSE 0 END) AS national_code_populated,
                   SUM(CASE WHEN Address IS NOT NULL AND LTRIM(RTRIM(Address))<>'' THEN 1 ELSE 0 END) AS address_populated,
                   SUM(CASE WHEN Latitude IS NOT NULL AND Longitude IS NOT NULL THEN 1 ELSE 0 END) AS coordinates_populated,
                   SUM(CASE WHEN Latitude=0 AND Longitude=0 THEN 1 ELSE 0 END) AS zero_coordinates,
                   SUM(CASE WHEN Latitude IS NOT NULL AND Longitude IS NOT NULL
                                  AND NOT (Latitude=0 AND Longitude=0)
                                  AND Latitude BETWEEN -90 AND 90
                                  AND Longitude BETWEEN -180 AND 180 THEN 1 ELSE 0 END) AS usable_coordinates,
                   SUM(CASE WHEN Latitude IS NOT NULL AND Longitude IS NOT NULL
                                  AND (Latitude NOT BETWEEN -90 AND 90
                                    OR Longitude NOT BETWEEN -180 AND 180) THEN 1 ELSE 0 END) AS out_of_range_coordinates,
                   SUM(CASE WHEN ParentCustomerId IS NOT NULL THEN 1 ELSE 0 END) AS parent_customer_populated,
                   SUM(CASE WHEN Username IS NOT NULL AND LTRIM(RTRIM(Username))<>'' THEN 1 ELSE 0 END) AS legacy_username_populated,
                   SUM(CASE WHEN Password IS NOT NULL AND DATALENGTH(Password)>0 THEN 1 ELSE 0 END) AS legacy_password_field_populated
            FROM GNR.tblCust
            """,
        )[0],
        "status_distribution": _rows(
            cursor,
            "SELECT Status,COUNT_BIG(*) AS customer_count FROM GNR.tblCust GROUP BY Status ORDER BY Status",
        ),
        "customer_type_distribution": _rows(
            cursor,
            "SELECT CustType,COUNT_BIG(*) AS customer_count FROM GNR.tblCust GROUP BY CustType ORDER BY CustType",
        ),
        "registration_type_distribution": _rows(
            cursor,
            "SELECT CustRegType,COUNT_BIG(*) AS customer_count FROM GNR.tblCust GROUP BY CustRegType ORDER BY CustRegType",
        ),
        "reference_coverage": _rows(
            cursor,
            """
            SELECT
              SUM(CASE WHEN CustCtgrRef IS NOT NULL THEN 1 ELSE 0 END) AS category_populated,
              SUM(CASE WHEN CustActRef IS NOT NULL THEN 1 ELSE 0 END) AS activity_populated,
              SUM(CASE WHEN CustLevelRef IS NOT NULL THEN 1 ELSE 0 END) AS level_populated,
              SUM(CASE WHEN CustGroupRef IS NOT NULL THEN 1 ELSE 0 END) AS group_populated,
              SUM(CASE WHEN StateRef IS NOT NULL THEN 1 ELSE 0 END) AS state_populated,
              SUM(CASE WHEN AreaRef IS NOT NULL THEN 1 ELSE 0 END) AS area_populated,
              SUM(CASE WHEN SalePathRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_path_populated
            FROM GNR.tblCust
            """,
        )[0],
        "category_distribution": _decode_fields(
            _rows(
                cursor,
                """
                SELECT c.CustCtgrRef,
                       CONVERT(varbinary(max),t.CustCtgrName) AS CustCtgrName,
                       COUNT_BIG(*) AS customer_count
                FROM GNR.tblCust c
                LEFT JOIN SLE.tblCustCtgrSle t ON t.ID=c.CustCtgrRef
                GROUP BY c.CustCtgrRef,t.CustCtgrName
                ORDER BY customer_count DESC,c.CustCtgrRef
                """,
            ),
            ("CustCtgrName",),
        ),
        "activity_distribution": _decode_fields(
            _rows(
                cursor,
                """
                SELECT c.CustActRef,
                       CONVERT(varbinary(max),t.CustActName) AS CustActName,
                       COUNT_BIG(*) AS customer_count
                FROM GNR.tblCust c
                LEFT JOIN GNR.tblCustAct t ON t.ID=c.CustActRef
                GROUP BY c.CustActRef,t.CustActName
                ORDER BY customer_count DESC,c.CustActRef
                """,
            ),
            ("CustActName",),
        ),
        "level_distribution": _decode_fields(
            _rows(
                cursor,
                """
                SELECT c.CustLevelRef,CONVERT(varbinary(max),t.Title) AS CustLevelTitle,
                       COUNT_BIG(*) AS customer_count
                FROM GNR.tblCust c
                LEFT JOIN GNR.tblCustlevel t ON t.ID=c.CustLevelRef
                GROUP BY c.CustLevelRef,t.Title
                ORDER BY customer_count DESC,c.CustLevelRef
                """,
            ),
            ("CustLevelTitle",),
        ),
        "classification_summary": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS classification_rows,
                   COUNT(DISTINCT CustRef) AS classified_customers,
                   (SELECT COUNT_BIG(*) FROM GNR.tblCust c LEFT JOIN GNR.tblCustMainSubType x
                      ON x.CustRef=c.ID WHERE x.ID IS NULL) AS customers_without_classification
            FROM GNR.tblCustMainSubType
            """,
        )[0],
        "credential_shape_aggregate_only": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS populated_rows,
                   MIN(LEN(Password)) AS min_character_length,
                   MAX(LEN(Password)) AS max_character_length,
                   COUNT(DISTINCT LEN(Password)) AS distinct_lengths
            FROM GNR.tblCust WHERE Password IS NOT NULL AND DATALENGTH(Password)>0
            """,
        )[0],
    }


def _supplier_profile(cursor: Any) -> dict[str, Any]:
    return {
        "population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_suppliers,
                   SUM(CASE WHEN Active=1 THEN 1 ELSE 0 END) AS active_suppliers,
                   SUM(CASE WHEN ContactId IS NOT NULL THEN 1 ELSE 0 END) AS contact_populated,
                   SUM(CASE WHEN UniqueId IS NOT NULL THEN 1 ELSE 0 END) AS uuid_populated,
                   SUM(CASE WHEN Mobile IS NOT NULL AND LTRIM(RTRIM(Mobile))<>'' THEN 1 ELSE 0 END) AS mobile_populated,
                   SUM(CASE WHEN NationalCode IS NOT NULL AND LTRIM(RTRIM(NationalCode))<>'' THEN 1 ELSE 0 END) AS national_code_populated
            FROM GNR.tblSupplier
            """,
        )[0],
        "goods_supplier_links": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS link_rows,COUNT(DISTINCT GoodsRef) AS distinct_goods,
                   COUNT(DISTINCT SupplierRef) AS distinct_suppliers
            FROM GNR.tblGoodsSupplier
            """,
        )[0],
        "business_window_usage": _rows(
            cursor,
            f"""
            SELECT
              (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr
                 WHERE SupplierRef IS NOT NULL AND VocherDate>='{BUSINESS_DATE_FROM}' AND VocherDate<='{BUSINESS_DATE_TO}') AS inventory_vouchers,
              (SELECT COUNT(DISTINCT SupplierRef) FROM inv.tblVocherHdr
                 WHERE SupplierRef IS NOT NULL AND VocherDate>='{BUSINESS_DATE_FROM}' AND VocherDate<='{BUSINESS_DATE_TO}') AS inventory_distinct_suppliers,
              (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr
                 WHERE SupplierRef IS NOT NULL AND OrderDate>='{BUSINESS_DATE_FROM}' AND OrderDate<='{BUSINESS_DATE_TO}') AS sales_orders,
              (SELECT COUNT(DISTINCT SupplierRef) FROM SLE.tblOrderHdr
                 WHERE SupplierRef IS NOT NULL AND OrderDate>='{BUSINESS_DATE_FROM}' AND OrderDate<='{BUSINESS_DATE_TO}') AS order_distinct_suppliers
            """,
        )[0],
    }


def _personnel_profile(cursor: Any) -> dict[str, Any]:
    return {
        "population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_personnel,
                   SUM(CASE WHEN IsActive=1 THEN 1 ELSE 0 END) AS active_personnel,
                   SUM(CASE WHEN PersonnelGUID IS NOT NULL THEN 1 ELSE 0 END) AS guid_populated,
                   SUM(CASE WHEN PrincipalId IS NOT NULL THEN 1 ELSE 0 END) AS principal_populated,
                   SUM(CASE WHEN EquivalentCustomerUniqueId IS NOT NULL THEN 1 ELSE 0 END) AS equivalent_customer_uuid_populated,
                   SUM(CASE WHEN PasswordHash IS NOT NULL AND LEN(PasswordHash)>0 THEN 1 ELSE 0 END) AS password_hash_field_populated,
                   SUM(CASE WHEN SecurityStamp IS NOT NULL AND LEN(SecurityStamp)>0 THEN 1 ELSE 0 END) AS security_stamp_field_populated,
                   SUM(CASE WHEN StockDcRef IS NOT NULL THEN 1 ELSE 0 END) AS stock_center_populated,
                   SUM(CASE WHEN PersonnelSaleOfficeRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_office_populated
            FROM dbo.Personnel
            """,
        )[0],
        "type_distribution": _decode_fields(
            _rows(
                cursor,
                """
                SELECT p.PersonnelTypeId,
                       CONVERT(varbinary(max),t.PersonnelTypeName) AS PersonnelTypeName,
                       COUNT_BIG(*) AS personnel_count,
                       SUM(CASE WHEN p.IsActive=1 THEN 1 ELSE 0 END) AS active_count
                FROM dbo.Personnel p
                LEFT JOIN dbo.PersonnelType t ON t.PersonnelTypeId=p.PersonnelTypeId
                GROUP BY p.PersonnelTypeId,t.PersonnelTypeName
                ORDER BY personnel_count DESC,p.PersonnelTypeId
                """,
            ),
            ("PersonnelTypeName",),
        ),
        "identity_crosswalk": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM dbo.Personnel p JOIN NGT.Principals n
                 ON n.Id=p.PrincipalId) AS principal_matches,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel p LEFT JOIN NGT.Principals n
                 ON n.Id=p.PrincipalId WHERE p.PrincipalId IS NOT NULL AND n.Id IS NULL) AS orphan_principals,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel p JOIN GNR.tblCust c
                 ON c.CustGUID=p.EquivalentCustomerUniqueId) AS equivalent_customer_uuid_matches,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel p LEFT JOIN GNR.tblCust c
                 ON c.CustGUID=p.EquivalentCustomerUniqueId
                 WHERE p.EquivalentCustomerUniqueId IS NOT NULL AND c.ID IS NULL) AS orphan_equivalent_customers,
              (SELECT COUNT_BIG(*) FROM dbo.AppUser a JOIN dbo.Personnel p
                 ON p.PersonnelId=a.PersonnelId) AS app_user_personnel_matches,
              (SELECT COUNT_BIG(*) FROM dbo.AppUser a LEFT JOIN dbo.Personnel p
                 ON p.PersonnelId=a.PersonnelId WHERE p.PersonnelId IS NULL) AS orphan_app_users
            """,
        )[0],
        "app_user_summary": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_app_users,
                   SUM(CASE WHEN IsActive=1 AND IsDeleted=0 THEN 1 ELSE 0 END) AS active_not_deleted,
                   SUM(CASE WHEN IsAdmin=1 AND IsDeleted=0 THEN 1 ELSE 0 END) AS admin_not_deleted,
                   SUM(CASE WHEN Password IS NOT NULL AND DATALENGTH(Password)>0 THEN 1 ELSE 0 END) AS password_blob_populated,
                   SUM(CASE WHEN NewPassword IS NOT NULL AND LEN(NewPassword)>0 THEN 1 ELSE 0 END) AS new_password_field_populated,
                   MIN(CASE WHEN Password IS NOT NULL THEN DATALENGTH(Password) END) AS min_password_blob_bytes,
                   MAX(CASE WHEN Password IS NOT NULL THEN DATALENGTH(Password) END) AS max_password_blob_bytes
            FROM dbo.AppUser
            """,
        )[0],
        "job_summary": _decode_fields(
            _rows(
                cursor,
                """
                SELECT j.JobId,CONVERT(varbinary(max),j.JobName) AS JobName,
                       COUNT_BIG(pj.PersonnelJobId) AS all_assignments,
                       SUM(CASE WHEN pj.PersonnelJobId IS NOT NULL
                                      AND (pj.EndDate IS NULL OR pj.EndDate>=SYSDATETIME())
                                THEN 1 ELSE 0 END) AS current_assignments,
                       COUNT(DISTINCT CASE WHEN pj.EndDate IS NULL OR pj.EndDate>=SYSDATETIME()
                                           THEN pj.PersonnelId END) AS current_distinct_personnel
                FROM dbo.Job j
                LEFT JOIN dbo.PersonnelJob pj ON pj.JobId=j.JobId
                GROUP BY j.JobId,j.JobName
                ORDER BY current_assignments DESC,all_assignments DESC,j.JobId
                """,
            ),
            ("JobName",),
        ),
        "job_assignment_quality": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_assignments,
                   SUM(CASE WHEN EndDate IS NULL OR EndDate>=SYSDATETIME() THEN 1 ELSE 0 END) AS current_assignments,
                   COUNT(DISTINCT CASE WHEN EndDate IS NULL OR EndDate>=SYSDATETIME()
                                       THEN PersonnelId END) AS current_personnel,
                   (SELECT COUNT_BIG(*) FROM dbo.PersonnelJob x LEFT JOIN dbo.Personnel p
                      ON p.PersonnelId=x.PersonnelId WHERE p.PersonnelId IS NULL) AS orphan_personnel,
                   (SELECT COUNT_BIG(*) FROM dbo.PersonnelJob x LEFT JOIN dbo.Job j
                      ON j.JobId=x.JobId WHERE j.JobId IS NULL) AS orphan_jobs,
                   (SELECT COUNT_BIG(*) FROM dbo.PersonnelJob x LEFT JOIN dbo.Personnel p
                      ON p.PersonnelId=x.ManagerId WHERE x.ManagerId IS NOT NULL AND p.PersonnelId IS NULL) AS orphan_managers,
                   (SELECT COUNT_BIG(*) FROM (
                      SELECT PersonnelId FROM dbo.PersonnelJob
                      WHERE EndDate IS NULL OR EndDate>=SYSDATETIME()
                      GROUP BY PersonnelId HAVING COUNT_BIG(*)>1
                    ) d) AS personnel_with_multiple_current_jobs
            FROM dbo.PersonnelJob
            """,
        )[0],
        "business_window_agent_usage": _rows(
            cursor,
            f"""
            SELECT
              (SELECT COUNT(DISTINCT DealerRef) FROM SLE.tblOrderHdr
                 WHERE DealerRef IS NOT NULL AND OrderDate>='{BUSINESS_DATE_FROM}' AND OrderDate<='{BUSINESS_DATE_TO}') AS order_dealers,
              (SELECT COUNT(DISTINCT SupervisorRef) FROM SLE.tblOrderHdr
                 WHERE SupervisorRef IS NOT NULL AND OrderDate>='{BUSINESS_DATE_FROM}' AND OrderDate<='{BUSINESS_DATE_TO}') AS order_supervisors,
              (SELECT COUNT(DISTINCT DealerRef) FROM SLE.tblSaleHdr
                 WHERE DealerRef IS NOT NULL AND SaleDate>='{BUSINESS_DATE_FROM}' AND SaleDate<='{BUSINESS_DATE_TO}') AS sale_dealers,
              (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr h LEFT JOIN dbo.Personnel p
                 ON p.PersonnelId=h.DealerRef
                 WHERE h.DealerRef IS NOT NULL AND h.OrderDate>='{BUSINESS_DATE_FROM}' AND h.OrderDate<='{BUSINESS_DATE_TO}'
                   AND p.PersonnelId IS NULL) AS orphan_order_dealer_rows,
              (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr h LEFT JOIN dbo.Personnel p
                 ON p.PersonnelId=h.DealerRef
                 WHERE h.DealerRef IS NOT NULL AND h.SaleDate>='{BUSINESS_DATE_FROM}' AND h.SaleDate<='{BUSINESS_DATE_TO}'
                   AND p.PersonnelId IS NULL) AS orphan_sale_dealer_rows
            """,
        )[0],
    }


def _ngt_customer_crosswalk(cursor: Any) -> dict[str, Any]:
    return {
        "path_customers": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_path_links,
                   SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) AS active_path_links,
                   COUNT(DISTINCT CASE WHEN IsRemoved=0 THEN CustomerUniqueId END) AS active_distinct_customer_uuids,
                   COUNT(DISTINCT CASE WHEN IsRemoved=0 AND c.ID IS NOT NULL THEN x.CustomerUniqueId END) AS active_distinct_matching_customers,
                   SUM(CASE WHEN x.IsRemoved=0 AND c.ID IS NULL THEN 1 ELSE 0 END) AS active_unmatched_path_rows
            FROM NGT.VisitTemplatePathCustomers x
            LEFT JOIN GNR.tblCust c ON c.CustGUID=x.CustomerUniqueId
            """,
        )[0],
        "customer_calls": _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) AS total_calls,
                   COUNT(DISTINCT CustomerUniqueId) AS distinct_customer_uuids,
                   SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) AS unmatched_call_rows,
                   COUNT(DISTINCT CASE WHEN c.ID IS NULL THEN x.CustomerUniqueId END) AS unmatched_distinct_customer_uuids,
                   SUM(CASE WHEN x.CallPDate>='{BUSINESS_DATE_FROM}' AND x.CallPDate<='{BUSINESS_DATE_TO}' THEN 1 ELSE 0 END) AS business_window_calls,
                   COUNT(DISTINCT CASE WHEN x.CallPDate>='{BUSINESS_DATE_FROM}' AND x.CallPDate<='{BUSINESS_DATE_TO}'
                                       THEN x.CustomerUniqueId END) AS business_window_distinct_customer_uuids
            FROM NGT.CustomerCalls x
            LEFT JOIN GNR.tblCust c ON c.CustGUID=x.CustomerUniqueId
            """,
        )[0],
    }


def _business_date_customer_activity(cursor: Any) -> dict[str, Any]:
    return {
        "basis": "Persian business dates; no names or customer-level rows are persisted",
        "from": BUSINESS_DATE_FROM,
        "to": BUSINESS_DATE_TO,
        "summary": _rows(
            cursor,
            f"""
            WITH order_customers AS (
              SELECT DISTINCT CustRef FROM SLE.tblOrderHdr
              WHERE CustRef IS NOT NULL AND OrderDate>='{BUSINESS_DATE_FROM}' AND OrderDate<='{BUSINESS_DATE_TO}'
            ), sale_customers AS (
              SELECT DISTINCT CustRef FROM SLE.tblSaleHdr
              WHERE CustRef IS NOT NULL AND SaleDate>='{BUSINESS_DATE_FROM}' AND SaleDate<='{BUSINESS_DATE_TO}'
            ), call_customers AS (
              SELECT DISTINCT c.ID AS CustRef
              FROM NGT.CustomerCalls n JOIN GNR.tblCust c ON c.CustGUID=n.CustomerUniqueId
              WHERE n.CallPDate>='{BUSINESS_DATE_FROM}' AND n.CallPDate<='{BUSINESS_DATE_TO}'
            ), active_customers AS (
              SELECT CustRef FROM order_customers
              UNION SELECT CustRef FROM sale_customers
              UNION SELECT CustRef FROM call_customers
            )
            SELECT
              (SELECT COUNT_BIG(*) FROM order_customers) AS customers_with_orders,
              (SELECT COUNT_BIG(*) FROM sale_customers) AS customers_with_sales,
              (SELECT COUNT_BIG(*) FROM call_customers) AS customers_with_ngt_calls,
              (SELECT COUNT_BIG(*) FROM active_customers) AS customers_with_any_activity,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust c LEFT JOIN active_customers a ON a.CustRef=c.ID
                 WHERE a.CustRef IS NULL) AS customers_without_activity
            """,
        )[0],
    }


def _data_quality(cursor: Any) -> dict[str, Any]:
    return {
        "referential_integrity": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN dbo.Contact c
                 ON c.ContactId=x.ContactId WHERE x.ContactId IS NOT NULL AND c.ContactId IS NULL) AS orphan_customer_contacts,
              (SELECT COUNT_BIG(*) FROM GNR.tblSupplier x LEFT JOIN dbo.Contact c
                 ON c.ContactId=x.ContactId WHERE x.ContactId IS NOT NULL AND c.ContactId IS NULL) AS orphan_supplier_contacts,
              (SELECT COUNT_BIG(*) FROM dbo.Personnel x LEFT JOIN dbo.Contact c
                 ON c.ContactId=x.ContactId WHERE c.ContactId IS NULL) AS orphan_personnel_contacts,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN GNR.tblCust p
                 ON p.ID=x.ParentCustomerId WHERE x.ParentCustomerId IS NOT NULL AND p.ID IS NULL) AS orphan_parent_customers,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust WHERE ParentCustomerId=ID) AS self_parent_customers,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN SLE.tblCustCtgrSle c
                 ON c.ID=x.CustCtgrRef WHERE c.ID IS NULL) AS orphan_customer_categories,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN GNR.tblCustAct a
                 ON a.ID=x.CustActRef WHERE x.CustActRef IS NOT NULL AND a.ID IS NULL) AS orphan_customer_activities,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN GNR.tblCustlevel l
                 ON l.ID=x.CustLevelRef WHERE x.CustLevelRef IS NOT NULL AND l.ID IS NULL) AS orphan_customer_levels,
              (SELECT COUNT_BIG(*) FROM GNR.tblCust x LEFT JOIN GNR.tblCustGroup g
                 ON g.ID=x.CustGroupRef WHERE x.CustGroupRef IS NOT NULL AND g.ID IS NULL) AS orphan_customer_groups,
              (SELECT COUNT_BIG(*) FROM GNR.tblCustMainSubType x LEFT JOIN GNR.tblCust c
                 ON c.ID=x.CustRef WHERE c.ID IS NULL) AS orphan_customer_classifications,
              (SELECT COUNT_BIG(*) FROM GNR.tblCustMainSubType x LEFT JOIN GNR.tblMainCustType m
                 ON m.ID=x.MainTypeRef WHERE m.ID IS NULL) AS orphan_customer_main_types,
              (SELECT COUNT_BIG(*) FROM GNR.tblCustMainSubType x LEFT JOIN GNR.tblSubCustType s
                 ON s.ID=x.SubTypeRef WHERE s.ID IS NULL) AS orphan_customer_sub_types
            """,
        )[0],
        "duplicate_key_groups": _rows(
            cursor,
            """
            SELECT 'customer_code' AS check_name,COUNT_BIG(*) AS duplicate_groups FROM (
              SELECT CustCode FROM GNR.tblCust GROUP BY CustCode HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'customer_guid',COUNT_BIG(*) FROM (
              SELECT CustGUID FROM GNR.tblCust WHERE CustGUID IS NOT NULL GROUP BY CustGUID HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'customer_contact_id',COUNT_BIG(*) FROM (
              SELECT ContactId FROM GNR.tblCust WHERE ContactId IS NOT NULL GROUP BY ContactId HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'supplier_code',COUNT_BIG(*) FROM (
              SELECT SupplierCode FROM GNR.tblSupplier WHERE SupplierCode IS NOT NULL
              GROUP BY SupplierCode HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'personnel_code',COUNT_BIG(*) FROM (
              SELECT PersonnelCode FROM dbo.Personnel GROUP BY PersonnelCode HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'personnel_guid',COUNT_BIG(*) FROM (
              SELECT PersonnelGUID FROM dbo.Personnel WHERE PersonnelGUID IS NOT NULL
              GROUP BY PersonnelGUID HAVING COUNT_BIG(*)>1
            ) d
            UNION ALL SELECT 'customer_classification_triplet',COUNT_BIG(*) FROM (
              SELECT CustRef,MainTypeRef,SubTypeRef FROM GNR.tblCustMainSubType
              GROUP BY CustRef,MainTypeRef,SubTypeRef HAVING COUNT_BIG(*)>1
            ) d
            """,
        ),
        "customer_group_hierarchy": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM GNR.tblCustGroup WHERE ParentRef IS NULL) AS root_groups,
              (SELECT COUNT_BIG(*) FROM GNR.tblCustGroup WHERE NLeft>=NRight) AS invalid_nested_set_bounds,
              (SELECT COUNT_BIG(*) FROM GNR.tblCustGroup c JOIN GNR.tblCustGroup p
                 ON p.ID=c.ParentRef WHERE NOT (p.NLeft<c.NLeft AND p.NRight>c.NRight)) AS parent_interval_mismatches,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT c.ID FROM GNR.tblCustGroup c LEFT JOIN GNR.tblCust x
                   ON x.CustGroupRef=c.ID GROUP BY c.ID HAVING COUNT_BIG(x.ID)=0
               ) d) AS groups_without_direct_customers
            """,
        )[0],
    }


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT s.name AS schema_name,o.name AS object_name,o.type_desc,
               m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='dbo' AND o.name IN ('PDealer','DealerCtgr','CustType'))
           OR (s.name='GNR' AND o.name IN ('vwPersonnel','vwCustStatus','vwCustRegType'))
           OR (s.name='FRU' AND o.name IN ('CustTypeModel','CustRegTypeModel','CustStatusModel'))
        ORDER BY s.name,o.name
        """,
    )


def _semantic_view_counts(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT
            'dbo.PDealer' AS object_name,
            COUNT_BIG(*) AS row_count,
            SUM(CASE WHEN IsActive=1 THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END)
                AS active_role_rows
        FROM dbo.PDealer
        UNION ALL
        SELECT 'GNR.vwPersonnel',COUNT_BIG(*),NULL FROM GNR.vwPersonnel
        """,
    )


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [
            _table_metadata(cursor, item["object"], item["role"])
            for item in DOMAIN_TABLES
        ]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "parties_customers_suppliers_personnel",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate-only party evidence",
                "pii_policy": "no names, addresses, phone values, national IDs, usernames, credentials, hashes, or stamps",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "contact_roles": _contact_role_summary(cursor),
            "customers": _customer_profile(cursor),
            "suppliers": _supplier_profile(cursor),
            "personnel": _personnel_profile(cursor),
            "ngt_customer_crosswalk": _ngt_customer_crosswalk(cursor),
            "business_date_customer_activity": _business_date_customer_activity(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "semantic_view_counts": _semantic_view_counts(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() AS captured_at")[0],
            "evidence_limits": [
                "All party evidence is aggregate-only; raw PII and credential material are intentionally excluded.",
                "Contact flags and actual role-table links are both measured because neither should silently overwrite the other.",
                "DealerRef in sales documents is a personnel role, not a separate dealer person master.",
                "Customer GUID and personnel PrincipalId are cross-system identifiers; numeric IDs are not interchangeable.",
                "Legacy credential fields must not be copied to the replacement; authentication migration requires a separate security contract.",
                "Three-month activity uses Persian business dates and does not expose customer-level rows.",
                "Formal dependencies do not capture dynamic SQL or every UUID and Ref/Id convention.",
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
