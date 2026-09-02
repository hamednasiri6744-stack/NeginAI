# کاتالوگ Workflow و State machineهای Runtime

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۰ از ۲۰ Workflow form با IL هدفمند و Redaction تحلیل شد**

## خط مبنا

- ۲۰ فرم Workflow/Tracking؛
- ۱۰۱ Method فرمانی؛
- ۴۷۶ Call edge به Business/DataAccess؛
- صفر فرم جاافتاده و صفر اجرای Command/Application؛
- دامنه‌ها: توزیع ۸، فروش ۴، وصول/خزانه ۳، چک دریافتی ۲، چک پرداختنی ۲ و
  کنترل تاریخ عملیاتی ۱.

اعداد Method/Call اندازه پیچیدگی فنی‌اند، نه تعداد Use case نهایی؛ چند Method
رویداد UI یا Variant قدیمی/جدید می‌تواند یک Command کسب‌وکاری را پیاده کند.

## خزانه Legacy: چهار Instrument با State machine جدا

`frmGuaranteeTracking` یک فرم واحد با چهار Aggregate مستقل دارد:

- GuaranteeCheque؛
- GuaranteeBankPaper؛
- GuaranteeBankableBill؛
- GuaranteeOwnerPaper.

هرکدام Query adapter، Status master، Workflow، Add-history و Delete-last-history
جدا دارند. بنابراین وب نباید همه «تضمین‌ها» را در یک جدول با Status عمومی
ادغام کند؛ می‌توان UI مشترک داشت ولی Contract و History هر Instrument باید
Typed بماند.

`frmRBankDraftTracking` نیز Work queue وضعیت‌های `1,3` است و قبل از Transition
Receipt status، Reconcile item و History را بررسی می‌کند. این فرم در کنار
R/PCheque نشان می‌دهد الگوی عمومی خزانه چنین است:

```text
Filtered work queue
  -> selection
  -> allowed next states from workflow
  -> operation-date/reconcile/context validation
  -> append state history
  -> current projection
  -> optional undo of last event
```

## توزیع: یک Orchestrator چندمرحله‌ای

هشت فرم زیر یک Aggregate ساده نیستند:

- `FormDistManagementList` و `DataEntry`؛
- `FormFactorSelection`؛
- `FormOrderToDist`؛
- `FormFollowDist`؛
- `FormExitExportationDataEntry`؛
- `FormRemoveExitFromDistReason`؛
- `FormChangeBatchNo`.

انتخاب فاکتور علاوه بر آزادبودن DistRef، ظرفیت مبلغ/وزن/حجم خودرو، نوع حمل و
Amani را کنترل می‌کند. Follow تیم واقعی، تاریخ ارسال/بازگشت و Status را ثبت
می‌کند. صدور خروج Validator موجودی/Batch/عملیات را اجرا می‌کند. حذف خروج Reason
اجباری و LastClosedDate دارد. تغییر Batch مسیر مستقل Handler دارد.

برای مقصد، این‌ها Commandهای مستقل با Saga/transaction boundary روشن هستند؛
`PATCH /distribution/{id}` نباید جای همه آن‌ها را بگیرد.

## Follow voucher و ساخت فروش

`FormFollowVocherList/DataEntry` بزرگ‌ترین Orchestration مشاهده‌شده در این
مجموعه است. مسیر تبدیل حواله به فروش به این زیرسامانه‌ها وصل است:

- Sale/SaleItem/SaleItemDetail؛
- EVC محاسبه تخفیف و جایزه، با Variant قدیمی و V2؛
- Discount/PeriodicDiscount و Prize package؛
- Customer credit validation؛
- Goods status و Batch/Package؛
- Order prevention، Sale amount discount و Distribution after-save؛
- تبدیل کامل، چندتایی و جزئی؛
- Return voucher و Undelivered.

این شاهد تأکید می‌کند `Order → Sale` یک Copy رکورد نیست. Golden parity قیمت،
تخفیف، جایزه، اعتبار مشتری، موجودی و اثر توزیع باید پیش از هر Command وبی ساخته
شود.

## Workflowهای کنترل‌کننده

- `FormOrderPrizeInFollowVocher`: اعتبارسنجی و پذیرش جایزه هنگام Follow؛
- `FormFinalDateManagement`: تغییر تاریخ‌های فروش/مالی/تنخواه با Handler و
  Validator؛ این صفحه Control-plane حساس است؛
- `FormReceiptManagmentTracking`: Permission مستقل `ChangeStatus`، Confirm و
  UnConfirm با `RollbackToPreviousStatus`، StatusDate، Reason و ReceiptAgent.

Confirm/UnConfirm باید Commandهای مستقل با Audit باشند و هرگز Boolean ساده روی
Header مقصد نشوند.

## قرارداد مشترک مقصد

برای هر Workflow:

1. `WorkQueueQuery` با Filter وضعیت و Data partition؛
2. `AllowedTransitionsQuery` از Workflow master؛
3. Command نام‌دار با Permission key و Feature guard؛
4. `ExpectedCurrentEventId/Version` برای جلوگیری از race؛
5. Business date و Reason/Context typed؛
6. Domain validator سمت سرور؛
7. Append-only event + current projection در یک Transaction؛
8. Idempotency key و Audit نتیجه؛
9. Undo فقط به‌عنوان Command دامنه‌ای و نه حذف عمومی تاریخچه؛
10. Reconciliation با Projection/ledger مرجع.

## Artifact و محدودیت

- `artifacts/varanegar_analysis/ui/varanegar_workflow_catalog_20260827.json`
- `scripts/windows/build_varanegar_workflow_catalog.py`

Artifact فقط نام Method، Call edge، Literal تجاری Allowlist‌شده و Static UI
label را دارد؛ داده ردیف، Message runtime، Credential و رشته غیرمجاز ذخیره نشده
است. وجود Call edge مجوز کاربر جاری را ثابت نمی‌کند.

گام بعدی: استخراج ۲۰ Report form و اتصال Query source/Filter/Export آن‌ها؛ سپس
رتبه‌بندی Sliceهای وب با خط مبنای سه‌ماهه و ریسک مالی.
