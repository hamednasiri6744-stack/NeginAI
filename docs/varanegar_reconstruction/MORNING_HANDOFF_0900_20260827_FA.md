# تحویل صبح تحلیل وارانگار برای ساخت ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Baseline چندمنبعی قوی برای طراحی؛ نه شناخت کامل Runtime و نه مجوز Write**

## پاسخ روشن

شناخت ما اکنون برای تعیین مرز ماژول‌ها، طراحی Slice اول فقط‌خواندنی، تعریف
قراردادهای Command پرریسک، برنامه مهاجرت و فهرست تصمیم‌های مالک کافی است. اما
هنوز نمی‌توان گفت همه Branchهای Runtime، Settingهای مؤثر، Grant اشخاص، Layout
پویا، Integration خارجی یا نتیجه واقعی هر Command را کامل می‌شناسیم.

Baseline فعلی شامل ۱۸ دامنه معتبر، ۴۴۵ Form candidate، ۸۳۶ Route، بیست Workflow،
بیست Report/output، چهارده ماژول مقصد، ده Process انتها‌به‌انتها، ۸۷۷ Golden case
مصنوعی و ۴۶ ریسک باز (۲۴ بحرانی) است. Command-ready module و
Implementation-ready process هر دو صفرند.

## مهم‌ترین مرزهای کشف‌شده

- مشتری/کالا: دو Screen و ۱۳۰ Input؛ ۶۴ Golden طراحی‌شده ولی اجرا‌نشده؛
- تأمین‌کننده: یک Screen و دوازده Input؛ Guard پرداخت، Accounting group،
  Contact/DL، Attachment و Cardex؛ ۳۲ Golden طراحی‌شده ولی اجرا‌نشده؛
- Context عملیاتی: سه Screen و ۲۶ Input؛ سال عملیاتی/مالی، DC، دفتر فروش،
  انبار، نوع موجودی و PriceMethod جدا؛ ۹۶ پیوند Golden اجرا‌نشده؛
- قیمت/تخفیف زمینه‌ای: دو Screen و چهل Input؛ Scope، Priority، تاریخ مؤثر،
  Rounding، Close/History و Explain؛ ۶۴ Golden طراحی‌شده ولی اجرا‌نشده؛
- هویت/دسترسی: شانزده Route مدیریت کاربر/گروه/Scope؛ Runtime-matched form و
  Grant مؤثر هر دو صفر؛
- تنظیمات سیستم: پانزده Route پیکربندی‌شده و فقط چهار Runtime-matched؛
  precedence مؤثر و اثر Publish/Close صفر؛
- تاریخ قطعی: پنج Route و چهار Command مستقل فروش/خرید/مالی/تنخواه؛ سه Form
  unmatched و Runtime effect/Golden execution صفر؛
- سفارش/فروش/برگشت: سه Screen و ۱۴۰ Input؛ گراف ۷۳ Trigger و Frontier باز؛
- خزانه: سه Command، دو View قابل‌نوشتن، ۲۹ Trigger و ۵۱ تعهد پذیرش اجرا‌نشده؛
- سند انبار/توزیع: ۸۷ Root trigger، ۳۸ Write target حل‌شده و گراف Truncated؛
- فاکتور خرید: چهار Root trigger و ۲۹ Write target؛ کپی خاموش/روشن‌کردن Trigger
  در مقصد ممنوع؛
- حسابداری: هفت Command candidate؛ تفکیک سند تولیدی/دستی و Exact SQL binding
  هنوز Gate است.

دو Invariant معماری نیز در بازبینی نهایی قفل شد: ماژول Configuration تنها مالک
`config_definition/config_value/config_version` و دو Command انتشار
General/WebService است؛ و هر ۸۷۷ Golden case دقیقاً به یک فرایند از ده فرایند
مقصد نگاشت شده است (بدون مورد جاافتاده یا چندمالکیتی).

## ترتیب پیشنهادی ساخت

1. تصمیم Stack، RPO/RTO، محیط Target ایزوله و Source adapter فقط‌خواندنی؛
2. Kernel سازمان/Context و Authorization/Scope توضیح‌پذیر؛
3. List/Search/Detail فقط‌خواندنی مشتری، کالا، تأمین‌کننده و گزارش‌های محدود؛
4. Snapshot تغییرناپذیر، Crosswalk UUID، Quarantine و Reconciliation؛
5. Harness مصنوعی برای ۸۷۷ Golden case، Fault injection، Idempotency و Outbox؛
6. Commandهای Master فقط پس از Review مالک و فقط روی Target ایزوله؛
7. سپس Sales/Stock/Distribution/Treasury/Procurement/Accounting با Gate دامنه؛
8. در پایان UAT واقعی، Performance، Security، Restore، Delta reconciliation و
   Rollback drill پیش از Pilot/Cutover.

## تصمیم‌هایی که از کاربر/مالک لازم است

- انتخاب Stack نهایی backend/web/database/deployment؛
- RPO/RTO و مسئول Backup/Restore؛
- معنای DC=0/1 و ترکیب‌های معتبر Office/Stock/Year؛
- نام مالک Master، Stock، Treasury، Procurement، Accounting، Reports و
  Migration review؛
- انتخاب اولین Workflow احرازشده فقط‌خواندنی برای UAT.
- تعداد کاربر همزمان و رشد یک‌ساله؛
- نیاز یا عدم نیاز عملیات Offline انبار/فروشنده در Release اول.

## مرز ایمنی و صداقت

هیچ Write، Delete، Confirm، Status change یا Command عملیاتی روی وارانگار اجرا
نشد. Clone و Runtime source فقط‌خواندنی ماندند. Static IL/label/SQL name شاهد
Result parity نیست. Clone نیز به‌تنهایی حقیقت زنده عملیاتی نیست.

## Artifact ماشین‌خوان

- `artifacts/varanegar_analysis/ui/negin_erp_morning_readiness_handoff_20260827.json`
- `scripts/windows/build_negin_erp_morning_readiness_handoff.py`

این Artifact پس از Snapshot نهایی ساعت ۰۸:۴۶، با Hash و شمارش Bundle نهایی
دوباره تولید و اعتبارسنجی شد.
