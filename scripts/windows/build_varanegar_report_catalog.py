"""Build a redacted report/query catalog from form metadata and targeted IL."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPORT_METHOD = re.compile(
    r"(?:Report|Print|Export|Preview|Search|Calculate|Refresh|LoadData|LoadInitData|Show)",
    re.IGNORECASE,
)
FILTER_CALL = re.compile(
    r"\.get_.*(?:Date|Ref|Status|Group|Code|Sale|Customer|Cust|Supplier|Goods|Stock|DC|Year|Type|No|Amount)",
    re.IGNORECASE,
)
QUERY_LITERAL = re.compile(
    r"(?:select|usp|view|vw|tbl|report|cardex|statement|invoice|sale|supplier|customer|stock|goods|date|status)",
    re.IGNORECASE,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forms", required=True, type=Path)
    parser.add_argument("--il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    forms = _load(args.forms)
    il = _load(args.il)
    il_types = {
        row["type"]: row
        for assembly in il["assemblies"]
        for row in assembly["target_types"]
        if row["found"]
    }
    report_forms = [
        row for row in forms["forms"] if row["page_shape"] == "report_or_analysis"
    ]
    reports: list[dict[str, Any]] = []
    missing: list[str] = []
    for form in report_forms:
        target = il_types.get(form["type"])
        if target is None:
            missing.append(form["type"])
            continue
        methods = target["methods"]
        report_methods = sorted(
            {row["method"] for row in methods if REPORT_METHOD.search(row["method"])}
        )
        external_calls = sorted(
            {
                call
                for method in methods
                for call in method["calls"]
                if (
                    ".Business." in call
                    or ".DataAccess." in call
                    or call.startswith("TreasuryOld.DataLayer.")
                )
            }
        )
        filter_calls = sorted(
            {
                call
                for method in methods
                for call in method["calls"]
                if FILTER_CALL.search(call)
            }
        )
        query_literals = sorted(
            {
                literal["safe_literal"]
                for method in methods
                for literal in method["string_literals"]
                if "safe_literal" in literal
                and QUERY_LITERAL.search(literal["safe_literal"])
            }
        )
        ui_labels = sorted(
            {
                literal["safe_ui_literal"]
                for method in methods
                if method["method"] == "InitializeComponent"
                for literal in method["string_literals"]
                if "safe_ui_literal" in literal
            }
        )
        reports.append(
            {
                "type": form["type"],
                "family": form["family"],
                "primary_domain_id": form["primary_domain_id"],
                "report_methods": report_methods,
                "external_contract_calls": external_calls,
                "filter_contract_calls": filter_calls,
                "query_contract_literals": query_literals,
                "safe_static_ui_labels": ui_labels,
                "evidence": {
                    "method_body_count": len(methods),
                    "has_report_method": bool(report_methods),
                    "has_external_contract": bool(external_calls),
                    "has_filter_contract": bool(filter_calls),
                },
            }
        )

    artifact = {
        "artifact": "varanegar_report_form_contract_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {"forms": args.forms.as_posix(), "il": args.il.as_posix()},
        "safety": {
            "mode": "DERIVED_FROM_REDACTED_TARGETED_IL",
            "live_ui_actions": 0,
            "reports_executed": 0,
            "exports_created": 0,
            "assemblies_loaded_or_executed": 0,
            "database_queries": 0,
            "raw_report_rows_persisted": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "report_form_count": len(report_forms),
            "analyzed_count": len(reports),
            "missing_target_count": len(missing),
            "report_method_count": sum(len(row["report_methods"]) for row in reports),
            "external_contract_call_count": sum(len(row["external_contract_calls"]) for row in reports),
            "forms_with_filter_contracts": sum(bool(row["filter_contract_calls"]) for row in reports),
            "domain_counts": dict(
                sorted(
                    Counter(
                        str(row["primary_domain_id"])
                        if row["primary_domain_id"] is not None
                        else "unmapped"
                        for row in reports
                    ).items()
                )
            ),
        },
        "limits": [
            "No report was run; row-level output, totals, and production filter defaults are not observed here.",
            "Static call graphs reveal query contracts but not authoritative business metric definitions by themselves.",
            "Export and print capability must remain authorization- and privacy-aware in the destination.",
        ],
        "missing_targets": missing,
        "reports": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
