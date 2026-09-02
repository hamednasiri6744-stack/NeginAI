"""Build a redacted workflow catalog from form metadata and targeted IL."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


COMMAND_METHOD = re.compile(
    r"(?:Save|Confirm|UnConfirm|Cancel|ChangeStatus|Undo|Follow|Return|Remove|"
    r"Create|Update|Accept|Delete|Set.*Status|DoChange|DoUndo|VocherToSale)",
    re.IGNORECASE,
)
QUERY_METHOD = re.compile(
    r"(?:LoadData|LoadInitData|LoadDetailData|Refresh|ApplyingFilter|GetData|GetAll)",
    re.IGNORECASE,
)
CONTRACT_LITERAL = re.compile(
    r"(?:workflow|status|history|usp|tbl|view|permission|approval|backto|removed|freedist)",
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
    workflow_forms = [
        row for row in forms["forms"] if row["page_shape"] == "workflow_or_tracking"
    ]

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for form in workflow_forms:
        target = il_types.get(form["type"])
        if target is None:
            missing.append(form["type"])
            continue
        methods = target["methods"]
        command_methods = sorted(
            {row["method"] for row in methods if COMMAND_METHOD.search(row["method"])}
        )
        query_methods = sorted(
            {row["method"] for row in methods if QUERY_METHOD.search(row["method"])}
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
        permission_literals = sorted(
            {
                literal["safe_literal"]
                for method in methods
                if "permission" in method["method"].casefold()
                for literal in method["string_literals"]
                if "safe_literal" in literal
            }
        )
        contract_literals = sorted(
            {
                literal["safe_literal"]
                for method in methods
                for literal in method["string_literals"]
                if "safe_literal" in literal
                and CONTRACT_LITERAL.search(literal["safe_literal"])
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
        rows.append(
            {
                "type": form["type"],
                "family": form["family"],
                "primary_domain_id": form["primary_domain_id"],
                "command_methods": command_methods,
                "query_methods": query_methods,
                "external_contract_calls": external_calls,
                "permission_literals": permission_literals,
                "contract_literals": contract_literals,
                "safe_static_ui_labels": ui_labels,
                "evidence": {
                    "method_body_count": len(methods),
                    "has_command": bool(command_methods),
                    "has_query": bool(query_methods),
                    "has_external_contract": bool(external_calls),
                },
            }
        )

    artifact = {
        "artifact": "varanegar_workflow_form_contract_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {"forms": args.forms.as_posix(), "il": args.il.as_posix()},
        "safety": {
            "mode": "DERIVED_FROM_REDACTED_TARGETED_IL",
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "database_queries": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "workflow_form_count": len(workflow_forms),
            "analyzed_count": len(rows),
            "missing_target_count": len(missing),
            "command_method_count": sum(len(row["command_methods"]) for row in rows),
            "external_contract_call_count": sum(len(row["external_contract_calls"]) for row in rows),
            "forms_with_permission_literals": sum(bool(row["permission_literals"]) for row in rows),
            "domain_counts": dict(
                sorted(
                    Counter(
                        str(row["primary_domain_id"])
                        if row["primary_domain_id"] is not None
                        else "unmapped"
                        for row in rows
                    ).items()
                )
            ),
        },
        "limits": [
            "A method name or call edge proves capability presence, not authorization for the current user.",
            "Only static UI labels from InitializeComponent are persisted; runtime row values remain excluded.",
            "Transition ordering still requires SQL workflow and history reconciliation.",
        ],
        "missing_targets": missing,
        "workflows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
