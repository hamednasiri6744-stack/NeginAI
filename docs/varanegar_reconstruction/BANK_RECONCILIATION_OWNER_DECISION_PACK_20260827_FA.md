# بستهٔ تصمیم‌های باز مالک فرایند مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS از نظر پوشش؛ هیچ تصمیمی هنوز تأیید مالک نشده است**

## نتیجهٔ صریح

۱۲ Case دارای `owner_decision_required` به هفت تصمیم غیرهم‌پوشان نگاشت شد. برای
هر تصمیم، گزینه‌ها، اثر، ریسک، شاهد لازم، نقش مالک و یک پیش‌فرض محافظه‌کارانه
ثبت شده است. پیش‌فرض پیشنهادی **تأیید کسب‌وکار نیست** و Command مربوط تا ثبت
گزینهٔ انتخاب‌شده، نقش تأییدکننده و مرجع شاهد بسته می‌ماند.

| تصمیم | Case | پیش‌فرض محافظه‌کارانه | پیش از کدام Slice لازم است؟ |
|---|---:|---|---|
| Aliasهای `RBANKDARFT`/`RCASHDRAF` | ۲ | حفظ Literal دقیق Legacy تا Parity | Summary read model |
| Debit و Credit هم‌زمان | ۱ | رد ردیف | Parser staging |
| ردیف مبلغ صفر | ۱ | رد ردیف | Parser staging |
| فعال‌سازی HDR/StartRow/Seperator/IsArabic | ۴ | غیرفعال تا Parser typed و تست‌شده | Parser staging |
| ابزار از قبل Reconciled | ۱ | Conflict و رد | Confirm |
| Reversal جلسهٔ Confirmed | ۲ | ممنوع تا Reversal ممیزی‌شده | Reverse command |
| Cancel/Archive Header خالی | ۱ | Archive با دلیل | Cancel command |

## فرم تصمیم‌گیری مالک

### BR-DEC-001 — Aliasهای Summary

- گزینه A: Literalهای دقیق Legacy حفظ شوند؛ ریسک آن حفظ احتمالی حذف اشتباه است.
- گزینه B: Alias table نسخه‌دار هر دو املای Summary/Matching را بپذیرد؛ رفتار
  Legacy تغییر می‌کند و Parity ردیفی لازم دارد.
- توصیهٔ موقت: A. Count تفکیکی Clone اکنون نشان می‌دهد `RCASHDRAFT=146576` و
  `RCASHDRAF=0`؛ بنابراین واگرایی مادی است، نه مجوز Normalize. شاهد باقیمانده:
  خروجی تفاضلی هر یازده Metric روی Fixture یکسان و تأیید صریح مالک.

### BR-DEC-002 — Debit و Credit هم‌زمان

- گزینه A: ردیف با Error پایدار رد شود.
- گزینه B: ردیف فقط در Staging قرنطینه و برای Review نگه داشته شود.
- توصیهٔ موقت: A. شاهد لازم: نمونهٔ تأییدشدهٔ بانکی اگر چنین ردیفی معنای واقعی دارد.

### BR-DEC-003 — مبلغ صفر

- گزینه A: ردیف قبل از Commit رد شود.
- گزینه B: به‌عنوان Informational و خارج Ledger در Staging نگهداری شود.
- توصیهٔ موقت: A. شاهد لازم: Fixture فرمت بانکی که معنای ردیف صفر را ثابت کند.

### BR-DEC-004 — Optionهای Dormant Profile

- گزینه A: HDR/StartRow/Seperator/IsArabic تا وجود Parser typed و تست‌شده غیرفعال بمانند.
- گزینه B: زیرمجموعهٔ مصوب در Profile version مشخص فعال شود.
- توصیهٔ موقت: A. شاهد لازم: Profile واقعی Redacted و Parity خروجی برای هر Format.

### BR-DEC-005 — Instrument از قبل Reconciled

- گزینه A: Conflict و رد؛ مسیر بررسی/Reverse جدا باشد.
- گزینه B: فقط اگر Command identity و مالکیت همان Session دقیقاً برابر است،
  نتیجهٔ قبلی Idempotent برگردد.
- توصیهٔ موقت: A. شاهد لازم: سیاست Idempotency و Cross-session مصوب.

### BR-DEC-006 — Reversal جلسهٔ Confirmed

- گزینه A: تا قرارداد Reversal ممیزی‌شده همهٔ Reverseها Deny شوند.
- گزینه B: Session و تمام Instrumentها با Reason/Actor/Version به‌صورت اتمیک برگردند.
- توصیهٔ موقت: A. شاهد لازم: سیاست حسابداری، SoD احراز‌شده و Failure injection.

### BR-DEC-007 — Cancel/Archive Header خالی

- گزینه A: Header/Rows با Reason به State آرشیوی Transition کنند.
- گزینه B: فقط Session تأییدنشده، خالی و بدون Link با Version guard حذف سخت شود.
- توصیهٔ موقت: A. شاهد لازم: Retention policy و تعریف مصوب تفاوت Discard/Cancel.

در همهٔ موارد «توصیهٔ موقت» فقط Safe default مهندسی است؛ ستون Selected option در
Artifact هنوز `null` و وضعیت همهٔ تصمیم‌ها `NOT_APPROVED` است.

## چرا این بسته لازم است؟

Static analysis می‌تواند رفتار Legacy و ریسک آن را اثبات کند، اما نمی‌تواند
به‌جای مالک خزانه/مالی دربارهٔ معنای ردیف صفر، سیاست Reversal یا Retention تصمیم
بگیرد. این Register مرز «دانستهٔ فنی» و «انتخاب کسب‌وکار» را ماشین‌خوان می‌کند
تا توصیهٔ مهندسی ناخواسته به Requirement قطعی تبدیل نشود.

## Gate ثبت تصمیم

یک تصمیم فقط وقتی از `NOT_APPROVED` خارج می‌شود که این سه جزء کنار هم ثبت شوند:

1. گزینهٔ انتخاب‌شده از گزینه‌های موجود؛
2. نقش/هویت مالک مجاز و زمان تأیید؛
3. مرجع شاهد لازم مانند Fixture Redacted، Parity output یا UAT احراز‌شده.

تا آن زمان اجرای Source/Target command، Pilot یا ادعای برابری Runtime مجاز نیست.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_owner_decision_register_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_owner_decision_pack.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_negin_erp_bank_reconciliation_owner_decision_pack.py `
  --differential-acceptance G:\NeginAI\artifacts\varanegar_analysis\ui\negin_erp_bank_reconciliation_differential_acceptance_20260827.json `
  --type-alias-aggregates G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_type_alias_aggregates_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\negin_erp_bank_reconciliation_owner_decision_register_20260827.json
```

Builder فقط Artifact پذیرش تفاضلی و Snapshot تجمیعی Alias را می‌خواند؛ اتصال
دیتابیس، UI action، هویت واقعی، Approval استنباطی یا تغییر داده ندارد. Count
Clone برای `BR-DEC-001` شاهد جزئی است و وضعیت تصمیم همچنان `NOT_APPROVED` می‌ماند.
