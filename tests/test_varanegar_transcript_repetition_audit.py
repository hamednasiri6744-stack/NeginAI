from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "windows" / "audit_varanegar_transcript_repetition.py"
SPEC = importlib.util.spec_from_file_location("audit_varanegar_transcript_repetition", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def make_segments(text: str, count: int, seconds_each: float = 10.0) -> list[dict]:
    return [
        {"start": index * seconds_each, "end": (index + 1) * seconds_each, "text": text}
        for index in range(count)
    ]


def test_long_repeated_phrase_is_flagged() -> None:
    findings = AUDIT.suspicious_runs(make_segments("این را دوباره رفرش کنید", 8))

    assert len(findings) == 1
    assert findings[0]["segment_count"] == 8
    assert findings[0]["duration_seconds"] == 80.0


def test_short_filler_is_ignored() -> None:
    assert AUDIT.suspicious_runs(make_segments("خب", 25, 2.0)) == []


def test_varied_transcript_passes() -> None:
    segments = [
        {"start": index * 10.0, "end": (index + 1) * 10.0, "text": f"جمله متفاوت شماره {index}"}
        for index in range(20)
    ]

    assert AUDIT.suspicious_runs(segments) == []
