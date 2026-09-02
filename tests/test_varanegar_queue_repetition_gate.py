from __future__ import annotations

import re
import unittest
from pathlib import Path


QUEUE_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "windows"
    / "run_varanegar_training_video_queue.ps1"
)


class QueueRepetitionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = QUEUE_SCRIPT.read_text(encoding="utf-8-sig")

    def test_medium_audit_is_a_required_dependency(self) -> None:
        self.assertIn("$TranscriptRepetitionAuditor =", self.source)
        required_line = next(
            line for line in self.source.splitlines()
            if line.startswith("foreach ($required in @(")
        )
        self.assertIn("$TranscriptRepetitionAuditor", required_line)

    def test_audit_runs_before_merge(self) -> None:
        pipeline = re.search(
            r"function Complete-VideoKnowledgePipeline \{(?P<body>.*?)\n\}",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(pipeline)
        body = pipeline.group("body")
        audit_position = body.index("Run-MediumRepetitionAudit")
        merge_position = body.index("Merge-ReviewTranscripts")
        self.assertLess(audit_position, merge_position)

    def test_completion_paths_require_fresh_pass_audit(self) -> None:
        gate = "Test-PassJsonCurrent -Path $mediumRepetitionAudit"
        self.assertGreaterEqual(self.source.count(gate), 3)
        self.assertIn("MEDIUM_REPETITION_AUDIT_FAILED", self.source)
        self.assertIn("transcript is not eligible for merge", self.source)

    def test_audio_question_evidence_runs_before_merge_and_is_required(self) -> None:
        self.assertIn("$AudioQuestionEvidenceBuilder =", self.source)
        pipeline = re.search(
            r"function Complete-VideoKnowledgePipeline \{(?P<body>.*?)\n\}",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(pipeline)
        body = pipeline.group("body")
        self.assertLess(
            body.index("Build-AudioQuestionEvidence"),
            body.index("Merge-ReviewTranscripts"),
        )
        self.assertGreaterEqual(
            self.source.count("Test-PassJsonCurrent -Path $audioQuestionEvidence"),
            3,
        )


if __name__ == "__main__":
    unittest.main()
