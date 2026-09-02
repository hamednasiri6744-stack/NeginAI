"""Transcribe one Varanegar training video into JSON, TXT, SRT, and progress evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_resume_checkpoint(
    path: Path,
    source: Path,
    model: str,
    language: str,
    overlap_seconds: float,
) -> dict:
    empty = {
        "resumed": False,
        "resume_start_seconds": 0.0,
        "segments": [],
        "checkpoint_segment_count": 0,
        "reused_segment_count": 0,
        "previous_elapsed_seconds": 0.0,
        "checkpoint_updated_at": None,
        "reason": "checkpoint_missing",
    }
    if not path.is_file():
        return empty
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        identity = payload.get("source", {})
        if payload.get("status") != "INCOMPLETE":
            return {**empty, "reason": "checkpoint_not_incomplete"}
        if int(identity.get("size_bytes", -1)) != source.stat().st_size:
            return {**empty, "reason": "source_size_mismatch"}
        if int(identity.get("mtime_ns", -1)) != source.stat().st_mtime_ns:
            return {**empty, "reason": "source_mtime_mismatch"}
        if payload.get("engine", {}).get("model") != model:
            return {**empty, "reason": "model_mismatch"}
        if payload.get("language", {}).get("requested") != language:
            return {**empty, "reason": "language_mismatch"}
        checkpoint_segments = list(payload.get("segments", []))
        if not checkpoint_segments:
            return {**empty, "reason": "checkpoint_has_no_segments"}
        checkpoint_segments.sort(key=lambda item: (float(item["start"]), float(item["end"])))
        last_end = float(payload.get("summary", {}).get("last_end_seconds", 0))
        candidate_start = max(0.0, last_end - max(0.0, overlap_seconds))
        reusable = [item for item in checkpoint_segments if float(item["end"]) <= candidate_start]
        if not reusable:
            return {**empty, "reason": "checkpoint_too_short_for_safe_overlap"}
        resume_start = float(reusable[-1]["end"])
        if resume_start <= 0:
            return {**empty, "reason": "invalid_resume_start"}
        return {
            "resumed": True,
            "resume_start_seconds": round(resume_start, 3),
            "segments": reusable,
            "checkpoint_segment_count": len(checkpoint_segments),
            "reused_segment_count": len(reusable),
            "previous_elapsed_seconds": float(payload.get("summary", {}).get("elapsed_seconds", 0) or 0),
            "checkpoint_updated_at": payload.get("updated_at"),
            "reason": "checkpoint_valid",
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {**empty, "reason": f"checkpoint_invalid:{type(exc).__name__}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--output-stem", required=True)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--model", default="medium")
    parser.add_argument("--language", default="fa")
    parser.add_argument("--checkpoint-segments", type=int, default=250)
    parser.add_argument("--checkpoint-seconds", type=int, default=300)
    parser.add_argument("--resume-overlap-seconds", type=float, default=5.0)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / f"{args.output_stem}.transcript.json"
    text_path = args.output_dir / f"{args.output_stem}.transcript.txt"
    srt_path = args.output_dir / f"{args.output_stem}.transcript.srt"
    progress_path = args.output_dir / f"{args.output_stem}.progress.json"
    partial_path = args.output_dir / f"{args.output_stem}.transcript.partial.json"

    resume = load_resume_checkpoint(
        partial_path,
        source,
        args.model,
        args.language,
        args.resume_overlap_seconds,
    )
    if args.validate_only:
        print(json.dumps({
            "validation": "PASS",
            "status": "INPUTS_VALID",
            "source": {
                "path": str(source),
                "size_bytes": source.stat().st_size,
                "mtime_ns": source.stat().st_mtime_ns,
            },
            "engine": {"model": args.model, "language": args.language},
            "checkpoint": {
                key: value for key, value in resume.items() if key != "segments"
            },
        }, ensure_ascii=True))
        return 0

    if result_path.is_file():
        existing = json.loads(result_path.read_text(encoding="utf-8-sig"))
        if existing.get("validation") == "PASS" and existing.get("source", {}).get("sha256") == sha256(source):
            print(json.dumps({"validation": "PASS", "status": "ALREADY_COMPLETE", "output": str(result_path)}, ensure_ascii=False))
            return 0

    started_at = datetime.now().astimezone().isoformat()
    started = time.monotonic()
    write_json(progress_path, {
        "status": "STARTING",
        "source": str(source),
        "model": args.model,
        "updated_at": datetime.now().astimezone().isoformat(),
        "started_at": started_at,
        "segment_count": resume["reused_segment_count"],
        "last_end_seconds": resume["resume_start_seconds"],
        "resumed_from_checkpoint": resume["resumed"],
        "resume_reason": resume["reason"],
        "resume_start_seconds": resume["resume_start_seconds"],
    })
    model = WhisperModel(args.model, device="cpu", compute_type="int8", download_root=str(args.model_dir))
    transcribe_options = {
        "language": args.language,
        "beam_size": 5,
        "vad_filter": True,
        "word_timestamps": False,
    }
    if resume["resumed"]:
        transcribe_options["clip_timestamps"] = [resume["resume_start_seconds"]]
        context = " ".join(str(item["text"]) for item in resume["segments"][-8:]).strip()
        if context:
            transcribe_options["initial_prompt"] = context[-800:]
    segment_stream, info = model.transcribe(str(source), **transcribe_options)
    segments: list[dict[str, object]] = list(resume["segments"])
    last_progress = time.monotonic()
    last_checkpoint = time.monotonic()
    for segment in segment_stream:
        text = segment.text.strip()
        if not text:
            continue
        segments.append({"start": round(segment.start, 3), "end": round(segment.end, 3), "text": text})
        now = time.monotonic()
        if len(segments) % 50 == 0 or now - last_progress >= 60:
            last_progress = now
            current_elapsed = now - started
            cumulative_elapsed = resume["previous_elapsed_seconds"] + current_elapsed
            processed_seconds = max(float(segment.end), 0.001)
            running_rtf = cumulative_elapsed / processed_seconds
            write_json(progress_path, {
                "status": "RUNNING",
                "source": str(source),
                "model": args.model,
                "updated_at": datetime.now().astimezone().isoformat(),
                "started_at": started_at,
                "segment_count": len(segments),
                "last_end_seconds": round(segment.end, 3),
                "duration_seconds": round(info.duration, 3),
                "percent": round(min(100, segment.end / info.duration * 100), 3) if info.duration else None,
                "elapsed_seconds_current_run": round(current_elapsed, 3),
                "elapsed_seconds_cumulative": round(cumulative_elapsed, 3),
                "real_time_factor_so_far": round(running_rtf, 6),
                "estimated_remaining_seconds": round(max(0.0, info.duration - segment.end) * running_rtf, 3),
                "resumed_from_checkpoint": resume["resumed"],
                "resume_reason": resume["reason"],
                "resume_start_seconds": resume["resume_start_seconds"],
                "checkpoint_segments_reused": resume["reused_segment_count"],
            })
            print(json.dumps({"segments": len(segments), "last_end_seconds": round(segment.end, 3)}, ensure_ascii=False), flush=True)
        if (
            len(segments) % max(1, args.checkpoint_segments) == 0
            or now - last_checkpoint >= max(30, args.checkpoint_seconds)
        ):
            last_checkpoint = now
            current_elapsed = now - started
            write_json(partial_path, {
                "artifact": "varanegar_training_video_transcript_checkpoint",
                "schema_version": 1,
                "status": "INCOMPLETE",
                "updated_at": datetime.now().astimezone().isoformat(),
                "source": {
                    "path": str(source),
                    "size_bytes": source.stat().st_size,
                    "mtime_ns": source.stat().st_mtime_ns,
                },
                "engine": {"name": "faster-whisper", "model": args.model, "device": "cpu", "compute_type": "int8"},
                "language": {"requested": args.language, "detected": info.language, "probability": round(info.language_probability, 6)},
                "summary": {
                    "duration_seconds": round(info.duration, 3),
                    "segment_count": len(segments),
                    "last_end_seconds": round(segment.end, 3),
                    "elapsed_seconds": round(resume["previous_elapsed_seconds"] + current_elapsed, 3),
                    "elapsed_seconds_current_run": round(current_elapsed, 3),
                    "resumed_from_checkpoint": resume["resumed"],
                    "resume_start_seconds": resume["resume_start_seconds"],
                    "checkpoint_segments_reused": resume["reused_segment_count"],
                },
                "segments": segments,
                "limits": ["Checkpoint is incomplete and must not be treated as a final transcript."],
            })

    elapsed_current_run = round(time.monotonic() - started, 3)
    elapsed = round(resume["previous_elapsed_seconds"] + elapsed_current_run, 3)
    source_digest = sha256(source)
    validation = "PASS" if segments else "FAIL"
    output = {
        "artifact": "varanegar_training_video_transcript",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "source": {"path": str(source), "size_bytes": source.stat().st_size, "sha256": source_digest},
        "engine": {"name": "faster-whisper", "model": args.model, "device": "cpu", "compute_type": "int8"},
        "language": {"requested": args.language, "detected": info.language, "probability": round(info.language_probability, 6)},
        "summary": {
            "duration_seconds": round(info.duration, 3),
            "elapsed_seconds": elapsed,
            "real_time_factor": round(elapsed / info.duration, 6) if info.duration else None,
            "segment_count": len(segments),
            "elapsed_seconds_current_run": elapsed_current_run,
            "resumed_from_checkpoint": resume["resumed"],
            "resume_start_seconds": resume["resume_start_seconds"],
            "checkpoint_segment_count": resume["checkpoint_segment_count"],
            "checkpoint_segments_reused": resume["reused_segment_count"],
        },
        "segments": segments,
        "limits": [
            "Automatic Persian transcription requires visual and domain-term review before becoming canonical knowledge.",
            "This transcript is training evidence and does not prove operational execution or business correctness.",
        ],
    }
    write_json(result_path, output)
    text_path.write_text("\n".join(str(item["text"]) for item in segments) + "\n", encoding="utf-8")
    srt_path.write_text(
        "\n\n".join(
            f"{index}\n{timestamp(float(item['start']))} --> {timestamp(float(item['end']))}\n{item['text']}"
            for index, item in enumerate(segments, 1)
        ) + "\n",
        encoding="utf-8",
    )
    write_json(progress_path, {
        "status": "COMPLETE" if validation == "PASS" else "FAILED",
        "source": str(source),
        "model": args.model,
        "updated_at": datetime.now().astimezone().isoformat(),
        "started_at": started_at,
        "segment_count": len(segments),
        "last_end_seconds": segments[-1]["end"] if segments else 0,
        "duration_seconds": round(info.duration, 3),
        "elapsed_seconds": elapsed,
        "elapsed_seconds_current_run": elapsed_current_run,
        "resumed_from_checkpoint": resume["resumed"],
        "resume_start_seconds": resume["resume_start_seconds"],
        "checkpoint_segments_reused": resume["reused_segment_count"],
        "result": str(result_path),
    })
    if partial_path.exists():
        partial_path.unlink()
    print(json.dumps({"validation": validation, **output["summary"], "output": str(result_path)}, ensure_ascii=False), flush=True)
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
