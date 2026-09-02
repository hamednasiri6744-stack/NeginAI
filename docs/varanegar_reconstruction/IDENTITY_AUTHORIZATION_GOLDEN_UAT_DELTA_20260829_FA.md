# Golden/UAT Delta هویت و مجوزدهی

۱۸۴ Case provisional موجود برای Role Template، capability، deny pattern، context invalidation و SoD بدون تکرار reuse می‌شود. ۴۲ Case تازه در شش سطح ساخته شده است: تقدم deny، Application/Owner/Data scope، default-deny endpoint، حذف admin bypass، revoke/session epoch و SoD/break-glass.

هر سطح هفت حالت authorization denial، stale policy/version، duplicate command، scope/policy mismatch، fault injection، grant/revoke هم‌زمان و success دارد. مجموع طراحی ۲۲۶ است؛ executed، passed-runtime، owner-approved و production-assignment همگی صفرند.

اجرای آینده فقط در target ایزوله، با principalهای کاملاً مصنوعی و opaque، policy تأییدشده، token/session harness، fault injection و پوشش مکانیکی endpoint مجاز است.
