# قرارداد مقصد Read Model و Summary مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ هنوز Query پیاده‌سازی یا Runtime parity تأیید نشده است**

## نتیجه

سومین Slice مجاز اکنون چهار Projection با ۴۴ Field، پنج Query contract، یازده
فرمول Summary، شش نگاشت Instrument نوع‌دار و شانزده تعهد Acceptance دارد.
هیچ Query یا Commandی اجرا نشده و Clone جاری Fixture Runtime ندارد.

Projectionها `SessionView`، `StatementRowView`، `LinkView` و `SummaryView` هستند.
Queryها Session، ردیف‌ها، Linkها، Match candidate فقط‌خواندنی و Summary را با
Scope اجباری Fiscal/DC/BankAccount/Session/AsOfDate ارائه می‌کنند.

## قواعد غیرقابل حذف

- تمام یازده مبلغ API signed decimal و non-null هستند؛ پرانتز/رنگ فقط Presentation است؛
- pagination ترتیب پایدار و کلید یکتای نهایی دارد؛
- Candidate query هیچ persistence یا Grid-event write ندارد؛
- هر Link معتبر دقیقاً یک Reference نوع‌دار دارد؛ صفر/چند Reference قرنطینه می‌شود؛
- State ناسازگار Legacy قرنطینه و Marker تأیید معادل سلامت همه Instrumentها نیست؛
- دو Alias املایی تا تصمیم `BR-DEC-001` بی‌صدا Normalize نمی‌شوند؛
- خروجی Profile version/hash را دارد ولی SQL/Path اجرایی را افشا نمی‌کند.

Authorization سمت سرور اشتراک Capability، Feature، Fiscal/DC/Account scope،
AsOfDate و Domain validation است؛ Deny مقدم و Neutral غیرمجاز است.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_read_model_contract_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_read_model_contract.py`
- `tests/test_varanegar_ui_evidence.py`

فرمول‌ها قرارداد Semantic ایستا هستند، نه اثبات برابری ردیف‌های Runtime.
