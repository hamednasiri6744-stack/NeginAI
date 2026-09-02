"""Audit cross-file consistency and completion state for one Varanegar training video."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_medium_repetition_audit(audit_path: Path, medium_path: Path) -> list[str]:
    errors: list[str] = []
    if not audit_path.is_file() or not medium_path.is_file():
        return errors
    try:
        audit = load_json(audit_path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [f"final PASS has unreadable medium_repetition_audit: {type(exc).__name__}"]
    if audit.get("artifact") != "varanegar_transcript_repetition_audit":
        errors.append("medium repetition audit artifact identity mismatch")
    if audit.get("validation") != "PASS":
        errors.append(f"medium repetition audit must PASS: {audit.get('validation')}")
    if int(audit.get("summary", {}).get("suspicious_run_count", -1)) != 0:
        errors.append("medium repetition audit reports suspicious runs")
    try:
        audited_transcript = Path(str(audit.get("transcript", ""))).resolve()
    except (OSError, ValueError, TypeError):
        audited_transcript = Path()
    if audited_transcript != medium_path.resolve():
        errors.append("medium repetition audit targets a different transcript")
    if audit_path.stat().st_mtime_ns < medium_path.stat().st_mtime_ns:
        errors.append("medium repetition audit is older than the Medium transcript")
    return errors


def validate_audio_question_evidence(bundle_path: Path, matrix_path: Path, medium_path: Path, expected_questions: int) -> list[str]:
    if not bundle_path.is_file() or not matrix_path.is_file() or not medium_path.is_file():
        return []
    try:
        bundle = load_json(bundle_path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [f"final PASS has unreadable audio_question_evidence: {type(exc).__name__}"]
    errors: list[str] = []
    if bundle.get("artifact") != "varanegar_audio_question_evidence" or bundle.get("validation") != "PASS":
        errors.append("audio question evidence identity or validation is invalid")
    summary = bundle.get("summary", {})
    if int(summary.get("question_count", -1)) != expected_questions:
        errors.append("audio question evidence count does not match visual questions")
    if int(summary.get("error_count", -1)) != 0 or list(bundle.get("errors", [])):
        errors.append("audio question evidence contains errors")
    expected_inputs = {
        "matrix": matrix_path,
        "transcript": medium_path,
    }
    for name, target in expected_inputs.items():
        recorded = bundle.get("inputs", {}).get(name, {})
        try:
            recorded_path = Path(str(recorded.get("path", ""))).resolve()
        except (OSError, ValueError, TypeError):
            recorded_path = Path()
        if recorded_path != target.resolve() or recorded.get("sha256") != sha256(target):
            errors.append(f"audio question evidence has stale or mismatched {name} input")
    latest_input = max(matrix_path.stat().st_mtime_ns, medium_path.stat().st_mtime_ns)
    if bundle_path.stat().st_mtime_ns < latest_input:
        errors.append("audio question evidence is older than its inputs")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--stem", required=True)
    parser.add_argument("--video-index", required=True, type=int)
    parser.add_argument("--video-title", required=True)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()

    root = args.artifact_root.resolve()
    review = root / "review_packs" / args.stem
    expert_root = root / "reports" / "expert"
    transcript_root = root / "transcripts"
    paths = {
        "visual_review": review / "visual_review.json",
        "medium_plan": review / "medium_review_plan.json",
        "audio_matrix": review / "AUDIO_REVIEW_MATRIX_FA.md",
        "glossary": review / "GLOSSARY_WORKING_FA.md",
        "delta_matrix": review / "RECONSTRUCTION_DELTA_MATRIX_FA.md",
        "uat_scenarios": review / "UAT_SCENARIOS_FA.md",
        "completion_checklist": review / "expert_completion_checklist.json",
        "expert_json": expert_root / f"{args.stem}_expert_analysis.json",
        "expert_markdown": expert_root / f"{args.stem}_expert_analysis_fa.md",
        "working_report": expert_root / f"{args.stem}_expert_analysis_working_fa.md",
        "small_transcript": transcript_root / f"{args.stem}.transcript.json",
        "medium_transcript": review / "medium_review.transcript.json",
        "medium_repetition_audit": review / "medium_repetition_audit.json",
        "audio_question_evidence": review / "audio_question_evidence.json",
        "merged_transcript": review / "review_merged.transcript.json",
        "expert_workbook": review / "expert_review_workbook.json",
    }
    errors: list[str] = []
    warnings: list[str] = []
    required_scaffold = [
        "visual_review", "medium_plan", "audio_matrix", "glossary", "delta_matrix",
        "uat_scenarios", "completion_checklist", "expert_json", "expert_markdown",
        "working_report",
    ]
    for name in required_scaffold:
        if not paths[name].is_file():
            errors.append(f"missing required scaffold: {name} -> {paths[name]}")
    if not args.source.resolve().is_file():
        errors.append(f"source video missing: {args.source}")

    visual = plan = checklist = expert = {}
    if not errors:
        for name, target in (
            ("visual_review", paths["visual_review"]),
            ("medium_plan", paths["medium_plan"]),
            ("completion_checklist", paths["completion_checklist"]),
            ("expert_json", paths["expert_json"]),
        ):
            try:
                value = load_json(target)
                if name == "visual_review":
                    visual = value
                elif name == "medium_plan":
                    plan = value
                elif name == "completion_checklist":
                    checklist = value
                else:
                    expert = value
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {name}: {type(exc).__name__}")

    visual_frames = int(visual.get("scope", {}).get("reviewed_frame_count", 0) or 0)
    visual_observations = len(list(visual.get("verified_visual_observations", [])))
    audio_questions = len(list(visual.get("audio_review_required", [])))
    if visual.get("validation") != "PASS" or visual_frames <= 0 or visual_observations <= 0 or audio_questions <= 0:
        errors.append("visual review must be PASS with non-zero frames, observations and audio questions")

    clips = sorted(list(plan.get("clips", [])), key=lambda item: float(item.get("start", 0)))
    calculated_review_seconds = 0.0
    previous_end = -1.0
    for clip in clips:
        start = float(clip.get("start", -1))
        end = float(clip.get("end", -1))
        if start < 0 or end <= start or start < previous_end:
            errors.append(f"invalid or overlapping Medium clip: {clip.get('id')}")
        calculated_review_seconds += max(0.0, end - start)
        previous_end = end
    declared_review_seconds = float(plan.get("total_review_seconds", 0) or 0)
    if plan.get("validation") != "PASS" or not clips or abs(calculated_review_seconds - declared_review_seconds) > 0.01:
        errors.append("Medium plan validation/count/duration mismatch")

    uat_text = paths["uat_scenarios"].read_text(encoding="utf-8-sig") if paths["uat_scenarios"].is_file() else ""
    uat_ids = sorted(set(re.findall(r"UAT-[A-Z0-9]+(?:-[A-Z0-9]+)+", uat_text)))
    checks = list(checklist.get("checks", []))
    status_counts = {
        "pass": sum(item.get("status") == "PASS" for item in checks),
        "pending": sum(item.get("status") == "PENDING" for item in checks),
        "fail": sum(item.get("status") == "FAIL" for item in checks),
        "not_applicable_with_reason": sum(item.get("status") == "NOT_APPLICABLE_WITH_REASON" for item in checks),
        "critical_pending": sum(item.get("critical") is True and item.get("status") == "PENDING" for item in checks),
        "critical_fail": sum(item.get("critical") is True and item.get("status") == "FAIL" for item in checks),
    }
    summary = checklist.get("summary", {})
    if int(summary.get("total", -1)) != len(checks):
        errors.append("checklist total does not match checks")
    for key, value in status_counts.items():
        if int(summary.get(key, -1)) != value:
            errors.append(f"checklist summary mismatch: {key}")

    expert_summary = expert.get("summary", {})
    expected_pairs = {
        "visual_frames_reviewed": visual_frames,
        "verified_visual_observations": visual_observations,
        "audio_questions_total": audio_questions,
        "medium_clip_count": len(clips),
        "uat_scenarios_designed": len(uat_ids),
    }
    for key, expected in expected_pairs.items():
        if int(expert_summary.get(key, -1)) != expected:
            errors.append(f"expert summary mismatch: {key} expected {expected}")
    if abs(float(expert_summary.get("medium_review_seconds", -1)) - declared_review_seconds) > 0.01:
        errors.append("expert summary mismatch: medium_review_seconds")

    expected_source = args.source.resolve()
    expert_source = expert.get("source", {})
    if (
        int(expert_source.get("video_index", -1)) != args.video_index
        or expert_source.get("title") != args.video_title
        or expert_source.get("output_stem") != args.stem
        or Path(str(expert_source.get("path", ""))).resolve() != expected_source
        or int(expert_source.get("size_bytes", -1)) != expected_source.stat().st_size
    ):
        errors.append("expert source identity metadata mismatch")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(expert_source.get("sha256", ""))):
        errors.append("expert source sha256 is missing or invalid")

    accepted_claims = list(expert.get("accepted_claims", []))
    rejected_claims = list(expert.get("rejected_claims", []))
    unknowns = list(expert.get("unknowns", []))
    chapters = list(expert.get("chapter_status", []))
    evidence_manifest = list(expert.get("evidence_manifest", []))
    structural_counts = {
        "accepted_claim_count": len(accepted_claims),
        "rejected_claim_count": len(rejected_claims),
        "unknown_with_reason_count": len(unknowns),
        "critical_pending_count": status_counts["critical_pending"],
    }
    for key, expected in structural_counts.items():
        if int(expert_summary.get(key, -1)) != expected:
            errors.append(f"expert structural summary mismatch: {key} expected {expected}")
    audio_resolved = int(expert_summary.get("audio_questions_resolved", -1))
    if audio_resolved < 0 or audio_resolved > audio_questions:
        errors.append("expert audio_questions_resolved is outside the valid range")
    for claim in accepted_claims:
        if not str(claim.get("id", "")).strip() or not str(claim.get("statement", "")).strip() or not list(claim.get("evidence", [])):
            errors.append("accepted claim is missing id, statement or evidence")
    for claim in rejected_claims:
        if not str(claim.get("id", "")).strip() or not str(claim.get("statement", "")).strip() or not str(claim.get("reason", "")).strip() or not list(claim.get("evidence", [])):
            errors.append("rejected claim is missing id, statement, reason or evidence")
    for unknown in unknowns:
        if unknown.get("status") not in {"UNKNOWN_WITH_REASON", "NEEDS_UAT", "NOT_APPLICABLE_WITH_REASON"}:
            errors.append(f"unknown has invalid status: {unknown.get('id')}")
        if not str(unknown.get("reason", "")).strip() or not list(unknown.get("next_evidence", [])):
            errors.append(f"unknown is missing reason or next evidence: {unknown.get('id')}")
    if not chapters:
        errors.append("expert report has no chapter status records")
    for chapter in chapters:
        if chapter.get("status") not in {"PASS", "UNKNOWN_WITH_REASON", "NEEDS_UAT"}:
            errors.append(f"chapter has invalid status: {chapter.get('id')}")
        if not str(chapter.get("reason", "")).strip() or not list(chapter.get("primary_clips", [])):
            errors.append(f"chapter is missing reason or primary clips: {chapter.get('id')}")
    if not evidence_manifest:
        errors.append("expert report has no evidence manifest")
    for evidence in evidence_manifest:
        if evidence.get("status") not in {"PASS", "PASS_DESIGN_ONLY", "UNKNOWN_WITH_REASON", "NOT_APPLICABLE_WITH_REASON"}:
            errors.append(f"evidence manifest has invalid status: {evidence.get('kind')}")
        if not str(evidence.get("kind", "")).strip() or not str(evidence.get("path", "")).strip():
            errors.append("evidence manifest entry is missing kind or path")

    expert_validation = expert.get("validation")
    pack_state = "INVALID"
    if expert_validation == "DRAFT":
        pack_state = "DRAFT_CONSISTENT"
        warnings.append("expert pack is internally consistent but remains DRAFT")
        if checklist.get("validation") == "PASS":
            warnings.append("checklist is PASS while expert report remains DRAFT")
    elif expert_validation == "PASS":
        if audio_resolved != audio_questions:
            errors.append("final PASS requires every audio question to be resolved or dispositioned")
        final_json_names = ["small_transcript", "medium_transcript", "medium_repetition_audit", "audio_question_evidence", "merged_transcript", "expert_workbook"]
        for name in final_json_names:
            if not paths[name].is_file():
                errors.append(f"final PASS missing {name}")
                continue
            try:
                payload = load_json(paths[name])
                expected_validation = "DRAFT" if name == "expert_workbook" else "PASS"
                if payload.get("validation") != expected_validation:
                    errors.append(f"final PASS has invalid {name}: {payload.get('validation')}")
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"final PASS has unreadable {name}: {type(exc).__name__}")
        errors.extend(validate_medium_repetition_audit(
            paths["medium_repetition_audit"],
            paths["medium_transcript"],
        ))
        errors.extend(validate_audio_question_evidence(
            paths["audio_question_evidence"],
            paths["audio_matrix"],
            paths["medium_transcript"],
            audio_questions,
        ))
        if checklist.get("validation") != "PASS" or status_counts["pending"] or status_counts["fail"] or status_counts["critical_pending"] or status_counts["critical_fail"]:
            errors.append("final PASS requires a zero-pending, zero-fail PASS checklist")
        markdown = paths["expert_markdown"].read_text(encoding="utf-8-sig") if paths["expert_markdown"].is_file() else ""
        if "DRAFT" in markdown or len(markdown) < 1000:
            errors.append("final PASS markdown is draft or too short")
        if not errors:
            pack_state = "FINAL_PASS"
    else:
        errors.append(f"unsupported expert validation: {expert_validation}")

    manifest = []
    for name, target in sorted(paths.items()):
        if target.is_file():
            manifest.append({
                "name": name,
                "path": str(target),
                "size_bytes": target.stat().st_size,
                "sha256": sha256(target),
                "last_write_time": datetime.fromtimestamp(target.stat().st_mtime).astimezone().isoformat(),
            })

    audit = {
        "artifact": "varanegar_video_expert_pack_audit",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "pack_state": pack_state if not errors else "INVALID",
        "video": {
            "index": args.video_index,
            "title": args.video_title,
            "stem": args.stem,
            "source": str(expected_source),
        },
        "counts": {
            "visual_frames": visual_frames,
            "visual_observations": visual_observations,
            "audio_questions": audio_questions,
            "medium_clips": len(clips),
            "medium_review_seconds": round(calculated_review_seconds, 3),
            "uat_scenarios": len(uat_ids),
            "checklist_total": len(checks),
            **status_counts,
        },
        "errors": errors,
        "warnings": warnings,
        "source_manifest": manifest,
        "limits": [
            "A DRAFT_CONSISTENT result proves internal scaffold consistency, not completion.",
            "FINAL_PASS proves evidence-pack gates only; operational certification still depends on authorized UAT."
        ],
    }
    review.mkdir(parents=True, exist_ok=True)
    json_path = review / "expert_pack_audit.json"
    markdown_path = review / "EXPERT_PACK_AUDIT_FA.md"
    write_json(json_path, audit)
    markdown_path.write_text(
        "# ممیزی بستهٔ کارشناسی\n\n"
        f"- وضعیت ممیزی: **{audit['validation']}**\n"
        f"- وضعیت بسته: **{audit['pack_state']}**\n"
        f"- فریم/مشاهده/پرسش: {visual_frames} / {visual_observations} / {audio_questions}\n"
        f"- کلیپ و زمان Medium: {len(clips)} / {round(calculated_review_seconds, 3)} ثانیه\n"
        f"- سناریوهای UAT: {len(uat_ids)}\n"
        f"- چک‌لیست: {len(checks)} کنترل؛ PASS={status_counts['pass']}؛ Pending={status_counts['pending']}؛ Fail={status_counts['fail']}\n\n"
        "## خطاها\n\n" + ("\n".join(f"- {item}" for item in errors) if errors else "- ندارد") +
        "\n\n## هشدارها\n\n" + ("\n".join(f"- {item}" for item in warnings) if warnings else "- ندارد") + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": audit["validation"], "pack_state": audit["pack_state"], "json": str(json_path), "errors": len(errors)}, ensure_ascii=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
