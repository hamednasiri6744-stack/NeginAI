# Reference Evaluator مصنوعی دورهٔ مالی

این evaluator فقط boolean/state/version ثابت و مصنوعی را پردازش می‌کند. هیچ دوره، دفتر، سند، مانده یا entry عملیاتی نمی‌خواند و هیچ Close، Reopen، Adjustment، Reversal یا Posting اجرا نمی‌کند.

ترتیب تصمیم Schema، Scope، Version، State، پوشش همهٔ مسیرهای Lock، Blocking unknown، وابستگی‌های Close، اتمی‌بودن Numbering rollover، Adjustment، Reopen، Reclose و سپس Acceptance است. بنابراین receipt ظاهراً معتبر نمی‌تواند scope/version/state نامعتبر یا مسیر دورزنندهٔ قفل را بپوشاند.

پنج مسیر مثبت Soft close، Hard close، Adjustment، Reopen و Reclose و هجده mutation منفی تعریف شده است. Mutationها schema، scope، version، state، lock bypass، unknown، subledger/control total/numbering، adjustment class/balance/reversal، reopen impact/SoD/token/break-glass و reclose rerun/lineage را می‌سنجند.

این یک reference implementation است، نه provider قفل تقویم یا دفتر. Operational implementation/read/run/receipt و Command/Pilot readiness صفر است؛ پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت می‌ماند.
