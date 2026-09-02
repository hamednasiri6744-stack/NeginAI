"""Classify Varanegar form metadata into page shapes and ERP domains."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DOMAIN_RULES: tuple[tuple[int, str, tuple[str, ...]], ...] = (
    (14, "payable_cheque", ("pcheque", "chequebook", "pwithdraw", "pcash")),
    (12, "received_cheque", ("rcheque", "retcheque", "chequeunpaid", "cession")),
    (15, "supplier_cardex", ("suppliercardex", "supsettlement", "supplierbalance")),
    (18, "accounting_posting", ("externalvoucher", "accounting", "ledger", "manualvoucher", "createvoucher")),
    (11, "sales_return", ("retsale", "returnsale", "salereturn", "retfactor")),
    (9, "distribution", ("distmanagement", "distribution", "delivery", "undelivered", "followdist")),
    (13, "supplier_purchase", ("porder", "supinvoice", "supplierinvoice", "purchase", "buytoll", "buytype")),
    (16, "authorization", ("permission", "accessnode", "usergroup", "userpermission", "appuser", "role")),
    (17, "configuration", ("config", "setting", "oprdate", "operationdate", "finaldate")),
    (5, "parties", ("customer", "cust", "supplier", "personnel", "dealer", "driver", "distributer")),
    (1, "organization", ("accyear", "saleoffice", "stockdc", "distributioncenter", "fiscalyear")),
    (8, "inventory", ("stockgoods", "cardex", "warehouse", "stock", "goodsexit", "exitexportation", "voucher")),
    (7, "order_sale", ("order", "sale", "invoice", "callcenter", "followvocher", "vocherfollowup", "printbatch")),
    (6, "pricing", ("price", "discount", "prize", "cprice")),
    (4, "product", ("goods", "product", "brand", "batch", "barcode")),
    (3, "units_documents", ("unit", "package", "vouchertype", "healthcode")),
    (2, "geography_routes", ("city", "state", "country", "area", "zone", "route", "distpath")),
    (
        10,
        "collections_payments",
        (
            "receipt",
            "payment",
            "collection",
            "openinvoice",
            "cash",
            "fund",
            "pay",
            "transfer",
            "settlement",
            "guarantee",
            "bankdraft",
            "bankaccount",
            "statement",
            "cheque",
        ),
    ),
)


def _page_shape(type_name: str, base_type: str, methods: set[str]) -> str:
    text = f"{type_name} {base_type}".casefold()
    if any(token in text for token in ("report", "print", "cardex", "statement", "dashboard")):
        return "report_or_analysis"
    if any(token in text for token in ("tracking", "management", "follow", "workflow")):
        return "workflow_or_tracking"
    if "selector" in text or "lookup" in text or re.search(r"formselect(?:or)?", text):
        return "selector"
    if "masterdetail" in text:
        return "master_detail_entry"
    if "dataentry" in text or type_name.casefold().endswith("edit"):
        return "data_entry"
    if "duallist" in text:
        return "dual_list_assignment"
    if "treelist" in text or "treeselector" in text:
        return "tree"
    if "simplelist" in text or type_name.casefold().endswith("list"):
        return "list"
    if "dialog" in text:
        return "dialog"
    if {"NewCommand", "EditCommand", "DeleteCommand"} & methods:
        return "master_crud"
    return "form"


def _domain_matches(type_name: str) -> list[dict[str, Any]]:
    compact = re.sub(r"[^a-z0-9]", "", type_name.casefold())
    tokens = {
        token.casefold()
        for part in re.split(r"[._+]", type_name)
        for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", part)
    }
    matches = []
    for domain_id, domain_name, keywords in DOMAIN_RULES:
        hit = [
            keyword
            for keyword in keywords
            if (keyword in tokens if len(keyword) <= 5 else keyword in compact)
        ]
        if hit:
            matches.append(
                {
                    "domain_id": domain_id,
                    "domain": domain_name,
                    "matched_keywords": hit,
                }
            )
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemblies", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.assemblies.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for assembly in source["assemblies"]:
        for form in assembly["form_candidates"]:
            methods = set(form["methods"])
            domain_matches = _domain_matches(form["type"])
            strong_form_evidence = (
                "InitializeComponent" in methods
                and (
                    "form" in form["base_type"].casefold()
                    or "VNForm" in form["base_type"]
                )
            )
            rows.append(
                {
                    "assembly": assembly["file"],
                    "family": assembly["family"],
                    "type": form["type"],
                    "base_type": form["base_type"],
                    "method_count": form["method_count"],
                    "page_shape": _page_shape(form["type"], form["base_type"], methods),
                    "form_evidence_confidence": "high" if strong_form_evidence else "medium",
                    "domain_matches": domain_matches,
                    "primary_domain_id": domain_matches[0]["domain_id"] if domain_matches else None,
                    "has_report_method": any("report" in method.casefold() or "print" in method.casefold() for method in methods),
                    "has_create_or_save_method": any(method in methods for method in ("NewCommand", "SaveCommand", "InternalNewCommand")),
                    "has_delete_method": any("delete" in method.casefold() for method in methods),
                    "has_permission_method": any("permission" in method.casefold() for method in methods),
                }
            )

    family_counts = Counter(row["family"] for row in rows)
    shape_counts = Counter(row["page_shape"] for row in rows)
    primary_counts = Counter(
        str(row["primary_domain_id"]) if row["primary_domain_id"] is not None else "unmapped"
        for row in rows
    )
    artifact = {
        "artifact": "varanegar_dotnet_form_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": args.assemblies.as_posix(),
        "safety": {
            "mode": "DERIVED_FROM_DOTNET_METADATA_ONLY",
            "assemblies_loaded_or_executed": 0,
            "method_bodies_read": 0,
            "resources_or_user_strings_read": 0,
            "live_ui_actions": 0,
            "database_queries": 0,
        },
        "summary": {
            "form_candidate_count": len(rows),
            "high_confidence_form_count": sum(row["form_evidence_confidence"] == "high" for row in rows),
            "medium_confidence_candidate_count": sum(row["form_evidence_confidence"] == "medium" for row in rows),
            "mapped_primary_domain_count": sum(row["primary_domain_id"] is not None for row in rows),
            "unmapped_count": sum(row["primary_domain_id"] is None for row in rows),
            "report_capable_count": sum(row["has_report_method"] for row in rows),
            "write_capable_count": sum(row["has_create_or_save_method"] or row["has_delete_method"] for row in rows),
            "permission_aware_count": sum(row["has_permission_method"] for row in rows),
            "family_counts": dict(sorted(family_counts.items())),
            "page_shape_counts": dict(sorted(shape_counts.items())),
            "primary_domain_counts": dict(sorted(primary_counts.items())),
        },
        "classification_limits": [
            "Type and method names are capability evidence, not proof that a menu item is enabled for the current user.",
            "Keyword domain mapping is heuristic and may assign adjacent-domain forms to the first matching rule.",
            "A form class can support multiple workflows even when one primary domain is selected for navigation planning.",
        ],
        "forms": sorted(rows, key=lambda row: (row["family"], row["type"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
