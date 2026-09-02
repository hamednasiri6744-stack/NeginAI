# مرز Undo تخریبی تاریخچهٔ چک پرداختنی

تاریخ شاهد: ۲۰۲۶-۰۸-۲۹  
وضعیت: **تأییدشده از Clone فقط‌خواندنی، Log ناشناس و IL هش‌سنجی‌شده**

## نتیجهٔ اصلی

Undo چک پرداختنی در وارانگار Event جبرانی اضافه نمی‌کند؛ آخرین
`PChequeHistory` را حذف، Pointer جاری چک را به History قبلی برمی‌گرداند و مصرف
برگ دسته‌چک را بازحساب می‌کند. Projection فعلی سازگار است، اما Audit trail ذاتاً
تخریبی است و برای ERP مقصد نباید کپی شود.

## قرارداد SQL

`dbo.DoPCheque_DeleteLastPChequeHistory`:

1. پیش از تراکنش، وابستگی سند حسابداری را کنترل می‌کند؛
2. تراکنش و TRY/CATCH باز می‌کند؛
3. آخرین History را Delete می‌کند؛
4. `PCheque.PChequeHistoryId` را به History قبلی برمی‌گرداند؛
5. `PChequeBookItem.IsUsed` را با وضعیت جدید بازحساب می‌کند؛
6. Commit دارد و در Catch، Rollback/خطای Domain دارد؛
7. هیچ History جبرانی Append نمی‌کند.

مسیر Add برعکس، History را Insert و بعد Projection و Leaf را Update می‌کند.
`usp_sdsnet_PChequeChangeStatus_Save` هر دو Add و DeleteLast را زیر تراکنش
بالاتر صدا می‌زند. از ده ماژول منتخب، چهار مورد تراکنش محلی صریح دارند.

## شاهد Log و فعالیت واقعی

در `GNR.tblLog` برای `dbo.PChequeHistory`:

- ۱۵٬۱۷۸ Insert، ۶٬۳۴۶ Update و ۱٬۶۶۸ Delete متمایز ثبت شده؛
- ۷۸ Delete در June–August 2026 است؛
- ۱٬۵۳۷ Delete دنبالهٔ دقیق SQL Undo یعنی
  `History DELETE → PCheque UPDATE → PChequeBookItem UPDATE` دارند؛ همهٔ ۷۸ مورد
  سه‌ماهه در همین گروه‌اند؛
- ۱۱۷ Delete در همان Session سیگنال حذف خود PCheque دارند و به Undo نسبت داده
  نشدند؛
- ۱۴ Delete فقط Partial update tail دارند و جدا نگه داشته شدند.

این تطبیق، اجرای واقعی قابلیت Undo را با اطمینان بالا ثابت می‌کند، اما Status
حذف‌شده، دلیل، User و Actor intent را بازیابی نمی‌کند.

## شکاف ۴۰۲ History

۱۵٬۱۷۸ History ID لاگ‌شده اکنون به ۱۳٬۱۰۸ حاضر و ۲٬۰۷۰ غایب تقسیم می‌شوند.
۱٬۶۶۸ غایب Delete log دارند، اما ۴۰۲ ID فقط Insert log دارند و اکنون غایب‌اند.
همهٔ این ۴۰۲ مورد در یک Batch حدود ۱٫۳ ثانیه‌ای در ۲۰۲۴-۰۳-۲۷ Insert شده‌اند و
هیچ مورد سه‌ماهه نیست.

این Batch به Undo، Trigger disable، Migration یا خطای خاصی نسبت داده نشد. برای
مهاجرت باید State مستقل `INSERT_LOGGED_ABSENT_WITHOUT_RETAINED_DELETE` بگیرد.

## Snapshot جاری

- ۴٬۶۷۲ چک و ۱۳٬۱۰۸ History؛ حداقل دو و حداکثر چهار History برای هر چک؛
- Pointer اشتباه، Pointer غیر-Max و Parent mismatch: صفر؛
- Current status: یک عودت، ۳٬۶۳۷ پرداخت، ۸۱ ابطالی و ۹۵۳ پرداختنی؛
- Transitionهای جاری فقط `1→4`، `1→5`، `2→4`، `5→2` و `5→3` هستند و با Master
  قبلی سازگارند.

Snapshot سالم، کامل‌بودن تاریخچهٔ حذف‌شده را ثابت نمی‌کند.

## شاهد Managed Runtime

دو Assembly `TreasuryOld.Forms.dll` و `TreasuryOld.DataAccess.dll` با Inventory
قبلی هم‌هش بودند. پنج Method و ۷۱۴ Instruction فقط از PE/IL خوانده شدند.

- فرم Legacy ابتدا `CanDoUndo`، سپس Transaction.Start و Adapter DeleteLast را
  صدا می‌زند؛ سیگنال Branch اختیاری `CreateApprovePChequeHistory`، Rollback،
  Refresh و Commit نیز وجود دارد.
- Adapter یک Transaction تو‌در‌تو دور ExecuteNonQuery با Commit/Rollback دارد.
- `frmPChequeTrackingNew.UndoStatus` فقط یک Instruction دارد، درحالی‌که CanDoUndo
  آن History count را می‌خواند. اینکه کدام فرم برای هر Role فعال است ثابت نشد.

ترتیب خطی IL، Branch اختیاری Reapprove یا نتیجهٔ Rollback را ثابت نمی‌کند.

## قرارداد مقصد

`R-073` با شدت بالا ثبت شد. مقصد باید:

- History را append-only نگه دارد؛
- Undo را به Event جبرانی `Reversed` با Ref به Event قبلی تبدیل کند؛
- Pointer، Leaf، Supplier ledger، Voucher dependency audit و Outbox را در یک
  Transaction بنویسد؛
- ExpectedVersion و Idempotency Key داشته باشد؛
- ۱٬۵۳۷ Undo قطعی و ۴۰۲ شکاف Batch را فقط به‌صورت Tombstone/Unknown provenance
  وارد کند و Status/Actor/Reason جعلی نسازد.

Fault injection و concurrent undo باید یک Projection قطعی بدهد. نسبت برگ‌های
مصرف‌شده نیز باید همان Baseline قبلی بماند: ۴٬۸۲۷ = ۴٬۶۷۲ متصل به چک + ۱۵۵
`SOURCE_USED_UNLINKED`.

## خروجی‌ها

- `artifacts/varanegar_analysis/domains/payable_cheque_undo_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/payable_cheque_undo_runtime_boundary_20260829.json`
- `scripts/sql/extract_varanegar_payable_cheque_undo_boundary.py`
- `scripts/sql/extract_varanegar_payable_cheque_undo_runtime_boundary.py`
- `scripts/windows/build_varanegar_payable_cheque_undo_checkpoint_20260829.py`
- `tests/test_varanegar_payable_cheque_undo_boundary.py`

هیچ Procedure، فرم، Command یا Assembly اجرا نشد و هیچ شناسهٔ چک/برگ/بانک، مبلغ،
SQL definition، Log script یا هویت عامل ذخیره نشده است.
