#!/usr/bin/env python3
"""Read-only compact freshness audit for the Varanegar checkpoint graph."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--root", default=".")
    parser.add_argument("--all-checkpoints", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    queue = deque([args.checkpoint.replace("\\", "/")])
    visited: set[str] = set()
    stale: list[dict[str, object]] = []
    invalid_json: list[str] = []

    json_files = list((root / "artifacts" / "varanegar_analysis").rglob("*.json"))
    parsed: dict[Path, dict[str, object]] = {}
    for candidate in json_files:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                parsed[candidate] = payload
        except (OSError, UnicodeError, json.JSONDecodeError):
            invalid_json.append(candidate.relative_to(root).as_posix())
    if args.all_checkpoints:
        queue.extend(
            candidate.relative_to(root).as_posix()
            for candidate, payload in parsed.items()
            if "_checkpoint_" in candidate.stem and "validation" in payload
        )

    while queue:
        relative = queue.popleft()
        if relative in visited:
            continue
        visited.add(relative)
        checkpoint_path = root / relative
        if not checkpoint_path.is_file():
            stale.append({"path": relative, "reason": "missing_checkpoint"})
            continue
        try:
            payload = json.loads(checkpoint_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            stale.append({"path": relative, "reason": "invalid_checkpoint_json"})
            continue
        if payload.get("validation") != "PASS":
            stale.append({"path": relative, "reason": "checkpoint_not_pass"})
        references = list(payload.get("source_manifest", []))
        previous = payload.get("previous_checkpoint")
        if isinstance(previous, dict) and previous.get("path"):
            references.append(previous)
            queue.append(str(previous["path"]).replace("\\", "/"))
        for item in references:
            target_relative = str(item.get("path", "")).replace("\\", "/")
            target = root / target_relative
            if not target.is_file():
                stale.append({"checkpoint": relative, "path": target_relative, "reason": "missing"})
                continue
            actual_size = target.stat().st_size
            actual_sha = digest(target)
            if item.get("size_bytes") is not None and item["size_bytes"] != actual_size:
                stale.append({"checkpoint": relative, "path": target_relative, "reason": "size"})
            if item.get("sha256") and item["sha256"] != actual_sha:
                stale.append({"checkpoint": relative, "path": target_relative, "reason": "sha256"})

    official_path = root / "artifacts" / "varanegar_analysis" / "varanegar_25h_final_test_result_20260829.json"
    official = json.loads(official_path.read_text(encoding="utf-8-sig"))
    runner = official.get("runner", {})
    seed = root / "artifacts" / "varanegar_analysis" / "varanegar_test_evidence_recovery_seed_20260831.json"
    summary = {
        "validation": "PASS" if not stale and not invalid_json else "FAIL",
        "audit_mode": "ALL_CHECKPOINTS" if args.all_checkpoints else "REACHABLE_FROM_ROOT",
        "json_files": len(json_files),
        "invalid_json": len(invalid_json),
        "reachable_checkpoints": len(visited),
        "stale_references": len(stale),
        "stale_sample": stale[:10],
        "official_test_files": runner.get("test_file_count"),
        "official_passed_tests": runner.get("passed_test_count"),
        "official_bootstrap_exclusions": runner.get("bootstrap_excluded_test_file_count"),
        "recovery_seed_present": seed.exists(),
    }
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0 if summary["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
