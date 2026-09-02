from __future__ import annotations

import json
from pathlib import Path

from analysis import DAILY_SQL


ROOT = Path(__file__).resolve().parent
RESULT = json.loads((ROOT / "analysis_result.json").read_text(encoding="utf-8"))


def billion(value: float) -> float:
    return round(value / 1_000_000_000, 3)


generated_at = RESULT["generated_at"]
source_id = "sales_review_fast_sql"

headline = [
    {
        "current_3day_bn": billion(RESULT["current"]["sales_toman"]),
        "central_forecast_bn": billion(RESULT["forecast"]["central_toman"]),
        "low_forecast_bn": billion(RESULT["forecast"]["scenario_min_toman"]),
        "high_forecast_bn": billion(RESULT["forecast"]["scenario_max_toman"]),
    }
]

uplift_rows = []
for index, row in enumerate(RESULT["uplift_curve"], start=1):
    uplift_rows.append(
        {
            "sort_order": index,
            "period": row["bucket"],
            "median_multiplier": round(row["median_multiplier"], 4),
            "increase_percent": round((row["median_multiplier"] - 1) * 100, 1),
            "minimum_multiplier": round(row["minimum_multiplier"], 4),
            "maximum_multiplier": round(row["maximum_multiplier"], 4),
            "month_1405_02": round(row["month_multipliers"]["1405/02"], 4),
            "month_1405_03": round(row["month_multipliers"]["1405/03"], 4),
            "month_1405_05": round(row["month_multipliers"]["1405/05"], 4),
        }
    )

scenario_rows = [
    {
        "source_month": row["source_month"],
        "forecast_bn": billion(row["forecast_toman"]),
        "current_baseline_daily_bn": billion(RESULT["current"]["baseline_daily_toman"]),
        "expected_workdays": sum(RESULT["expected_workdays"].values()),
    }
    for row in RESULT["curve_scenarios"]
]

forecast_part_rows = [
    {
        "sort_order": index,
        "period": row["bucket"],
        "workdays": row["expected_workdays"],
        "multiplier": round(row["multiplier"], 4),
        "daily_bn": billion(row["forecast_daily_toman"]),
        "period_bn": billion(row["forecast_bucket_toman"]),
    }
    for index, row in enumerate(RESULT["forecast_parts"], start=1)
]

source = {
    "id": source_id,
    "label": "فروش خالص اسناد فروش ورانگر",
    "query": {
        "engine": "sqlserver",
        "sql": DAILY_SQL.strip(),
        "description": "فروش خالص روزانه فاکتور و حواله، پس از کسر مبلغ برگشتی، برای چهار ماه کامل و سه روز نخست شهریور.",
        "executed_at": RESULT["source_snapshot"]["server_time"],
        "tables_used": ["NeginPakhsh.dbo.SalesReviewFast"],
        "filters": [
            "ReportDate between 1405/02/01 and 1405/06/03",
            "روز ناقص: اسناد کمتر از 20 درصد میانه ماه",
            "تیر از برازش نهایی حذف شد چون بازه 1 تا 5 فقط دو روز کامل داشت",
        ],
        "metric_definitions": [
            "فروش خالص تومان = SUM(SellNetAmount - SellReturnNetAmount) / 10",
            "ضریب هر بازه = میانگین فروش روز کامل بازه / میانگین فروش روز کامل بازه 1 تا 5 همان ماه",
            "پیش‌بینی = میانگین فروش سه روز نخست شهریور × ضریب میانه سه ماه معتبر × روزهای کاری هر بازه",
        ],
    },
}

title = "پیش‌بینی فروش شهریور با الگوی رشد داخل ماه"

artifact = {
    "surface": "report",
    "manifest": {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "پیش‌بینی غیرخطی فروش شهریور ۱۴۰۵ با استفاده از منحنی افزایش فروش در طول ماه.",
        "generatedAt": generated_at,
        "cards": [
            {
                "id": "current_sales_card",
                "dataset": "headline",
                "sourceId": source_id,
                "description": "فروش خالص ثبت‌شده در سه روز نخست شهریور.",
                "metrics": [
                    {
                        "label": "فروش ۱ تا ۳ شهریور",
                        "field": "current_3day_bn",
                        "format": "number",
                        "unit": "میلیارد تومان",
                    }
                ],
            },
            {
                "id": "forecast_card",
                "dataset": "headline",
                "sourceId": source_id,
                "description": "برآورد مرکزی مبتنی بر میانه منحنی سه ماه معتبر.",
                "metrics": [
                    {
                        "label": "پیش‌بینی مرکزی",
                        "field": "central_forecast_bn",
                        "format": "number",
                        "unit": "میلیارد تومان",
                    },
                    {
                        "label": "کف سناریو",
                        "field": "low_forecast_bn",
                        "format": "number",
                    },
                    {
                        "label": "سقف سناریو",
                        "field": "high_forecast_bn",
                        "format": "number",
                    },
                ],
            },
        ],
        "charts": [
            {
                "id": "uplift_curve_chart",
                "title": "ضریب فروش روزانه در طول ماه",
                "description": "میانه سه ماه معتبر؛ مبنا برابر میانگین روزهای ۱ تا ۵ است.",
                "type": "bar",
                "dataset": "uplift_curve",
                "sourceId": source_id,
                "encodings": {
                    "x": {"field": "period", "type": "nominal"},
                    "y": {
                        "field": "median_multiplier",
                        "type": "quantitative",
                        "unit": "برابر",
                    },
                },
            },
            {
                "id": "forecast_scenarios_chart",
                "title": "سناریوهای پیش‌بینی بر اساس شکل ماه‌های گذشته",
                "description": "هر ستون، شکل یکی از سه ماه معتبر را روی سرعت سه روز اول شهریور اعمال می‌کند.",
                "type": "bar",
                "dataset": "forecast_scenarios",
                "sourceId": source_id,
                "encodings": {
                    "x": {"field": "source_month", "type": "nominal"},
                    "y": {
                        "field": "forecast_bn",
                        "type": "quantitative",
                        "unit": "میلیارد تومان",
                    },
                },
            },
        ],
        "tables": [
            {
                "id": "forecast_parts_table",
                "title": "اجزای پیش‌بینی ماه",
                "description": "فروش روزانه و جمع هر بازه با لحاظ تعداد روز کاری شهریور.",
                "dataset": "forecast_parts",
                "sourceId": source_id,
                "defaultSort": {"field": "sort_order", "direction": "asc"},
                "columns": [
                    {"field": "sort_order", "label": "ترتیب"},
                    {"field": "period", "label": "بازه ماه"},
                    {"field": "workdays", "label": "روز کاری"},
                    {"field": "multiplier", "label": "ضریب نسبت به ابتدا"},
                    {"field": "daily_bn", "label": "فروش روزانه", "unit": "میلیارد تومان"},
                    {"field": "period_bn", "label": "جمع بازه", "unit": "میلیارد تومان"},
                ],
            }
        ],
        "sources": [{"id": source_id, "label": source["label"]}],
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "executive_summary",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## Executive Summary\n\n"
                    "- **پیش‌بینی خطی قبلی کم‌برآورد بود.** فروش در ماه‌های معتبر با عبور از نیمه ماه شتاب می‌گیرد و نمی‌توان سرعت سه روز اول را ثابت فرض کرد.\n"
                    "- **برآورد مرکزی جدید ۴۳۵٫۵ میلیارد تومان است.** این عدد از اعمال ضریب رشد هر بازه بر متوسط ۱۰٫۱ میلیارد تومان فروش روزانه سه روز اول به دست آمده است.\n"
                    "- **دامنه تصمیم‌گیری ۳۴۷ تا ۵۲۴ میلیارد تومان است.** پراکندگی ماه‌های گذشته زیاد است و فعلاً فقط سه روز از شهریور مشاهده شده؛ بنابراین عدد مرکزی باید همراه دامنه گزارش شود."
                ),
            },
            {
                "id": "headline_metrics",
                "type": "metric-strip",
                "cardIds": ["current_sales_card", "forecast_card"],
            },
            {
                "id": "curve_finding",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## فروش هرچه به پایان ماه نزدیک می‌شود، واقعاً بیشتر است\n\n"
                    "در سه ماه قابل‌مقایسه، فروش روزانه روزهای ۶–۱۰ حدود **۱٫۵ برابر** ابتدای ماه است. این ضریب برای روزهای ۱۶–۲۰ به **۱٫۶۶ برابر** و برای روزهای ۲۱ تا پایان ماه به **۲٫۳۲ برابر** می‌رسد. پس فرض فروش روزانه ثابت، بخش بزرگی از فروش نیمه دوم ماه را حذف می‌کند."
                ),
            },
            {"id": "uplift_curve", "type": "chart", "chartId": "uplift_curve_chart"},
            {
                "id": "scenario_finding",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## سه شکل تاریخی، یک نقطه مرکزی نزدیک ۴۳۵ میلیارد می‌دهند\n\n"
                    "اگر شهریور شکل اردیبهشت، خرداد یا مرداد را تکرار کند، خروجی بین **۳۴۷ تا ۵۲۴ میلیارد تومان** قرار می‌گیرد. میانه سناریوها **۴۳۳٫۲ میلیارد** و برآورد قطعه‌به‌قطعه با ضرایب میانه **۴۳۵٫۵ میلیارد تومان** است؛ نزدیکی این دو، نقطه مرکزی را تقویت می‌کند."
                ),
            },
            {"id": "forecast_scenarios", "type": "chart", "chartId": "forecast_scenarios_chart"},
            {
                "id": "forecast_method",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## پیش‌بینی از پنج قطعه ساخته شده است\n\n"
                    "برای هر بازه، متوسط فروش سه روز نخست شهریور در ضریب تاریخی همان بازه و تعداد روز کاری آن ضرب شده است. بیشترین سهم پیش‌بینی از روزهای ۲۱ تا پایان ماه می‌آید؛ این بخش به‌تنهایی حدود **۲۱۱٫۵ میلیارد تومان** از برآورد مرکزی را تشکیل می‌دهد."
                ),
            },
            {"id": "forecast_parts", "type": "table", "tableId": "forecast_parts_table"},
            {
                "id": "next_steps",
                "type": "markdown",
                "body": (
                    "## اقدام پیشنهادی\n\n"
                    "- پیش‌بینی را در پایان روزهای ۵، ۱۰، ۱۵ و ۲۰ دوباره محاسبه کنید؛ با هر بازه کامل، عدم‌قطعیت به‌طور محسوسی کم می‌شود.\n"
                    "- عدد عملیاتی فعلی را **حدود ۴۳۵ میلیارد تومان** بگیرید، اما برای برنامه نقدینگی کف **۳۵۰ میلیارد تومان** را مبنای محافظه‌کارانه قرار دهید.\n"
                    "- اگر فروش روزهای ۶–۱۰ کمتر از ۱٫۳ برابر روزهای اول باشد، پیش‌بینی باید سریعاً به سمت کف دامنه اصلاح شود."
                ),
            },
            {
                "id": "questions",
                "type": "markdown",
                "body": (
                    "## Further Questions\n\n"
                    "آیا بخشی از جهش پایان ماه ناشی از سیاست وصول، ثبت دیرهنگام اسناد یا هدف‌گذاری فروشندگان است؟ تفکیک بعدی برحسب درجه مشتری و شعبه می‌تواند مشخص کند این الگو عملیاتی است یا فقط زمان ثبت اسناد."
                ),
            },
            {
                "id": "caveats",
                "type": "markdown",
                "sourceId": source_id,
                "body": (
                    "## مفروضات و محدودیت‌ها\n\n"
                    "تیر از برازش اصلی حذف شد چون روزهای ۱–۵ آن فقط دو روز کامل داشت و ضریب پایان ماه را به ۵٫۶۵ برابر می‌رساند. روزهای با اسناد کمتر از ۲۰٪ میانه ماه نیز روز ناقص تلقی شدند. آزمون بازگشتی سه‌ماهه خطایی بین حدود منفی ۲۵٪ تا مثبت ۳۸٪ نشان می‌دهد؛ بنابراین اعتماد به جهت روند **متوسط** و اعتماد به عدد دقیق **متوسط رو به پایین** است. مبلغ برگشتی در این نما طی بازه بررسی صفر بوده و باید در صورت وجود منبع برگشتی مستقل، جداگانه تطبیق شود."
                ),
            },
        ],
    },
    "snapshot": {
        "version": 1,
        "generatedAt": generated_at,
        "status": "ready",
        "datasets": {
            "headline": headline,
            "uplift_curve": uplift_rows,
            "forecast_scenarios": scenario_rows,
            "forecast_parts": forecast_part_rows,
        },
    },
    "sources": [source],
}

(ROOT / "artifact.json").write_text(
    json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(ROOT / "artifact.json")
