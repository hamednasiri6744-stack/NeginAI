# Truth Table فرمان، Outcome و Lineage حسابداری — ۱۴۰۵/۰۶/۰۷

هفت candidate فرمان به سه سطح شواهد تفکیک شدند: چهار مسیر External Voucher با Procedure دقیق و transaction owner ایستای قوی؛ یک مسیر confirm/unconfirm سند انبار با ابهام route؛ و دو مسیر Manual Voucher که فعلاً فقط candidate UI هستند.

نکتهٔ کلیدی کارشناسی: متن خطا معادل Rollback نیست. در transfer حسابداری، cleanup مربوط به `SetVoucherNo` می‌تواند پیش از validation رخ دهد و business-error بدون exception با اثر durable همراه باشد. بنابراین retry باید پس از read-back وضعیت، pointer، history و effect انجام شود، نه کورکورانه.

همچنین current pointer معادل `MAX(history)` نیست؛ ۱٬۰۹۴ pointer غیرحداکثری و ۱۴٬۹۴۶ event متأخر وجود دارد. یک shell شماره‌دار بدون line نیز نباید خودکار تکمیل یا شماره‌اش بازیافت شود.

قرارداد ERP مقصد باید command id، expected version، snapshot policy، نتیجهٔ typed، committed flag، durable-effect summary و correlation id داشته باشد. Artifact ماشین‌خوان جزئیات هر هفت مسیر، confidence، موارد اثبات‌نشده، risk links و hash منابع را ثبت می‌کند.
