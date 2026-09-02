"""Reconcile all Varanegar training artifacts into one evidence-based knowledge ledger."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


VIDEOS = (
    (1, "01_base_information_01", "اطلاعات پایه ۱", "اطلاعات پایه 1.mp4"),
    (2, "02_base_information_02", "اطلاعات پایه ۲", "اطلاعات پایه 2.mp4"),
    (3, "03_inventory", "انبار", "انبار.mp4"),
    (4, "04_varanegar_qa", "پرسش و پاسخ ورانگر", "پرسش و پاسخ ورانگر.mp4"),
    (5, "05_tablet_previsit", "تبلت پیش‌ویزیت", "تبلت پیش ویزیت.mp4"),
    (6, "06_tablet_distribution", "تبلت توزیع", "تبلت توزیع.mp4"),
    (7, "07_tablet_supervisor", "تبلت سرپرست", "تبلت سرپرست.mp4"),
    (8, "08_tablet_hot_sale", "تبلت گرم", "تبلت گرم.mp4"),
    (9, "09_tablet_device_settings", "تنظیمات دستگاه تبلت", "تنظیمات دستگاه تبلت.mp4"),
    (10, "10_system_settings", "تنظیمات سیستم", "تنظیمات سیستم.mp4"),
    (11, "11_inventory_purchase_accounting", "حسابداری انبار و خرید", "حسابداری انبار و خرید.mp4"),
    (12, "12_financial_accounting", "حسابداری مالی", "حسابداری مالی.mp4"),
    (13, "13_treasury_01", "خزانه ۱", "خزانه 1.mp4"),
    (14, "14_treasury_02", "خزانه ۲", "خزانه2.mp4"),
    (15, "15_tablet_sales_demo", "دموی تبلت فروش گرم، پیش‌ویزیت و توزیع", "دموی تبلت فروش گرم فروش پیش ویزیت و توزیع.mp4"),
    (16, "16_tracking_grs", "ردیابی و GRS", "ردیابی و GRS.mp4"),
    (17, "17_sales", "فروش", "فروش.mp4"),
    (18, "18_access_control_01", "کنترل دسترسی ۱", "کنترل دسترسی 1.mp4"),
    (19, "19_access_control_02", "کنترل دسترسی ۲", "کنترل دسترسی 2.mp4"),
    (20, "20_ngt_hq_console_01", "کنسول NGT ستاد ۱", "کنسول NGT ستاد 1.mp4"),
    (21, "21_ngt_hq_console_02", "کنسول NGT ستاد ۲", "کنسول NGT ستاد 2.mp4"),
    (22, "22_ngt_branch_console", "کنسول NGT شعب، گرم، سرد و توزیع", "کنسول NGT شعب - گرم - سرد - توزیع.mp4"),
    (23, "23_varanegar_reports", "گزارشات ورانگر", "گزارشات ورانگر.mp4"),
)


def load_pass(path: Path) -> tuple[bool, dict | None, str | None]:
    if not path.is_file():
        return False, None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return False, None, f"invalid_json: {error}"
    if payload.get("validation") != "PASS":
        return False, payload, f"validation={payload.get('validation')}"
    return True, payload, None


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--video-root", required=True, type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    video_root = args.video_root.resolve()
    artifact_root = repo_root / "artifacts" / "varanegar_training_video_analysis"
    transcript_root = artifact_root / "transcripts"
    review_root = artifact_root / "review_packs"
    report_root = artifact_root / "reports"
    expert_root = report_root / "expert"
    expert_root.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for index, stem, title, filename in VIDEOS:
        transcript_path = transcript_root / f"{stem}.transcript.json"
        review_path = review_root / stem / "review_pack.json"
        visual_review_path = review_root / stem / "visual_review.json"
        draft_path = review_root / stem / "analysis_draft.json"
        completion_report = report_root / f"{index:02d}_{stem}_completion_fa.md"
        expert_json = expert_root / f"{stem}_expert_analysis.json"
        expert_markdown = expert_root / f"{stem}_expert_analysis_fa.md"
        transcript_ok, transcript, transcript_error = load_pass(transcript_path)
        review_ok, review, review_error = load_pass(review_path)
        visual_review_ok, visual_review, visual_review_error = load_pass(visual_review_path)
        draft_ok, draft, draft_error = load_pass(draft_path)
        expert_ok, expert, expert_error = load_pass(expert_json)
        source = video_root / filename

        if expert_ok:
            stage = "EXPERT_REVIEW_COMPLETE"
        elif draft_ok:
            stage = "READY_FOR_EXPERT_REVIEW"
        elif review_ok:
            stage = "READY_FOR_DRAFT"
        elif transcript_ok:
            stage = "READY_FOR_VISUAL_REVIEW_PACK"
        else:
            stage = "WAITING_FOR_TRANSCRIPT"
        entry = {
            "index": index,
            "stem": stem,
            "title": title,
            "source": {"path": str(source), "exists": source.is_file(), "size_bytes": source.stat().st_size if source.is_file() else None},
            "stage": stage,
            "transcript": {
                "complete": transcript_ok,
                "path": str(transcript_path),
                "error": transcript_error,
                "segment_count": transcript.get("summary", {}).get("segment_count") if transcript else None,
                "duration_seconds": transcript.get("summary", {}).get("duration_seconds") if transcript else None,
            },
            "review_pack": {
                "complete": review_ok,
                "path": str(review_path),
                "error": review_error,
                "frame_count": review.get("sampling", {}).get("frame_count") if review else None,
                "contact_sheet_count": review.get("sampling", {}).get("contact_sheet_count") if review else None,
            },
            "visual_review": {
                "complete": visual_review_ok,
                "path": str(visual_review_path),
                "error": visual_review_error,
                "reviewed_frame_count": visual_review.get("scope", {}).get("reviewed_frame_count") if visual_review else None,
                "verified_observations": len(visual_review.get("verified_visual_observations", [])) if visual_review else None,
                "audio_review_items": len(visual_review.get("audio_review_required", [])) if visual_review else None,
            },
            "analysis_draft": {
                "complete": draft_ok,
                "path": str(draft_path),
                "error": draft_error,
                "action_candidates": draft.get("summary", {}).get("action_candidate_count") if draft else None,
                "rule_candidates": draft.get("summary", {}).get("rule_candidate_count") if draft else None,
            },
            "expert_review": {
                "complete": expert_ok,
                "json": str(expert_json),
                "markdown": str(expert_markdown),
                "markdown_exists": expert_markdown.is_file(),
                "error": expert_error,
                "verified_claims": expert.get("summary", {}).get("verified_claims") if expert else None,
                "unresolved_items": expert.get("summary", {}).get("unresolved_items") if expert else None,
            },
            "completion_report": {"path": str(completion_report), "exists": completion_report.is_file()},
            "operational_execution": {
                "status": "UNVERIFIED_NO_SANDBOX",
                "reason": "No executable Varanegar training instance and test data are available.",
            },
        }
        entries.append(entry)

    counts = {
        "total_files": len(entries),
        "source_files_present": sum(item["source"]["exists"] for item in entries),
        "transcripts_complete": sum(item["transcript"]["complete"] for item in entries),
        "review_packs_complete": sum(item["review_pack"]["complete"] for item in entries),
        "visual_reviews_complete": sum(item["visual_review"]["complete"] for item in entries),
        "analysis_drafts_complete": sum(item["analysis_draft"]["complete"] for item in entries),
        "expert_reviews_complete": sum(item["expert_review"]["complete"] for item in entries),
        "completion_reports_present": sum(item["completion_report"]["exists"] for item in entries),
        "operational_executions_verified": 0,
    }
    next_entry = next((item for item in entries if not item["expert_review"]["complete"]), None)
    ledger = {
        "artifact": "varanegar_training_knowledge_ledger",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if counts["source_files_present"] == len(entries) else "FAIL",
        "counts": counts,
        "knowledge_training_complete": counts["expert_reviews_complete"] == len(entries),
        "operational_expertise_proven": False,
        "next_required_file": None if next_entry is None else {"index": next_entry["index"], "title": next_entry["title"], "stage": next_entry["stage"]},
        "entries": entries,
        "completion_gates": {
            "all_sources_present": counts["source_files_present"] == len(entries),
            "all_transcripts_complete": counts["transcripts_complete"] == len(entries),
            "all_review_packs_complete": counts["review_packs_complete"] == len(entries),
            "all_visual_reviews_complete": counts["visual_reviews_complete"] == len(entries),
            "all_analysis_drafts_complete": counts["analysis_drafts_complete"] == len(entries),
            "all_expert_reviews_complete": counts["expert_reviews_complete"] == len(entries),
            "operational_sandbox_validation": False,
        },
        "limits": [
            "Knowledge training completion requires all 23 expert-review JSON records to validate as PASS.",
            "Operational expertise remains unproven until representative workflows run successfully in a safe Varanegar environment.",
        ],
    }
    ledger_path = artifact_root / "knowledge_ledger.json"
    write_json(ledger_path, ledger)

    rows = []
    for item in entries:
        rows.append(
            f"| {item['index']} | {item['title']} | {item['stage']} | "
            f"{'✓' if item['transcript']['complete'] else '—'} | "
            f"{'✓' if item['review_pack']['complete'] else '—'} | "
            f"{'✓' if item['visual_review']['complete'] else '—'} | "
            f"{'✓' if item['analysis_draft']['complete'] else '—'} | "
            f"{'✓' if item['expert_review']['complete'] else '—'} |"
        )
    next_text = "همهٔ فایل‌ها بازبینی شده‌اند" if next_entry is None else f"فایل {next_entry['index']}، «{next_entry['title']}» — {next_entry['stage']}"
    markdown = f"""# دفتر کنترل دانش ویدیوهای آموزشی ورانگر

- زمان به‌روزرسانی: {ledger['generated_at']}
- فایل‌های منبع حاضر: {counts['source_files_present']} از {counts['total_files']}
- رونویسی کامل: {counts['transcripts_complete']} از {counts['total_files']}
- بستهٔ بازبینی کامل: {counts['review_packs_complete']} از {counts['total_files']}
- بازبینی تصویری کامل: {counts['visual_reviews_complete']} از {counts['total_files']}
- پیش‌نویس تحلیل کامل: {counts['analysis_drafts_complete']} از {counts['total_files']}
- بازبینی تخصصی کامل: {counts['expert_reviews_complete']} از {counts['total_files']}
- گام بعدی: {next_text}

| ردیف | عنوان | مرحله | رونویسی | بستهٔ شواهد | بازبینی تصویری | پیش‌نویس | بازبینی تخصصی |
|---:|---|---|:---:|:---:|:---:|:---:|:---:|
{chr(10).join(rows)}

## مرز اعتبار

تکمیل آموزش دانشی با تکمیل بازبینی تخصصی هر ۲۳ فایل سنجیده می‌شود. اجرای عملیاتی تا زمان دسترسی به محیط آزمایشی ورانگر «اثبات‌نشده» باقی می‌ماند.
"""
    markdown_path = artifact_root / "KNOWLEDGE_LEDGER_FA.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"validation": ledger["validation"], "ledger": str(ledger_path), "markdown": str(markdown_path), **counts, "next": ledger["next_required_file"]}, ensure_ascii=True))
    return 0 if ledger["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
