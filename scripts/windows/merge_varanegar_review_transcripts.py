"""Replace selected small-model transcript intervals with targeted medium-model evidence."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def overlaps_clip(segment: dict, clips: list[dict]) -> bool:
    start = float(segment["start"])
    end = float(segment["end"])
    for clip in clips:
        clip_start = float(clip["start"])
        clip_end = float(clip["end"])
        if start < clip_end and end > clip_start:
            return True
    return False


def intersects_source_duration(segment: dict, duration_seconds: float) -> bool:
    return float(segment["end"]) > 0 and float(segment["start"]) < duration_seconds


def bounded_times(segment: dict, duration_seconds: float) -> tuple[float, float]:
    return max(0.0, float(segment["start"])), min(duration_seconds, float(segment["end"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-transcript", required=True, type=Path)
    parser.add_argument("--review-transcript", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    base_path = args.base_transcript.resolve()
    review_path = args.review_transcript.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = json.loads(base_path.read_text(encoding="utf-8-sig"))
    review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    if base.get("validation") != "PASS" or review.get("validation") != "PASS":
        raise ValueError("Both transcripts must validate as PASS")
    clips = list(review.get("plan", {}).get("clips", []))
    if not clips:
        raise ValueError("Review transcript has no clip plan")

    duration_seconds = float(base.get("summary", {}).get("duration_seconds") or 0)
    if duration_seconds <= 0:
        raise ValueError("Base transcript has no valid duration")
    raw_base_segments = list(base.get("segments", []))
    raw_review_segments = list(review.get("segments", []))
    base_segments = [item for item in raw_base_segments if intersects_source_duration(item, duration_seconds)]
    review_segments = [item for item in raw_review_segments if intersects_source_duration(item, duration_seconds)]
    kept_base = [item for item in base_segments if not overlaps_clip(item, clips)]
    replaced_base_count = len(base_segments) - len(kept_base)
    merged_segments = []
    for item in kept_base:
        start, end = bounded_times(item, duration_seconds)
        merged_segments.append({
            "start": start,
            "end": end,
            "text": str(item["text"]),
            "source_model": base.get("engine", {}).get("model", "small"),
            "clip_id": None,
        })
    for item in review_segments:
        start, end = bounded_times(item, duration_seconds)
        merged_segments.append({
            "start": start,
            "end": end,
            "text": str(item["text"]),
            "source_model": review.get("engine", {}).get("model", "medium"),
            "clip_id": item.get("clip_id"),
        })
    merged_segments.sort(key=lambda item: (item["start"], item["end"], item["source_model"]))
    validation = "PASS" if merged_segments and review_segments and replaced_base_count > 0 else "FAIL"
    payload = {
        "artifact": "varanegar_training_video_review_merged_transcript",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "source": base.get("source"),
        "base_transcript": str(base_path),
        "review_transcript": str(review_path),
        "engine": {
            "strategy": "small_complete_with_medium_interval_replacement",
            "base_model": base.get("engine", {}).get("model"),
            "review_model": review.get("engine", {}).get("model"),
        },
        "language": base.get("language"),
        "summary": {
            "duration_seconds": duration_seconds,
            "base_segment_count": len(raw_base_segments),
            "base_segments_replaced": replaced_base_count,
            "base_segments_kept": len(kept_base),
            "base_segments_outside_duration_dropped": len(raw_base_segments) - len(base_segments),
            "review_segment_count": len(review_segments),
            "review_segments_outside_duration_dropped": len(raw_review_segments) - len(review_segments),
            "merged_segment_count": len(merged_segments),
            "review_clip_count": len(clips),
        },
        "review_clips": clips,
        "segments": merged_segments,
        "limits": [
            "Medium-model segments replace base segments only inside explicitly planned intervals.",
            "The merged transcript still requires expert checking against audio and UI before canonical use.",
        ],
    }
    json_path = output_dir / "review_merged.transcript.json"
    text_path = output_dir / "review_merged.transcript.txt"
    srt_path = output_dir / "review_merged.transcript.srt"
    write_json(json_path, payload)
    text_path.write_text(
        "\n".join(f"[{timestamp(float(item['start'])).replace(',', '.')}] [{item['source_model']}] {item['text']}" for item in merged_segments) + "\n",
        encoding="utf-8",
    )
    srt_path.write_text(
        "\n\n".join(
            f"{index}\n{timestamp(float(item['start']))} --> {timestamp(float(item['end']))}\n[{item['source_model']}] {item['text']}"
            for index, item in enumerate(merged_segments, 1)
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": validation, "json": str(json_path), **payload["summary"]}, ensure_ascii=True))
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
