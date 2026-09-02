# قرارداد تشخیص تسویه‌ی بین‌مشتری چک برگشتی

## نتیجه‌ی قطعی

۴۹ ردیف `Acc.tblPayments` که در آن‌ها مشتری Payment با
`Acc.TblCheque.CustRef` فرق دارد، **خرابی یا تغییر اشتباه مشتری نیستند**. هر ۴۹
ردیف دقیقاً به تخصیص اولیه‌ی همان چک، همان Sale و همان مشتری Payment متصل‌اند:

```text
AuthorityKey = RetChequeRef + SaleRef + AllocationCustomer
49 / 49 exact source-allocation matches
0 unexplained rows
31 cheque-sale-customer pairs
0 over-settled pairs
```

از ۴۹ ردیف، ۴۸ ردیف Sale دارند و Customer فاکتور در همه‌ی آن ۴۸ مورد با
Customer پرداخت برابر است؛ هیچ‌کدام با مالک چک برابر نیست. یک ردیف مربوط به
`واریز بدهی قبل` و بدون Sale است، اما آن نیز تخصیص اولیه‌ی دقیق همان
چک/Customer را دارد. بنابراین نقش‌ها باید جدا بمانند:

| نقش | مرجع |
|---|---|
| مالک/آورنده‌ی چک | `TblCheque.CustRef` |
| Customer تخصیص اولیه | `tblPayments.CustRef` روی ردیف `ChqRef` |
| Customer فاکتور | `tblSaleHdr.CustRef` |
| Customer ثبت دستی منبع | `TblCheque.ManualCustRef`؛ صرفاً Metadata |

`ManualCustRef` فقط در ۲ مورد با Customer تسویه برابر است؛ پس مرجع اصلاح یا
تخصیص نیست.

## شواهد رسمی SQL

- `Acc.Usp_CreatePaymentsFromOthersCust` مسیر صریح پرداخت برای مشتری دیگر را
  می‌سازد و `SaleRefForOtherCust` را نگه می‌دارد.
- `dbo.Usp_CheckRemRetChequeRef` مانده را با ترکیب Cheque و Sale کنترل می‌کند؛
  کنترل فقط در سطح مالک چک نیست.
- `dbo.USP_SDSNet_RetChequeForSettlement_GetList` مبلغ تسویه‌شده را برای همان
  `RetChequeRef + SaleRef` کم می‌کند.
- `dbo.UspPaymentInsert_Settlement` مقدار `RetChequeRef` را تا Insert حمل می‌کند.
- `dbo.UspPaymentParentCustomerInsert_Settlement` چند پایه‌ی حسابداری مرتبط برای
  تسویه‌ی گروهی/والد می‌سازد و `RetChequeRef` و Referenceها را حفظ می‌کند.

در Snapshot فعلی، ۲۷ Pair کامل و ۴ Pair جزئی تسویه شده‌اند؛ هیچ Pair بیش از
تخصیص اولیه تسویه نشده است. وضعیت جاری چک‌های مربوطه ۵ یا ۹ است، یعنی در مسیر
استرداد/حقوقی قرار دارند و پرداخت برگشتی روی همان تخصیص اولیه عمل کرده است.

## شواهد UI و Transaction

تحلیل IL بدون اجرای Assembly برای
`TreasuryOld.Forms.frmSettlementByCustomer` نشان می‌دهد فرم:

- فهرست چک‌های برگشتی قابل تسویه را می‌گیرد؛
- `RetChequeRef` را روی Settlement قرار می‌دهد؛
- مسیرهای `Commit` و `RollBack` صریح دارد.

این شاهد، همراه با Stored Procedureهای رسمی، نشان می‌دهد Cross-party allocation
قابلیت واقعی سیستم است، نه اثر تصادفی داده‌ی قدیمی.

## قاعده‌ی بازسازی و مهاجرت

مدل هدف باید حداقل این موجودیت‌ها را جدا کند:

```text
ReceivedCheque(owner_customer)
ChequeSaleAllocation(cheque, sale, allocation_customer, allocated_amount)
ReturnedChequeSettlement(allocation, amount, payment_type, source_links)
LinkedAccountingLeg(reference/payment relation, counterparty role)
```

صرف متفاوت بودن Customer تسویه و مالک چک **نباید** باعث Quarantine، تغییر
Customer یا ادغام رکورد شود. Review فقط وقتی لازم است که یکی از موارد زیر رخ
دهد:

- تخصیص اولیه‌ی دقیق وجود ندارد؛
- Customer فاکتور با Customer تخصیص ناسازگار است؛
- مبلغ تسویه از مبلغ تخصیص بیشتر است؛
- پایه‌ی حسابداری مرتبط یا Source provenance شکسته است؛
- Sale/Customer/Reference لازم مفقود است.

Golden Caseهای هدف باید تسویه کامل، تسویه جزئی، چند فاکتور برای یک چک، Customer
متفاوت از مالک چک، Parent-customer، Retry و Rollback را پوشش دهند و هم مانده‌ی
فاکتور و هم مانده‌ی تخصیص را بازسازی کنند.

## حدود شواهد

Aggregateهای فعلی دلیل تجاری نوشته‌شده توسط اپراتور را نشان نمی‌دهند و Static
SQL/IL اجرای دقیق هر سند تاریخی را ثابت نمی‌کند. آخرین Bucket مشاهده‌شده
`1404/12` است؛ بنابراین این Snapshot شاهد وجود و سازگاری قابلیت است، نه نرخ
استفاده در سه ماه اخیر. هیچ فرم، Stored Procedure، Transaction یا Assembly اجرا
نشده و هیچ شناسه، نام، شماره چک، توضیح یا ردیف خام ذخیره نشده است.

## Artifact بازتولیدپذیر

- Extractor:
  `scripts/sql/extract_varanegar_returned_cheque_cross_customer_diagnostic_contract.py`
- Artifact:
  `artifacts/varanegar_analysis/ui/varanegar_returned_cheque_cross_customer_diagnostic_contract_20260827.json`
- Validation: `PASS`

