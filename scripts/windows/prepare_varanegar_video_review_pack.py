"""Build a visual and textual review pack from one completed training transcript."""
from __future__ import annotations

import argparse
import bisect
import json
import math
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path


DOMAIN_TERMS = (
    "کالا",
    "انبار",
    "مشتری",
    "تامین",
    "تأمین",
    "فروشنده",
    "ویزیت",
    "فاکتور",
    "خرید",
    "فروش",
    "بارکد",
    "گروه",
    "برند",
    "مسیر",
    "حساب",
    "ثبت",
    "تعریف",
    "انتخاب",
    "تنظیم",
    "گزارش",
    "تخفیف",
    "قیمت",
    "واحد",
    "موجودی",
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hhmmss(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def closest_segment(segments: list[dict], starts: list[float], target: float) -> dict | None:
    if not segments:
        return None
    index = bisect.bisect_left(starts, target)
    candidates = [position for position in (index - 1, index) if 0 <= position < len(segments)]
    best = min(candidates, key=lambda position: abs(float(segments[position]["start"]) - target))
    low = max(0, best - 1)
    high = min(len(segments), best + 2)
    context = " ".join(str(item["text"]).strip() for item in segments[low:high])
    return {
        "segment_index": best,
        "segment_start": float(segments[best]["start"]),
        "segment_end": float(segments[best]["end"]),
        "context": context,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--interval-seconds", type=int, default=180)
    args = parser.parse_args()

    source = args.source.resolve()
    transcript_path = args.transcript.resolve()
    output_dir = args.output_dir.resolve()
    frames_dir = output_dir / "frames"
    sheets_dir = output_dir / "contact_sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir.mkdir(parents=True, exist_ok=True)

    if not source.is_file():
        raise FileNotFoundError(source)
    if not transcript_path.is_file():
        raise FileNotFoundError(transcript_path)
    transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    if transcript.get("validation") != "PASS":
        raise ValueError("Transcript is not validated as PASS")
    if args.interval_seconds < 30:
        raise ValueError("interval-seconds must be at least 30")

    duration = float(transcript["summary"]["duration_seconds"])
    segments = list(transcript.get("segments", []))
    starts = [float(item["start"]) for item in segments]
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg executable was not found")

    existing_frames = sorted(frames_dir.glob("frame_*.jpg"))
    expected_minimum = max(1, math.floor(duration / args.interval_seconds) - 1)
    frame_command: list[str] | None = None
    if len(existing_frames) < expected_minimum:
        for old_frame in existing_frames:
            old_frame.unlink()
        frame_pattern = str(frames_dir / "frame_%04d.jpg")
        frame_command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"fps=1/{args.interval_seconds},scale=960:-2",
            "-q:v",
            "3",
            frame_pattern,
        ]
        subprocess.run(frame_command, check=True)

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise RuntimeError("No review frames were generated")

    samples: list[dict] = []
    for position, frame in enumerate(frames):
        target = min(duration, position * args.interval_seconds)
        samples.append(
            {
                "sample_index": position + 1,
                "approx_seconds": round(target, 3),
                "timestamp": hhmmss(target),
                "frame": str(frame),
                "transcript_context": closest_segment(segments, starts, target),
            }
        )

    combined_text = "\n".join(str(item.get("text", "")) for item in segments)
    term_counts = Counter({term: combined_text.count(term) for term in DOMAIN_TERMS})
    term_counts = Counter({term: count for term, count in term_counts.items() if count})

    sheet_warning = None
    sheet_count = math.ceil(len(frames) / 12)
    sheet_command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        "1",
        "-start_number",
        "1",
        "-i",
        str(frames_dir / "frame_%04d.jpg"),
        "-vf",
        "scale=480:-2,tile=4x3:padding=6:margin=6:color=black",
        "-frames:v",
        str(sheet_count),
        str(sheets_dir / "sheet_%03d.jpg"),
    ]
    try:
        subprocess.run(sheet_command, check=True)
    except subprocess.CalledProcessError as error:
        sheet_warning = f"Contact-sheet generation failed with exit code {error.returncode}; individual frames remain valid."

    sheet_paths = sorted(sheets_dir.glob("sheet_*.jpg"))
    payload = {
        "artifact": "varanegar_training_video_review_pack",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS",
        "source": str(source),
        "transcript": str(transcript_path),
        "sampling": {
            "interval_seconds": args.interval_seconds,
            "frame_count": len(frames),
            "contact_sheet_count": len(sheet_paths),
            "duration_seconds": duration,
        },
        "domain_term_counts": dict(term_counts.most_common()),
        "samples": samples,
        "contact_sheets": [str(path) for path in sheet_paths],
        "commands": {"frames": frame_command, "contact_sheets": sheet_command},
        "warnings": [sheet_warning] if sheet_warning else [],
        "limits": [
            "Sample timestamps are approximate and intended to accelerate manual visual review.",
            "Automatic term counts and ASR text are not canonical until checked against the video UI and audio.",
        ],
    }
    write_json(output_dir / "review_pack.json", payload)

    rows = []
    for sample in samples:
        context = sample["transcript_context"]
        text = "" if context is None else str(context["context"]).replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {sample['sample_index']} | {sample['timestamp']} | {sample['frame']} | {text} |")
    terms = "، ".join(f"{term}: {count}" for term, count in term_counts.most_common()) or "موردی ثبت نشد"
    markdown = f"""# بستهٔ بازبینی ویدیوی آموزشی ورانگر

- منبع: {source}
- رونویسی: {transcript_path}
- مدت: {hhmmss(duration)}
- فاصلهٔ نمونه‌برداری تصویری: هر {args.interval_seconds} ثانیه
- تعداد تصاویر: {len(frames)}
- تعداد برگه‌های تماس: {len(sheet_paths)}
- فراوانی واژگان منتخب: {terms}

## شاخص زمانی متن و تصویر

| ردیف | زمان تقریبی | تصویر | متن پیرامونیِ رونویسی |
|---:|---:|---|---|
{chr(10).join(rows)}

## وضعیت اعتبار

این بسته ابزار بازبینی است، نه گزارش دانش نهایی. عنوان فرم‌ها، نام فیلدها، ترتیب عملیات و قواعد کسب‌وکار باید با تصویر و صوت کنترل شوند.
"""
    (output_dir / "review_index_fa.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"validation": "PASS", "output": str(output_dir), "frames": len(frames), "sheets": len(sheet_paths)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
