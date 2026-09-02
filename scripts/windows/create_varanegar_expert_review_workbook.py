"""Turn a deterministic Varanegar analysis draft into an auditable expert-review workbook."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


VALID_REVIEW_STATES = ("UNREVIEWED", "VERIFIED", "PROBABLE", "INFERRED", "AMBIGUOUS", "REJECTED", "NEEDS_SANDBOX")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-draft", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    draft_path = args.analysis_draft.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    draft = json.loads(draft_path.read_text(encoding="utf-8-sig"))
    if draft.get("validation") != "PASS":
        raise ValueError("Analysis draft must validate as PASS")

    combined: dict[tuple[int, float], dict] = {}
    for candidate_type, items in (
        ("ACTION_OR_NAVIGATION", draft.get("action_candidates", [])),
        ("RULE_OR_CONSTRAINT", draft.get("rule_candidates", [])),
    ):
        for item in items:
            key = (int(item["segment_index"]), float(item["start"]))
            record = combined.setdefault(
                key,
                {
                    "candidate_id": "",
                    "categories": [],
                    "timestamp": item["timestamp"],
                    "start": item["start"],
                    "end": item["end"],
                    "transcript_text": item["text"],
                    "nearest_frame": item.get("nearest_frame"),
                    "matched_terms": [],
                    "review_status": "UNREVIEWED",
                    "canonical_statement": "",
                    "ui_label_or_path": "",
                    "prerequisites": [],
                    "expected_result": "",
                    "exception_or_recovery": "",
                    "audio_checked": False,
                    "visual_checked": False,
                    "medium_asr_required": False,
                    "review_notes": "",
                },
            )
            if candidate_type not in record["categories"]:
                record["categories"].append(candidate_type)
            record["matched_terms"] = sorted(set(record["matched_terms"]) | set(item.get("matched_terms", [])))

    candidates = sorted(combined.values(), key=lambda item: (float(item["start"]), item["transcript_text"]))
    for index, item in enumerate(candidates, 1):
        item["candidate_id"] = f"C{index:04d}"

    entity_reviews = []
    for index, (term, occurrences) in enumerate(draft.get("entity_occurrences", {}).items(), 1):
        entity_reviews.append(
            {
                "entity_id": f"E{index:03d}",
                "asr_term": term,
                "canonical_name": "",
                "review_status": "UNREVIEWED",
                "meaning_or_scope": "",
                "relationships": [],
                "evidence": [
                    {
                        "timestamp": item["timestamp"],
                        "text": item["text"],
                        "nearest_frame": item.get("nearest_frame"),
                    }
                    for item in occurrences
                ],
                "review_notes": "",
            }
        )

    workbook = {
        "artifact": "varanegar_expert_review_workbook",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "DRAFT",
        "source_analysis_draft": str(draft_path),
        "allowed_review_states": list(VALID_REVIEW_STATES),
        "progress": {
            "candidate_total": len(candidates),
            "candidate_reviewed": 0,
            "entity_total": len(entity_reviews),
            "entity_reviewed": 0,
            "audio_checks": 0,
            "visual_checks": 0,
        },
        "chapter_review": [
            {
                "chapter_index": item["index"],
                "start_timestamp": item["start_timestamp"],
                "end_timestamp": item["end_timestamp"],
                "suggested_terms": item["top_terms"],
                "reviewed": False,
                "topic_summary": "",
                "forms_or_menus": [],
                "procedures": [],
                "business_rules": [],
                "exceptions": [],
                "notes": "",
            }
            for item in draft.get("chapters", [])
        ],
        "claim_candidates": candidates,
        "entity_reviews": entity_reviews,
        "final_synthesis": {
            "module_scope": "",
            "prerequisites": [],
            "menu_paths_and_forms": [],
            "procedures": [],
            "business_rules": [],
            "roles_and_permissions": [],
            "errors_and_recovery": [],
            "reports_and_outputs": [],
            "cross_module_links": [],
            "new_knowledge": [],
            "conflicts_with_existing_knowledge": [],
            "unresolved_items": [],
            "sandbox_scenarios": [],
            "practice_questions": [],
        },
        "completion_requirements": [
            "All chapters must be reviewed.",
            "Every retained claim must include checked visual or audio evidence and a non-UNREVIEWED status.",
            "Rejected and ambiguous ASR candidates must not become canonical claims.",
            "Every procedure must include prerequisites, ordered steps, expected result, and evidence timestamps.",
            "Operational-only claims must remain NEEDS_SANDBOX until executed in a safe Varanegar instance.",
        ],
    }
    json_path = output_dir / "expert_review_workbook.json"
    write_json(json_path, workbook)

    claim_rows = []
    for item in candidates:
        text = item["transcript_text"].replace("|", "\\|").replace("\n", " ")
        claim_rows.append(
            f"| {item['candidate_id']} | {item['timestamp']} | {'، '.join(item['categories'])} | "
            f"{text} | {item.get('nearest_frame') or ''} | UNREVIEWED |"
        )
    entity_rows = []
    for item in entity_reviews:
        timestamps = "، ".join(evidence["timestamp"] for evidence in item["evidence"][:10])
        entity_rows.append(f"| {item['entity_id']} | {item['asr_term']} | {timestamps} | UNREVIEWED |")
    markdown = f"""# کاربرگ بازبینی تخصصی ویدیوی ورانگر

- منبع پیش‌نویس: {draft_path}
- تعداد نامزدهای ادعا: {len(candidates)}
- تعداد موجودیت‌های منتخب: {len(entity_reviews)}
- وضعیت: DRAFT

## وضعیت‌های مجاز

UNREVIEWED، VERIFIED، PROBABLE، INFERRED، AMBIGUOUS، REJECTED، NEEDS_SANDBOX

## نامزدهای ادعا

| شناسه | زمان | دسته | متن رونویسی | نزدیک‌ترین تصویر | وضعیت |
|---|---:|---|---|---|---|
{chr(10).join(claim_rows) or '| — | — | — | موردی استخراج نشد | — | — |'}

## موجودیت‌های منتخب

| شناسه | عبارت رونویسی | زمان‌های نمونه | وضعیت |
|---|---|---|---|
{chr(10).join(entity_rows) or '| — | — | — | — |'}

## قاعدهٔ پذیرش

هیچ ردیفی با وضعیت UNREVIEWED، AMBIGUOUS یا REJECTED نباید به‌عنوان دانش قطعی وارد گزارش تخصصی شود. موارد وابسته به اجرای واقعی باید NEEDS_SANDBOX باقی بمانند.
"""
    markdown_path = output_dir / "expert_review_workbook_fa.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"validation": "DRAFT", "json": str(json_path), "markdown": str(markdown_path), "candidates": len(candidates), "entities": len(entity_reviews)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
