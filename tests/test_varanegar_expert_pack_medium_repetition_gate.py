from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "windows"
    / "audit_varanegar_video_expert_pack.py"
)
SPEC = importlib.util.spec_from_file_location("expert_pack_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class MediumRepetitionExpertGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.medium = root / "medium_review.transcript.json"
        self.audit = root / "medium_repetition_audit.json"
        self.medium.write_text(
            json.dumps({"validation": "PASS", "segments": []}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_audit(self, *, validation: str = "PASS", suspicious: int = 0, transcript: Path | None = None) -> None:
        self.audit.write_text(
            json.dumps({
                "artifact": "varanegar_transcript_repetition_audit",
                "validation": validation,
                "transcript": str(transcript or self.medium.resolve()),
                "summary": {"suspicious_run_count": suspicious},
            }),
            encoding="utf-8",
        )

    def test_accepts_fresh_pass_for_exact_medium_transcript(self) -> None:
        self.write_audit()
        self.assertEqual(
            MODULE.validate_medium_repetition_audit(self.audit, self.medium),
            [],
        )

    def test_rejects_suspicious_or_wrong_target(self) -> None:
        self.write_audit(suspicious=1, transcript=self.medium.with_name("other.json"))
        errors = MODULE.validate_medium_repetition_audit(self.audit, self.medium)
        self.assertIn("medium repetition audit reports suspicious runs", errors)
        self.assertIn("medium repetition audit targets a different transcript", errors)

    def test_rejects_audit_older_than_medium(self) -> None:
        self.write_audit()
        audit_time = self.audit.stat().st_mtime_ns
        os.utime(self.medium, ns=(audit_time + 2_000_000_000, audit_time + 2_000_000_000))
        self.assertIn(
            "medium repetition audit is older than the Medium transcript",
            MODULE.validate_medium_repetition_audit(self.audit, self.medium),
        )


class AudioQuestionEvidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.matrix = root / "AUDIO_REVIEW_MATRIX_FA.md"
        self.medium = root / "medium_review.transcript.json"
        self.bundle = root / "audio_question_evidence.json"
        self.matrix.write_text("| AQ01 | question | MR00 | V001 | PENDING |", encoding="utf-8")
        self.medium.write_text(json.dumps({"validation": "PASS"}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_bundle(self, *, question_count: int = 1) -> None:
        self.bundle.write_text(json.dumps({
            "artifact": "varanegar_audio_question_evidence",
            "validation": "PASS",
            "inputs": {
                "matrix": {"path": str(self.matrix.resolve()), "sha256": MODULE.sha256(self.matrix)},
                "transcript": {"path": str(self.medium.resolve()), "sha256": MODULE.sha256(self.medium)},
            },
            "summary": {"question_count": question_count, "error_count": 0},
            "errors": [],
        }), encoding="utf-8")

    def test_accepts_fresh_bundle_with_matching_hashes_and_count(self) -> None:
        self.write_bundle()
        self.assertEqual(
            MODULE.validate_audio_question_evidence(self.bundle, self.matrix, self.medium, 1),
            [],
        )

    def test_rejects_stale_hash_or_question_count(self) -> None:
        self.write_bundle(question_count=2)
        self.matrix.write_text("changed matrix", encoding="utf-8")
        errors = MODULE.validate_audio_question_evidence(self.bundle, self.matrix, self.medium, 1)
        self.assertIn("audio question evidence count does not match visual questions", errors)
        self.assertIn("audio question evidence has stale or mismatched matrix input", errors)


if __name__ == "__main__":
    unittest.main()
