# نقشهٔ منو و ناوبری وارانگار به ماژول‌های مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۸۳۶ Route در ۳۱ ریشه؛ درخت بدون Cycle/Orphan و Validation برابر PASS**

## ساختار واقعی منو

پیکربندی سراسری وارانگار ۸۳۶ ردیف Menu دارد؛ ۳۱ بخش ریشه، عمق حداکثر چهار،
۳۹۹ Route دارای FormInfo/AccessNode، ۲۴۱ تنظیم قابل نمایش در Container، ۱۷ Route
Modal و سه Action menu ثبت شد. این کاتالوگ منوی مؤثر یک کاربر خاص نیست.

بزرگ‌ترین بخش‌ها:

- «فروش»: ۱۷۸ Route، ۱۸ فرم Runtime تطبیق‌شده؛
- «خزانه‌داری»: ۱۴۳ Route، ۴۴ فرم Runtime تطبیق‌شده؛
- «اطلاعات پایه ۲»: ۵۷ Route، ۳۹ فرم Runtime تطبیق‌شده؛
- «انبار»: ۵۵ Route، شش فرم Runtime تطبیق‌شده؛
- «تنظیمات سیستم»: ۵۰ Route، چهار فرم Runtime تطبیق‌شده؛
- «کنسول تبلت»: ۴۳ Route و صفر فرم Runtime تطبیق‌شده در بستهٔ فعلی؛
- «کنسول مدیریت فروش»: ۴۰ Route و صفر تطبیق Runtime.

این توزیع توضیح می‌دهد چرا ERP مقصد باید Navigation را بر اساس Capability و
Context بازطراحی کند؛ تکرار عین درخت Legacy، مرز مالکیت ماژول را مخدوش می‌کند.

## پوشش Runtime Routeها

هر ۸۳۶ Route در یکی از کلاس‌های زیر قرار گرفت:

- ۴۳۷ Navigation-only بدون Form config؛
- ۱۶۰ Form تطبیق‌شده با Runtime فعلی؛
- ۶۱ Navigation/selector shell دارای FormInfo ولی بدون Type نهایی تطبیق‌شده؛
- ۳۴ Leaf که به Package حاضر اشاره می‌کند ولی Type آن با کاتالوگ فرم تطبیق نشد؛
- ۱۰۴ Leaf با Hint بستهٔ خارجی یا غایب؛
- ۳۷ Leaf با Target تهی/Placeholder؛
- سه Leaf با Target Redacted که Review می‌خواهد.

از ۱۶۰ تطبیق Runtime، فقط ۱۲۶ مورد Primary domain دارند. ۱۷۸ Leaf/Shell
تطبیق‌نشده را نباید به‌صورت ۱۷۸ قابلیت مفقود تفسیر کرد؛ بعضی Menu shell، Legacy،
افزونهٔ خارجی، Placeholder یا Dynamic target هستند. بااین‌حال ۳۴ مورد
Present-package و ۱۰۴ External/absent برای Scope freeze نیازمند Review هستند.

## نگاشت ماژولی

ریشه‌ها به‌عنوان Navigation hint و Formهای تطبیق‌شده به‌عنوان Domain hint جدا
نگه داشته شدند. Hint ریشه مالکیت نهایی Aggregate نیست. یک بخش Legacy می‌تواند
چندماژولی باشد؛ برای نمونه خزانه‌داری هم Receivables و هم Payables را پوشش می‌دهد،
حسابداری انبار میان Inventory/Accounting مشترک است و سامانه ردیابی میان Report و
دو سوی Treasury قرار می‌گیرد.

تعداد Assignment ماژولی ۱٬۱۹۲ برای ۸۳۶ Route است چون Rootهای چندماژولی به‌زور
در یک مالک ادغام نشدند. تنها ۱۳۱ Assignment از Primary domain فرم تطبیق‌شده
می‌آید و شاهد قوی‌تر برای مالکیت رفتاری است.

## پیامد طراحی Web ERP

- منو از Capability + Scope + Context + Config ساخته می‌شود؛ Visibility مجوز
  Query/Command نیست؛
- Routeهای Shell و Selector به صفحهٔ مستقل تبدیل نمی‌شوند مگر Workflow ایجاب کند؛
- Sales/Treasury/Master/Inventory چهار خوشهٔ نخست برای Information architecture
  و تست Navigation هستند؛
- Tablet/B2B/POS و بسته‌های خارجی مرز Integration دارند و در Core table writer
  ادغام نمی‌شوند؛
- Rootهای چندماژولی در مقصد به Navigation view تبدیل می‌شوند، نه مالک داده.

## مرز اطمینان

این نقشه از پیکربندی ثابت Redacted ساخته شده و هیچ حق کاربر/گروه یا دادهٔ عملیاتی
نخوانده است. `is_show_in_container=1` به معنی قابل‌استفاده بودن برای همه کاربران
نیست. Target غایب نیز می‌تواند Plugin، Dynamic loader یا نسخهٔ خارج از Share
فعلی باشد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_navigation_module_map_20260827.json`
- `scripts/windows/build_varanegar_navigation_module_map.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: اولویت‌بندی ۱۷۸ Shell/Leaf تطبیق‌نشده بر اساس Visible/Access/Module و
ساخت Scope-freeze checklist برای قابلیت‌های خارج از بستهٔ فعلی.
