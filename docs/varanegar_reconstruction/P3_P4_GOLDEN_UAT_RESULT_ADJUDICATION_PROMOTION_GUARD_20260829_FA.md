# ماتریس داوری نتیجهٔ Golden/UAT و Promotion Guard برای P3/P4

این سند چهار Outcome تشخیصی Result parity را به تصمیم‌های قابل‌ممیزی برای هشت Packet گزارش و Export متصل می‌کند. هدف، جلوگیری از تبدیل یک Match ظاهری، Exception یا شاهد ناقص به پذیرش CG-05 و آمادگی عملیاتی است.

## دامنه

- هشت Packet: پنج فرمان P3 و سه Export در P4.
- ۵۶ Golden/UAT Case: هفت Case برای هر Packet.
- چهار Outcome تشخیصی و ۳۲ مسیر داوری.
- ۲۲۴ اتصال Outcome-to-Case.
- دوازده Promotion Guard برای هر Packet، در مجموع ۹۶ انتساب Guard.
- ۱۶۰ انتساب بُعد parity و ۲۷ انتساب Receipt زیر CG-05.

این اعداد cross-link طراحی هستند و Case یا اجرای تازه ایجاد نمی‌کنند. Lower bound طراحی ۱۴۰۴، Risk count برابر ۸۴ و Trace assignment برابر ۳۴۳ باقی می‌ماند.

## قواعد چهار Outcome

### Match مبتنی بر hash پذیرفته‌شده

`MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE` تنها Outcomeای است که می‌تواند Packet را وارد بازبینی پذیرش CG-05 کند. این ورود نیازمند manifestهای جاری، disposition پذیرفته‌شدهٔ key/grain/dimension، Receiptهای جاری، بازبینی مستقل مالک و نبود expiry/conflict/supersession است.

Match به‌تنهایی CG-05 را نمی‌بندد و هیچ Command/Pilot readiness نمی‌سازد.

### Exception نسخه‌دار و تأییدشده

`EXPLAINED_OWNER_APPROVED_VERSIONED_EXCEPTION` Result parity نیست. Exception باید scope، نسخه، تاریخ اثر/انقضا، Risk acceptance مستقل، Conflict/Supersession و مرز Containment/Rollback داشته باشد. CG-05 باز می‌ماند و Promotion خودکار ممنوع است.

### شاهد نامعتبر یا کهنه

`INVALID_OR_STALE_EVIDENCE_RECOLLECTION_REQUIRED` تصمیم parity ایجاد نمی‌کند. Rejection code، مرز manifest نامعتبر، hash مرجع و مجوز جداگانهٔ Recollection لازم است. خود این ماتریس مجوز Recapture نمی‌دهد.

### اختلاف توضیح‌نداده‌شده

`UNEXPLAINED_DIFFERENCE_BLOCKS_CG05` Hard Block است. اولین بُعد نامنطبق، Difference manifest، مجموعهٔ Case/Packet متاثر، Receipt نقش پاسخ‌گو و Attestation منع Promotion باید ثبت شود.

## دوازده Promotion Guard

1. Manifestهای Fixture، Output و Comparison جاری و hash-pinned.
2. مجموعهٔ دقیق Case و پوشش case-kind.
3. مجوز جداگانه و Capture هر دو سمت Legacy/Target.
4. disposition مربوط به stable key، grain، cardinality و inclusion.
5. پذیرش تک‌تک ابعاد parity لازم.
6. پذیرش جاری همهٔ Receiptهای قابل‌اعمال CG-05.
7. صفر اختلاف توضیح‌نداده‌شده و Unknown outcome.
8. Policy و Risk acceptance نسخه‌دار برای Exception احتمالی.
9. بازبینی مستقل مالک پاسخ‌گو و Separation of Duties.
10. کنترل Version، Expiry، Conflict و Supersession.
11. اجرای Golden/UAT ایزوله و پذیرش CG-04.
12. تصمیم جداگانه برای Command readiness و Pilot readiness.

هر Guard در وضعیت فعلی unsatisfied است. شکست هر Guard نتیجهٔ `STOP_NO_PROMOTION` دارد.

## وضعیت فعلی

- Route داوری‌شده: صفر از ۳۲.
- Match پذیرفته‌شده، Exception پذیرفته‌شده، Recollection و Hard Block ثبت‌شده: همگی صفر.
- Packet واردشده به بازبینی CG-05: صفر.
- CG-05 بسته‌شده: صفر.
- Owner approval و Case اجراشده: صفر.
- Command readiness و Pilot readiness: صفر.

وضعیت `PASS` این Artifact فقط انسجام قرارداد داوری را ثابت می‌کند. هیچ Capture، اجرای گزارش/Export، اجرای UAT، Repair، Replay، Recapture، پذیرش Exception، Closure یا Promotion انجام نشده است.

## مرز ایمنی

این بسته فقط از Artifactهای hash-only موجود استفاده می‌کند. هیچ اتصال دیتابیس، اجرای فرم یا Stored Procedure، Load/Execute اسمبلی، تغییر داده، ایجاد Write access یا ذخیرهٔ مقدار خام تجاری/هویتی/Credential انجام نمی‌دهد.
