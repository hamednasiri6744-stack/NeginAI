"""Compare two persisted read-only Varanegar UI inventories offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


VOLATILE_KEYS = {"generated_at", "captured_at", "process_id"}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(child) for key, child in sorted(value.items()) if key not in VOLATILE_KEYS}
    if isinstance(value, list):
        normalized = [_stable(child) for child in value]
        return sorted(normalized, key=lambda child: json.dumps(child, ensure_ascii=False, sort_keys=True))
    return value


def _sha(value: Any) -> str:
    raw = json.dumps(_stable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
    current = json.loads(args.current.read_text(encoding="utf-8-sig"))
    sections = ("source", "safety", "summary", "windows", "win32_window_tree", "safe_named_controls")
    section_comparisons = []
    for section in sections:
        before = baseline.get(section)
        after = current.get(section)
        before_sha = _sha(before)
        after_sha = _sha(after)
        section_comparisons.append(
            {
                "section": section,
                "status": "UNCHANGED" if before_sha == after_sha else "CHANGED",
                "baseline_semantic_sha256": before_sha,
                "current_semantic_sha256": after_sha,
            }
        )

    changed = [row["section"] for row in section_comparisons if row["status"] == "CHANGED"]
    baseline_method = baseline.get("source", {}).get("ui_automation_traversal", "LEGACY_DESCENDANTS")
    current_method = current.get("source", {}).get("ui_automation_traversal", "LEGACY_DESCENDANTS")
    observation_method_changed = baseline_method != current_method
    summary_keys = sorted(set(baseline.get("summary", {})) | set(current.get("summary", {})))
    summary_comparison = [
        {
            "metric": key,
            "baseline": baseline.get("summary", {}).get(key),
            "current": current.get("summary", {}).get(key),
            "status": "UNCHANGED" if baseline.get("summary", {}).get(key) == current.get("summary", {}).get(key) else "CHANGED",
        }
        for key in summary_keys
        if key not in {"approved_label_hashes"}
    ]
    errors = []
    if baseline.get("artifact") != "varanegar_windows_ui_inventory" or current.get("artifact") != "varanegar_windows_ui_inventory":
        errors.append("unexpected inventory artifact kind")
    if baseline.get("safety") != current.get("safety"):
        errors.append("safety contract changed")

    artifact = {
        "artifact": "varanegar_read_only_ui_checkpoint_semantic_comparison",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "comparison_status": (
            "OBSERVATION_METHOD_CHANGED"
            if observation_method_changed
            else "NO_SEMANTIC_UI_DRIFT"
            if not changed
            else "SEMANTIC_UI_DRIFT_DETECTED"
        ),
        "safety": {
            "mode": "OFFLINE_COMPARISON_OF_PERSISTED_READ_ONLY_UI_INVENTORIES",
            "live_ui_actions": 0,
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "business_values_or_control_text_added": 0,
        },
        "inputs": {
            "baseline": args.baseline.as_posix(),
            "current": args.current.as_posix(),
            "volatile_keys_ignored": sorted(VOLATILE_KEYS),
            "baseline_ui_automation_traversal": baseline_method,
            "current_ui_automation_traversal": current_method,
        },
        "summary": {
            "compared_section_count": len(section_comparisons),
            "changed_section_count": len(changed),
            "unchanged_section_count": len(section_comparisons) - len(changed),
            "changed_sections": changed,
            "observation_method_changed": observation_method_changed,
            "baseline_top_level_window_count": baseline["summary"]["top_level_window_count"],
            "current_top_level_window_count": current["summary"]["top_level_window_count"],
            "baseline_observed_control_count": baseline["summary"]["observed_control_count"],
            "current_observed_control_count": current["summary"]["observed_control_count"],
            "baseline_safe_named_control_count": baseline["summary"]["safe_named_control_count"],
            "current_safe_named_control_count": current["summary"]["safe_named_control_count"],
            "validation_error_count": len(errors),
        },
        "section_comparisons": section_comparisons,
        "summary_metric_comparisons": summary_comparison,
        "validation_errors": errors,
        "limits": [
            "No-drift means the approved redacted UI inventory stayed equal; it does not prove every role, hidden form or business workflow.",
            "Process identity and capture timestamps are intentionally ignored.",
            "The comparison performs no UI action and cannot prove command behavior.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "comparison_status": artifact["comparison_status"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
