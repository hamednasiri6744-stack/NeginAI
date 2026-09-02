# مسیر Generic Save و Transaction در Manual Voucher — ۱۴۰۵/۰۶/۰۷

پنج Assembly با hash موجود در inventory فقط از طریق PE/CLR metadata و IL ایستا خوانده شدند. مسیر دقیق به این صورت resolve شد:

`FormManualVoucherDataEntry2.SaveCommand` → `IBusinessHandler<ManualVoucherAdapter,…>.SaveCommand` → overload policy-aware → یکی از `SaveV2/Insert/Update/Delete` → `BaseDataV2Adapter`.

UI پیش از Save یک `DataContext` با operand صفر (`Transaction.Begin`) می‌سازد. خود UI و دو overload عمومی Handler، Commit ندارند؛ سه overload context-taking مربوط به Insert/Update/Delete هرکدام یک `DataContext.Commit` دارند و Rollback صریح در مسیرهای انتخاب‌شده دیده نشد. Branch واقعی بین V2/Fararu/Insert/Update/Delete وابسته به config و state است و اجرا نشده است.

این مسیر generic entity-metadata persistence است و Procedure نام‌دار مخصوص ManualVoucher در آن دیده نمی‌شود. بنابراین نبود Procedure literal نباید «عدم mutation» تعبیر شود. Retry در ERP مقصد باید command-id و read-back داشته باشد و exception/error را با اثر durable تطبیق دهد.
