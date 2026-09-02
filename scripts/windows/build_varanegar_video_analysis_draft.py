"""Create an evidence-indexed analysis draft from a completed Varanegar transcript."""
from __future__ import annotations

import argparse
import bisect
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ACTION_TERMS = ("کلیک", "انتخاب", "وارد", "ثبت", "تعریف", "باز", "منو", "گزینه", "تیک", "ذخیره", "اضافه", "ویرایش", "حذف", "تأیید", "تایید")
RULE_TERMS = ("باید", "نباید", "اگر", "شرط", "اجازه", "امکان", "نمی", "ضروری", "الزام", "محدود", "فقط")
ENTITY_TERMS = (
    "کالا", "انبار", "مشتری", "تامین", "تأمین", "فروشنده", "ویزیت", "فاکتور", "خرید", "فروش",
    "بارکد", "گروه", "برند", "مسیر", "حساب", "گزارش", "تخفیف", "قیمت", "واحد", "موجودی",
    "خزانه", "توزیع", "سرپرست", "تبلت", "دسترسی", "شعبه", "ستاد",
)
STOPWORDS = {
    "این", "اون", "آن", "که", "برای", "ولی", "اگر", "یک", "یا", "را", "رو", "به", "از", "در", "با", "می", "شود", "شده",
    "کنیم", "کنید", "کرد", "کرده", "هست", "هستش", "است", "داریم", "داره", "دارند", "یعنی", "بعد", "خود", "هم", "من",
    "شما", "ما", "تو", "روی", "باید", "میشه", "نمی", "چه", "چون", "تا", "و", "یه", "دو", "سه",
}


def stamp(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(text: str) -> str:
    return text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").strip()


def evidence_item(index: int, segment: dict, frames: list[dict], frame_times: list[float]) -> dict:
    start = float(segment["start"])
    frame = None
    if frames:
        position = bisect.bisect_left(frame_times, start)
        candidates = [item for item in (position - 1, position) if 0 <= item < len(frames)]
        nearest = min(candidates, key=lambda item: abs(frame_times[item] - start))
        frame = frames[nearest].get("frame")
    return {
        "segment_index": index,
        "start": start,
        "end": float(segment["end"]),
        "timestamp": stamp(start),
        "text": normalize_text(str(segment["text"])),
        "nearest_frame": frame,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--review-pack", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--chapter-seconds", type=int, default=300)
    parser.add_argument("--max-candidates", type=int, default=250)
    args = parser.parse_args()

    transcript_path = args.transcript.resolve()
    review_path = args.review_pack.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    if transcript.get("validation") != "PASS" or review.get("validation") != "PASS":
        raise ValueError("Transcript and review pack must both validate as PASS")

    segments = list(transcript.get("segments", []))
    frame_samples = list(review.get("samples", []))
    frame_times = [float(item.get("approx_seconds", 0)) for item in frame_samples]
    action_candidates: list[dict] = []
    rule_candidates: list[dict] = []
    entity_occurrences: dict[str, list[dict]] = {term: [] for term in ENTITY_TERMS}

    for index, segment in enumerate(segments):
        text = normalize_text(str(segment.get("text", "")))
        item = None
        if any(term in text for term in ACTION_TERMS):
            item = evidence_item(index, segment, frame_samples, frame_times)
            item["matched_terms"] = [term for term in ACTION_TERMS if term in text]
            if len(action_candidates) < args.max_candidates:
                action_candidates.append(item)
        if any(term in text for term in RULE_TERMS):
            if item is None:
                item = evidence_item(index, segment, frame_samples, frame_times)
            rule_item = dict(item)
            rule_item["matched_terms"] = [term for term in RULE_TERMS if term in text]
            if len(rule_candidates) < args.max_candidates:
                rule_candidates.append(rule_item)
        for term in ENTITY_TERMS:
            if term in text and len(entity_occurrences[term]) < 50:
                entity_occurrences[term].append(evidence_item(index, segment, frame_samples, frame_times))

    entity_occurrences = {term: items for term, items in entity_occurrences.items() if items}
    duration = float(transcript["summary"]["duration_seconds"])
    chapter_count = max(1, int(duration // args.chapter_seconds) + 1)
    chapters: list[dict] = []
    word_pattern = re.compile(r"[آ-یA-Za-z0-9]{2,}")
    for chapter_index in range(chapter_count):
        start = chapter_index * args.chapter_seconds
        end = min(duration, start + args.chapter_seconds)
        chapter_segments = [item for item in segments if start <= float(item["start"]) < end]
        combined = " ".join(normalize_text(str(item["text"])) for item in chapter_segments)
        words = [word for word in word_pattern.findall(combined) if word not in STOPWORDS and not word.isdigit()]
        top_terms = [word for word, _ in Counter(words).most_common(12)]
        chapters.append({
            "index": chapter_index + 1,
            "start": start,
            "end": end,
            "start_timestamp": stamp(start),
            "end_timestamp": stamp(end),
            "segment_count": len(chapter_segments),
            "top_terms": top_terms,
            "opening_text": " ".join(str(item["text"]).strip() for item in chapter_segments[:3]),
        })

    payload = {
        "artifact": "varanegar_training_video_analysis_draft",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS",
        "source_transcript": str(transcript_path),
        "source_review_pack": str(review_path),
        "summary": {
            "duration_seconds": duration,
            "segment_count": len(segments),
            "chapter_count": len(chapters),
            "action_candidate_count": len(action_candidates),
            "rule_candidate_count": len(rule_candidates),
            "entity_term_count": len(entity_occurrences),
        },
        "chapters": chapters,
        "action_candidates": action_candidates,
        "rule_candidates": rule_candidates,
        "entity_occurrences": entity_occurrences,
        "limits": [
            "This is a deterministic candidate index, not a canonical operational analysis.",
            "Each candidate must be checked against the linked visual frame and source audio before acceptance.",
            "ASR spelling errors may reduce recall or create misleading matches.",
        ],
    }
    json_path = output_dir / "analysis_draft.json"
    write_json(json_path, payload)

    def rows(items: list[dict]) -> str:
        rendered = []
        for item in items:
            text = item["text"].replace("|", "\\|").replace("\n", " ")
            terms = "، ".join(item.get("matched_terms", []))
            rendered.append(f"| {item['timestamp']} | {terms} | {text} | {item.get('nearest_frame') or ''} |")
        return "\n".join(rendered) or "| — | — | موردی استخراج نشد | — |"

    chapter_rows = "\n".join(
        f"| {item['index']} | {item['start_timestamp']}–{item['end_timestamp']} | {item['segment_count']} | {'، '.join(item['top_terms'])} |"
        for item in chapters
    )
    entity_rows = "\n".join(
        f"| {term} | {len(items)} | {'، '.join(item['timestamp'] for item in items[:10])} |"
        for term, items in entity_occurrences.items()
    ) or "| — | ۰ | — |"
    markdown = f"""# پیش‌نویس شاهد‌محور تحلیل ویدیوی ورانگر

این سند فهرست نامزدهای تحلیل است و قبل از بازبینی صوت و تصویر، دانش قطعی محسوب نمی‌شود.

## نمای کلی بازه‌ها

| بخش | بازه | قطعات متن | واژگان پرتکرار |
|---:|---:|---:|---|
{chapter_rows}

## نامزدهای روش اجرایی و مسیر کار

| زمان | کلیدواژه | متن رونویسی | نزدیک‌ترین تصویر |
|---:|---|---|---|
{rows(action_candidates)}

## نامزدهای قواعد، شروط و محدودیت‌ها

| زمان | کلیدواژه | متن رونویسی | نزدیک‌ترین تصویر |
|---:|---|---|---|
{rows(rule_candidates)}

## موجودیت‌های منتخب

| موجودیت | تعداد شاهد نگه‌داری‌شده | زمان‌های نمونه |
|---|---:|---|
{entity_rows}

## کنترل لازم

هر ردیف باید با ویدیو کنترل و سپس در یکی از طبقات «تأییدشده»، «محتمل»، «استنباط»، «نامشخص» یا «نیازمند محیط عملی» ثبت شود.
"""
    markdown_path = output_dir / "analysis_draft_fa.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"validation": "PASS", "json": str(json_path), "markdown": str(markdown_path), **payload["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
