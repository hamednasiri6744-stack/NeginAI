# قرارداد Outcome/Retry فرمان‌های توزیع — ۱۴۰۵/۰۶/۰۷

چهار فرمان معتبر به envelope واحد متصل شدند: `create_or_update`، `issue_exit`، `merge_or_adjust_exit` و `remove_exit`. هر چهار مسیر UI→Business→Adapter→SQL دارند و هیچ‌کدام پارامتر idempotency صریح ندارند.

در مسیر عادی Issue و Remove، UI یک DataContext می‌سازد و پس از Adapter commit می‌کند، اما enlistment فیزیکی contextهای تو‌در‌تو اثبات نشده است. Merge در UI context/commit صریح ندارد و Procedure نیز commit محلی ندارد؛ بنابراین transaction owner آن صریحاً `UNPROVEN` است. Issue چند جدول را پیش از cardex check می‌نویسد و Remove بدون Begin/Commit محلی، graph سند انبار را حذف، فروش‌ها را unlink، خروج را soft-cancel و وضعیت توزیع را reset می‌کند.

چهار outcome مقصد `COMMITTED`، `REJECTED_NO_EFFECT`، `REJECTED_WITH_DURABLE_EFFECT` و `UNKNOWN_REQUIRES_READBACK` هستند. retry فقط بعد از read-back توزیع، خروج، سند نوع ۶۰، sale links، history و audit/outbox مجاز است. runtime parity، اجرای acceptance و owner approval صفر باقی مانده‌اند.
