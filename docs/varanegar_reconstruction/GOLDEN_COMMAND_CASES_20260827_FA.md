# Golden command cases برای ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۷۷ قرارداد تست مصنوعی؛ هیچ Command روی وارانگار اجرا نشده است**

## هدف

این مجموعه معیار «ساخته شد» را از وجود Endpoint جدا می‌کند. هشت Command
Mutating هرکدام باید علاوه بر سناریوی موفق، Permission deny، Scope deny، نسخهٔ
قدیمی، Retry همان Command و Fault وسط Transaction را پاس کنند. ۳۴ Case خاص
دامنه نیز قواعد واقعی کشف‌شده در چک/توزیع/انبار را پوشش می‌دهند.

خلاصه:

- ۴۰ Case پایه برای هشت Command Mutating؛
- ۳۴ Case خاص دامنه؛
- سه Case Read/Validation بدون Side effect؛
- جمع ۷۷ Case در ۱۱ گروه ریسک.

## Gate مشترک هر Command Mutating

1. `auth_denied`: مجوز اتمی وجود ندارد → صفر Write و Audit امن Denial؛
2. `scope_denied`: رکورد خارج DC/SaleOffice/Stock scope → صفر Write؛
3. `stale_version`: Current state/history تغییر کرده → `STALE_VERSION`؛
4. `duplicate_command_id`: پاسخ Commit گم شده و Retry می‌شود → همان نتیجه قبلی
   با فقط یک Write set منطقی؛
5. `fault_after_first_write`: Fault بعد از اولین Write → Rollback کامل و Retry
   امن.

## Caseهای مهم توزیع

### Create/Update

- شماره توزیع همزمان: دو Command نباید `AccYear/DC/DistNo` تکراری بسازند؛
- SaleS خالی، تاریخ بسته و ظرفیت نامعتبر قبل از Write رد شوند؛
- Header، Sale link و History پس از Commit با هم سازگار باشند.

### IssueExit

- Voucher item/detail باید با مجموع Sale به تفکیک Goods/Batch برابر باشد؛
- Cardex منفی، Batch mismatch، Status نامعتبر و Lock شخص دیگر صفر Write durable
  بدهند؛
- State ۲، ExitRef و Voucher/Cardex فقط با هم Commit شوند.

### Merge/Adjust

- Goods خارج توزیع، مقدار بیش از eligible quantity و Duplicate goods/batch رد
  شوند؛ RD یک working set سازگار باقی بماند.

### RemoveExit

- Reason اجباری، تاریخ بسته و Posting وابسته قبل از Reverse بررسی شوند؛
- Exit cancel، پاک‌شدن Sale.ExitRef، بازگشت Dist به State ۱، Reverse Voucher/RD
  و ثبت Full history باید یک واحد اتمیک باشند؛
- وجود چند Exit نیازمند Scope قطعی است و نباید Exit انتخاب‌نشده را تغییر دهد.

## Caseهای چک

### ChangeStatus

- فقط Edge تنظیم‌شده؛
- تاریخ عملیات عقب‌تر از تاریخ چک/History رد؛
- Context اجباری مقصد State (Bank/Safe/Reason/Legal/Pay) کامل؛
- دقیقاً یک History event و Current pointer همسان.

### Undo

- فقط Latest leaf با Expected history/version؛
- Transfer/Cession/Balance برای دریافتی و Voucher/BookItem/Pay برای پرداختنی
  Guard شوند؛
- پس از Undo، Previous chain و Current pointer معتبر بماند.

## سه Case فقط‌خواندنی

- موجودی: همان GoodsRef در دو Stock scope نباید نشت داده دهد و Snapshot به‌عنوان
  Projection برچسب بخورد؛
- دو Workflow validator چک باید برای Edge مجاز/غیرمجاز نتیجه Deterministic و
  صفر Write بدهند.

## نحوه اجرا در آینده

این Artifact فعلاً طراحی تست است. اجرای آن فقط روی Target test DB جدا با Fixture
کاملاً مصنوعی مجاز است. Failure injection یا Mutation case هرگز روی وارانگار،
Clone یا دیتابیس عملیاتی اجرا نشود.

تعریف Pilot-ready برای یک Command:

```text
success + auth/scope denial + stale version + idempotent retry
+ transaction rollback + domain validations + ledger reconciliation = PASS
```

## Artifact و کد

- `scripts/windows/build_varanegar_golden_command_cases.py`
- `artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json`
- `tests/test_varanegar_ui_evidence.py`
