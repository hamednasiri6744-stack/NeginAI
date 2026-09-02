"""Build the review notebook and portable-report payload from classification CSVs."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import ROOT_DIR


ANALYSIS_DIR = ROOT_DIR / "data" / "analysis" / "sales_access_classification"
END_DATE = "1405-05-19"
DETAIL_PATH = ANALYSIS_DIR / f"sales_access_assignments_{END_DATE}.csv"
SUMMARY_PATH = ANALYSIS_DIR / f"sales_access_summary_{END_DATE}.csv"
METADATA_PATH = ANALYSIS_DIR / f"sales_access_metadata_{END_DATE}.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _integer(value: str) -> int:
    return int(float(value or 0))


def _number(value: str) -> float:
    return float(value or 0)


def _notebook(assignments: list[dict[str, str]], metadata: dict) -> dict:
    example = next(row for row in assignments if row["نام"] == "عارف کامران" and row["نقش"] == "فروشنده")
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## tl;dr\n",
                f"- بازه تحلیل: `{metadata['period']['start']}` تا `{metadata['period']['end']}`.\n",
                f"- {metadata['assignment_counts']['sellers']} فروشنده و {metadata['assignment_counts']['supervisors']} سرپرست طبقه‌بندی شدند.\n",
                f"- {metadata['assignment_counts']['review']} تخصیص برای بازبینی علامت خورده‌اند.\n",
                f"- کنترل نمونه: عارف کامران = {example['شعبه پیشنهادی']} / {example['لاین پیشنهادی']}.\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Context & Methods\n",
                "### Key Assumptions\n",
                "شخص فعال یعنی فردی که در ماه ۱۴۰۵/۰۵ گردش خالص مثبت دارد؛ گردش خالص برابر فروش خالص منهای برگشتی است. "
                "شعبه از `CustomerLevelName` و لاین از `CustomerCategoryName` گرفته شده است. "
                "رتبه‌بندی ابتدا با تعداد مشتری یکتا، سپس تعداد سند و بعد آخرین فعالیت انجام می‌شود.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import csv, json\n",
                "from pathlib import Path\n",
                "analysis_dir = Path('data/analysis/sales_access_classification')\n",
                "with (analysis_dir / 'sales_access_assignments_1405-05-19.csv').open(encoding='utf-8-sig') as f:\n",
                "    assignments = list(csv.DictReader(f))\n",
                "with (analysis_dir / 'sales_access_metadata_1405-05-19.json').open(encoding='utf-8') as f:\n",
                "    metadata = json.load(f)\n",
                "metadata['assignment_counts']\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Data\n", "منبع اصلی: `dbo.SalesReviewFast`. خروجی کامل در CSV جزئیات ذخیره شده است.\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "review_rows = [r for r in assignments if r['اطمینان'] == 'نیازمند بررسی']\n",
                "len(assignments), len(review_rows)\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Results\n",
                "فهرست کامل شامل نقش، شناسه، شعبه، لاین، سهم هر تخصیص، گزینه دوم و دلیل بازبینی است. "
                "نام‌های دارای هر دو نقش باید در مرحله ساخت حساب به یک هویت با دو نقش تبدیل شوند.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "example = [r for r in assignments if r['نام'] == 'عارف کامران' and r['نقش'] == 'فروشنده']\n",
                "example\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Takeaways\n",
                "قبل از ایجاد حساب‌ها، ردیف‌های «نیازمند بررسی» و شناسه‌های تکراری باید تأیید شوند. "
                "سایر ردیف‌ها می‌توانند مبنای پیش‌نویس دسترسی شعبه و لاین باشند.\n",
            ],
        },
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _artifact(assignments: list[dict[str, str]], summary: list[dict[str, str]], metadata: dict) -> dict:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    counts = metadata["assignment_counts"]
    unique_names = len({row["نام"] for row in assignments})
    cross_role_names = len({row["نام"] for row in assignments if "+" in row["نقش‌های ثبت‌شده برای این نام"]})
    duplicate_names = len({row["نام"] for row in assignments if row["شناسه‌های هم‌نام در همین نقش"]})
    example = next(row for row in assignments if row["نام"] == "عارف کامران" and row["نقش"] == "فروشنده")

    detail_rows = [
        {
            "role": row["نقش"],
            "person_id": _integer(row["شناسه"]),
            "name": row["نام"],
            "registered_roles": row["نقش‌های ثبت‌شده برای این نام"],
            "branch": row["شعبه پیشنهادی"],
            "branch_customers": _integer(row["تعداد مشتری شعبه"]),
            "branch_share_pct": _number(row["سهم شعبه (%)"]),
            "line": row["لاین پیشنهادی"],
            "line_customers": _integer(row["تعداد مشتری لاین"]),
            "line_share_pct": _number(row["سهم لاین (%)"]),
            "total_customers": _integer(row["کل مشتری یکتا"]),
            "documents": _integer(row["کل اسناد فروش"]),
            "last_activity": row["آخرین فعالیت"],
            "confidence": row["اطمینان"],
            "review_reason": row["دلیل بررسی"],
        }
        for row in assignments
    ]
    summary_rows = [
        {"role": row["نقش"], "branch": row["شعبه"], "line": row["لاین"], "people": _integer(row["تعداد نفر"])}
        for row in summary
    ]
    branch_role_counts: dict[tuple[str, str], int] = {}
    for row in summary_rows:
        key = (row["role"], row["branch"])
        branch_role_counts[key] = branch_role_counts.get(key, 0) + row["people"]
    branch_role_rows = [
        {"role": role, "branch": branch, "people": people}
        for (role, branch), people in sorted(branch_role_counts.items())
    ]
    review_rows = [row for row in detail_rows if row["confidence"] == "نیازمند بررسی"]
    overview = [{
        "sellers": counts["sellers"],
        "supervisors": counts["supervisors"],
        "role_assignments": counts["total"],
        "unique_names": unique_names,
        "high_confidence": counts["high"],
        "medium_confidence": counts["medium"],
        "ready_for_draft": counts["high"] + counts["medium"],
        "needs_review": counts["review"],
        "cross_role_names": cross_role_names,
        "duplicate_names": duplicate_names,
    }]
    example_rows = [{
        "name": example["نام"],
        "branch": example["شعبه پیشنهادی"],
        "branch_customers": _integer(example["تعداد مشتری شعبه"]),
        "branch_share_pct": _number(example["سهم شعبه (%)"]),
        "line": example["لاین پیشنهادی"],
        "line_customers": _integer(example["تعداد مشتری لاین"]),
        "line_share_pct": _number(example["سهم لاین (%)"]),
    }]

    source_id = "sales_review_1405"
    title = "پیشنهاد طبقه‌بندی دسترسی فروش"
    source = {
        "id": source_id,
        "query": {
            "engine": "Microsoft SQL Server",
            "language": "sql",
            "sql": "SELECT DealerId, DealerName, SupervisorId, SupervisorName, CustomerId, CustomerLevelId, CustomerLevelName, CustomerCategoryId, CustomerCategoryName, SellId, ReportDate, SellNetAmount, SellReturnNetAmount FROM dbo.SalesReviewFast WHERE ReportDate >= N'1405/05/01' AND ReportDate < N'1405/06/01'",
            "description": "داده مبنای طبقه‌بندی فروشنده و سرپرست دارای گردش خالص مثبت در ماه ۱۴۰۵/۰۵.",
            "executed_at": generated_at,
            "tables_used": ["dbo.SalesReviewFast"],
            "filters": ["1405/05/01 <= ReportDate < 1405/06/01", "گردش خالص شخص > 0", "فقط شناسه‌های غیرتهی فروشنده و سرپرست"],
            "metric_definitions": [
                "شعبه پیشنهادی: درجه مشتری با بیشترین تعداد مشتری یکتا برای شخص.",
                "لاین پیشنهادی: طبقه مشتری با بیشترین تعداد مشتری یکتا برای شخص.",
                "تساوی‌شکن: تعداد سند فروش، سپس آخرین فعالیت، سپس نام بُعد.",
            ],
        },
    }
    manifest_source = {"id": source_id, "label": "فروش و مشتریان ماه ۱۴۰۵/۰۵", "path": "dbo.SalesReviewFast"}
    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "پیش‌نویس شعبه و لاین فروشنده‌ها و سرپرست‌ها پیش از ساخت حساب کاربری.",
            "generatedAt": generated_at,
            "filters": [],
            "cards": [
                {"id": "seller_card", "description": "فروشنده‌های دارای گردش خالص مثبت در ماه ۱۴۰۵/۰۵.", "dataset": "overview", "sourceId": source_id, "metrics": [{"label": "فروشنده فعال", "field": "sellers", "format": "number"}]},
                {"id": "supervisor_card", "description": "سرپرست‌های دارای گردش خالص مثبت در ماه ۱۴۰۵/۰۵.", "dataset": "overview", "sourceId": source_id, "metrics": [{"label": "سرپرست فعال", "field": "supervisors", "format": "number"}]},
                {"id": "ready_card", "description": "تخصیص‌های با اطمینان بالا یا متوسط برای پیش‌نویس دسترسی.", "dataset": "overview", "sourceId": source_id, "metrics": [{"label": "قابل استفاده در پیش‌نویس", "field": "ready_for_draft", "format": "number"}, {"label": "از این تعداد با اطمینان متوسط", "field": "medium_confidence", "format": "number"}]},
                {"id": "review_card", "description": "تخصیص‌هایی که پیش از ساخت حساب باید بازبینی شوند.", "dataset": "overview", "sourceId": source_id, "metrics": [{"label": "نیازمند بررسی", "field": "needs_review", "format": "number"}]},
            ],
            "charts": [
                {
                    "id": "branch_role_chart",
                    "title": "تعداد فروشنده و سرپرست به تفکیک شعبه",
                    "subtitle": "فقط افراد دارای گردش خالص مثبت در ماه ۱۴۰۵/۰۵؛ تخصیص بر اساس مشتریان یکتای همان ماه.",
                    "type": "bar",
                    "dataset": "branch_role",
                    "sourceId": source_id,
                    "valueFormat": "number",
                    "encodings": {
                        "x": {"field": "branch", "type": "nominal", "label": "شعبه"},
                        "y": {"field": "people", "type": "quantitative", "label": "تعداد نفر"},
                        "color": {"field": "role", "type": "nominal", "label": "نقش"},
                        "tooltip": [
                            {"field": "role", "type": "nominal", "label": "نقش"},
                            {"field": "people", "type": "quantitative", "label": "تعداد نفر", "format": "number"},
                        ],
                    },
                }
            ],
            "tables": [
                {
                    "id": "summary_table", "title": "تعداد نفر به تفکیک نقش، شعبه و لاین",
                    "subtitle": "گردش خالص مثبت از ۱۴۰۵/۰۵/۰۱ تا ۱۴۰۵/۰۵/۱۹؛ هر ردیف یک تخصیص نقش است.",
                    "dataset": "summary", "sourceId": source_id,
                    "defaultSort": {"field": "people", "direction": "desc"},
                    "columns": [
                        {"field": "role", "label": "نقش", "type": "text"},
                        {"field": "branch", "label": "شعبه", "type": "text"},
                        {"field": "line", "label": "لاین", "type": "text"},
                        {"field": "people", "label": "تعداد نفر", "format": "number"},
                    ],
                },
                {
                    "id": "review_table", "title": "موارد نیازمند بررسی قبل از ساخت حساب",
                    "subtitle": "سابقه کم، غلبه ضعیف، تساوی یا تعارض هویتی باعث ورود به این فهرست شده است.",
                    "dataset": "review", "sourceId": source_id,
                    "defaultSort": {"field": "total_customers", "direction": "desc"},
                    "columns": [
                        {"field": "role", "label": "نقش", "type": "text"},
                        {"field": "person_id", "label": "شناسه", "format": "number"},
                        {"field": "name", "label": "نام", "type": "text"},
                        {"field": "branch", "label": "شعبه پیشنهادی", "type": "text"},
                        {"field": "line", "label": "لاین پیشنهادی", "type": "text"},
                        {"field": "total_customers", "label": "مشتری یکتا", "format": "number"},
                        {"field": "review_reason", "label": "دلیل بررسی", "type": "text"},
                    ],
                },
                {
                    "id": "detail_table", "title": "فهرست کامل تخصیص‌های پیشنهادی",
                    "subtitle": "مبنای تخصیص مشتری یکتا است؛ سهم‌ها درصد غلبه گزینه بر سایر گزینه‌های همان شخص‌اند.",
                    "dataset": "detail", "sourceId": source_id,
                    "defaultSort": {"field": "name", "direction": "asc"},
                    "columns": [
                        {"field": "role", "label": "نقش", "type": "text"},
                        {"field": "person_id", "label": "شناسه", "format": "number"},
                        {"field": "name", "label": "نام", "type": "text"},
                        {"field": "branch", "label": "شعبه", "type": "text"},
                        {"field": "branch_share_pct", "label": "سهم شعبه (%)", "format": "number"},
                        {"field": "line", "label": "لاین", "type": "text"},
                        {"field": "line_share_pct", "label": "سهم لاین (%)", "format": "number"},
                        {"field": "total_customers", "label": "مشتری یکتا", "format": "number"},
                        {"field": "last_activity", "label": "آخرین فعالیت", "type": "text"},
                        {"field": "confidence", "label": "اطمینان", "type": "text"},
                    ],
                },
            ],
            "sources": [manifest_source],
            "blocks": [
                {
                    "id": "executive_summary", "type": "markdown", "sourceId": source_id,
                    "body": f"# {title}\n\n## خلاصه مدیریتی\n\n- فقط افراد دارای **گردش خالص مثبت در ماه ۱۴۰۵/۰۵** نگه داشته شدند: **{counts['sellers']} فروشنده و {counts['supervisors']} سرپرست**.\n- **{counts['high'] + counts['medium']} تخصیص** برای پیش‌نویس دسترسی قابل استفاده است و **{counts['review']} تخصیص** باید قبل از ساخت حساب بازبینی شود.\n- **{cross_role_names} نام** در هر دو نقش فروشنده و سرپرست دیده می‌شود؛ برای هرکدام یک حساب با دو نقش مناسب‌تر است.\n- کنترل نمونه تأیید شد: **عارف کامران = دفتر فروش البرز / لاین مارکت**."
                },
                {"id": "metrics", "type": "metric-strip", "cardIds": ["seller_card", "supervisor_card", "ready_card", "review_card"]},
                {
                    "id": "method", "type": "markdown", "sourceId": source_id,
                    "body": "## قاعده تخصیص\n\nشخص فعال یعنی فردی که در ماه ۱۴۰۵/۰۵ مجموع **فروش خالص منهای برگشتی** او بزرگ‌تر از صفر باشد. شعبه از **درجه مشتری** و لاین از **طبقه مشتری** همان ماه تعیین شده است. معیار اصلی تعداد مشتری یکتاست؛ تعداد سند فروش، آخرین فعالیت و نام بُعد فقط تساوی‌شکن‌اند. نداشتن گردش مثبت فقط باعث حذف از فهرست دسترسی می‌شود و به‌تنهایی اثبات خروج از شرکت نیست. هیچ حساب یا دسترسی‌ای در این مرحله ساخته نشده است."
                },
                {
                    "id": "branch_chart_intro", "type": "markdown", "sourceId": source_id,
                    "body": "## تمرکز نیروی فروش در شعبه‌ها\n\nنمودار توزیع نقش‌ها را بر اساس شعبه پیشنهادی نشان می‌دهد. این تصویر برای کنترل ظرفیت و کشف تخصیص‌های غیرعادی مفید است؛ اما مبنای دسترسی هر فرد همچنان سابقه مشتری یکتای خودش است، نه اندازه شعبه."
                },
                {"id": "branch_chart", "type": "chart", "chartId": "branch_role_chart"},
                {"id": "summary", "type": "table", "tableId": "summary_table"},
                {
                    "id": "identity", "type": "markdown", "sourceId": source_id,
                    "body": f"## هویت‌ها را پیش از ایجاد نام کاربری یکی کنیم\n\nاز {counts['total']} ردیف نقش، **{unique_names} نام یکتا** به دست آمد. {cross_role_names} نفر در هر دو نقش حضور دارند. همچنین **{duplicate_names} نام** با بیش از یک شناسه در همان نقش ثبت شده است؛ «محمد صادق نجف‌زاده» با شناسه‌های ۱۳۷ و ۵۱۰ و دو تخصیص متفاوت، مورد اصلی تأیید هویت است."
                },
                {"id": "review", "type": "table", "tableId": "review_table"},
                {
                    "id": "full_list_intro", "type": "markdown",
                    "body": "## فهرست کامل برای تأیید مدیریتی\n\nاین جدول مبنای مرحله بعدی ساخت نام کاربری و سیاست دسترسی است. ردیف‌های با اطمینان بالا و متوسط می‌توانند پیش‌نویس باشند؛ ردیف‌های نیازمند بررسی نباید خودکار فعال شوند."
                },
                {"id": "details", "type": "table", "tableId": "detail_table"},
                {
                    "id": "next_step", "type": "markdown",
                    "body": "## اقدام بعدی\n\nپس از تأیید موارد بازبینی، هویت‌های دو‌نقشی ادغام می‌شوند و برای هر شخص یک نام کاربری ساخته می‌شود. سطح دسترسی پیش‌فرض باید به همان شعبه و لاین پیشنهادی محدود باشد؛ دسترسی سرپرست می‌تواند فروشنده‌های زیرمجموعه همان محدوده را نیز ببیند."
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {"overview": overview, "branch_role": branch_role_rows, "summary": summary_rows, "review": review_rows, "detail": detail_rows, "example": example_rows},
            "accessIssues": [],
        },
        "sources": [source],
    }


def main() -> None:
    assignments = _read_csv(DETAIL_PATH)
    summary = _read_csv(SUMMARY_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    notebook_path = ANALYSIS_DIR / f"sales_access_classification_{END_DATE}.ipynb"
    notebook_path.write_text(json.dumps(_notebook(assignments, metadata), ensure_ascii=False, indent=1), encoding="utf-8")

    artifact_path = ANALYSIS_DIR / f"sales_access_report_artifact_{END_DATE}.json"
    artifact_path.write_text(json.dumps(_artifact(assignments, summary, metadata), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"notebook={notebook_path}")
    print(f"artifact={artifact_path}")


if __name__ == "__main__":
    main()
