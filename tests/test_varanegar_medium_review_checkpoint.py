from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "windows"
    / "transcribe_varanegar_review_clips.py"
)
SPEC = importlib.util.spec_from_file_location("medium_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class MediumReviewCheckpointTests(unittest.TestCase):
    def test_checkpoint_identity_must_match_all_runtime_inputs(self) -> None:
        source = {"path": "video.mp4", "size_bytes": 10, "mtime_ns": 20}
        checkpoint = {
            "artifact": "varanegar_medium_review_checkpoint",
            "schema_version": 1,
            "source": source,
            "plan": {"sha256": "abc"},
            "engine": {"model": "medium"},
            "language": "fa",
            "segments": [],
        }
        self.assertTrue(MODULE.checkpoint_is_compatible(
            checkpoint,
            source_identity=source,
            plan_digest="abc",
            model="medium",
            language="fa",
        ))
        checkpoint["plan"]["sha256"] = "changed"
        self.assertFalse(MODULE.checkpoint_is_compatible(
            checkpoint,
            source_identity=source,
            plan_digest="abc",
            model="medium",
            language="fa",
        ))

    def test_checkpoint_rejects_malformed_or_non_monotonic_segments(self) -> None:
        source = {"path": "video.mp4", "size_bytes": 10, "mtime_ns": 20}
        checkpoint = {
            "artifact": "varanegar_medium_review_checkpoint",
            "schema_version": 1,
            "source": source,
            "plan": {"sha256": "abc"},
            "engine": {"model": "medium"},
            "language": "fa",
            "segments": [
                {"start": 10.0, "end": 12.0, "text": "first"},
                {"start": 9.0, "end": 13.0, "text": "out of order"},
            ],
        }
        self.assertFalse(MODULE.checkpoint_is_compatible(
            checkpoint,
            source_identity=source,
            plan_digest="abc",
            model="medium",
            language="fa",
        ))

    def test_resume_reprocesses_overlap_and_keeps_only_safe_segments(self) -> None:
        clips = [
            {"id": "MR00", "start": 0.0, "end": 100.0},
            {"id": "MR01", "start": 100.0, "end": 200.0},
        ]
        segments = [
            {"start": 85.0, "end": 90.0, "text": "safe", "clip_id": "MR00"},
            {"start": 90.0, "end": 96.0, "text": "overlap", "clip_id": "MR00"},
        ]
        reusable, remaining, resume_start = MODULE.prepare_resume(
            clips,
            segments,
            overlap_seconds=5.0,
        )
        self.assertEqual(resume_start, 91.0)
        self.assertEqual([item["text"] for item in reusable], ["safe"])
        self.assertEqual(remaining[0]["start"], 91.0)
        self.assertEqual(remaining[0]["end"], 100.0)
        self.assertEqual(remaining[1]["start"], 100.0)

    def test_atomic_json_write_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "checkpoint.json"
            MODULE.write_json(target, {"status": "RUNNING"})
            self.assertTrue(target.is_file())
            self.assertFalse(target.with_name(target.name + ".tmp").exists())
            self.assertIn("RUNNING", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
