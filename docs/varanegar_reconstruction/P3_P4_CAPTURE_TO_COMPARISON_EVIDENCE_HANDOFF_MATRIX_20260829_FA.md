# ماتریس Handoff شواهد از Capture به Comparison Adapter

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

این بسته پل ماشین‌خوان میان مجوز Capture ایزوله و Comparison Adapter را تعریف می‌کند. هیچ Payload یا فایل از این مرز عبور نمی‌کند؛ فقط Hash، Count محدود، Status و Opaque reference مجاز است.

## پوشش

- هشت Packet، شانزده Capture Channel و هشت Pair دوطرفه؛
- ۲۷ Receipt slot زیر CG-05 با ۵۴ اتصال Channel-to-Receipt؛
- بیست بُعد parity با ۳۲۰ اتصال Channel-to-Dimension؛
- هشت Adapter Profile با شانزده اتصال Profile-to-Channel؛
- Envelope بیست‌فیلدی؛
- دوازده Gate برای هر Pair، یعنی ۹۶ assignment.

هر Pair دقیقاً یک Channel Legacy، یک Channel Target و یک Adapter Profile دارد. Set مورد Case، Dimension و Receipt slot با hash مستقل pin می‌شود. Authorization، Redaction attestation، Policy version، custody receipt و expiry فقط به‌صورت reference/hash وارد Envelope می‌شوند.

## Gateها

هر دو مجوز باید Active و در Scope باشند؛ هر دو Redaction attestation باید مستقل پذیرفته شوند؛ Case set و Dimension set باید برابر باشند؛ Profile/Schema و Policyها باید pin شوند؛ scan دسته‌های ممنوع و نابودی مواد موقت باید برای هر دو سمت تأیید شود؛ custody باید current و unexpired باشد؛ ورودی‌های Idempotency باید کامل و بدون تعارض باشند. شکست هر Gate با `BLOCK_COMPARISON_HANDOFF` متوقف می‌شود.

## وضعیت فعلی

- هر هشت Pair در `NOT_READY_NO_AUTHORIZED_CAPTURE` است.
- هر ۹۶ Gate assignment در `UNMET` است.
- در ۵۴ اتصال Receipt و ۳۲۰ اتصال Dimension، accepted evidence برابر صفر است.
- Ready/Accepted handoff، Adapter request، Comparison run، Receipt، Result parity، CG-05 closure، Owner approval و Readiness همگی صفرند.
- این ماتریس هیچ مجوز Capture صادر نمی‌کند و هیچ Payload، فایل، مقدار تجاری، هویت یا Credential ذخیره نمی‌کند.
- پایهٔ ۸۴ ریسک، ۳۴۳ انتساب و lower bound طراحی ۱۴۰۴ ثابت است.

