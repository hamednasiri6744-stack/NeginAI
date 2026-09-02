# Delta آمادگی قواعد قیمت‌گذاری — ۲۰۲۶۰۸۲۹

پوشش طراحی Outcome/Retry در Ledger چهارده‌ماژوله از ۷ به ۸ ماژول رسید و فقط `pricing_rules` تغییر کرد. این تغییر صرفاً پوشش طراحی است؛ Runtime authorization، تخصیص اتمیک، Effect parity، Retry/Idempotency، تأیید مالک، Command readiness و Pilot readiness همگی صفر و اثبات‌نشده باقی ماندند.

چهار مانع اصلی باز است: سیاست تأییدشدهٔ اولویت/Qualification، جایگزینی `MAX(Id)+1` و تست Parallel writer، جایگزینی SQL اجرایی با DSL Allowlist‌شده، و تکمیل امنیت/ترتیب/Receipt/Quarantine در Replication.
