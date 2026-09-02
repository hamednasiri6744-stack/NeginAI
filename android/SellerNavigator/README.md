# نگین فروش برای Android

این پوشه یک اپ بومی Android برای فروشنده است، نه WebView. قابلیت‌های فعلی آن:

- ورود امن به NeginAI و نگهداری نشست در فضای رمزنگاری‌شدهٔ Android
- دریافت فقط مسیرهای فروشندهٔ واردشده از بک‌اند NeginAI
- GPS زنده، نشانگر موقعیت، خط مسیر، کارت «تا ۲۰۰ متر دیگر / به چپ بپیچید» و رد کردن پایگاه
- تشخیص رسیدن به پایگاه در شعاع ۷۰ متر و اصلاح خودکار مسیر وقتی بیش از ۸۰ متر از مسیر خارج شود
- مسیریابی و بهینه‌سازی فقط در سرور؛ هیچ `NESHAN_SERVICE_API_KEY` در APK نیست
- راهنمای تصویریِ بدون صدا؛ بنابراین به کیفیت TTS یا اینترنتِ سرویس هوش مصنوعی وابسته نیست

## ساخت APK

1. Android Studio را نصب کنید و همین پوشه (`android/SellerNavigator`) را باز کنید.
2. در Android Studio یک debug signing key ایجاد می‌شود. SHA-1 آن را بگیرید:

   ```powershell
   keytool -list -v -keystore "$env:USERPROFILE\.android\debug.keystore" -alias androiddebugkey -storepass android -keypass android
   ```

3. در پنل نشان یک مجوز **Android SDK** با package زیر و SHA-1 کلید debug و release بسازید:

   ```text
   ir.neginpakhsh.seller
   ```

4. فایل دانلودشدهٔ `neshan.licence` را در این مسیر قرار دهید:

   ```text
   app/src/main/res/raw/neshan.licence
   ```

5. اگر آدرس سرویس شما متفاوت است، در `gradle.properties` مقدار `NEGIN_BASE_URL` را به دامنهٔ HTTPS واقعی تغییر دهید.
6. از Android Studio گزینهٔ **Build > Build APK(s)** را بزنید.

نقشهٔ نشان برای Android طبق راهنمای رسمی به فایل مجوزی نیاز دارد که به package و SHA‑1 امضای اپ متصل است؛ وابستگی‌های آن در Gradle پروژه قرار گرفته‌اند. تا زمان قراردادن مجوز، هستهٔ مسیر، موقعیت و کارت‌های راهنما کار می‌کنند اما لایهٔ نقشهٔ نشان نباید برای انتشار نهایی فعال تلقی شود.

## نکتهٔ بک‌اند

مسیرهای `/seller-workspace` اکنون bearer token معتبر را هم در کنار نشست وب می‌پذیرند. اپ فعلی برای ورود از نشست امن استفاده می‌کند و به API key داخلی دسترسی ندارد.
