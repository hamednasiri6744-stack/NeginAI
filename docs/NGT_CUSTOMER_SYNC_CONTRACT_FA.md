# قرارداد ثبت و ویرایش مشتری در NGT

تاریخ بررسی: ۱۴۰۵/۰۶/۰۳ ـ 2026-08-25

منابع بررسی‌شده:

- `C:\clientnew\NGT.ViewModels.dll` نسخه `5.9.0.170`
- `\\192.168.1.171\exe\NGTApp\Server\bin\NGT.WebApi.dll`
- `\\192.168.1.171\exe\NGTApp\Server\bin\NGT.Business.dll`

اصل معماری این بخش:

`اپ فروشنده نگین → NeginAI Backend → NGT Web API → آداپتور رسمی BackOffice ورانگر`

هیچ‌کدام از عملیات زیر نباید با نوشتن مستقیم در جداول عملیاتی ورانگر انجام شوند.

## درگاه مشترک تور

در NGT هر سه جریان همراه مدل `SyncGetTourViewModel` به درگاه زیر می‌رسند:

`POST /api/v2/ngt/tour/sync/savedata`

متد سرور متناظر:

`TourController.RequestSaveTourData(SyncGetTourViewModel tour, int? deviceSettingCode)`

این مدل سه محل مستقل برای اطلاعات مشتری دارد:

- `CustomerUpdates`: ویرایش مشخصات مشتری موجود
- `CustomerLocations`: ثبت یا اصلاح مختصات مشتری موجود
- `CustomerCalls[].SyncCustomer`: تعریف مشتری جدید

## ۱. ثبت موقعیت مشتری موجود

مدل رسمی `SyncGetCustomerUpdateLocationViewModel`:

- `CustomerId: Guid`
- `AgentUniqueId: string`
- `CustomerCode: string`
- `BackOfficeId: string`
- `Longitude: double`
- `Latitude: double`

مسیر قطعی در سرور NGT:

`SyncGetTourViewModel.CustomerLocations[]`

→ `TourDomain.SaveTourData`

→ `CustomerDomain.UpdateCustomerLatitudeLongitude`

→ `CustomerDomain.UpdateCustomersLocation`

→ `VisitTemplatePathPointRepository.UpdateCustomerPointLocation`

→ `SyncFactory.GetSyncAdapter<Customer>().RetrieveInfo(CustomerUpdateLocation, BackOfficeConnectionString)`

بنابراین ثبت مختصات هم داده داخلی NGT/نقطه مسیر را به‌روزرسانی می‌کند و هم از آداپتور رسمی BackOffice برای نشاندن نتیجه در ورانگر استفاده می‌کند.

## ۲. ویرایش مشخصات مشتری موجود

مدل رسمی `SyncGetCustomerUpdateDataViewModel`:

- شناسه‌ها: `CustomerId`, `TourUniqueId`, `AgentUniqueId`
- تماس و هویت: `Phone`, `Mobile`, `NationalCode`, `EconomicCode`, `PostalCode`, `CustomerCode`
- مشخصات محل کسب: `StoreName`, `Address`, `CityZone`
- طبقه‌بندی‌ها: `CustomerActivityId`, `CustomerLevelId`, `CustomerCategoryId`, `OwnerTypeRef`
- جغرافیای اداری: `StateId`, `CityId`, `CountyId`

مختصات در این مدل وجود ندارد و باید جداگانه در `CustomerLocations` ارسال شود.

مسیر قطعی در سرور NGT:

`SyncGetTourViewModel.CustomerUpdates[]`

→ `TourDomain.SaveTourData`

→ `BackOfficeInfoRetrieverViewModel.CustomerUpdateData`

→ آداپتور رسمی BackOffice

و هم‌زمان `CustomerDomain.UpdateCustomer` اطلاعات متناظر NGT را در تراکنش محلی به‌روزرسانی می‌کند.

## ۳. تعریف مشتری جدید

مشتری جدید عضو مستقل در ریشه تور نیست. داخل یک `CustomerCall` ثبت می‌شود:

- `CustomerCalls[].IsNewCustomer = true`
- `CustomerCalls[].SyncCustomer = SyncGetNewCustomerViewModel`

فیلدهای مدل `SyncGetNewCustomerViewModel`:

- نام و تماس: `FirstName`, `LastName`, `StoreName`, `Address`, `Phone`, `Mobile`
- هویت: `PostalCode`, `NationalCode`
- مسیر و سازمان: `PathId`, `DealerId`
- طبقه‌بندی: `CustomerCategoryId`, `CustomerLevelId`, `CustomerActivityId`, `CustomerCityZoneId`, `OwnerTypeId`, `CustomerGroupId`
- محدوده اداری: `StateId`, `CityId`, `CountyId`
- پرسش‌نامه‌ها: `CustomerCallQuestionnaires`

مسیر قطعی در سرور:

`TourDomain.SaveTourData`

→ `CustomerDomain.RegisterNewCustomer`

→ کنترل مشتری تکراری

→ `SyncFactory` و آداپتور رسمی با `BackOfficeConnectionString`

→ ثبت نتیجه در NGT و ورانگر

نتیجه رسمی شامل `UniqueId`, `Code`, `ErrMsg` است. پرسش‌نامه‌های همراه نیز از مسیر `SaveQuestinnariesInRegisterNewCustomer` پردازش می‌شوند.

## تفاوت با انتقال سفارش پیش‌فروش

انتقال سفارش پیش‌فروش به ورانگر مسیر کنترل‌شده زیر را دارد:

`GET /api/v2/ngt/tour/PreSale/Replicate/{tourId}`

ولی ویرایش اطلاعات پایه مشتری، ثبت موقعیت و تعریف مشتری جدید در خود پردازش `savedata` از آداپتور BackOffice استفاده می‌کنند. این سه قابلیت نباید به اشتباه به مسیر Replicate سفارش یا نوشتن مستقیم SQL وصل شوند.

## وضعیت فعلی NeginAI

- فرم مشتری قرارداد فیلدهای NGT را می‌خواند.
- تغییرات در `previsit_customer_update_drafts` فقط به‌صورت پیش‌نویس محلی ذخیره می‌شوند.
- دکمه «ثبت موقعیت فعلی مشتری» GPS تازه می‌گیرد و فقط `latitude/longitude` فرم را پر می‌کند.
- هنوز هیچ ارسال خودکار `CustomerUpdates`، `CustomerLocations` یا تعریف مشتری جدید از رابط فعال نشده است.

مرحله بعدی باید پس از تأیید کاربردها، یک سازنده payload ممیزی‌پذیر بسازد که مختصات را از مشخصات جدا کند، شناسه‌های NGT را کامل کند، ارسال را idempotent نگه دارد و نتیجه NGT/BackOffice را ثبت کند.
