# چاپ Batch، Partial Success و Completion — ۲۰۲۶-۰۸-۲۹

## نتیجه

`RPT-09` یک گزارش واحد نیست؛ Orchestrator ترتیبی هفت خروجی Templateمحور است.
`PrintCommand` با ۷۲۰ Instruction چند Method چاپ را Dispatch می‌کند و میان آن‌ها
`Thread.Sleep` دارد، اما DataContext/Transaction یا Rollback در Orchestrator منتخب
دیده نمی‌شود.

هفت مسیر Render شناسایی شد:

- چهار مسیر `PrintBeforeReportJoze`، `PrintDrfact`، `PrintExitList` و
  `PrintExitReportJoze` پس از `ShowReportFact`، `PrintedCompleted` را می‌خوانند و
  سپس Completion command فراخوانی می‌کنند.
- سه مسیر `PrintExitForm`، `PrintRetOrder` و `PrintTeamPakhsh` Render می‌شوند ولی
  Completion audit متناظر در Method منتخب ندارند.

دو Completion handler به Commit می‌رسند: `SetPrintCompleatedReportJoze` مستقیم و
`SetPrintCompleatedDrFact` از طریق `SaveCommandDRFact`. در سه Method منتخب هیچ
Rollback محلی دیده نشد. این شاهد Call/ownership ایستا است، نه اثبات Outcome فیزیکی.

## قرارداد Partial Success

شکست خروجی سوم نباید دو خروجی موفق قبلی را انکار کند یا باعث چاپ کور دوباره شود.
پاسخ مقصد باید Outcome هر Item و خلاصه Batch را جدا بدهد. Idempotency key پیشنهادی:
`request_id + document_id + output_kind + template_hash`. Retry فقط برای Itemهای
Failed یا Unconfirmed مجاز است.

Stateهای مقصد: `PENDING`، `RENDERED`، `PRINT_CONFIRMED`، `AUDIT_COMMITTED`،
`FAILED` و `CANCELLED`. هر Transition یک Audit/Outbox event تغییرناپذیر دارد.

## Golden Caseهای موج اول

1. موفقیت هر هفت خروجی و فقط چهار Completion event قدیمی؛
2. شکست خروجی سوم پس از دو موفقیت؛
3. Render موفق و Commit ثبت چاپ ناموفق؛
4. Preview با صفر Completion command؛
5. Retry همان Item/Template با جلوگیری از Audit تکراری.

## Playbook

Batch request، Flag خروجی‌ها، مجموعه اسناد و Template hashها را Pin کن؛ Permission،
وضعیت توزیع، OperationDate و ExitNo را برای هر Item جدا کنترل کن؛ محل شکست را در
Dispatch ترتیبی بیاب؛ Render و Completion commit را مستقل تطبیق بده؛ خروجی موفق
را کورکورانه تکرار نکن؛ خطای Template، Device/Render، Audit commit و پیام Mixed
result را جدا طبقه‌بندی کن.

Query/Formula Templateها و Result parity همچنان اثبات‌نشده‌اند. Risk جدید ساخته
نشد و `R-007/R-017/R-084` و ریسک‌های موجود reuse شدند. هیچ Form، Template، Report،
Procedure یا Command اجرا و هیچ داده‌ای تغییر داده نشد.
