# مرز Undo تخریبی چک دریافتی و Projection مبتنی بر Trigger

تاریخ شاهد: ۲۰۲۶-۰۸-۲۹  
وضعیت: **تأییدشده از Clone فقط‌خواندنی، Log ناشناس و IL هش‌سنجی‌شده**

## نتیجهٔ اصلی

Undo چک دریافتی در وارانگار Event جبرانی نمی‌سازد. رخداد جاری را حذف می‌کند و
در یک شاخه خاص، رخداد گذرای وضعیت ۸ را نیز همراه آن پاک می‌کند. سپس Trigger
رخداد قبلی را دوباره `IsLast=1` می‌کند. بنابراین Projection جاری سالم است، اما
Audit trail تخریبی و تعداد رخدادهای حذف‌شده برای هر فرمان ثابت نیست.

## مسیر SQL واقعی

`dbo.DoRCheque_DeleteLastRChequeHistory`:

1. پیش از Transaction، `BeforeRChequeHistory` را برای Validation صدا می‌زند؛
2. Transaction و TRY/CATCH/Commit/Rollback دارد؛
3. History جاری با `IsLast=1` را Delete می‌کند؛
4. اگر `PreviousStatRef=8` و Status حذف‌شده ۱ باشد، History وضعیت ۸ قبلی را نیز
   Delete می‌کند؛
5. Master چک را فقط برای اطلاعات تغییر/کاربر به‌روزرسانی می‌کند؛
6. هیچ Event جبرانی Append نمی‌کند.

Projection وضعیت داخل Master نیست. Trigger فعال `Acc.trg_ChqHist_Del` پس از
Delete، History قبلی را جاری می‌کند؛ Trigger Insert نیز رخداد قبلی را از حالت
جاری خارج می‌کند. هر دو جدول اصلی Non-temporal و بدون CDC/Change Tracking هستند.

فرم Desktop مستقیم Adapter حذف آخرین History را صدا نمی‌زند. مسیر واقعی آن
`RChequeAdapter.DeleteCessionToOther` است؛ Procedure متناظر خودش Transaction
می‌گیرد، `DeleteLastRChequeHistory` را صدا می‌زند و Commit می‌کند، اما Token صریح
Rollback ندارد. Procedure گروهی SDSNET نیز Add و DeleteLast را زیر
Transaction/Savepoint خودش اجرا می‌کند.

## تطبیق Log و فعالیت سه‌ماهه

برای `Acc.tblChqHist` تعداد ۱۴٬۷۱۱ Delete متمایز ثبت شده است. تطبیق دنباله‌های
مجاور همان Session با ترتیب ایستای Trigger/Procedure نشان داد:

- ۱٬۵۰۲ فرمان نامزد Undo با tail نهایی
  `History DELETE → previous History UPDATE → TblCheque UPDATE`؛
- ۲۲ مورد از این فرمان‌ها شاخه دوحذفی دارند و tail آن‌ها ابتدا
  `DELETE → UPDATE → DELETE → UPDATE` است؛
- در نتیجه ۱٬۵۰۲ فرمان به ۱٬۵۲۴ History حذف‌شده نسبت داده می‌شود؛
- ۴۷۱ فرمان و ۴۷۵ History حذف‌شده در June–August 2026 است؛
- ۱۲ Delete سه‌ماهه باقی‌مانده و جمعیت بزرگ حذف تاریخی به Undo نسبت داده نشد.

در شمارش، Delete دوم هر شاخه دوحذفی خودش شکل Single tail دارد. بنابراین تعداد
فرمان برابر ۱٬۵۰۲ است و برای شمار ردیف حذف‌شده باید ۲۲ head دوحذفی به آن افزوده
شود. این یک تطبیق قوی Static/Log است، نه اثبات Actor، Reason یا Status حذف‌شده.

## Snapshot و شکاف Audit

- ۲۳٬۸۲۲ چک و ۱۰۶٬۱۳۱ History؛ حداقل یک و حداکثر ده History؛
- برای همه چک‌ها دقیقاً یک `IsLast=1` وجود دارد و همان Max ID است؛
- Parent، PreviousHistRef و PreviousStatRef mismatch همگی صفرند؛
- از ۱۲۱٬۰۹۴ History ID لاگ‌شده، ۱۴٬۹۶۳ اکنون غایب‌اند؛ ۱۴٬۷۱۱ مورد Insert و
  Delete retained دارند؛
- ۲۵۲ ID فقط Insert log دارند و اکنون غایب‌اند. این جمعیت در بازه تاریخی
  ۲۰۲۴-۰۳-۲۷ تا ۲۰۲۴-۰۳-۲۸ است و هیچ مورد سه‌ماهه ندارد.

۲۵۲ شکاف به Undo، Migration یا Trigger bypass نسبت داده نشد. Projection سالم،
تاریخچه حذف‌شده را قابل بازیابی نمی‌کند.

## شاهد Managed Runtime

دو Assembly با Inventory قبلی هم‌هش بودند. شش Method و ۷۰۰ Instruction فقط از
PE/IL خوانده شدند و هیچ Assembly Load/Execute نشد.

- هر دو فرم Legacy و New در `DoUndo` ابتدا Transaction می‌گیرند، `CanDoUndo` را
  کنترل می‌کنند، Wrapper `DeleteCessionToOther` را صدا می‌زنند، Refresh و سپس
  Commit/Rollback signal دارند؛
- هر دو `CanDoUndo` تعداد History را می‌خوانند؛
- Adapterهای Wrapper و Direct Delete هر دو Transaction تو‌در‌تو دور
  `ExecuteNonQuery` دارند؛
- انتخاب Runtime فرم و reachability شاخه Cleanup/rollback اثبات نشده است.

## قرارداد مقصد

`R-074` با شدت بالا ثبت شد. ERP مقصد باید:

- `ReceivedChequeStateEvent` را append-only نگه دارد؛
- Undo را Event جبرانی با Ref به همه رخدادهای superseded ثبت کند؛
- Collapse وضعیت گذرای ۸ را یک تصمیم صریح و نسخه‌دار کند، نه Delete دوم پنهان؛
- Event، Projection، Cession cleanup، تخصیص چک برگشتی، Audit حسابداری و Outbox
  را در یک Transaction بنویسد؛
- ExpectedVersion و Idempotency Key داشته باشد؛
- ۱٬۵۰۲ فرمان، ۲۲ شاخه دوحذفی و ۲۵۲ شکاف را بدون ساختن Status/Actor/Reason
  خیالی مهاجرت دهد.

Fault injection، concurrent undo و retry باید دقیقاً یک Projection بسازند و
هر ۲۳٬۸۲۲ چک پس از import همچنان یک رخداد جاری با chain سالم داشته باشند.

## خروجی‌ها

- `artifacts/varanegar_analysis/domains/received_cheque_undo_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/received_cheque_undo_runtime_boundary_20260829.json`
- `scripts/sql/extract_varanegar_received_cheque_undo_boundary.py`
- `scripts/sql/extract_varanegar_received_cheque_undo_runtime_boundary.py`

هیچ Procedure، Trigger، فرم، Command یا Assembly اجرا نشد و هیچ شناسهٔ چک،
بانک، مشتری، مبلغ، توضیح، User/Host، SQL definition یا Log script ذخیره نشد.
