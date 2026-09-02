# قرارداد Command چهار Orchestrator اصلی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۰ قرارداد مقصد؛ تمام Method evidence موجود و Validation برابر PASS**

## Commandها

از Order، RetSale، SupplierInvoice/SupplierReturn و Stock Voucher ده Command
مستقل استخراج شد:

1. `order.save`؛
2. `order.cancel`؛
3. `order.convert_to_sale`؛
4. `sales_return.save`؛
5. `sales_return.cancel_and_generate_voucher`؛
6. `supplier_invoice.save`؛
7. `supplier_return.save`؛
8. `stock_voucher.save`؛
9. `stock_voucher.confirm_or_unconfirm`؛
10. `stock_voucher.generate_return`.

هر قرارداد به Methodهای واقعی Handler/Validator در Call graph وصل است و
Invariants، وابستگی ماژولی، نقاط Failure injection و Reconciliation لازم دارد.

## الگوی اجرای مقصد

هر Command یک Transaction owner در Application layer دارد. Handlerهای دامنه
داخل آن مستقل Commit نمی‌کنند. اثر میان ماژول‌ها با Transactional outbox و
Consumer idempotent منتشر می‌شود. Number allocation باید در Concurrent retry
همان نتیجه اولیه را برگرداند، نه شماره یا Aggregate دوم بسازد.

Envelope مشترک:

`command_id + aggregate_id + expected_version + operational_date + fiscal_year + dc_ref + actor_context`

نتیجه مشترک:

`command_id + aggregate_id + new_version + new_state + audit_event_id + reconciliation_status`

## Failure boundaryهای کلیدی

- Order: تخصیص شماره، Header، Item، Batch، Pricing/EVC و Outbox؛
- Convert-to-sale: Sale identity، Header، Item/detail و Order pointer؛
- RetSale: Header، Item/detail/batch، Discount/EVC و Settlement request؛
- Cancel return: Cancel event، Voucher و Settlement compensation؛
- SupplierInvoice: شماره، Header، Item، Toll و Inventory-document link؛
- StockVoucher: هویت، Header، Item/detail/batch، Ledger event و Projection/Outbox؛
- Confirm/return voucher: State event، Ledger/projection، Posting provenance و
  Source/return link.

در هر نقطه خطای تزریق‌شده نباید Business outcome ناقص ولی Accepted باقی بگذارد.

## Invariantهای مهم

Order علاوه بر Context و Credit به Qty/detail، Stock/batch و Pricing trace نیاز
دارد. Return از Remaining quantity و Returnability فراتر نمی‌رود. SupplierInvoice
رابطه Supplier/Goods، شماره، Price/Qty/Toll و ICA/Voucher provenance را حفظ
می‌کند. StockVoucher باید Ledger-first باشد و Projection آن از Ledger بازسازی
شود.

## مرز نتیجه

این قراردادها طراحی مقصدند؛ Atomicity Legacy را ثابت نمی‌کنند. Inheritance،
Reflection، ORM hook و Branch تنظیمات ممکن است Callهای دیگری داشته باشند.
هیچ Command روی وارانگار یا DB مقصد اجرا نشده است.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_orchestrator_command_contracts_20260827.json`
- `scripts/windows/build_varanegar_orchestrator_command_contracts.py`
- `tests/test_varanegar_ui_evidence.py`
