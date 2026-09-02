# مرز تقدم، ترکیب و انتقال تنظیمات NGT — ۱۴۰۵/۰۶/۰۷

## نتیجه

تنظیمات NGT یک جدول یا یک زنجیره‌ی override ساده نیست. دست‌کم پنج سطح مستقل در
رفتار فعلی دیده می‌شود: تنظیم سراسری `GeneralConfig`، تنظیم سراسری Server، تنظیم
مرکز پخش، singleton برنامه و پروفایل Device متصل به کاربر. مسیر زنده‌ی Business و
Viewهای انتقال نیز همیشه یک Resolver مشترک ندارند.

این بررسی دو اختلاف جاری و قابل‌اندازه‌گیری را ثابت کرد:

1. `MandatoryCustomerVisit` در Business از `DeviceSettings` خوانده می‌شود، اما
   در View انتقال از `AppSettings` می‌آید. مقدار singleton برنامه با هر ۱۷ پروفایل
   فعال Device ناسازگار است؛ دو مقدار Device نیز NULL هستند.
2. تنظیمات BackOffice زنده با `DataOwnerCenterKey` و
   `GNR.SdsNet_serverConfig` مرکز-محور بازیابی می‌شوند، اما
   `FRU.NGT_TourBackOfficeSettingModel` از `tblServerConfig` سراسری Pivot می‌سازد.
   در ۱۲ نگاشت بررسی‌شده، یک خروجی در قرارداد UNPIVOT جا افتاده، پنج خروجی
   تعریف‌شده اکنون غایب‌اند و هفت مقایسه‌ی مرکز-به-انتقال ناسازگار است.

این‌ها اختلاف قرارداد هستند؛ وقوع خطای عملیاتی برای کاربر یا ارسال واقعی پروفایل
حذف‌شده ادعا نمی‌شود.

## مرز ایمنی و منابع

- دیتابیس فقط‌خواندنی `NeginPakhsh_WebDev` با `can_update=0` و
  `db_denydatawriter=1` خوانده شد.
- هیچ SP عملیاتی، Endpoint یا فرمان برنامه اجرا نشد.
- چهار Assembly با مجموع ۲۷٬۷۸۸ بدنه‌ی متد فقط از طریق PE metadata و IL خوانده
  شدند؛ Assembly بارگذاری یا اجرا نشد.
- مقدار تنظیم، Connection String، Secret، Host، هویت و ردیف خام تاریخچه در
  Artifactها ذخیره نشده است.
- سه خطای parse بدنه وجود دارد؛ یکی `Migrations.Configuration.Seed` است. این خطا
  به مسیر runtime انتخاب تنظیم نسبت داده نشده، ولی Seed کامل اثبات‌شده نیست.

## لایه‌های ذخیره‌سازی فعلی

| سطح | شکل فعلی |
|---|---:|
| `GNR.tblGeneralConfig` | ۱۷۷ کلید یکتا، بدون NULL |
| `GNR.tblServerConfig` | ۳۳۴ کلید یکتا، سه مقدار NULL |
| `GNR.tblServerConfigDC` | دو ردیف، ۱۰۷ ستون، بدون PK/Unique ثبت‌شده |
| `GNR.tblCustConfig` | ۱۰۲ ردیف، PK فقط روی ID |
| `GNR.tblCustConfigDC` | دو ردیف، بدون PK/Unique ثبت‌شده |
| `NGT.AppSettings` | یک ردیف فعال، ۶۵ ستون، PK فقط روی ID |
| `NGT.DeviceSettings` | ۴۰ ردیف: ۱۷ فعال و ۲۳ حذف‌شده، ۱۵۵ ستون |
| `NGT.DeviceSettingKeyTypes` | ۲۱۳ کلید انتقال |

چهار نام کلید بین General و Server دقیقاً مشترک‌اند، اما هم‌نامی به‌تنهایی تقدم
را ثابت نمی‌کند. سه کلید Server مقدار NULL دارند. در دو ردیف تنظیم مرکز، دو فیلد
کنترلی چک هر کدام یک NULL دارند؛ در App یک قاعده‌ی تاریخ برگشت NULL است؛ و
`MandatoryCustomerVisit` در کل Deviceها پنج NULL دارد که دو مورد آن فعال است.

## Resolver زنده‌ی Business

`DeviceSettingDomain.GetDeviceSettings(agentId, subSystemType)`:

- برای DeviceSetting و DeviceUser از `GetQueryByOwner` استفاده می‌کند؛
- روی هر دو Entity شرط `IsRemoved != true` می‌سازد؛
- DeviceUser را با DeviceSetting join و کاربر را با `agentId` محدود می‌کند؛
- نتیجه را با `FirstOrDefault` برمی‌گزیند؛
- خروجی Sync را به ترتیب App، General، Tracking، PreSale، HotSale، Distribution،
  TaskPriority، Report، Print، BackOffice و Inquiry به یک List اضافه می‌کند.

`GetDistributionDeviceSetting` و `GetVanSaleDeviceSetting` نیز
`GetQueryByOwner → Where(SubSystemType) → FirstOrDefault` دارند. طبق مرز Owner
قبلی، `GetQueryByOwner` علاوه بر Application/DataOwner/Center، سیاست RemovedData
را وارد Predicate می‌کند.

`AppSettingDomain.GetAppSetting` برعکس، با `GetById` و شناسه‌ی singleton ثابت
`AppSettingUniqueId` بازیابی می‌شود. `GetSettings` علاوه بر ردیف DB، تنظیمات
runtime برنامه مانند ReplicationEnabled و Connection String را نیز به ViewModel
اضافه می‌کند؛ مقدار این تنظیمات در این تحلیل خوانده یا ذخیره نشده است.

فرمان‌های Add، Update و Remove پروفایل Device transaction صریح، Commit و
Rollback دارند. Update همچنین User، OrderType، TaskPriority و PrintConfig را
مدیریت می‌کند. این وجود Transaction، صحت تمام قواعد یا idempotency را به‌تنهایی
ثابت نمی‌کند.

## مسیر BackOffice زنده در برابر View انتقال

`BackOfficeSettingDomain.GetSettings` یک Sync adapter می‌سازد،
`DataOwnerCenterKey` را روی درخواست می‌گذارد، درخواست نوع ۶۶ را Invoke می‌کند و
اولین نتیجه را برمی‌گرداند. SQL متناظر `dbo.NGT_GetBackOfficeSettings` تنظیمات
مرکز را از `GNR.SdsNet_serverConfig WHERE DcRef=@DCRef` می‌خواند.

در مقابل، `FRU.NGT_TourBackOfficeSettingModel`:

- General را از `tblGeneralConfig` Pivot می‌کند؛
- ServerSetting را فقط از `tblServerConfig` سراسری Pivot می‌کند؛
- CustConfig را بدون شرط `DcRef` Pivot می‌کند؛
- چهار CTE را Cross Join و سپس به نام/مقدار UNPIVOT می‌کند.

Procedure زنده ۳۶ نام خروجی دارد و قرارداد UNPIVOT انتقال ۳۰ نام. پس از کنار
گذاشتن rename شناخته‌شده‌ی `DCName → DistributionCenterName`، شش خروجی Procedure
در View انتقال نیستند: `CompanyEconCode`، `CustomerCounty`، `CustomerState`،
`CustStatusAfterUpdate`، `SendInactiveDealerForInvoiceReturn` و
`SettlementDiscountPercent`.

برای ۱۲ فیلد منبع→نام انتقال:

- پنج فیلد `MaximumOrderAmount`، `MinimumOrderAmount`،
  `MaximumOrderItemCount`، `MinimumOrderItemCount` و `RefRetOrder` در دو مرکز با
  خروجی انتقال فعلی هم‌ارزند؛
- `SettlementDiscountPercent` در CTE ساخته می‌شود ولی در فهرست UNPIVOT نیست؛
- پنج خروجی دیگر در UNPIVOT تعریف شده‌اند اما در snapshot فعلی ردیف خروجی
  ندارند، چون منبع سراسری NULL/غایب است؛
- روی همان پنج خروجی، هفت ردیف مرکز مقدار مؤثر متفاوت/موجود دارد.

SQL `UNPIVOT` مقدار NULL را به ردیف تبدیل نمی‌کند؛ بنابراین غیبت کلید در خروجی
با «وجود کلید و مقدار پیش‌فرض» یکسان نیست.

## اختلاف `MandatoryCustomerVisit`

- Business `GetGeneralConfigs`، getter متعلق به `DeviceSetting` را فراخوانی و
  مقدار را به رشته تبدیل می‌کند؛ getter متناظر App در `GetAppSettingConfigs`
  وجود ندارد.
- `FRU.NGT_TourAppSettingModel` فیلد App را به قرارداد انتقال می‌برد.
- `FRU.NGT_TourDeviceSettingModel` فیلد Device را وارد قرارداد نمی‌کند.
- در snapshot فعلی، هر ۱۷ Device فعال با App singleton ناسازگار است و دو مقدار
  Device NULL هستند.

پس نام واحد، معنای واحد را تضمین نمی‌کند. برای ERP مقصد باید تعیین شود این قانون
Global است یا per-device؛ کپی‌کردن یکی از دو مسیر بدون تصمیم مالک محصول مجاز نیست.

## حذف پروفایل و ارجاعات

- ۴۰ شماره‌ی DeviceSetting یکتا هستند؛ duplicate شماره وجود ندارد.
- View خام `FRU.NGT_TourDeviceSettingModel` هر ۴۰ شماره را منتشر می‌کند و ۲۱۸۴
  ردیف key/value متعلق به ۲۳ پروفایل حذف‌شده می‌سازد.
- `DeviceUsers`، `DeviceTaskPriorities` و `DevicePrintConfigs` فعلی به پروفایل
  حذف‌شده وصل نیستند.
- ۵۱ ردیف فعال `DeviceOrderTypes` به پروفایل‌های حذف‌شده FK دارند.
- مسیر runtime انتخاب کاربر، removed را صریح/ضمنی حذف می‌کند؛ بنابراین ارسال
  واقعی پروفایل حذف‌شده اثبات نشده است.

در مقصد، Profile retirement باید قرارداد جدا برای وابستگی‌های User، OrderType،
TaskPriority و PrintConfig داشته باشد؛ Cascade خام یا باقی‌گذاشتن ارجاع مبهم هر دو
نامناسب‌اند.

## تصمیم معماری برای ERP نگین

یک Resolver نسخه‌دار لازم است که ورودی آن شامل ApplicationOwner، DataOwner،
DataOwnerCenter، subsystem، device profile، user assignment و زمان اثر باشد و
برای هر خروجی این موارد را برگرداند:

- نام Canonical و نوع داده؛
- مقدار مؤثر؛
- لایه‌ی منبع و نسخه؛
- علت fallback/default؛
- وضعیت active/removed؛
- نام legacy و نام خروجی انتقال؛
- سیاست NULL و Unknown؛
- hash قرارداد استفاده‌شده در Sync.

`R-061` تا زمانی باز می‌ماند که Golden caseهای Business/API/Replication برای تمام
فیلدهای مشترک صفر اختلاف توضیح‌نداده داشته باشند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/domains/configuration_precedence_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_configuration_runtime_boundary_20260829.json`
- `artifacts/varanegar_analysis/varanegar_configuration_checkpoint_20260829.json`
- `scripts/sql/extract_varanegar_configuration_precedence_boundary.py`
- `scripts/sql/extract_varanegar_ngt_configuration_runtime_boundary.py`
- `scripts/windows/build_varanegar_configuration_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json` (`R-061`)

هر دو Extractor فقط خواندنی‌اند. اجرای مجدد IL باید روی همان چهار DLL hash-pinned
انجام شود و اجرای SQL فقط روی Clone محلی READ_ONLY مجاز است.
Checkpoint مستقل این خوشه ۱۵ منبع را hash-pin کرده و هر ۳۹ gate آن `PASS` است؛
این عدد به معنی آمادگی اجرای Command نیست و Traceability همچنان صفر ماژول
command-ready نشان می‌دهد.
