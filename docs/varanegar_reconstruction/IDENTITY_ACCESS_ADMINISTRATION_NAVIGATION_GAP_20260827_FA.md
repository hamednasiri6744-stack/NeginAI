# شکاف Runtime مدیریت کاربر، گروه و دسترسی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای قرارداد شکاف Navigation؛ صفر هویت/Grant واقعی و صفر رفتار Runtime اثبات‌شده**

## نتیجه

در درخت ۸۳۶ Route وارانگار، شانزده مسیر استاتیک مرتبط با معرفی کاربر/گروه،
تنظیمات کاربری، دسترسی ویژه، دسترسی انبار/مالی، صندوق و دسترسی کاربر/گروه به
اطلاعات جدا شد. هیچ‌یک در بسته Runtime فعلی به Form type منطبق نرسید:

- شش مسیر فقط Navigation هستند؛
- پنج مسیر به Package خارجی یا غایب اشاره دارند؛
- دو مسیر Type حاضر ولی Runtime-unmatched دارند؛
- دو مسیر Shell انتخاب/Navigation هستند؛
- یک مسیر Target تهی/Placeholder دارد.

ده مسیر `FormInfoId` و `AccessNodeId` دارند، اما این شناسه‌ها فقط Configuration
route هستند و رفتار مجوز مؤثر را ثابت نمی‌کنند. هیچ نام کاربر، عضویت گروه، رمز،
Token یا Grant فردی خوانده یا ذخیره نشد.

## قرارداد مقصد

مرز مقصد باید `deny-first capability + scope` باشد و تخصیص کاربر و گروه را از
خود Capability جدا نگه دارد. Explain هر تصمیم حداقل Decision، Capability، Scope،
منبع Role/Exception، علت Deny و Policy version را برگرداند. دسترسی ویژه باید
زمان‌دار، دلیل‌دار و Auditپذیر باشد؛ Scope صندوق، انبار، مالی، اطلاعات و «اسناد
همه کاربران» نیز Capability صریح است، نه نتیجه‌ی پنهان visibility منو.

اولین Slice مجاز، کاتالوگ فقط‌خواندنی Role/Capability/Scope بدون هویت شخص است.
فعال‌سازی Write یا مدیریت Grant تا Policy مورد تأیید مالک، UAT احرازشده، تست‌های
SoD و Audit تغییرناپذیر روی Target ایزوله مسدود است.

## شواهد و محدودیت

- Artifact: `varanegar_identity_access_navigation_gap_contract_20260827.json`
- Builder: `build_varanegar_identity_access_navigation_gap_contract.py`
- ورودی‌ها: `varanegar_navigation_module_map_20260827.json` و
  `negin_erp_role_sod_contract_20260827.json`
- این سند رفتار Package غایب، Grant مؤثر اشخاص یا نتیجه Runtime را ادعا نمی‌کند.
