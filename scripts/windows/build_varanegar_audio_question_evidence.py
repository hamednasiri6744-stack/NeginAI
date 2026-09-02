"""Build a question-to-Medium-clip evidence bundle from the Persian audio matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


QUESTION_ID = re.compile(r"^(?:AQ|Q)\d{1,2}$")
CLIP_ID = re.compile(r"MR\d{2}[A-Z]?")
CLIP_RANGE = re.compile(r"MR(\d{2})\s*[–—-]\s*(?:MR)?(\d{2})")
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def expand_clip_expression(value: str) -> list[str]:
    clips: set[str] = set(CLIP_ID.findall(value))
    for match in CLIP_RANGE.finditer(value):
        start = int(match.group(1))
        end = int(match.group(2))
        if end < start:
            start, end = end, start
        clips.update(f"MR{number:02d}" for number in range(start, end + 1))
    return sorted(clips)


def normalize_question_id(value: str) -> str | None:
    normalized = value.translate(PERSIAN_DIGITS).strip().upper()
    if QUESTION_ID.fullmatch(normalized):
        number = int(re.search(r"\d+", normalized).group())
        return f"AQ{number:02d}"
    if normalized.isdigit():
        return f"AQ{int(normalized):02d}"
    return None


def parse_audio_matrix(text: str) -> list[dict]:
    questions: list[dict] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        question_id = normalize_question_id(columns[0]) if columns else None
        if len(columns) < 5 or question_id is None:
            continue
        questions.append({
            "id": question_id,
            "question": columns[1],
            "clip_expression": columns[2],
            "clip_ids": expand_clip_expression(columns[2]),
            "visual_evidence": columns[3],
            "matrix_status": columns[4],
        })
    return questions


def timestamp(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    matrix_path = args.matrix.resolve()
    transcript_path = args.transcript.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = parse_audio_matrix(matrix_path.read_text(encoding="utf-8-sig"))
    transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    segments = list(transcript.get("segments", []))
    grouped: dict[str, list[dict]] = {}
    for segment in segments:
        clip_id = str(segment.get("clip_id") or "")
        if CLIP_ID.fullmatch(clip_id):
            grouped.setdefault(clip_id, []).append({
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": str(segment.get("text", "")).strip(),
            })

    errors: list[str] = []
    if transcript.get("validation") != "PASS":
        errors.append(f"Medium transcript is not PASS: {transcript.get('validation')}")
    if not questions:
        errors.append("audio matrix contains no AQ rows")
    question_ids = [item["id"] for item in questions]
    if len(question_ids) != len(set(question_ids)):
        errors.append("audio matrix contains duplicate AQ ids")
    for question in questions:
        if not question["clip_ids"]:
            errors.append(f"{question['id']} has no Medium clip mapping")
        missing = [clip_id for clip_id in question["clip_ids"] if not grouped.get(clip_id)]
        if missing:
            errors.append(f"{question['id']} references clips with no transcript segments: {', '.join(missing)}")

    clips = []
    for clip_id in sorted(grouped):
        clip_segments = grouped[clip_id]
        clips.append({
            "id": clip_id,
            "segment_count": len(clip_segments),
            "start_seconds": min(item["start"] for item in clip_segments),
            "end_seconds": max(item["end"] for item in clip_segments),
            "segments": clip_segments,
        })
    payload = {
        "artifact": "varanegar_audio_question_evidence",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "inputs": {
            "matrix": {"path": str(matrix_path), "sha256": sha256(matrix_path)},
            "transcript": {"path": str(transcript_path), "sha256": sha256(transcript_path)},
        },
        "summary": {
            "question_count": len(questions),
            "clip_count": len(clips),
            "segment_count": len(segments),
            "error_count": len(errors),
        },
        "questions": questions,
        "clips": clips,
        "errors": errors,
        "limits": [
            "This bundle groups ASR evidence; it does not decide whether an operational claim is true.",
            "Every AQ row still requires expert disposition and UI/UAT boundaries where applicable.",
        ],
    }
    json_path = output_dir / "audio_question_evidence.json"
    markdown_path = output_dir / "AUDIO_QUESTION_EVIDENCE_FA.md"
    write_json(json_path, payload)
    clip_lookup = {item["id"]: item for item in clips}
    lines = [
        "# بستهٔ شاهد پرسش‌های صوتی",
        "",
        f"- وضعیت: **{payload['validation']}**",
        f"- پرسش‌ها: {len(questions)}",
        f"- کلیپ‌ها: {len(clips)}",
        f"- قطعات Medium: {len(segments)}",
        "",
    ]
    for question in questions:
        lines.extend([f"## {question['id']} — {question['question']}", ""])
        lines.append(f"کلیپ‌ها: {', '.join(question['clip_ids'])}؛ شاهد تصویری: {question['visual_evidence']}")
        lines.append("")
        for clip_id in question["clip_ids"]:
            clip = clip_lookup.get(clip_id)
            if clip is None:
                lines.append(f"- {clip_id}: شاهد متنی موجود نیست.")
                continue
            text = " ".join(item["text"] for item in clip["segments"] if item["text"])
            lines.append(
                f"- {clip_id} ({timestamp(clip['start_seconds'])}–{timestamp(clip['end_seconds'])}، "
                f"{clip['segment_count']} قطعه): {text}"
            )
        lines.extend(["", "وضعیت تصمیم کارشناسی: **PENDING**", ""])
    if errors:
        lines.extend(["## خطاها", "", *(f"- {item}" for item in errors), ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "validation": payload["validation"],
        "questions": len(questions),
        "clips": len(clips),
        "json": str(json_path),
        "markdown": str(markdown_path),
        "errors": len(errors),
    }, ensure_ascii=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
