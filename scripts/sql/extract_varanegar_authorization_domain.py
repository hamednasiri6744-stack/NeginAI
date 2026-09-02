"""Extract legacy and NGT authorization contracts without identities/secrets.

Read-only by design. The JSON contains schema metadata, aggregate authorization
counts, scope coverage, integrity checks, and selected SQL contracts. It never
persists usernames, names, passwords/hashes, contact details, tokens, API keys,
individual membership rows, or raw per-user grants.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "dbo.AppUser", "role": "legacy_application_user"},
    {"object": "dbo.UserGroup", "role": "legacy_user_group"},
    {"object": "dbo.UserGroupXAppUser", "role": "legacy_user_group_membership"},
    {"object": "dbo.AccessNode", "role": "legacy_permission_tree_node"},
    {"object": "dbo.UserRights", "role": "legacy_direct_node_grant"},
    {"object": "dbo.UserGroupRights", "role": "legacy_group_node_grant"},
    {"object": "dbo.AppUserDC", "role": "legacy_user_dc_scope"},
    {"object": "dbo.UserGroupDC", "role": "legacy_group_dc_scope"},
    {"object": "dbo.AppUserDCSaleOffice", "role": "legacy_user_sale_office_scope"},
    {"object": "dbo.UserGroupDCSaleOffice", "role": "legacy_group_sale_office_scope"},
    {"object": "dbo.AppUserStockDC", "role": "legacy_user_stock_scope_by_operation"},
    {"object": "dbo.UserGroupStockDC", "role": "legacy_group_stock_scope_by_operation"},
    {"object": "GNR.tblCustUserAndGroupAccess", "role": "customer_row_scope"},
    {"object": "GNR.tblStockUserAndGroupAccess", "role": "stock_row_scope"},
    {"object": "GNR.tblSupervisorUserAndGroupAccess", "role": "supervisor_row_scope"},
    {"object": "GNR.tblPaymentUsanceUserAndGroupAccess", "role": "payment_usance_scope"},
    {"object": "GNR.tblManufacturerUserAndGroupAccess", "role": "manufacturer_scope"},
    {"object": "SLE.tblOrderTypeUserAndGroupRight", "role": "order_type_scope"},
    {"object": "NGT.Principals", "role": "ngt_authorization_principal"},
    {"object": "NGT.Roles", "role": "ngt_identity_role"},
    {"object": "NGT.UserRoles", "role": "ngt_user_role_membership"},
    {"object": "NGT.UserGroups", "role": "ngt_user_group"},
    {"object": "NGT.UserGroupUsers", "role": "ngt_user_group_membership"},
    {"object": "NGT.Permissions", "role": "ngt_atomic_permission"},
    {"object": "NGT.PermissionActions", "role": "ngt_permission_action"},
    {"object": "NGT.PermissionCatalogs", "role": "ngt_permission_catalog"},
    {"object": "NGT.PermissionCatalogPermissions", "role": "ngt_catalog_permission_link"},
    {"object": "NGT.PrincipalPermissions", "role": "ngt_principal_atomic_grant"},
    {"object": "NGT.PrincipalPermissionCatalogs", "role": "ngt_principal_catalog_grant"},
)


def _ids() -> str:
    return ",".join(f"OBJECT_ID(N'{x['object']}', 'U')" for x in DOMAIN_TABLES)


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "username", "usernamestr", "name", "fullname", "title", "password",
        "newpassword", "passwordhash", "securitystamp", "email", "phonenumber",
        "lastentryip", "resetsmscode", "resetsmspass", "apikey", "token",
        "appuserid", "sqlusername", "winusername", "hostname", "applicationname",
    }
    result = dict(metadata)
    result["columns"] = [c for c in metadata.get("columns", [])
                         if str(c.get("column_name", "")).lower() not in excluded]
    result["redacted_column_count"] = len(metadata.get("columns", [])) - len(result["columns"])
    return result


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT fk.name constraint_name,
             OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
             OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
             OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
             OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
             fk.delete_referential_action_desc on_delete,
             fk.update_referential_action_desc on_update,fk.is_disabled,fk.is_not_trusted
      FROM sys.foreign_keys fk
      JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
      JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
      JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
      WHERE fk.parent_object_id IN ({ids}) OR fk.referenced_object_id IN ({ids})
      ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,fk.name,fkc.constraint_column_id
    """)


def _consumers(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
             OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
             OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
             OBJECT_NAME(d.referenced_id) source_table,d.is_schema_bound_reference,
             o.modify_date consumer_modify_date
      FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id=d.referencing_id
      WHERE d.referenced_id IN ({ids})
      ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _legacy_identity(cursor: Any) -> dict[str, Any]:
    users = _rows(cursor, """
      SELECT COUNT_BIG(*) users,
             SUM(CASE WHEN IsActive=1 AND ISNULL(IsDeleted,0)=0 THEN 1 ELSE 0 END) active_not_deleted,
             SUM(CASE WHEN IsActive=0 THEN 1 ELSE 0 END) inactive,
             SUM(CASE WHEN IsDeleted=1 THEN 1 ELSE 0 END) deleted,
             SUM(CASE WHEN IsAdmin=1 THEN 1 ELSE 0 END) administrators,
             SUM(CASE WHEN PersonnelId IS NOT NULL THEN 1 ELSE 0 END) personnel_linked,
             SUM(CASE WHEN OpenDC=1 THEN 1 ELSE 0 END) open_all_dc,
             SUM(CASE WHEN OpenDCSaleOffice=1 THEN 1 ELSE 0 END) open_all_sale_office,
             SUM(CASE WHEN OpenStockDC=1 THEN 1 ELSE 0 END) open_all_stock,
             SUM(CASE WHEN AllSupervisor=1 THEN 1 ELSE 0 END) all_supervisor,
             SUM(CASE WHEN AllPersonnel=1 THEN 1 ELSE 0 END) all_personnel,
             SUM(CASE WHEN ShowAllBankAccount=1 THEN 1 ELSE 0 END) show_all_bank_account,
             SUM(CASE WHEN ShowAllSafe=1 THEN 1 ELSE 0 END) show_all_safe
      FROM dbo.AppUser
    """)[0]
    memberships = _rows(cursor, """
      WITH m AS (SELECT AppUserId,COUNT_BIG(*) groups FROM dbo.UserGroupXAppUser GROUP BY AppUserId)
      SELECT (SELECT COUNT_BIG(*) FROM dbo.UserGroup) groups,
             (SELECT COUNT_BIG(*) FROM dbo.UserGroupXAppUser) memberships,
             COUNT_BIG(*) users,
             SUM(CASE WHEN m.AppUserId IS NULL THEN 1 ELSE 0 END) without_group,
             SUM(CASE WHEN m.groups=1 THEN 1 ELSE 0 END) exactly_one_group,
             SUM(CASE WHEN m.groups>1 THEN 1 ELSE 0 END) multiple_groups,
             MAX(ISNULL(m.groups,0)) maximum_groups
      FROM dbo.AppUser u LEFT JOIN m ON m.AppUserId=u.AppUserId
    """)[0]
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupXAppUser x LEFT JOIN dbo.AppUser u ON u.AppUserId=x.AppUserId WHERE u.AppUserId IS NULL) orphan_membership_user,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupXAppUser x LEFT JOIN dbo.UserGroup g ON g.UserGroupId=x.UserGroupId WHERE g.UserGroupId IS NULL) orphan_membership_group,
       (SELECT COUNT_BIG(*) FROM (SELECT AppUserId,UserGroupId FROM dbo.UserGroupXAppUser GROUP BY AppUserId,UserGroupId HAVING COUNT_BIG(*)>1)x) duplicate_membership_pairs
    """)[0]
    return {"user_profile_without_identities": users, "group_membership_profile": memberships,
            "membership_integrity": integrity}


def _access_tree_and_rights(cursor: Any) -> dict[str, Any]:
    tree = _rows(cursor, """
      SELECT COUNT_BIG(*) nodes,
             SUM(CASE WHEN ParentId IS NULL OR ParentId=0 THEN 1 ELSE 0 END) roots,
             SUM(CASE WHEN IsShow=1 THEN 1 ELSE 0 END) shown,
             SUM(CASE WHEN IsUsedInSDS=1 THEN 1 ELSE 0 END) used_in_sds,
             SUM(CASE WHEN IsUsedInFRU=1 THEN 1 ELSE 0 END) used_in_fru,
             SUM(CASE WHEN NULLIF(LTRIM(RTRIM(AccessNodeKey)),'') IS NOT NULL THEN 1 ELSE 0 END) key_present,
             MIN(LevelOfNode) minimum_level,MAX(LevelOfNode) maximum_level,
             SUM(CASE WHEN ParentId=AccessNodeId THEN 1 ELSE 0 END) self_parent
      FROM dbo.AccessNode
    """)[0]
    tree_quality = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.AccessNode n LEFT JOIN dbo.AccessNode p ON p.AccessNodeId=n.ParentId WHERE n.ParentId IS NOT NULL AND n.ParentId<>0 AND p.AccessNodeId IS NULL) orphan_parent,
       (SELECT COUNT_BIG(*) FROM (SELECT ParentId,AccessNodeKey FROM dbo.AccessNode WHERE NULLIF(LTRIM(RTRIM(AccessNodeKey)),'') IS NOT NULL GROUP BY ParentId,AccessNodeKey HAVING COUNT_BIG(*)>1)x) duplicate_sibling_key_groups,
       (SELECT COUNT_BIG(*) FROM (SELECT ParentId,AccessNodeName FROM dbo.AccessNode GROUP BY ParentId,AccessNodeName HAVING COUNT_BIG(*)>1)x) duplicate_sibling_name_groups
    """)[0]
    direct = _rows(cursor, """
      SELECT AccessValue,COUNT_BIG(*) rights,COUNT(DISTINCT AppUserId) users,
             COUNT(DISTINCT AccessNodeId) nodes
      FROM dbo.UserRights GROUP BY AccessValue ORDER BY AccessValue
    """)
    groups = _rows(cursor, """
      SELECT AccessValue,COUNT_BIG(*) rights,COUNT(DISTINCT UserGroupId) groups,
             COUNT(DISTINCT AccessNodeId) nodes
      FROM dbo.UserGroupRights GROUP BY AccessValue ORDER BY AccessValue
    """)
    coverage = _rows(cursor, """
      WITH u AS (SELECT AppUserId,COUNT_BIG(*) rights FROM dbo.UserRights GROUP BY AppUserId),
           g AS (SELECT UserGroupId,COUNT_BIG(*) rights FROM dbo.UserGroupRights GROUP BY UserGroupId)
      SELECT
       (SELECT MIN(rights) FROM u) min_rights_per_user,
       (SELECT MAX(rights) FROM u) max_rights_per_user,
       (SELECT AVG(CONVERT(decimal(18,2),rights)) FROM u) avg_rights_per_user,
       (SELECT MIN(rights) FROM g) min_rights_per_group,
       (SELECT MAX(rights) FROM g) max_rights_per_group,
       (SELECT AVG(CONVERT(decimal(18,2),rights)) FROM g) avg_rights_per_group
    """)[0]
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.UserRights r LEFT JOIN dbo.AppUser u ON u.AppUserId=r.AppUserId WHERE u.AppUserId IS NULL) orphan_direct_user,
       (SELECT COUNT_BIG(*) FROM dbo.UserRights r LEFT JOIN dbo.AccessNode n ON n.AccessNodeId=r.AccessNodeId WHERE n.AccessNodeId IS NULL) orphan_direct_node,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupRights r LEFT JOIN dbo.UserGroup g ON g.UserGroupId=r.UserGroupId WHERE g.UserGroupId IS NULL) orphan_group,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupRights r LEFT JOIN dbo.AccessNode n ON n.AccessNodeId=r.AccessNodeId WHERE n.AccessNodeId IS NULL) orphan_group_node,
       (SELECT COUNT_BIG(*) FROM (SELECT AppUserId,AccessNodeId FROM dbo.UserRights GROUP BY AppUserId,AccessNodeId HAVING COUNT_BIG(*)>1)x) duplicate_direct_pairs,
       (SELECT COUNT_BIG(*) FROM (SELECT UserGroupId,AccessNodeId FROM dbo.UserGroupRights GROUP BY UserGroupId,AccessNodeId HAVING COUNT_BIG(*)>1)x) duplicate_group_pairs,
       (SELECT COUNT_BIG(*) FROM dbo.UserRights WHERE AccessValue NOT IN (0,1,2)) invalid_direct_values,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupRights WHERE AccessValue NOT IN (0,1,2)) invalid_group_values
    """)[0]
    inherited = _rows(cursor, """
      WITH x AS (
       SELECT m.AppUserId,g.AccessNodeId,g.AccessValue group_value,u.AccessValue user_value
       FROM dbo.UserGroupXAppUser m JOIN dbo.UserGroupRights g ON g.UserGroupId=m.UserGroupId
       LEFT JOIN dbo.UserRights u ON u.AppUserId=m.AppUserId AND u.AccessNodeId=g.AccessNodeId
      )
      SELECT COUNT_BIG(*) membership_node_rows,
             SUM(CASE WHEN group_value=1 THEN 1 ELSE 0 END) group_allow_rows,
             SUM(CASE WHEN group_value=2 THEN 1 ELSE 0 END) group_deny_rows,
             SUM(CASE WHEN user_value=1 AND group_value=2 THEN 1 ELSE 0 END) direct_allow_group_deny,
             SUM(CASE WHEN user_value=2 AND group_value=1 THEN 1 ELSE 0 END) direct_deny_group_allow,
             SUM(CASE WHEN user_value IS NULL THEN 1 ELSE 0 END) no_direct_row
      FROM x
    """)[0]
    return {"access_node_tree": tree, "access_node_quality": tree_quality,
            "direct_right_distribution": direct, "group_right_distribution": groups,
            "right_coverage": coverage, "right_integrity": integrity,
            "direct_group_overlap": inherited,
            "effective_contract": (
                "Admin grants immediately. Otherwise direct and group AccessValue=1 are ORed; "
                "any direct or group AccessValue=2 then denies. Value 0 is neutral. Deny wins."
            )}


def _legacy_scope(cursor: Any) -> dict[str, Any]:
    summary = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.AppUserDC) user_dc,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupDC) group_dc,
       (SELECT COUNT_BIG(*) FROM dbo.AppUserDCSaleOffice) user_sale_office,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupDCSaleOffice) group_sale_office,
       (SELECT COUNT_BIG(*) FROM dbo.AppUserStockDC) user_stock,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupStockDC) group_stock,
       (SELECT COUNT_BIG(*) FROM GNR.tblCustUserAndGroupAccess) customer_access,
       (SELECT COUNT_BIG(*) FROM GNR.tblStockUserAndGroupAccess) stock_access,
       (SELECT COUNT_BIG(*) FROM GNR.tblSupervisorUserAndGroupAccess) supervisor_access,
       (SELECT COUNT_BIG(*) FROM GNR.tblPaymentUsanceUserAndGroupAccess) payment_usance_access,
       (SELECT COUNT_BIG(*) FROM GNR.tblManufacturerUserAndGroupAccess) manufacturer_access,
       (SELECT COUNT_BIG(*) FROM SLE.tblOrderTypeUserAndGroupRight) order_type_access
    """)[0]
    stock_flags = _rows(cursor, """
      SELECT 'user' principal_type,COUNT_BIG(*) rows,
             SUM(CASE WHEN forOrder=1 THEN 1 ELSE 0 END) for_order,
             SUM(CASE WHEN forSale=1 THEN 1 ELSE 0 END) for_sale,
             SUM(CASE WHEN forInv=1 THEN 1 ELSE 0 END) for_inventory,
             SUM(CASE WHEN forReport=1 THEN 1 ELSE 0 END) for_report,
             SUM(CASE WHEN forRetSale=1 THEN 1 ELSE 0 END) for_return,
             SUM(CASE WHEN ForRetSaleDist=1 THEN 1 ELSE 0 END) for_distributed_return
      FROM dbo.AppUserStockDC
      UNION ALL
      SELECT 'group',COUNT_BIG(*),SUM(CASE WHEN forOrder=1 THEN 1 ELSE 0 END),
             SUM(CASE WHEN forSale=1 THEN 1 ELSE 0 END),SUM(CASE WHEN forInv=1 THEN 1 ELSE 0 END),
             SUM(CASE WHEN forReport=1 THEN 1 ELSE 0 END),SUM(CASE WHEN forRetSale=1 THEN 1 ELSE 0 END),
             SUM(CASE WHEN ForRetSaleDist=1 THEN 1 ELSE 0 END)
      FROM dbo.UserGroupStockDC
    """)
    return {"scope_table_population": summary, "stock_scope_operation_flags": stock_flags,
            "contract": "Functional permission and data scope are separate. DC, sale-office, stock, customer, supervisor, payment-usance, manufacturer, and order-type scopes must all be preserved."}


def _ngt_authorization(cursor: Any) -> dict[str, Any]:
    identities = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM NGT.Users) users,
       (SELECT COUNT_BIG(*) FROM NGT.Users WHERE IsActive=1 AND IsRemoved=0 AND IsDeactive=0) active_users,
       (SELECT COUNT_BIG(*) FROM NGT.Users WHERE IsRemoved=1) removed_users,
       (SELECT COUNT_BIG(*) FROM NGT.Users WHERE PrincipalId IS NULL) users_without_principal,
       (SELECT COUNT_BIG(*) FROM NGT.Principals) principals,
       (SELECT COUNT_BIG(*) FROM NGT.UserGroups) user_groups,
       (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers) group_memberships,
       (SELECT COUNT_BIG(*) FROM NGT.Roles) roles,
       (SELECT COUNT_BIG(*) FROM NGT.UserRoles) user_roles
    """)[0]
    permissions = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM NGT.Permissions) permissions,
       (SELECT COUNT_BIG(*) FROM NGT.PermissionActions) actions,
       (SELECT COUNT_BIG(*) FROM NGT.PermissionCatalogs) catalogs,
       (SELECT COUNT_BIG(*) FROM NGT.PermissionCatalogPermissions) catalog_permission_links,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions) principal_permission_rows,
       (SELECT SUM(CASE WHEN [Grant]=1 THEN 1 ELSE 0 END) FROM NGT.PrincipalPermissions) atomic_grants,
       (SELECT SUM(CASE WHEN [Grant]=0 THEN 1 ELSE 0 END) FROM NGT.PrincipalPermissions) atomic_denies,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs) principal_catalog_rows,
       (SELECT SUM(CASE WHEN [Grant]=1 THEN 1 ELSE 0 END) FROM NGT.PrincipalPermissionCatalogs) catalog_grants,
       (SELECT SUM(CASE WHEN [Grant]=0 THEN 1 ELSE 0 END) FROM NGT.PrincipalPermissionCatalogs) catalog_denies
    """)[0]
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM NGT.UserRoles WHERE IdentityRole_Id IS NULL) formal_identity_role_ref_unused,
       (SELECT COUNT_BIG(*) FROM NGT.UserRoles r LEFT JOIN NGT.Roles x ON x.Id=r.RoleId WHERE x.Id IS NULL) implicit_role_id_without_role,
       (SELECT COUNT_BIG(*) FROM NGT.UserRoles r LEFT JOIN NGT.Users u ON u.Id=r.UserId WHERE u.Id IS NULL) role_subject_not_user_rows,
       (SELECT COUNT_BIG(*) FROM NGT.UserRoles r LEFT JOIN NGT.Users u ON u.Id=r.UserId JOIN NGT.Principals p ON p.Id=r.UserId WHERE u.Id IS NULL) role_subject_matches_principal,
       (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.Users u ON u.Id=m.UserId WHERE u.Id IS NULL) group_membership_subject_not_user,
       (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.Users u ON u.Id=m.UserId JOIN NGT.Principals p ON p.Id=m.UserId WHERE u.Id IS NULL) group_membership_subject_matches_principal,
       (SELECT COUNT_BIG(*) FROM NGT.UserGroupUsers m LEFT JOIN NGT.UserGroups g ON g.Id=m.UserGroupId WHERE g.Id IS NULL) group_membership_without_group,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions x LEFT JOIN NGT.Principals p ON p.Id=x.PrincipalId WHERE p.Id IS NULL) atomic_grant_without_principal,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions x LEFT JOIN NGT.Permissions p ON p.Id=x.Permission_Id WHERE p.Id IS NULL) atomic_grant_without_permission,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs x LEFT JOIN NGT.Principals p ON p.Id=x.PrincipalId WHERE p.Id IS NULL) catalog_grant_without_principal,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs x LEFT JOIN NGT.PermissionCatalogs p ON p.Id=x.PermissionCatalog_Id WHERE p.Id IS NULL) catalog_grant_without_catalog,
       (SELECT COUNT_BIG(*) FROM (SELECT UserId,IdentityRole_Id FROM NGT.UserRoles GROUP BY UserId,IdentityRole_Id HAVING COUNT_BIG(*)>1)x) duplicate_user_role_pairs,
       (SELECT COUNT_BIG(*) FROM (SELECT PrincipalId,Permission_Id FROM NGT.PrincipalPermissions GROUP BY PrincipalId,Permission_Id HAVING COUNT_BIG(*)>1)x) duplicate_atomic_permission_pairs,
       (SELECT COUNT_BIG(*) FROM (SELECT PrincipalId,PermissionCatalog_Id FROM NGT.PrincipalPermissionCatalogs GROUP BY PrincipalId,PermissionCatalog_Id HAVING COUNT_BIG(*)>1)x) duplicate_catalog_permission_pairs,
       (SELECT COUNT_BIG(*) FROM (SELECT PrincipalId,PermissionCatalog_Id FROM NGT.PrincipalPermissionCatalogs GROUP BY PrincipalId,PermissionCatalog_Id HAVING MIN(CONVERT(int,[Grant]))<>MAX(CONVERT(int,[Grant])))x) duplicate_catalog_pairs_with_mixed_direction
    """)[0]
    role_cardinality = _rows(cursor, """
      WITH x AS (SELECT UserId,COUNT_BIG(*) roles FROM NGT.UserRoles GROUP BY UserId)
      SELECT COUNT_BIG(*) users_with_roles,MIN(roles) minimum_roles,MAX(roles) maximum_roles,
             AVG(CONVERT(decimal(18,3),roles)) average_roles
      FROM x
    """)[0]
    return {"identity_and_membership_population": identities,
            "permission_population_and_direction": permissions,
            "reference_and_duplicate_integrity": integrity,
            "role_cardinality": role_cardinality,
            "boundary": "NGT RBAC is a separate principal/role/permission/catalog system. It must not be silently merged with legacy AccessNode rights without an explicit crosswalk."}


def _sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
      SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
             DATALENGTH(m.definition) definition_bytes
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      JOIN sys.sql_modules m ON m.object_id=o.object_id
      WHERE (s.name='dbo' AND o.name IN
        ('GetUsersRightsSByAccessNodeId','GetUsersRightsSByAccessNodeId_MoreThanOne',
         'usp_CheckUserRightsByAccessNodeId','Usp_SDSNET_UserAccessNode',
         'usp_sdsnet_UserRights_Save','usp_sdsnet_UserGroupRights_Save',
         'usp_sdsnet_Pay_CheckUserRights','usp_sdsnet_PChequeChangeStatus_CheckUserRights',
         'usp_sdsnet_RChequeChangeStatus_CheckUserRights',
         'usp_sdsnet_SupInvoice_CheckUserRights','usp_sdsnet_RetSupInvoice_CheckUserRights'))
      ORDER BY s.name,o.name
    """)


def _quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.UserRights WHERE AccessValue NOT IN(0,1,2)) invalid_legacy_direct_values,
       (SELECT COUNT_BIG(*) FROM dbo.UserGroupRights WHERE AccessValue NOT IN(0,1,2)) invalid_legacy_group_values,
       (SELECT COUNT_BIG(*) FROM dbo.AccessNode n LEFT JOIN dbo.AccessNode p ON p.AccessNodeId=n.ParentId WHERE n.ParentId IS NOT NULL AND n.ParentId<>0 AND p.AccessNodeId IS NULL) legacy_orphan_access_parent,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissions x LEFT JOIN NGT.Permissions p ON p.Id=x.Permission_Id WHERE p.Id IS NULL) ngt_orphan_atomic_permission,
       (SELECT COUNT_BIG(*) FROM NGT.PrincipalPermissionCatalogs x LEFT JOIN NGT.PermissionCatalogs p ON p.Id=x.PermissionCatalog_Id WHERE p.Id IS NULL) ngt_orphan_catalog_permission
    """)[0]


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "legacy_and_ngt_authorization",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only metadata and aggregate authorization evidence",
                      "privacy_policy": "no usernames/names/passwords/hashes/contact/token/API-key values, individual membership rows, or raw per-user grants"},
            "safety": {"target_is_local": True, "database_name": safety["database_name"],
                       "updateability": safety["updateability"], "can_select": safety["can_select"],
                       "can_view_definition": safety["can_view_definition"], "can_update": safety["can_update"],
                       "denies_data_writes": safety["denies_data_writes"]},
            "tables": [_public_metadata(_table_metadata(cursor, x["object"], x["role"])) for x in DOMAIN_TABLES],
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _consumers(cursor),
            "legacy_identity": _legacy_identity(cursor),
            "legacy_access_nodes_and_rights": _access_tree_and_rights(cursor),
            "legacy_data_scope": _legacy_scope(cursor),
            "ngt_authorization": _ngt_authorization(cursor),
            "data_quality": _quality(cursor),
            "semantic_contract_sources": _sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "No username, name, password/hash, contact, token, API-key value, individual membership row, or raw per-user grant is persisted.",
                "Legacy functional permission and data scope are separate dimensions.",
                "Legacy deny (AccessValue=2) wins over direct or group allow; admin bypasses node evaluation.",
                "NGT uses a separate role/principal/atomic-permission/catalog model; no legacy-to-NGT crosswalk is established here.",
                "Permission existence does not prove an end-to-end UI route is reachable for a given authenticated user.",
                "Formal dependencies do not capture dynamic SQL or client-side node checks.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(collect(), ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
