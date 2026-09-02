from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "windows"
    / "build_varanegar_audio_question_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("audio_question_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class AudioQuestionEvidenceTests(unittest.TestCase):
    def test_expands_ranges_and_comma_separated_clips(self) -> None:
        self.assertEqual(
            MODULE.expand_clip_expression("MR02C، MR03، MR05–MR07"),
            ["MR02C", "MR03", "MR05", "MR06", "MR07"],
        )

    def test_parses_only_audio_question_table_rows(self) -> None:
        text = """
| شناسه | پرسش | بازه | تصویر | وضعیت |
|---|---|---|---|---|
| AQ01 | پرسش اول | MR00 | V001 | PENDING |
| متن | نامعتبر | MR01 | V002 | PENDING |
| AQ02 | پرسش دوم | MR02–MR04 | V003 | PENDING |
| ۳ | پرسش سوم | MR02B | V004 | PENDING |
"""
        rows = MODULE.parse_audio_matrix(text)
        self.assertEqual([row["id"] for row in rows], ["AQ01", "AQ02", "AQ03"])
        self.assertEqual(rows[1]["clip_ids"], ["MR02", "MR03", "MR04"])
        self.assertEqual(rows[2]["clip_ids"], ["MR02B"])

    def test_atomic_json_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bundle.json"
            MODULE.write_json(target, {"validation": "PASS"})
            self.assertTrue(target.is_file())
            self.assertFalse(target.with_name(target.name + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
