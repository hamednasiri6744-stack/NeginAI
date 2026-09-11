# جمع‌بندی اسکن امنیتی NeginAI — ۲۰۲۶/۰۹/۰۲

## حکم

اسکن استاندارد کل مخزن در بازبینی `673112f6ce5bb1f8dfaca41804cbd893b57bfc6c` تکمیل شد. ۱۰ یافته با مسیر حمله و اعتبارسنجی مستقل ثبت شد: **۵ High، ۴ Medium و ۱ Low**. هیچ تغییر اصلاحی در کد یا محیط رئیس/عملیاتی اعمال نشد.

این نتیجه یک بازبینی ایستای منبع است. دیتابیس و شبکه زنده، گواهی واقعی SQL Server، ACL درگاه بیرونی، دستگاه Android و بار ۲۰۰ کاربر آزمایش نشده‌اند.

## یافته‌های High

1. **رمز اولیه مشترک برای کاربران فروش:** اسکریپت provisioning رمز ثابت `1` را برای همه می‌سازد، کنار مشخصات حساب در CSV می‌گذارد و می‌تواند آن را روی حساب فعال اعمال کند. ریشه: `scripts/provision_sales_users.py:31`.
2. **API key مشترک با عبور از مرز هویت و مجوز:** همه دارندگان کلید به principal مشترک و unrestricted تبدیل می‌شوند؛ همان secret برای امضای session نیز استفاده می‌شود. ریشه کنترل: `app/access_control.py:199` و sink امضا: `app/auth_service.py:263`.
3. **ادامه OAuth پس از غیرفعال/حذف کاربر:** refresh و access validation وضعیت جاری کاربر را بررسی نمی‌کنند و refresh چرخشی عمر ۳۰روزه تازه می‌دهد. ریشه: `app/oauth_service.py:85`.
4. **اعتبارسنجی گواهی SQL Server خاموش است:** اتصال‌های ODBC گزارش و bridge به‌طور پیش‌فرض `TrustServerCertificate=yes` دارند. ریشه: `app/config.py:23`؛ sinkها: `app/database.py:612` و `app/varanegar_order_bridge.py:69`.
5. **کد ثالث در WebView دارای bridge ممتاز:** JavaScript نشان بدون SRI/CSP در context احراز‌شده اجرا می‌شود و bridge میکروفن، موقعیت، چاپ و TTS origin-bound نیست. ریشه: `app/static/assistant.html:301` و `AssistantActivity.kt:365`.

## یافته‌های Medium

6. **عدم ابطال session:** logout فقط cookie همان مرورگر را پاک می‌کند و تغییر رمز session کپی‌شده را تا پایان ۸ ساعت باطل نمی‌کند. `app/auth_service.py:263`.
7. **SQL فقط‌خواندنی اما بی‌مهار از نظر هزینه/قفل:** guard عملیات نوشتن را رد می‌کند، ولی lock hint و query بسیار پرهزینه را محدود نمی‌کند؛ سقف ردیف پس از اجراست. `app/sql_guard.py:19` و `app/database.py:762`.
8. **نبود quota/budget/concurrency سراسری مدل:** chat، فایل، STT و TTS فاقد محدودکننده توزیع‌شده per-user و سقف هزینه‌اند. `app/routes/chat.py:144`.
9. **buffer شدن کامل صوت پیش از سقف ۲۵MB:** `request.body()` پیش از بررسی اندازه اجرا می‌شود و Caddy نیز سقف بدنه ندارد. `app/routes/audio.py:137`.

## یافته Low

10. **افشای جزئیات readiness در `/health`:** endpoint عمومی وضعیت integrationها، write flags، مدل‌ها و limits را برمی‌گرداند. `app/routes/health.py:1`.

## اولویت اصلاح

- **P0 قبل از pilot:** یافته‌های ۱ تا ۵؛ جداسازی کلید session، هویت service-principal محدود، revocation کامل OAuth، TLS معتبر SQL Server و جداسازی امن WebView bridge.
- **P0 ظرفیت:** یافته‌های ۷ تا ۹؛ SQL allowlist، Redis-backed quota/semaphore/budget، صف محدود و streaming با body cap.
- **P1 عملیات:** session registry/generation و تفکیک liveness عمومی از readiness مدیریتی.

## دروازه‌های اثبات اصلاح

- هر activation secret تصادفی، یکتا، یک‌بارمصرف و بدون export کنار PII باشد.
- کلید service نتواند session کاربر بسازد یا raw SQL/admin/user-owned resource را بدون scope ببیند.
- deactivation، حذف و reset رمز، همه token familyها و sessionهای مربوط را باطل کند.
- اتصال با self-signed، hostname اشتباه و CA نامعتبر fail شود.
- کد third-party/iframe نتواند bridge، میکروفن یا موقعیت را فراخوانی یا دریافت کند.
- burst و soak چندکاربره دقیقاً در quota متوقف شود و latency دیگر کاربران را نقض نکند.
- queryهای lock-hint و cross-join انفجاری رد شوند و ERP در آزمون همزمان block نشود.
- فایل صوتی بسیار بزرگ و chunked با RSS تقریباً ثابت، پاسخ 413 بگیرد.

## خروجی canonical اسکن

- Scan ID: `9423b3ea-5e46-4a20-8f0c-a31c9b3bfd46`
- گزارش کامل: `C:\Users\Sys\AppData\Local\Temp\codex-security-scans-SQkReQ\NeginAI\673112f6ce5bb1f8dfaca41804cbd893b57bfc6c_20260902T105448Z_nx44xs2_\report.md`
- داده یافته‌ها: همان پوشه، `findings.json`
- پوشش: همان پوشه، `coverage.json`
- SARIF: همان پوشه، `exports\results.sarif`

هشدار ابزار: محتوای working tree در طول اسکن به‌دلیل ساخت همین گزارش‌ها تغییر کرد؛ اسکن روی snapshot ثابت بازبینی فوق مهر شده است.
