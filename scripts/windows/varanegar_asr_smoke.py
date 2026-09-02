"""Download/load a faster-whisper model and transcribe one short Persian sample."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="medium")
    parser.add_argument("--model-dir", required=True, type=Path)
    args = parser.parse_args()

    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8",
        download_root=str(args.model_dir),
    )
    segment_stream, info = model.transcribe(
        str(args.input),
        language="fa",
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
    )
    segments = [
        {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        }
        for segment in segment_stream
        if segment.text.strip()
    ]
    output = {
        "artifact": "varanegar_asr_installation_smoke_result",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if segments else "FAIL",
        "engine": "faster-whisper",
        "model": args.model,
        "device": "cpu",
        "compute_type": "int8",
        "requested_language": "fa",
        "detected_language": info.language,
        "detected_language_probability": round(info.language_probability, 6),
        "input": {
            "path": str(args.input.resolve()),
            "size_bytes": args.input.stat().st_size,
            "sha256": sha256(args.input),
        },
        "segment_count": len(segments),
        "segments": segments,
        "safety": {
            "network_used_for_model_download_only": True,
            "source_video_modified": False,
            "operational_system_connected": False,
            "operational_data_mutated": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "validation": output["validation"],
                "model": args.model,
                "language": info.language,
                "language_probability": output["detected_language_probability"],
                "segment_count": len(segments),
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if segments else 1


if __name__ == "__main__":
    raise SystemExit(main())
