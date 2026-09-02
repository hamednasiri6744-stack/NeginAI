"""Classify report, preview, export, print and report-like command surfaces."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _targets(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        target["type"]: target
        for assembly in payload["assemblies"]
        for target in assembly["target_types"]
    }


def _classify(methods: list[dict[str, Any]]) -> tuple[str, dict[str, bool]]:
    method_names = {row["method"] for row in methods}
    calls = {call for row in methods for call in row["calls"]}
    lowered_calls = {call.casefold() for call in calls}
    flags = {
        "has_preview_engine": any("frmpreviewprint" in call for call in lowered_calls),
        "has_print_completion_read": any("get_printedcompleted" in call for call in lowered_calls),
        "has_print_completion_write": any(
            "setprintcompleated" in call or "setlogindrfactforvocherorfactor" in call
            for call in lowered_calls
        ),
        "has_export_to_file": any("exportto" in call or "savefiledialog" in call for call in lowered_calls),
        "has_save_command": "SaveCommand" in method_names or any("typespecrow.savecommand" in call for call in lowered_calls),
        "has_validator": any("validator" in call or "validationresult" in call for call in lowered_calls),
        "has_print_method": any("print" in name.casefold() for name in method_names),
        "has_report_query_call": any(
            any(token in call for token in ("handler.", "adapter."))
            and any(token in call.rsplit(".", 1)[-1] for token in ("Get", "Report", "Cardex", "Refresh", "Load"))
            for call in lowered_calls
        ),
    }
    if flags["has_save_command"]:
        return "report_like_command_form", flags
    if flags["has_print_completion_write"]:
        return "transactional_document_output", flags
    if flags["has_export_to_file"]:
        return "read_report_with_file_export", flags
    if flags["has_report_query_call"]:
        return "interactive_read_report", flags
    if flags["has_preview_engine"] or flags["has_print_method"]:
        return "render_or_preview_shell", flags
    return "selector_dashboard_or_report_shell", flags


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report_payload = _load(args.reports)
    il_payload = _load(args.il)
    targets = _targets(il_payload)
    rows = []
    for report in report_payload["reports"]:
        target = targets[report["type"]]
        classification, flags = _classify(target["methods"])
        completion_calls = sorted(
            {
                call for method in target["methods"] for call in method["calls"]
                if "SetPrintCompleated" in call or "SetLoginDrFactForVocherOrFactor" in call
            }
        )
        query_calls = sorted(
            call for call in report["external_contract_calls"]
            if not any(token in call for token in ("SetPrintCompleated", "SetLoginDrFact", "Validator"))
        )
        permissions = ["report.read"]
        if flags["has_preview_engine"] or flags["has_print_method"]:
            permissions.append("report.preview")
        if flags["has_export_to_file"]:
            permissions.append("report.export_file")
        if flags["has_print_completion_write"]:
            permissions.extend(["document.print", "document.mark_print_completed"])
        if flags["has_save_command"]:
            permissions = ["statement.read", "statement.create_or_update"]
        rows.append(
            {
                "type": report["type"],
                "family": report["family"],
                "primary_domain_id": report["primary_domain_id"],
                "classification": classification,
                "execution_flags": flags,
                "report_methods": report["report_methods"],
                "query_contract_calls": query_calls,
                "filter_contract_calls": report["filter_contract_calls"],
                "query_contract_literals": report["query_contract_literals"],
                "safe_static_ui_labels": report["safe_static_ui_labels"],
                "print_completion_calls": completion_calls,
                "recommended_atomic_permissions": permissions,
                "output_contract": (
                    "Preview is side-effect free. Physical print completion is a distinct idempotent audited command."
                    if flags["has_print_completion_write"] else
                    "Read/render/export must not mutate ERP state; file creation is an external output event."
                    if not flags["has_save_command"] else
                    "This is a stateful statement data-entry aggregate and must not be exposed as a report endpoint."
                ),
            }
        )

    classes = Counter(row["classification"] for row in rows)
    artifact = {
        "artifact": "varanegar_report_preview_export_print_execution_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {
            "report_catalog": args.reports.as_posix(),
            "targeted_il": args.il.as_posix(),
        },
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_TARGETED_IL",
            "database_connections": 0,
            "reports_rendered": 0,
            "prints_or_exports_created": 0,
            "print_completion_commands_executed": 0,
            "live_ui_actions": 0,
            "business_rows_or_values_persisted": 0,
        },
        "summary": {
            "surface_count": len(rows),
            "classification_counts": dict(sorted(classes.items())),
            "transactional_document_output_count": sum(row["execution_flags"]["has_print_completion_write"] for row in rows),
            "file_export_surface_count": sum(row["execution_flags"]["has_export_to_file"] for row in rows),
            "report_like_command_form_count": sum(row["execution_flags"]["has_save_command"] for row in rows),
            "surface_with_filter_contract_count": sum(bool(row["filter_contract_calls"]) for row in rows),
        },
        "erp_output_contract": [
            "Separate report.read, report.preview, report.export_file, document.print and document.mark_print_completed permissions.",
            "Preview never changes business state; print-completed is emitted only after confirmed physical/output completion.",
            "Make print-completed idempotent by document/output-template/version and command_id.",
            "Persist report definition version, filter hash, scope, actor and output event without storing uncontrolled raw result data.",
            "Apply row/data scope at query time and again when opening drill-down routes.",
            "Treat report-like forms with SaveCommand as aggregates, not read-only reports.",
        ],
        "limits": [
            "Call presence proves completion hooks exist but not every branch condition; PrintedCompleted and Preview signals support the separation contract.",
            "File export creates an external artifact even when it does not mutate ERP tables.",
            "No report was run, rendered, printed or exported during this analysis.",
        ],
        "surfaces": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
