# Blueprint مبتنی بر شواهد برای ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **طرح ساخت تأییدپذیر؛ هنوز انتخاب فناوری، Command-ready یا Pilot-ready نیست**

## نتیجه

شناخت فعلی برای شروع طراحی و ساخت یک برش فقط‌خواندنی کافی است، اما برای
جایگزینی عملیاتی وارانگار کافی نیست. مدل مقصد باید ابتدا به‌صورت یک
`Modular Monolith` با مرزهای دامنه‌ای صریح ساخته شود؛ این انتخاب درباره شکل
معماری است و به معنی انتخاب زبان، Framework یا Database نیست.

Blueprint شامل ۱۴ ماژول و ۷ فاز است. برآورد کل برای تیم کوچک متمرکز ۲۱ تا ۳۳
هفته و اولین برش قابل استفاده فقط‌خواندنی ۳ تا ۵ هفته است. این اعداد برآورد
مهندسی‌اند، نه تعهد تقویمی؛ کیفیت داده، دسترسی کاربران واقعی و نتیجهٔ UAT می‌تواند
آن‌ها را تغییر دهد.

## ۱۴ مرز مالکیت

1. Platform: Command idempotency، Audit، Outbox، Approval و Job؛
2. Organization Context: شرکت، سال، مرکز، دفتر فروش، انبار و تاریخ عملیات؛
3. Identity & Authorization: نقش، Capability، Data scope و Decision trace؛
4. Configuration: تنظیمات نسخه‌دار و Resolution trace؛
5. Master Data: کالا، طرف‌حساب، مسیر، پرسنل، خودرو و تیم؛
6. Pricing Rules: قیمت، قرارداد، تخفیف، جایزه و Calculation trace؛
7. Sales: سفارش، فروش، برگشت و Conversion attempt؛
8. Inventory: Ledger موجودی، رزرو، Voucher، Batch و Exit؛
9. Distribution: مأموریت توزیع، پیوند فروش، تحویل، برگشت و Exit adjustment؛
10. Receivables & Treasury: دریافت، تخصیص، مانده باز و چک دریافتی؛
11. Procurement & Payables: خرید، مرجوعی، پرداخت و چک پرداختنی؛
12. Accounting: PreVoucher، Voucher، Journal، Posting و بستن دوره؛
13. Reporting & Documents: Projection، Export، Print و Print-completion؛
14. Integration & Migration: Snapshot، Crosswalk، Quarantine و Reconciliation.

هر ماژول فقط جداول خودش را می‌نویسد. همکاری بین ماژول‌ها با Command contract
داخلی یا Event/Outbox انجام می‌شود. گزارش‌های میان‌دامنه‌ای Projection نسخه‌دار
می‌خوانند، نه Join دلخواهی که مستقیم به مرورگر داده شود.

## قرارداد اجباری هر Command مقصد

حداقل Envelope:

`command_id + aggregate_id + expected_version + operational_date + fiscal_year + dc_ref + actor_context`

سرور قبل از تغییر باید Authentication، Capability، Data scope، نسخه تنظیمات،
تاریخ عملیات، Transition مجاز، Validation دامنه و Idempotency را کنترل کند. نتیجه
نیز باید نسخه و وضعیت جدید، شناسه Audit event و وضعیت Reconciliation را برگرداند.

این الزام مستقیماً از شکاف Legacy می‌آید: هر هشت مسیر Mutating تحلیل‌شده فاقد
پارامتر صریح Request/Command/Idempotency بودند.

## ترتیب ساخت

| فاز | خروجی قابل تحویل | برآورد |
|---|---|---:|
| P0 | DB مستقل مقصد، Migration، Audit/Outbox/Idempotency، Snapshot فقط‌خواندنی و Reconciliation shell | ۲–۳ هفته |
| P1 | مرور وب احراز‌شده و Scopeدار اطلاعات سازمان/کالا/طرف‌حساب/مسیر | ۳–۵ هفته |
| P2 | Trace قواعد قیمت، Order/Sale read model و تمرین Command مصنوعی | ۴–۶ هفته |
| P3 | Stock/Cardex بازسازی‌پذیر، Exit و State machine توزیع | ۶–۹ هفته |
| P4 | دریافت/تخصیص/مانده باز، برگشت فروش و چک دریافتی | ۴–۶ هفته |
| P5 | خرید/مرجوعی/پرداخت/چک پرداختنی و برابری کاردکس تأمین‌کننده | ۴–۶ هفته |
| P6 | UAT نقش‌ها، امنیت/کارایی/Recovery، Delta reconciliation و تمرین Rollback | ۴–۶ هفته |

فازها Gateدارند؛ تقویم به‌تنهایی اجازه ورود به فاز بعدی نیست. P1 اولین محصولی
است که می‌توان زودتر به کاربر نشان داد، اما فقط‌خواندنی است.

## شواهدی که طرح را محدود می‌کنند

- Manifest هجده دامنه `PASS` است و ۴۴۵ Form candidate شناخته شده؛
- ۴۰ Node مجوز چهار Route باز و ۲۲ State در سه State machine ثبت شده؛
- ۱۱ Trace فرمان فعال و ۸۷۷ Golden case مصنوعی داریم (۷۷ مسیر فعال، ۱۵۴
  Orchestrator پرتراکم، ۲۱۵ Extension مادی، ۱۷۵ Report/Output، ۶۴ Master data
  مشتری/کالا و ۱۹۲ مورد تأمین‌کننده/Context/قیمت)؛
- ۲۰ Report/output surface تفکیک شده؛
- Hash معنایی Baseline کامل‌شده:
  `f45672cb2ea0fa9b8dd2d14fbd036310faf1cdfc62b026e05fabd5ed3b095ebc`.

## Definition of Done هر برش

- Migration تکرارپذیر و Import قابل بازاجرا؛
- تست Deny نقش و Data scope؛
- Golden case موفق، Reverse، stale version، Retry و Failure injection؛
- تطبیق Ledger و Projection با اختلاف توضیح‌پذیر؛
- Audit/Outbox تغییرناپذیر و بازبینی PII/Secret/Log؛
- تست Performance، Backup/Restore و Rollback؛
- UAT واقعیِ احرازشده و تأیید مالک کسب‌وکار.

## مرز فعلی

این Blueprint هیچ اجازه‌ای برای Write روی وارانگار، Dual-write، Repair خودکار
ناهنجاری‌های Legacy یا Cutover ایجاد نمی‌کند. Technology stack هنوز توسط کاربر
انتخاب نشده و هیچ دامنه‌ای فعلاً Command-ready یا Pilot-ready اعلام نشده است.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json`
- `scripts/windows/build_varanegar_target_erp_blueprint.py`
- `tests/test_varanegar_ui_evidence.py`
