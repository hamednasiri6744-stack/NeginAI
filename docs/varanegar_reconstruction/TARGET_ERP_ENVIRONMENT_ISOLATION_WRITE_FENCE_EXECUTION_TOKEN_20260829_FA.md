# قرارداد Environment Isolation، Write Fence و Execution Token مقصد

چهار محیط `LEGACY_OPERATIONAL_REFERENCE`، Sandbox مصنوعی، UAT ایزوله و Production مقصد برای ۴۹ فرمان به ۱۹۶ انتساب متصل شده‌اند؛ همه `NOT_AUTHORIZED` هستند. وارانگار عملیاتی هرگز Command target نیست و حتی خواندن Reference فقط با Transport صریحاً Read-only ممکن است.

چهارده Fence در چهار محیط ۵۶ انتساب، دوازده Negative case در ۴۹ فرمان ۵۸۸ انتساب، Execution token بیست‌فیلدی، هجده Gate/۸۸۲ انتساب و شش Role/۲۹۴ انتساب تعریف شده است.

محیط از Host/Path/Connection string استنباط نمی‌شود؛ Token یک‌بارمصرف، زمان‌دار، Environment/Command/Scope/Fingerprint/Idempotency/Version-bound است. Sandbox/UAT token در Production قابل Replay نیست، Break-glass/Admin تأیید مستقل را دور نمی‌زند و UAT success به‌طور خودکار Production را promote نمی‌کند.

هیچ Endpoint، Credential، Principal، Connection یا Token انتخاب/خوانده/صادر نشده و هیچ فرمان Legacy/Target اجرا نشده است. Token/Connection/Run/Fence attestation/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
