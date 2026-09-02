"""Consolidate already-redacted three-month activity blocks across domains.

This tool does not connect to SQL Server. It reads the validated, aggregate-only
domain artifacts and preserves every block whose explicit business-date range
is 1405/03/01 through 1405/05/31, together with its source artifact hash/path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
FROM_DATE = "1405/03/01"
TO_DATE = "1405/05/31"
OMIT_DETAIL_KEYS = {"active_goods"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _windows(value: Any, path: str = "$") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if value.get("from") == FROM_DATE and value.get("to") == TO_DATE:
            yield path, value
            return
        for key, child in value.items():
            yield from _windows(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _windows(child, f"{path}[{index}]")


def _aggregate_copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _aggregate_copy(child) for key, child in value.items()
                if key not in OMIT_DETAIL_KEYS}
    if isinstance(value, list):
        return [_aggregate_copy(child) for child in value]
    return value


def build() -> dict[str, Any]:
    domain_dir = ROOT / "artifacts" / "varanegar_analysis" / "domains"
    sources: list[dict[str, Any]] = []
    total_blocks = 0
    for artifact in sorted(domain_dir.glob("*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        blocks = [{"json_path": path, "aggregate": _aggregate_copy(block)}
                  for path, block in _windows(payload)]
        if not blocks:
            continue
        total_blocks += len(blocks)
        sources.append({
            "domain": payload.get("domain"),
            "source_generated_at": payload.get("generated_at"),
            "artifact": str(artifact.relative_to(ROOT)).replace("\\", "/"),
            "artifact_sha256": _sha256(artifact),
            "window_block_count": len(blocks),
            "window_blocks": blocks,
        })
    source_times = [str(source["source_generated_at"]) for source in sources
                    if source.get("source_generated_at")]
    return {
        "generated_at": max(source_times) if source_times else None,
        "analysis": "varanegar_three_month_operational_activity",
        "business_date_basis": "Persian document/business date; not row creation or catalog modification time",
        "from": FROM_DATE,
        "to": TO_DATE,
        "source_domain_count": len(sources),
        "window_block_count": total_blocks,
        "sources": sources,
        "privacy_policy": "derived only from already-redacted aggregate domain artifacts; no raw rows or identities",
        "counting_note": "counts are domain-specific events and must not be summed into one transaction total",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build()
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(output.resolve())
    print(json.dumps({"source_domain_count": payload["source_domain_count"],
                      "window_block_count": payload["window_block_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
