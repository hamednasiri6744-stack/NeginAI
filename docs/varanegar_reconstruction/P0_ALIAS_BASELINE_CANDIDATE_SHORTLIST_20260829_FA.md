# Shortlist شواهد Baseline برای Action Aliasهای P0 ـ ۲۰۲۶-۰۸-۲۹

هفت Packet اولویت P0 و ۴۹ Case آن‌ها در baseline بازسازی‌شدهٔ Golden/UAT جست‌وجو شد. نتیجه سه Packet دارای کاندید و چهار Packet با `EXPLICIT_NONE_AFTER_RECONSTRUCTED_BASELINE_SEARCH` است. `EXPLICIT_NONE` فقط نبود کاندید در محدودهٔ بازسازی‌شده را بیان می‌کند و نبود پیاده‌سازی تاریخی را ثابت نمی‌کند.

- `stock_voucher.confirm_or_unconfirm`: یک Action دقیق در ماژول baseline موجودی با ۱۵ Case پیدا شد؛ اختلاف scope ماژولی اجازهٔ reuse خودکار نمی‌دهد.
- `bank_reconciliation.ReverseConfirmedSession`: سه کاندید lifecycle شامل cancel، confirm و unmatch با ۵۹ Case پایه ثبت شد.
- `received_cheque.delete`: دو کاندید lifecycle شامل change-status و undo با ۱۸ Case پایه ثبت شد.
- سه Action external-voucher حسابداری و Action تکثیر tour-payment در baseline بازسازی‌شده کاندید مستقیمی ندارند.

در مجموع شش Action reference، ۹۲ Case reference و ۳۷ هم‌پوشانی نوع Case ثبت شد. فقط یک Action string دقیق است و آن نیز cross-module است. همهٔ کاندیدها `REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE` هستند؛ پذیرش Action/Case، اجرای UAT، اثر شمارشی و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.

داوری معتبر به نگاشت صریح precondition، outcome vocabulary، assertion/effect، Alias نسخه‌دار یا وضعیت New Action، receipt نقش‌ها و policy expiry/supersession نیاز دارد.
