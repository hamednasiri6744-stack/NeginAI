# Test Vector و Receipt Verification برای Comparison Adapter مقصد

این بسته برای قرارداد Comparison Adapter، Vectorهای canonical مصنوعی و مرز اصالت/اعتبارسنجی Receipt را تعریف می‌کند. هیچ Key واقعی، Signature واقعی، Business fixture یا اجرای Runtime در آن وجود ندارد.

## Test vectorها

- دوازده Vector مثبت برای دوازده مرحلهٔ canonicalization.
- شانزده Vector منفی، دقیقاً یک مورد برای هر Error code قرارداد Adapter.
- جمعاً ۲۸ Vector و ۲۲۴ انتساب Profile-to-Vector برای هشت Profile.
- دوازده digest مورد انتظار با SHA-256 و domain tag مستقل.

تمام Objectهای Vector از Tokenهای مصنوعی ساخته شده‌اند و `contains_business_value=false` دارند. Digest از `domain_tag + NUL + canonical JSON` محاسبه می‌شود. این Vectorها قرارداد طراحی را تثبیت می‌کنند و اثبات اجرای Adapter نیستند.

## Authenticity metadata

Receipt شانزده Field اصالت دارد: شناسه و hash payload، نسخهٔ schema/canonicalization، Algorithm profile reference، Key id/version/status reference، Signature hash، نقش صادرکننده، زمان صدور/انقضا، Previous/Supersedes، Verification policy و Outcome.

Algorithm suite هنوز انتخاب نشده و به تصمیم جداگانهٔ Platform/Security وابسته است. Artifact هیچ Private key، Public key یا Signature bytes ندارد. فقط Reference و Hash مجاز است.

## Verification outcomeها

هشت Outcome عبارت‌اند از Authentic-current، Payload-hash mismatch، Invalid signature، Unknown key، Expired key، Revoked key، Superseded receipt و Profile/Policy mismatch. فقط `AUTHENTIC_CURRENT` می‌تواند وارد داوری مستقل شود؛ همین Outcome نیز Result parity، Owner acceptance، CG-05 closure یا Readiness را ثابت نمی‌کند.

## چرخهٔ Key و Rotation

شش State برای Key reference طراحی شده است: Proposed، Active، Retiring-verify-only، Revoked، Expired و Destroyed-reference-only. هشت Rule، Cutover، Verify-only retention، Revocation، Expiry، History immutability، Supersession و منع ورود material به Artifact را کنترل می‌کنند.

## وضعیت فعلی

- Algorithm profile انتخاب‌شده: صفر.
- Verification key ثبت‌شده: صفر.
- Receipt امضاشده: صفر.
- Verification run و Authentic receipt: صفر.
- Receipt پذیرفته، Result parity، UAT و Readiness: صفر.

این بسته هیچ اتصال Database/Network، اجرای فرم یا Procedure، Load/Execute اسمبلی، تغییر داده، تولید/بارگذاری Key یا Signature و ذخیرهٔ مقدار خام انجام نداده است. Risk 84، Trace 343 و lower bound 1404 ثابت است.
