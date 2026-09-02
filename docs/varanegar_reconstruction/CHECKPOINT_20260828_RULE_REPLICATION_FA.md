# Checkpoint شناخت صدور سند و Replication قواعد

تاریخ: ۲۰۲۶-۰۸-۲۸  
وضعیت: **PASS؛ Bundle آفلاین، ۲۱ منبع Hash‌شده و ۳۳ Gate موفق**

## نتیجه

این Checkpoint نقطهٔ ادامهٔ قابل‌بازتولید شناخت وارانگار است. چهار Artifact اصلی
را به Extractor، Builder، تست و سندشان متصل می‌کند:

- قرارداد صدور سند و Policy حسابداری؛
- مرز Transport/Receipt/Retry سرویس Replication؛
- دفتر ۵۶ ریسک باز شامل ۳۱ ریسک بحرانی؛
- Traceability شامل ۲۲۱ Assignment و صفر ماژول Command-ready.

## مرزهای مثبت تثبیت‌شده

- Package ارسال پیش از Upload در Binary outbox دیتابیس ماندگار می‌شود؛
- Completion محلی و FTP پیش از Helper تأیید دیتابیس است؛
- اجرای SQL دریافت و `LastExecLog` در یک Transaction قرار دارند؛
- `false` یا Exception در Executor پیش از Receipt به Rollback می‌رسد؛
- Commit و Execute در Connector خطا را Propagate می‌کنند.
- مرز تراکنش صدور Desktop تا Commit/Dispose با IL مستقر تثبیت شده است.
- شش Trigger قواعد خروجی `InsertToLog` را می‌گیرند اما بعد از Call مصرف نمی‌کنند؛
  بنابراین اثر مستقیم `IDENT_CURRENT` بر Control-flow همین Triggerها ادعا نشد.
- دو Trigger باینری Voucher خروجی `IDENT_CURRENT` را در جدول Mapping مصرف می‌کنند؛
  آن دو جدول Index/FK ندارند و خالی‌اند، پس Failure window قطعی ولی Incident جاری نامشهود است.
  Reader SQL و literal مستقیم در ۶۲ Assembly اصلی نیز صفر است؛ مصرف بیرونی نامعلوم ماند.
- `InsertToLog` در ۱۱۴۲ Trigger فعال روی ۳۷۶ جدول و شش Schema مصرف می‌شود؛ ۱۱۴۰
  تعریف نشانهٔ Cursor، صفر `TRY/CATCH`، سه نشانهٔ `XACT_ABORT` و صفر
  `NOT FOR REPLICATION` دارند. این Footprint فراگیر است، نه شاهد استفادهٔ اخیر
  تک‌تک جدول‌ها یا Delivery موفق.
- توزیع Trigger/Table به‌ترتیب `dbo=426/140`، `GNR=321/107`،
  `SLE=282/92`، `Acc=53/17`، `inv=45/15` و `ICA=15/5` است؛ بنابراین
  Blast radius ثبت تغییر، فروش/انبار/خرید/حسابداری/هسته را هم‌زمان لمس می‌کند.
- ۱۱۴۰ Trigger تک‌رویدادی Cursor-based هستند: ۳۷۶ Delete، ۳۸۲ Update و ۳۸۲
  Insert؛ فقط دو Trigger بدون Cursor هر سه Event را پوشش می‌دهند.

## شکاف‌های باز تثبیت‌شده

- Receipt یکتا، Replay-safe، Gapless و Multi-row safe اثبات نشد؛
- ترتیب قطعی Packageها و Serialization یک Sender برای هر Center اثبات نشد؛
- Content signature، Center binding رمزنگاری‌شده و Encryption شاخهٔ FTP اثبات نشد؛
- Hook پس از دریافت با Receipt فایل اتمیک نیست و Identity targetهای Clone صفرند؛
- شکست خود Rollback Propagate نمی‌شود؛
- File/FTP cleanup پیش از Commit انجام می‌شود و Recovery خودکار اثبات نشد؛
- نتیجهٔ Boolean Reset پس از Commit محلی توسط Caller نادیده گرفته می‌شود؛
- Single-flight بودن callback دوره‌ای سرویس اثبات نشد؛ Timer فعال می‌شود، اما
  تنظیم صریح non-repeating و Mutex/Monitor/Interlocked/Semaphore در `Run` دیده نشد؛
- Deadline مثبت و محدود برای همهٔ شاخه‌های اجرای Package اثبات نشد؛ Executor
  ثابت‌های `CommandTimeout` برابر ۰، ۶۰۰ و ۳۰۰۰۰ دارد و Cancellation سراسری دیده نشد؛
- در رد فنی Package، Local پس از Rollback پنج حذف فایل و FTP سه حذف فایل محلی
  دارد؛ Quarantine پایدار و Retry parity میان دو Transport اثبات نشد؛
- Receipt/Log باقی‌مانده به‌علت Cleanup/Provisioning تاریخچهٔ کامل و immutable نیست.
- Stored Procedure اصلی صدور مالک Transaction نیست و اتکای آن به Caller ثبت شد؛
- سیاست جاری، تاریخچهٔ grouping را کامل بازتولید نمی‌کند و Source snapshot به‌علت
  `NOLOCK` committed-consistent نیست؛
- IsolationLevel صریح Provider، Editor منتسب‌شده، انتشار اتمیک Template و
  سازگاری Schema انتقال Template اثبات نشدند.

## سطح ادعا

هیچ رخداد Race، Replay، Commit failure، Rollback failure، FTP فعال در مرکز مشخص،
Exploit یا Identity mutation جاری مشاهده نشده است. یافته‌ها قرارداد و Failure
window کد/Schema هستند، مگر جایی که Artifact صریحاً Aggregate Snapshot را ثبت
کرده باشد.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_analysis_checkpoint_20260828.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\varanegar_analysis_checkpoint_20260828.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest -q `
  G:\NeginAI\tests\test_varanegar_analysis_checkpoint_20260828.py `
  G:\NeginAI\tests\test_varanegar_rule_replication_transport_boundary.py `
  G:\NeginAI\tests\test_varanegar_voucher_creation_atomicity_policy.py
```

Builder فقط فایل‌های Redacted پروژه را می‌خواند و هیچ اتصال DB/Network/UI یا
اجرای Assembly/Command عملیاتی ندارد.

## Artifact

- `artifacts/varanegar_analysis/varanegar_analysis_checkpoint_20260828.json`
- `scripts/windows/build_varanegar_analysis_checkpoint_20260828.py`
- `tests/test_varanegar_analysis_checkpoint_20260828.py`
