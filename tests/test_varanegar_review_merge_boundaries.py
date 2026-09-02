from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "windows" / "merge_varanegar_review_transcripts.py"
SPEC = importlib.util.spec_from_file_location("merge_varanegar_review_transcripts", SCRIPT)
assert SPEC and SPEC.loader
MERGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MERGE)


def test_interval_overlap_replaces_boundary_crossing_segment() -> None:
    segment = {"start": 9.8, "end": 10.2}
    clips = [{"start": 10.0, "end": 20.0}]

    assert MERGE.overlaps_clip(segment, clips)


def test_segment_completely_after_source_duration_is_rejected() -> None:
    duration = 6082.606
    segment = {"start": 6086.36, "end": 6096.36}

    assert not MERGE.intersects_source_duration(segment, duration)


def test_boundary_segment_is_clamped_to_source_duration() -> None:
    duration = 6082.606
    segment = {"start": 6076.36, "end": 6086.36}

    assert MERGE.intersects_source_duration(segment, duration)
    assert MERGE.bounded_times(segment, duration) == (6076.36, duration)
