# قرارداد Outcome/Retry فرمان‌های خزانه — ۱۴۰۵/۰۶/۰۷

دوازده فرمان در چهار خانواده به یک envelope واحد متصل شدند: سه Edit قدیمی، دو فرمان lifecycle چک دریافتی، دو مسیر NGT payment/replication و پنج فرمان طراحی‌شدهٔ تطبیق بانکی. هفت مسیر اول شواهد ایستای hash-pinned دارند؛ پنج فرمان بانکی فقط قرارداد مقصدند و implementation آنها صفر است.

مرزهای مهم حفظ شدند. `received_cheque.delete` مالک transaction اثبات‌شده ندارد. Undo دارای transactionهای تو‌در‌تو و ابهام branch/form است. `SaveTourPaymentChanges` Begin/Commit/Rollback صریح دارد، اما ۵۷ مورد underallocation در aggregate کلون و runtime parity حل نشده است. در replication، Commit قبل و بعد از crosswalk setter در IL دیده می‌شود، ولی یک مسیر اتمیک runtime اثبات نشده است.

ERP مقصد چهار outcome صریح دارد: `COMMITTED`، `REJECTED_NO_EFFECT`، `REJECTED_WITH_DURABLE_EFFECT` و `UNKNOWN_REQUIRES_READBACK`. retry با `command_id` یکتا و read-back وضعیت، history، crosswalk و audit/outbox کنترل می‌شود. runtime effect parity، اجرای acceptance و تأیید مالک همگی صفر باقی مانده‌اند.
