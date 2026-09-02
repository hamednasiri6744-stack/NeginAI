# قرارداد آمادگی پیاده‌سازی مغایرت بانکی ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Artifact معتبر است؛ سه برش Read-side مجاز به شروع‌اند و Command/Pilot/Production آماده نیست**

## تصمیم اجرایی

شناخت ایستای این دامنه برای Schema/Read model پروفایل، Parser ایزولهٔ Staging و
Candidate فقط‌خواندنی Summary کافی است. برای Match، Unmatch، Confirm، Cancel یا Reverse کافی نیست.
این مرزبندی عمداً میان «قرارداد کشف‌شده» و «رفتار اجرا و تأییدشده» فاصله می‌گذارد.

Artifact از ۳۰ شاهد معتبر ساخته شده و این پوشش را یک‌جا تثبیت می‌کند:

- ۱۵ جدول Source، شش نگاشت نوع‌دار Match و Signature چهارده‌پارامتری Summary؛
- ۵۸ Method contract ایستا در Guard، Import، Persistence، Transaction، Match، Summary UI و State؛
- ۹۳ Golden case مصنوعی و ۱۰۰ UAT case بدون هویت؛
- قراردادهای مقصد شامل سه Entity Profile، چهار Entity Staging، چهار Projection/
  پنج Query، پنج Lifecycle state/هفت Transition و Envelope پنج Command است؛
- شش ستون Canonical Import، دو Parser مجری SQL خام، HDR مصرف‌شدهٔ صفر و مرز
  Commit غیراتمیک Legacy؛
- Defect قطعی Confirm که با Cursor نامرتب و Returnهای داخلی، حداکثر یک Link را
  در هر اجرا `IsReconciled` می‌کند؛
- ترکیب Outer transaction که همان Update اول را موفق تلقی و همراه markerهای
  Confirm Commit می‌کند، بدون Guard مجوز/تاریخ داخل DoAccept؛
- ۱۱۶ تعهد Acceptance تفاضلی شامل Reversal authorization/SoD/Fault و Discard/Cancel که هنوز اجرای واقعی صفر دارند؛
- Snapshot Aggregate جاری با صفر Session/Bill/Link/Profile؛ در نتیجه Frequency
  Defect و Runtime parity از Clone فعلی قابل‌اندازه‌گیری نیست؛
- Snapshot جداگانهٔ Alias روی ۱۹۲٬۱۰۶ ردیف Cardex، `RCASHDRAFT=146576` و
  `RCASHDRAF=0` را نشان می‌دهد؛ این ریسک Summary را تقویت می‌کند ولی جای
  Runtime parity و تصمیم مالک را نمی‌گیرد؛
- صفر Profile واقعی در Snapshot Clone، صفر UAT احراز‌شده، صفر تأیید مالک فرایند،
  صفر Root بسته‌شده و صفر Command اجراشده در مقصد.

## نه بُعد آمادگی

| بُعد | وضعیت | مانع اصلی |
|---|---|---|
| Source و Read model | قرارداد مقصد آماده، Runtime باز | Row-result parity مقصد |
| Import و Staging | قرارداد مقصد آماده، پیاده‌سازی باز | Profile واقعی و Parser worker امن |
| Profile versioning | قرارداد مقصد آماده، Parity مسدود | ردیف واقعی و Owner-approved Version/Approval |
| Session Summary | Read model/فرمول مقصد آماده؛ واگرایی Count یک Alias ثبت شده | Runtime parity و تصمیم مالک برای دو Alias |
| Match/Unmatch | Command envelope آماده، اجرا مسدود | Tolerance، Idempotency و UAT |
| Confirm/Transaction/Cardex | Command envelope آماده، پیاده‌سازی لازم | Fault/rollback/concurrency |
| Authorization/SoD | فقط طراحی | UAT احراز‌شده و Owner approval |
| Cancel/Reverse | State/Command contract آماده، معنای Owner مسدود | تصمیم‌های 006/007 و UAT |
| Rootهای حل‌نشده | Runtime/Owner evidence لازم | سه Root هنوز بسته نشده‌اند |

نکتهٔ مهم State: Legacy ستون Status صریح ندارد؛ Confirm با
`ConfirmerId/ConfirmDate` شناخته می‌شود و همان مسیر `Amount` را صفر می‌کند. صفر
شدن Amount فرمول محاسباتی Summary نیست و نباید به مقصد منتقل شود.

## ترتیب ساخت مجاز

1. **Profile catalog و Queryهای فقط‌خواندنی:** Schema مقصد، Scope حساب و Fixtureهای
   نسخه‌دار/تأییدشده تعریف شوند؛ خروج فقط با Row parity.
2. **Upload/Parser/Staging ایزوله:** Parser نوع‌دار، Content validation و منع کامل
   SQL/Provider/Path تأمین‌شده از Profile؛ هنوز هیچ Command مالی ندارد.
3. **Session Read model و Summary:** Candidate با یازده فرمول اثبات‌شده ساخته شود؛
   خروج فقط پس از Runtime parity و تعیین تکلیف دو Alias املایی.
4. **Match/Unmatch صریح و Idempotent:** فقط با ExpectedVersion، IdempotencyKey و
   سیاست مبلغ تأییدشده؛ Persistence داخل Event UI ممنوع است.
5. **Confirm/Transaction/Cardex:** یک مالک Transaction مقصد، Rollback کامل و
   Failure injection اجباری است.
6. **Cancel یا Compensating reversal:** فقط پس از تصمیم مکتوب مالک فرایند دربارهٔ
   State، Audit و اثر کاردکس.

سه مرحلهٔ اول اجازهٔ شروع طراحی/پیاده‌سازی محدود Read-side دارند؛ سه Command
بعدی هنوز Gateهای مسدودکننده دارند.

## هشت Gate اجباری Pilot

1. Fixture واقعی، Redacted، Versioned و Approved برای Profile؛
2. Parity سطرها و Diagnosticهای Import؛
3. Runtime parity هر یازده فرمول Summary و دو Alias Type؛
4. سیاست Tolerance مبلغ با تأیید مالک؛
5. UAT احراز‌شدهٔ Allow/Deny برای هر هفت Capability، شامل Reversal مستقل؛
6. Failure injection بدون هیچ Partial persistence؛
7. تصمیم Owner دربارهٔ Cancel/Reverse؛
8. شاهد Runtime/Owner بدون هویت و مقدار تجاری برای هر سه Root.

## Definition of Done مقصد

- Authorization سمت سرور باید Capability، Feature، Fiscal/DC/Account scope،
  OperationDate، State transition و Domain validation را با Deny-first ترکیب کند.
- هر Mutation باید ExpectedVersion و IdempotencyKey داشته باشد.
- Parser در Staging ایزوله اجرا شود و هیچ SQL، Provider یا Path از Profile را
  قابل‌اجرا نکند.
- Confirm باید Header، Link و Cardex را در یک Transaction مقصد Commit/Rollback کند.
- Audit باید Command، Aggregate، Reason، Before/After state و Correlation را ثبت
  کند، نه Credential، Raw SQL یا Payload تجاری خام را.
- Golden، Negative، Replay، Concurrency، Failure-injection و UAT احراز‌شده باید
  پیش از Pilot پاس شوند.
- وارانگار در تمام Discovery و Parity فقط‌خواندنی می‌ماند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_implementation_readiness_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_implementation_readiness.py`
- `tests/test_varanegar_ui_evidence.py`

این قرارداد هیچ Target implementation، اجرای Command، UAT احراز‌شده یا آمادگی
Pilot/Production را ادعا نمی‌کند.
