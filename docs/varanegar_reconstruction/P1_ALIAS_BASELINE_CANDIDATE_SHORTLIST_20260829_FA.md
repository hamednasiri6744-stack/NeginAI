# Shortlist شواهد Baseline برای Action Aliasهای P1 ـ ۲۰۲۶-۰۸-۲۹

هشت Packet اولویت P1 و ۵۶ Case آن‌ها در baseline بازسازی‌شدهٔ Golden/UAT جست‌وجو شد. چهار Packet بانکی دارای کاندید و چهار Packet دیگر دارای `EXPLICIT_NONE_AFTER_RECONSTRUCTED_BASELINE_SEARCH` هستند. `EXPLICIT_NONE` فقط نبود کاندید در محدودهٔ بازسازی‌شده را نشان می‌دهد و نبود پیاده‌سازی تاریخی را ثابت نمی‌کند.

قرارداد state-machine بانکی چهار نگاشت صریح دارد: `CancelSession` به `bank_reconciliation.cancel`، `ConfirmSession` به `bank_reconciliation.confirm`، `MatchInstrument` به `bank_reconciliation.match_instrument` و `UnmatchInstrument` به `bank_reconciliation.unmatch_instrument`. این چهار capability در baseline به‌ترتیب ۱۷، ۲۵، ۱۷ و ۱۷ Case دارند.

در مجموع چهار Action reference، ۷۶ Case reference و ۲۴ هم‌پوشانی نوع Case ثبت شد. چهار نگاشت command-to-capability دقیق‌اند، اما هیچ Action string دقیقی وجود ندارد. Actionهای `accounting.external_voucher.generate`، `accounting.manual_voucher.save`، `cash_receipt.edit` و `received_bank_draft.edit` در baseline بازسازی‌شده کاندید ندارند.

همهٔ کاندیدها `REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE` هستند. پذیرش Action/Case، اجرای UAT، اثر شمارشی و readiness صفر است و lower bound طراحی ۱۴۰۴ باقی می‌ماند. داوری معتبر همچنان به نگاشت precondition، outcome vocabulary، assertion/effect، تصمیم Alias نسخه‌دار یا New Action و receipt نقش‌های پاسخ‌گو نیاز دارد.
