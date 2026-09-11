"""Transcribe selected high-value Varanegar video intervals with one ASR model load."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def clip_for_time(clips: list[dict], seconds: float) -> dict | None:
    for clip in clips:
        if float(clip["start"]) - 1 <= seconds <= float(clip["end"]) + 1:
            return clip
    return None


def reviewed_seconds_through(clips: list[dict], seconds: float) -> float:
    total = 0.0
    for clip in clips:
        start = float(clip["start"])
        end = float(clip["end"])
        if seconds >= end:
            total += end - start
        elif seconds > start:
            total += seconds - start
            break
        else:
            break
    return total


def checkpoint_is_compatible(
    checkpoint: dict,
    *,
    source_identity: dict,
    plan_digest: str,
    model: str,
    language: str,
) -> bool:
    identity_matches = (
        checkpoint.get("artifact") == "varanegar_medium_review_checkpoint"
        and checkpoint.get("schema_version") == 1
        and checkpoint.get("source", {}).get("path") == source_identity["path"]
        and checkpoint.get("source", {}).get("size_bytes") == source_identity["size_bytes"]
        and checkpoint.get("source", {}).get("mtime_ns") == source_identity["mtime_ns"]
        and checkpoint.get("plan", {}).get("sha256") == plan_digest
        and checkpoint.get("engine", {}).get("model") == model
        and checkpoint.get("language") == language
        and isinstance(checkpoint.get("segments"), list)
    )
    if not identity_matches:
        return False
    try:
        if float(checkpoint.get("elapsed_seconds", 0.0) or 0.0) < 0:
            return False
        previous_start = -1.0
        for segment in checkpoint["segments"]:
            if not isinstance(segment, dict):
                return False
            start = float(segment["start"])
            end = float(segment["end"])
            if start < 0 or end < start or start < previous_start:
                return False
            if not str(segment.get("text", "")).strip():
                return False
            previous_start = start
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return True


def prepare_resume(
    clips: list[dict],
    checkpoint_segments: list[dict],
    *,
    overlap_seconds: float = 5.0,
) -> tuple[list[dict], list[dict], float]:
    if not checkpoint_segments:
        return [], clips, float(clips[0]["start"])
    last_end = min(
        max(float(item.get("end", 0.0)) for item in checkpoint_segments),
        float(clips[-1]["end"]),
    )
    containing = clip_for_time(clips, last_end)
    clip_floor = float(containing["start"]) if containing is not None else float(clips[0]["start"])
    resume_start = max(clip_floor, last_end - max(0.0, overlap_seconds))
    reusable = [item for item in checkpoint_segments if float(item.get("end", 0.0)) <= resume_start]
    remaining: list[dict] = []
    for clip in clips:
        start = float(clip["start"])
        end = float(clip["end"])
        if end <= resume_start:
            continue
        item = dict(clip)
        item["start"] = max(start, resume_start)
        remaining.append(item)
    return reusable, remaining, resume_start


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--model", default="medium")
    parser.add_argument("--language", default="fa")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    plan_path = args.plan.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    if not plan_path.is_file():
        raise FileNotFoundError(plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    if plan.get("validation") != "PASS":
        raise ValueError("Review plan must validate as PASS")
    clips = sorted(list(plan.get("clips", [])), key=lambda item: float(item["start"]))
    if not clips:
        raise ValueError("Review plan has no clips")
    previous_end = -1.0
    for clip in clips:
        start = float(clip["start"])
        end = float(clip["end"])
        if start < 0 or end <= start or start < previous_end:
            raise ValueError(f"Invalid or overlapping clip: {clip}")
        previous_end = end

    result_path = output_dir / "medium_review.transcript.json"
    text_path = output_dir / "medium_review.transcript.txt"
    srt_path = output_dir / "medium_review.transcript.srt"
    progress_path = output_dir / "medium_review.progress.json"
    checkpoint_path = output_dir / "medium_review.checkpoint.json"
    plan_digest = sha256_text(plan_path)
    source_identity = {
        "path": str(source),
        "size_bytes": source.stat().st_size,
        "mtime_ns": source.stat().st_mtime_ns,
    }
    total_review_seconds = sum(float(item["end"]) - float(item["start"]) for item in clips)
    if args.validate_only:
        print(json.dumps({
            "validation": "PASS",
            "status": "INPUTS_VALID",
            "source": source_identity,
            "plan": {
                "path": str(plan_path),
                "sha256": plan_digest,
                "clip_count": len(clips),
                "first_start_seconds": float(clips[0]["start"]),
                "last_end_seconds": float(clips[-1]["end"]),
                "total_review_seconds": round(total_review_seconds, 3),
            },
            "engine": {
                "model": args.model,
                "model_directory": str(args.model_dir.resolve()),
                "language": args.language,
            },
        }, ensure_ascii=True))
        return 0

    if result_path.is_file():
        existing = json.loads(result_path.read_text(encoding="utf-8-sig"))
        if (
            existing.get("validation") == "PASS"
            and existing.get("plan", {}).get("sha256") == plan_digest
            and existing.get("source", {}).get("size_bytes") == source_identity["size_bytes"]
            and existing.get("source", {}).get("mtime_ns") == source_identity["mtime_ns"]
            and existing.get("engine", {}).get("model") == args.model
        ):
            print(json.dumps({"validation": "PASS", "status": "ALREADY_COMPLETE", "output": str(result_path)}, ensure_ascii=True))
            return 0

    checkpoint: dict = {}
    if checkpoint_path.is_file():
        try:
            candidate = json.loads(checkpoint_path.read_text(encoding="utf-8-sig"))
            if checkpoint_is_compatible(
                candidate,
                source_identity=source_identity,
                plan_digest=plan_digest,
                model=args.model,
                language=args.language,
            ):
                checkpoint = candidate
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            checkpoint = {}
    previous_segments = list(checkpoint.get("segments", []))
    segments, transcription_clips, resume_start = prepare_resume(clips, previous_segments)
    resumed_from_checkpoint = bool(previous_segments)
    checkpoint_segments_reused = len(segments)
    previous_elapsed = float(checkpoint.get("elapsed_seconds", 0.0) or 0.0)
    clip_timestamps = [
        value
        for item in transcription_clips
        for value in (float(item["start"]), float(item["end"]))
    ]
    initial_prompt = "، ".join(str(term) for term in plan.get("initial_prompt_terms", [])) or None
    started = time.monotonic()
    write_json(progress_path, {
        "status": "STARTING",
        "updated_at": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "plan": str(plan_path),
        "model": args.model,
        "clip_count": len(clips),
        "total_review_seconds": round(total_review_seconds, 3),
        "segment_count": len(segments),
        "resumed_from_checkpoint": resumed_from_checkpoint,
        "checkpoint_segments_reused": checkpoint_segments_reused,
        "resume_start_seconds": round(resume_start, 3),
    })
    # Keep this optional, heavyweight runtime dependency out of module import
    # so checkpoint/resume validation can run in the ordinary application test
    # environment without installing the local ASR stack.
    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cpu", compute_type="int8", download_root=str(args.model_dir))
    # Do not duplicate initial_prompt as hotwords: faster-whisper can reserve
    # half of the 448-token decoder context for each and overflow the model.
    stream, info = model.transcribe(
        str(source),
        language=args.language,
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
        clip_timestamps=clip_timestamps,
        initial_prompt=initial_prompt,
    )
    seen_clips: set[str] = {
        str(item["clip_id"])
        for item in segments
        if item.get("clip_id")
    }
    last_progress = time.monotonic()
    for segment in stream:
        text = segment.text.strip()
        if not text:
            continue
        clip = clip_for_time(clips, float(segment.start))
        clip_id = None if clip is None else str(clip["id"])
        if clip_id:
            seen_clips.add(clip_id)
        segments.append({
            "start": round(float(segment.start), 3),
            "end": round(float(segment.end), 3),
            "text": text,
            "clip_id": clip_id,
        })
        now = time.monotonic()
        if len(segments) % 25 == 0 or now - last_progress >= 60:
            last_progress = now
            reviewed = reviewed_seconds_through(clips, float(segment.end))
            elapsed_so_far = round(previous_elapsed + now - started, 3)
            write_json(checkpoint_path, {
                "artifact": "varanegar_medium_review_checkpoint",
                "schema_version": 1,
                "status": "RUNNING",
                "updated_at": datetime.now().astimezone().isoformat(),
                "source": source_identity,
                "plan": {"path": str(plan_path), "sha256": plan_digest},
                "engine": {"model": args.model},
                "language": args.language,
                "elapsed_seconds": elapsed_so_far,
                "last_end_seconds": round(float(segment.end), 3),
                "segments": segments,
            })
            write_json(progress_path, {
                "status": "RUNNING",
                "updated_at": datetime.now().astimezone().isoformat(),
                "source": str(source),
                "plan": str(plan_path),
                "model": args.model,
                "clip_count": len(clips),
                "clips_seen": sorted(seen_clips),
                "segment_count": len(segments),
                "last_end_seconds": round(float(segment.end), 3),
                "reviewed_seconds_estimate": round(reviewed, 3),
                "total_review_seconds": round(total_review_seconds, 3),
                "percent": round(min(100.0, reviewed / total_review_seconds * 100), 3),
                "elapsed_seconds": elapsed_so_far,
                "resumed_from_checkpoint": resumed_from_checkpoint,
                "checkpoint_segments_reused": checkpoint_segments_reused,
                "resume_start_seconds": round(resume_start, 3),
            })
            print(json.dumps({"segments": len(segments), "last_end_seconds": round(float(segment.end), 3), "clips_seen": sorted(seen_clips)}, ensure_ascii=True), flush=True)

    elapsed = round(previous_elapsed + time.monotonic() - started, 3)
    validation = "PASS" if segments and seen_clips else "FAIL"
    payload = {
        "artifact": "varanegar_medium_review_transcript",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "source": source_identity,
        "plan": {"path": str(plan_path), "sha256": plan_digest, "clip_count": len(clips), "clips": clips},
        "engine": {"name": "faster-whisper", "model": args.model, "device": "cpu", "compute_type": "int8"},
        "resume": {
            "resumed_from_checkpoint": resumed_from_checkpoint,
            "checkpoint_segments_reused": checkpoint_segments_reused,
            "resume_start_seconds": round(resume_start, 3),
        },
        "language": {"requested": args.language, "detected": info.language, "probability": round(info.language_probability, 6)},
        "summary": {
            "review_seconds": round(total_review_seconds, 3),
            "elapsed_seconds": elapsed,
            "real_time_factor": round(elapsed / total_review_seconds, 6),
            "segment_count": len(segments),
            "clips_with_segments": sorted(seen_clips),
        },
        "segments": segments,
        "limits": [
            "Medium ASR is evidence for expert review and remains non-canonical until checked against audio and UI.",
            "Only intervals listed in the review plan are represented here.",
        ],
    }
    write_json(result_path, payload)
    text_path.write_text(
        "\n".join(f"[{timestamp(float(item['start'])).replace(',', '.')}] [{item['clip_id'] or 'UNMAPPED'}] {item['text']}" for item in segments) + "\n",
        encoding="utf-8",
    )
    srt_path.write_text(
        "\n\n".join(
            f"{index}\n{timestamp(float(item['start']))} --> {timestamp(float(item['end']))}\n[{item['clip_id'] or 'UNMAPPED'}] {item['text']}"
            for index, item in enumerate(segments, 1)
        ) + "\n",
        encoding="utf-8",
    )
    write_json(progress_path, {
        "status": "COMPLETE" if validation == "PASS" else "FAILED",
        "updated_at": datetime.now().astimezone().isoformat(),
        "model": args.model,
        "clip_count": len(clips),
        "clips_seen": sorted(seen_clips),
        "segment_count": len(segments),
        "total_review_seconds": round(total_review_seconds, 3),
        "elapsed_seconds": elapsed,
        "result": str(result_path),
        "resumed_from_checkpoint": resumed_from_checkpoint,
        "checkpoint_segments_reused": checkpoint_segments_reused,
        "resume_start_seconds": round(resume_start, 3),
    })
    write_json(checkpoint_path, {
        "artifact": "varanegar_medium_review_checkpoint",
        "schema_version": 1,
        "status": "COMPLETE" if validation == "PASS" else "FAILED",
        "updated_at": datetime.now().astimezone().isoformat(),
        "source": source_identity,
        "plan": {"path": str(plan_path), "sha256": plan_digest},
        "engine": {"model": args.model},
        "language": args.language,
        "elapsed_seconds": elapsed,
        "last_end_seconds": round(max((float(item["end"]) for item in segments), default=0.0), 3),
        "segments": segments,
        "result": str(result_path),
    })
    print(json.dumps({"validation": validation, "output": str(result_path), **payload["summary"]}, ensure_ascii=True), flush=True)
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
