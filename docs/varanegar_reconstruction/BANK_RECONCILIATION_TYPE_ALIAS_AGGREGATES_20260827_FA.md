# شمارش تجمیعی Aliasهای Type در مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ فقط‌خواندنی، Aggregate و بدون شناسه/مبلغ/حساب/هویت**

## نتیجهٔ مادی

در Clone فقط‌خواندنی `NeginPakhsh_WebDev`، جدول `BankAccountCardex` دارای
۱۹۲٬۱۰۶ ردیف است. از هشت Literal ازپیش‌مجازشده (شش Predicate دقیق Summary و
دو املای Matching جایگزین):

| زوج | Literal در Summary | شمارش | Literal در Matching | شمارش |
|---|---|---:|---|---:|
| حواله بانکی دریافتی | `RBANKDARFT` | ۰ | `RBANKDRAFT` | ۰ |
| حواله نقدی دریافتی | `RCASHDRAF` | ۰ | `RCASHDRAFT` | ۱۴۶٬۵۷۶ |

بنابراین اختلاف `RCASHDRAF/RCASHDRAFT` صرفاً املایی نیست: دادهٔ Clone تقریباً
همه با Literal مسیر Matching ثبت شده ولی Procedure Summary Literal کوتاه‌شده را
فیلتر می‌کند. این شاهد احتمال حذف این خانواده از محاسبات Summary Legacy را بالا
می‌برد، اما چون Procedure اجرا نشده و Fixture ردیفی مجاز نداریم، **برابری نتیجه،
فراوانی Production یا مجوز Normalize کردن ثابت نمی‌شود**.

در سطح کل Clone، شش Predicate دقیق Summary فقط ۴۵٬۴۵۴ ردیف (۲۳٫۶۶٪) را واجد
شرط می‌کنند؛ املای canonical فقط برای `RCASHDRAFT` تعداد ۱۴۶٬۵۷۶ ردیف
(۷۶٫۳۰٪) دیگر دارد. `RCHEQUE` نیز ۵۳ ردیف دارد که هیچ‌کدام Status=3 نیستند و
در Predicate Summary وارد نمی‌شوند. مجموع Typeهای شناخته‌شده ۱۹۲٬۰۸۳ است و
فقط ۲۳ ردیف در Typeهای دیگری قرار می‌گیرد. این نسبت‌ها «دامنهٔ بالقوهٔ فیلتر»
هستند، نه مبلغ یا خروجی مالی Summary.

اسکن Metadata ماژول‌ها نیز Outlier بودن هر دو زوج را نشان می‌دهد: `RCASHDRAFT`
در ۲۳ Object و `RBANKDRAFT` در دو View مصرف شده‌اند، ولی هر دو Literal کوتاه
`RCASHDRAF/RBANKDARFT` فقط در `dbo.DoReconcile_GetSummary` دیده شدند. نام/نوع
Object ثبت شده ولی Definition خام هیچ ماژولی ذخیره نشده است.

## اثر روی قرارداد مقصد

- تصمیم `BR-DEC-001` اکنون شاهد Count تفکیکی Clone دارد، ولی هنوز Approval ندارد.
- تا اجرای تفاضلی یازده Metric روی Fixture Redacted یکسان، Literalها بی‌صدا یکی
  نمی‌شوند.
- مقصد باید Alias table صریح و نسخه‌دار را فقط پس از تصمیم مالک فعال کند.
- هیچ ردیف Source اصلاح یا Rewrite نمی‌شود.

## مرز حریم و بازتولید

Extractor فقط `COUNT_BIG` و `SUM(CASE...)` هشت Literal ثابت را می‌خواند؛ سایر
Typeها فقط به‌صورت یک Count باقیمانده گزارش می‌شوند. هیچ ID، تاریخ، مبلغ، حساب،
کاربر، متن آزاد یا Procedure خوانده/اجرا/ذخیره نمی‌شود.

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_type_alias_aggregates_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_type_alias_aggregates.py`
- `tests/test_varanegar_ui_evidence.py`
