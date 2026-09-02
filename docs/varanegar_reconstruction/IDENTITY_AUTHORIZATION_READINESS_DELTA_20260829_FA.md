# دلتا‌ی آمادگی هویت و مجوزدهی

این دلتا فقط coverage طراحی Outcome/Retry ماژول `identity_authorization` را از false به true تغییر می‌دهد. تعداد ماژول‌های دارای target contract از ۱۰ به ۱۱ می‌رسد و ۱۸۴ Case مصنوعی موجود به ماژول نگاشت می‌شود.

هیچ ارتقای runtime رخ نداده است: مجوز مؤثر، owner-filter، invalidation نشست، SoD، break-glass، owner approval، command readiness و pilot readiness همگی اثبات‌نشده یا صفرند. ۶۰ endpoint فاقد declaration روشن و ۳۸ endpoint تغییردهنده زیرمجموعهٔ آن، gate بررسی code-owner باقی می‌مانند.
