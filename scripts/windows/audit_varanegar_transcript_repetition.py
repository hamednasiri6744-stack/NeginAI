"""Detect long exact-text repetition runs in Varanegar ASR transcripts."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\u0600-\u06ff]+", " ", text.casefold()).strip()


def repeated_runs(segments: list[dict]) -> list[dict]:
    runs: list[dict] = []
    current: list[dict] = []
    current_text: str | None = None

    def finish_run() -> None:
        if not current or current_text is None:
            return
        runs.append({
            "normalized_text": current_text,
            "segment_count": len(current),
            "start_seconds": float(current[0]["start"]),
            "end_seconds": float(current[-1]["end"]),
            "duration_seconds": round(float(current[-1]["end"]) - float(current[0]["start"]), 3),
        })

    for segment in segments:
        normalized = normalize_text(str(segment.get("text", "")))
        if normalized and normalized == current_text:
            current.append(segment)
            continue
        finish_run()
        current = [segment] if normalized else []
        current_text = normalized or None
    finish_run()
    return runs


def suspicious_runs(
    segments: list[dict],
    min_segments: int = 5,
    min_duration_seconds: float = 30.0,
    min_text_chars: int = 8,
) -> list[dict]:
    findings = [
        run for run in repeated_runs(segments)
        if run["segment_count"] >= min_segments
        and run["duration_seconds"] >= min_duration_seconds
        and len(run["normalized_text"]) >= min_text_chars
    ]
    return sorted(findings, key=lambda item: (item["duration_seconds"], item["segment_count"]), reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-segments", type=int, default=5)
    parser.add_argument("--min-duration-seconds", type=float, default=30.0)
    parser.add_argument("--min-text-chars", type=int, default=8)
    args = parser.parse_args()

    transcript_path = args.transcript.resolve()
    transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    segments = list(transcript.get("segments", []))
    findings = suspicious_runs(
        segments,
        min_segments=max(2, args.min_segments),
        min_duration_seconds=max(0.0, args.min_duration_seconds),
        min_text_chars=max(1, args.min_text_chars),
    )
    validation = "FAIL" if findings else "PASS"
    payload = {
        "artifact": "varanegar_transcript_repetition_audit",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "transcript": str(transcript_path),
        "thresholds": {
            "min_segments": max(2, args.min_segments),
            "min_duration_seconds": max(0.0, args.min_duration_seconds),
            "min_text_chars": max(1, args.min_text_chars),
        },
        "summary": {
            "segment_count": len(segments),
            "suspicious_run_count": len(findings),
        },
        "findings": findings[:20],
        "limits": [
            "This audit detects long consecutive exact-text repetitions after normalization.",
            "PASS does not prove semantic transcript accuracy; audio and UI review remain required.",
        ],
    }
    if args.output:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
