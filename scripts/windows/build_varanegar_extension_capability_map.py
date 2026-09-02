"""Build capability hints for 32 route-backed types outside the Core catalog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


CAPABILITY_MAP = {
    "VN.SDS.POSSystem.UI.BaseChargeDevice.FormBaseChargeDevice": ("pos.charge_device", ["sales", "integration_migration"]),
    "VN.SDS.POSSystem.UI.InstalmentMethod.FormInstalmentMethod": ("pos.instalment_method", ["sales", "receivables_treasury"]),
    "VN.SDS.POSSystem.UI.InstalmentReceipt.FormInstalmentReceiptList": ("pos.instalment_receipt", ["sales", "receivables_treasury"]),
    "VN.SDS.POSSystem.UI.LinearDiscount.FormLinearDiscount": ("pos.linear_discount", ["sales", "pricing_rules"]),
    "VN.SDS.POSSystem.UI.PChangePanel.FormPChangePanel": ("pos.price_change_panel", ["sales", "pricing_rules"]),
    "VN.SDS.POSSystem.UI.POSBarcodePrint.FormPOSBarcodePrint": ("pos.barcode_print", ["sales", "master_data", "reporting_documents"]),
    "VN.SDS.POSSystem.UI.POSOldPrice.FormPOSOldPrice": ("pos.old_price", ["sales", "pricing_rules"]),
    "VN.SDS.POSSystem.UI.POSSafe.FormPOSSafe": ("pos.safe", ["sales", "receivables_treasury"]),
    "VN.SDS.POSSystem.UI.POSSession.FormPOSSession": ("pos.session", ["sales", "receivables_treasury"]),
    "VN.SDS.POSSystem.UI.POSSetting.FormPOSSetting": ("pos.setting", ["sales", "configuration"]),
    "VN.SDS.POSSystem.UI.PosScale.FormPosScaleList": ("pos.scale", ["sales", "master_data", "integration_migration"]),
    "VN.SDS.POSSystem.UI.Subscriber.FormSubscriber": ("pos.subscriber", ["sales", "master_data"]),
    "VN.SDS.POSSystem.UI.Subscriber.FormSubscriberGroup": ("pos.subscriber_group", ["sales", "master_data"]),
    "VN.SDS.Report.InterFace.Forms.FrmReportSelectingMenu": ("report.dynamic_selector", ["reporting_documents"]),
    "VN.SDS.Setting.UI.ArticleTemplate.FormArticleTemplate": ("configuration.accounting_article_template", ["configuration", "accounting", "reporting_documents"]),
    "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementBuy": ("configuration.final_date_buy", ["configuration", "organization_context", "procurement_payables"]),
    "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementMali": ("configuration.final_date_financial", ["configuration", "organization_context", "accounting"]),
    "VN.SDS.Setting.UI.FinalDateManagement.FormFinalDateManagementTankhah": ("configuration.final_date_petty_cash", ["configuration", "organization_context", "accounting"]),
    "VN.SDS.Setting.UI.GeneralConfig.FormGeneralConfig": ("configuration.general", ["configuration"]),
    "VN.SDS.Setting.UI.StockAccAccess.FormStockAccAccess": ("authorization.stock_accounting_access", ["identity_authorization", "configuration", "inventory", "accounting"]),
    "VN.SDS.Setting.UI.UserSetting.UserSettingDesigning.FormUserSettingDesigning": ("configuration.user_setting_design", ["configuration", "identity_authorization"]),
    "VN.SDS.Setting.UI.WebServiceConfig.FormWebServiceConfig": ("configuration.web_service", ["configuration", "integration_migration"]),
    "VN.SDS.Tablet.UI.CalendarTemplates.FormCalendarTemplateList": ("tablet.calendar_template", ["integration_migration", "sales", "distribution"]),
    "VN.SDS.Tablet.UI.Catalogs.FormCatalogList": ("tablet.catalog", ["integration_migration", "master_data"]),
    "VN.SDS.Tablet.UI.Customers.FormCustomerList": ("tablet.customer", ["integration_migration", "master_data", "sales"]),
    "VN.SDS.Tablet.UI.Dealers.FormDealerList": ("tablet.dealer", ["integration_migration", "master_data", "sales"]),
    "VN.SDS.Tablet.UI.DealersDayPaths.FormDealerDayPathList": ("tablet.dealer_day_path", ["integration_migration", "sales", "distribution"]),
    "VN.SDS.Tablet.UI.ProductGroups.FormProductMainGroupList": ("tablet.product_group", ["integration_migration", "master_data"]),
    "VN.SDS.Tablet.UI.Products.FormProductList": ("tablet.product", ["integration_migration", "master_data"]),
    "VN.SDS.Tablet.UI.VisitPlans.FormVisitPlanList": ("tablet.visit_plan", ["integration_migration", "sales", "distribution"]),
    "VN.SDS.Tablet.UI.VisiteTemplates.FormVisiteTemplatesList": ("tablet.visit_template", ["integration_migration", "sales", "distribution"]),
    "VNMembers.Forms.frmContactList": ("party.contact_selector", ["master_data"]),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolved-routes", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    resolved = _load(args.resolved_routes)
    blueprint = _load(args.blueprint)
    module_ids = {row["id"] for row in blueprint["modules"]}

    route_by_type: dict[str, list[dict[str, Any]]] = {}
    contract_by_type: dict[str, dict[str, Any]] = {}
    assembly_by_type: dict[str, str] = {}
    base_by_type: dict[str, str] = {}
    for route in resolved["routes"]:
        for matched, contract in zip(route["matched_types"], route["matched_type_contracts"]):
            type_name = matched["type"]
            route_by_type.setdefault(type_name, []).append(
                {"menu_id": route["menu_id"], "priority": route["priority"], "root_menu_id": route["root_menu_id"]}
            )
            contract_by_type[type_name] = contract["contract"]
            assembly_by_type[type_name] = matched["assembly"]
            base_by_type[type_name] = matched["base_type"]

    capabilities = []
    module_assignments: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    for type_name in sorted(route_by_type):
        capability, modules = CAPABILITY_MAP[type_name]
        contract = contract_by_type[type_name]
        output_signal_calls = [
            call for call in contract["external_contract_calls"]
            if any(term in call.casefold() for term in ("report", "print", "export", "crystal"))
        ]
        transaction_signal_calls = [
            call for call in contract["external_contract_calls"]
            if any(term in call.casefold() for term in ("transaction.start", "transaction.commit", "transaction.rollback", "transaction.rollBack".casefold()))
        ]
        module_assignments.update(modules)
        family = (
            "POS" if ".POSSystem." in type_name else
            "Tablet" if ".Tablet." in type_name else
            "Setting" if ".Setting." in type_name else
            "Report" if ".Report." in type_name else
            "VNMembers"
        )
        family_counts[family] += 1
        if contract["write_like_methods"]:
            target_treatment = "COMMAND_CONTRACT_REQUIRED_BEFORE_ANY_TARGET_WRITE"
        elif output_signal_calls:
            target_treatment = "QUERY_PREVIEW_EXPORT_OR_DOCUMENT_COMMAND_REVIEW"
        else:
            target_treatment = "READ_SELECTOR_OR_CONTEXT_SURFACE_REVIEW"
        capabilities.append(
            {
                "capability_hint": capability,
                "type": type_name,
                "assembly": assembly_by_type[type_name],
                "base_type": base_by_type[type_name],
                "family": family,
                "route_count": len(route_by_type[type_name]),
                "routes": route_by_type[type_name],
                "target_module_hints_not_final_ownership": modules,
                "target_treatment": target_treatment,
                "evidence": {
                    "method_body_count": contract["method_body_count"],
                    "write_like_method_count": len(contract["write_like_methods"]),
                    "destructive_or_reversing_method_count": len(contract["destructive_or_reversing_methods"]),
                    "validation_method_count": len(contract["validation_methods"]),
                    "permission_method_count": len(contract["permission_methods"]),
                    "external_contract_call_count": contract["external_contract_call_count"],
                    "output_signal_call_count": len(output_signal_calls),
                    "transaction_signal_call_count": len(transaction_signal_calls),
                },
                "mandatory_gates": [
                    "business-owner scope disposition",
                    "server-side capability and data-scope decision",
                    "target command/query contract with deny tests",
                    "idempotency and reconciliation for any material write",
                ],
            }
        )

    errors = []
    if set(route_by_type) != set(CAPABILITY_MAP):
        errors.append("capability mapping coverage mismatch")
    unknown_modules = {module for _, modules in CAPABILITY_MAP.values() for module in modules} - module_ids
    if unknown_modules:
        errors.append("unknown target module hint")
    unresolved_routes = [row for row in resolved["routes"] if row["resolution_status"].startswith("UNRESOLVED")]
    if len(unresolved_routes) != 1 or unresolved_routes[0]["menu_id"] != 20037:
        errors.append("unresolved route checkpoint changed")

    artifact = {
        "artifact": "varanegar_route_backed_extension_capability_map",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_CAPABILITY_DERIVATION_FROM_REDACTED_TARGETED_IL_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "routes_permissions_or_configuration_changed": 0,
            "business_rows_or_identity_grants_persisted": 0,
        },
        "summary": {
            "capability_count": len(capabilities),
            "route_association_count": sum(row["route_count"] for row in capabilities),
            "family_counts": dict(sorted(family_counts.items())),
            "capability_with_write_like_method_count": sum(row["evidence"]["write_like_method_count"] > 0 for row in capabilities),
            "capability_with_destructive_or_reversing_method_count": sum(row["evidence"]["destructive_or_reversing_method_count"] > 0 for row in capabilities),
            "capability_with_validation_method_count": sum(row["evidence"]["validation_method_count"] > 0 for row in capabilities),
            "capability_with_local_permission_method_count": sum(row["evidence"]["permission_method_count"] > 0 for row in capabilities),
            "write_like_method_count": sum(row["evidence"]["write_like_method_count"] for row in capabilities),
            "destructive_or_reversing_method_count": sum(row["evidence"]["destructive_or_reversing_method_count"] for row in capabilities),
            "validation_method_count": sum(row["evidence"]["validation_method_count"] for row in capabilities),
            "permission_method_count": sum(row["evidence"]["permission_method_count"] for row in capabilities),
            "external_contract_call_count": sum(row["evidence"]["external_contract_call_count"] for row in capabilities),
            "unresolved_route_count": len(unresolved_routes),
            "auto_scope_decision_count": 0,
            "validation_error_count": len(errors),
        },
        "target_module_hint_capability_counts": dict(sorted(module_assignments.items())),
        "capabilities": capabilities,
        "unresolved_routes": [{"menu_id": row["menu_id"], "class_name": row["class_name"], "file_name": row["file_name"], "status": row["resolution_status"]} for row in unresolved_routes],
        "limits": [
            "Capability and module values are design hints from names, routes and call evidence; business-owner confirmation is required.",
            "Write-like names do not prove a write occurred and missing permission methods do not prove missing authorization.",
            "No extension capability is in target scope merely because its TypeDef exists in the package.",
        ],
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
