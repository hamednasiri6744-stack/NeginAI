"""Select the SQL anchors for distribution-to-exit commands from static evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


COMMANDS = {
    "distribution.create_or_update",
    "distribution.issue_exit",
    "distribution.merge_or_adjust_exit",
    "distribution.remove_exit",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-side-effects", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.command_side_effects.read_text(encoding="utf-8-sig"))
    traces = [row for row in source["command_traces"] if row["command"] in COMMANDS]
    found = {row["command"] for row in traces}
    errors = [f"missing command trace: {command}" for command in sorted(COMMANDS - found)]
    anchors = sorted(
        {name for row in traces for name in row["sql_objects"]}, key=str.casefold
    )
    artifact = {
        "artifact": "varanegar_distribution_to_exit_sql_anchor_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_SELECTION_FROM_REDACTED_COMMAND_SIDE_EFFECT_EVIDENCE",
            "database_connections": 0,
            "application_or_business_commands_executed": 0,
            "row_values_persisted": 0,
        },
        "summary": {
            "selected_command_count": len(traces),
            "sql_object_anchor_count": len(anchors),
            "mutation_command_count": sum(row["mutation_expected"] for row in traces),
            "explicit_idempotency_parameter_observed_count": sum(
                row["explicit_idempotency_parameter_observed"] for row in traces
            ),
            "validation_error_count": len(errors),
        },
        "commands": traces,
        "sql_object_anchors": anchors,
        "validation_errors": errors,
        "limits": [
            "Anchors are static SQL object names; their current runtime execution was not observed.",
            "No command was executed and no operational row value was read or persisted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
