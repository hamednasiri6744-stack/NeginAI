# دامنه ۹: توزیع، تیم ارسال، خروج و شاهد تحویل

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/distribution_delivery_20260826.json`

این مرحله ۱۴ جدول، ۹۷ ارتباط FK رسمی، ۱٬۲۷۸ مصرف‌کننده ماژولی و ۳۹ کاندید
ارتباط ضمنی را بررسی کرده است. ۳۰ کاندید FK رسمی ندارند. هیچ نام مشتری یا
پرسنل، متن توضیحات، مختصات، نام کاربر/میزبان، Credential یا مقدار خام
Collection در Artifact ذخیره نشده است.

## هسته دامنه

```text
SLE.tblDist
  ├─ تیم عملیاتی: Driver / Distributer / RealDistributer / Assistants
  ├─ خودرو: GNR.tblTruck
  ├─ فروش‌های تخصیص‌یافته: SLE.tblSaleHdr.DistRef
  ├─ خروج‌های انبار: inv.tblExit.DistRef
  ├─ رخداد وضعیت: SLE.tblDistLog
  └─ تاریخچه تخصیص فروش: tblSaleDistHist / tblSaleDistHistFull
```

`tblDist` تعداد ۲۶٬۰۸۶ توزیع از `۱۴۰۳/۰۱/۱۴` تا `۱۴۰۵/۰۵/۳۱` دارد. UUID
همه ردیف‌ها پر و یکتا است. شماره توزیع با ترکیب زیر یکتاست:

```text
(AccYear, DCRef, DistNo)
```

تمام ردیف‌ها Truck، Driver، Distributer و RealDistributer دارند و هیچ ارجاع
یتیم به خودرو یا Personnel پیدا نشد.

## ماشین حالت توزیع

Master وضعیت در `GNR.tblLookup(CodeType=44)` هشت مقدار دارد:

| کد | عنوان | ردیف جاری |
|---:|---|---:|
| ۰ | ابطال شده | ۲٬۵۸۴ |
| ۱ | صادر نشده | ۱ |
| ۲ | خروجی انبار | ۵۱ |
| ۳ | ارسال شده | ۴۷ |
| ۴ | توزیع شده | ۱۲ |
| ۵ | ارسال شده به تبلت | ۹ |
| ۶ | برگشتی | ۰ |
| ۷ | خاتمه یافته | ۲۳٬۳۸۲ |

مسیر غالب مشاهده‌شده در ۱۹۲٬۵۷۳ رخداد `tblDistLog`:

```text
ایجاد → 1 صادر نشده → 2 خروجی انبار → 3 ارسال شده
      → 4 توزیع شده → 7 خاتمه یافته
```

مسیرهای برگشتی نیز واقعی‌اند: `3→2` تعداد ۲۴٬۹۸۹ رخداد، `2→1` تعداد ۹٬۵۴۶
و `5→3` تعداد ۳۷۱ رخداد دارد. بنابراین Status فقط یک مقدار نمایشی نیست؛ مقصد
باید Event History و Guard انتقال را حفظ کند.

Log تعداد ۲۶٬۰۹۲ شناسه توزیع را پوشش می‌دهد؛ ۵۱ رخداد متعلق به شش توزیع قدیمی
است که Header فعلی آن‌ها دیگر وجود ندارد. این‌ها باید Legacy Tombstone تلقی
شوند، نه اینکه از تاریخچه حذف شوند.

## وضعیت‌های جاری و سه ماه عملیاتی

۲۴٬۲۲۳ توزیع `SendDate` و ۲۳٬۴۵۶ توزیع `ReturnDate` دارند. تمام ۲۳٬۳۸۲
توزیع خاتمه‌یافته هر دو تاریخ را دارند. ۶۲ توزیع ابطال‌شده نیز ReturnDate
دارند؛ پس Cancel لزوماً به معنی «هیچ اجرای قبلی» نیست.

در پنجره تجاری `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱`:

- ۳٬۳۷۹ توزیع؛
- ۲٬۹۳۷ خاتمه‌یافته و ۳۲۲ ابطال‌شده؛
- ۵۲ Driver، ۵۲ Distributer و ۵۲ RealDistributer؛
- فقط یک TruckRef؛
- چهار کد مسیر Legacy.

## تیم و خودرو

`SLE.tblDistTeam` فقط ۲۰ Template جاری دارد: ۲۰ Driver و ۲۰ Distributer متمایز
اما تنها یک Truck. `GNR.tblTruck` نیز فقط یک ردیف فعال دارد و تمام ۲۶٬۰۸۶
توزیع به همان ردیف وصل‌اند. بنابراین خودرو در داده فعلی یک Master تک‌عضوی
است و ظرفیت واقعی ناوگان را نمی‌توان از تعداد Truckها استنباط کرد.

هفت مقدار `DistPath` در Headerها استفاده شده و `GNR.tblDistPath` خالی است؛ اما
بررسی عمیق‌تر Schema، SQL و IL نشان داد این ستون FK به `tblDistPath.ID` نیست.
در تنظیمات فعلی `DistPathingType=0` و `DistLimitType=0`، فرم عدد آزاد می‌گیرد؛
حتی در حالت Lookup نیز `DistPathTreeNo` را ذخیره می‌کند، نه ID مستر. بنابراین
۲۶٬۰۸۶ ردیف «Orphan» نیستند. این اعداد باید به‌عنوان
`distribution_path_code` معتبر ولی بدون عنوان حفظ شوند و تا دستیابی به Crosswalk
معتبر، Zone/Area/Route حدسی نگیرند. جزئیات در
`DISTRIBUTION_PATH_RUNTIME_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

ستون‌های `TourId` و `TourNo` در تمام Headerهای `tblDist` صفرند. اتصال NGT از
این دو ستون ساخته نمی‌شود.

## تخصیص Sale به Distribution

در وضعیت جاری:

- ۲۴۸٬۵۵۴ Sale به ۲۳٬۵۰۲ توزیع وصل‌اند؛
- میانگین ۱۰٫۵۸ Sale و حداکثر ۷۵ Sale در هر توزیع؛
- ۱۸٬۴۲۵ توزیع چند Sale دارند؛
- هیچ DistRef یتیم نیست؛
- ۲۴۷٬۰۸۳ Sale به توزیع خاتمه‌یافته وصل‌اند؛
- هیچ Sale جاری به توزیع ابطال‌شده وصل نیست.

`SLE.tblSaleDistHist` تعداد ۲۶۶٬۵۴۵ ردیف برای ۲۵۰٬۳۶۱ Sale دارد و ۱۵٬۱۷۸
Sale بیش از یک تخصیص تاریخی دارند. آخرین History برای تمام ۲۴۸٬۵۵۴ Sale دارای
DistRef با اشاره جاری دقیقاً منطبق است. برای ۱٬۸۰۷ Sale، History حفظ شده ولی
اشاره جاری `SaleHdr.DistRef` پاک شده است. بنابراین پاک‌شدن تخصیص یک رویداد
دامنه است و History نباید Cascade Delete شود.

`tblSaleDistHistFull` تعداد ۹۵۳٬۹۷۸ Event/Snapshot یکتا برای ۲۵۶٬۲۵۴ Sale
دارد؛ ۲۵۵٬۶۷۹ Sale چند Event دارند. با وجود نام ستون، `PreviousId` در همه
۹۵۳٬۹۷۸ ردیف Null است. ترتیب باید از زمان/ID و قرارداد Procedure ساخته شود،
نه از `PreviousId`.

## اتصال خروج انبار

۳۳٬۹۴۵ خروج برای ۲۵٬۲۱۴ توزیع وجود دارد: ۲۴٬۰۳۵ فعال و ۹٬۹۱۰ لغوشده.
۲۳٬۵۰۱ توزیع خروج فعال دارند و ۵۳۴ توزیع دقیقاً دو خروج فعال دارند؛ حداکثر
خروج فعال در یک توزیع دو است. این Multiplicity باید در مقصد حفظ شود.

- ۸۷۲ توزیع هیچ خروجی ندارند؛
- ۲٬۵۸۵ توزیع خروج فعال ندارند؛ این مجموعه با ۲٬۵۸۴ توزیع ابطال‌شده و یک
  توزیع «صادر نشده» هم‌راستاست؛
- هیچ Exit با DistRef یتیم وجود ندارد؛
- DistRef فروش و DistRef خروج در تمام ۲۴۸٬۵۵۳ Sale دارای Exit با هم منطبق‌اند؛
- فقط یک Sale جاری DistRef دارد ولی ExitRef ندارد؛ توزیع آن در وضعیت «صادر
  نشده» است.

رابطه مقصد:

```text
Distribution 1 ─── n WarehouseExit 1 ─── n Sale
```

رابطه مستقیم `Distribution 1 ─ n Sale` نیز برای Assignment و History لازم
است؛ نمی‌توان یکی را از دیگری حذف کرد.

## عدم تحویل و برگشت توزیع

Master عدم تحویل سه دلیل معتبر دارد: «بسته بودن مغازه»، «عدم پرداخت وجه» و
«عدم حضور تحویل‌گیرنده». بااین‌حال `UndeliveredReasonRef` در هر دو جدول
تاریخچه فعلی صفر بار استفاده شده است.

همچنین `inv.tblRetDistHdr` و `inv.tblRetDistItm` خالی‌اند و Status کد ۶
«برگشتی» نه در Header جاری و نه در Transitionهای ثبت‌شده مصرف ندارد. این
اجزا Schema معتبر ولی Workflow غیرفعال/جایگزین‌شده‌اند؛ UI مقصد نباید پیش از
کشف مسیر واقعی، فرم برگشت توزیع را عملیاتی اعلام کند.

## پل NGT و شاهد تحویل

از ۲٬۴۷۱٬۲۵۰ `NGT.CustomerCalls` فقط ۷٬۴۰۵ Call به ۵۲۱ توزیع وصل‌اند. برای
همه این ۷٬۴۰۵ ردیف:

- `DistributionUniqueId` به `tblDist.UniqueId` وصل است؛
- `DistributionRef` عددی به `tblDist.ID` وصل است؛
- ID و UUID دقیقاً به یک Header اشاره می‌کنند؛
- شماره و تاریخ توزیع پر است.

اما در همین ۷٬۴۰۵ Call، `DeliveryDate` و `SaleDate` هر دو صفر بار پر شده‌اند؛
فقط ۳٬۱۴۳ Call `SendDate` دارند. بنابراین Status «توزیع شده» یا «خاتمه یافته»
شاهد عملیاتی پایان کار است، نه اثبات مستقل دریافت مشتری.

از ۶۴٬۵۶۱ Tour، تعداد ۵۶۶ Tour بین ۲۰۲۶-۰۶-۰۲ و ۲۰۲۶-۰۸-۲۲
`HasDistribution=1` دارند. این Tourها ۲۹ Agent، ۲۹ Driver، یک Vehicle و پنج
Status را پوشش می‌دهند؛ Vehicle هر ۵۶۶ مورد با همان Truck یکتای GNR تطبیق
دارد. وضعیت‌ها: ۲۸۲ «انصراف داده»، ۲۷۲ «خاتمه یافته»، ۵ «غیرفعال»، ۵ «ارسال
شده» و ۲ «دریافت شده».

`DistributionNoCollection` در همه Tourها خالی است. Crosswalk فعال NGT باید از
CustomerCallهای توزیع‌شده ساخته شود، نه از Collection متنی Tour.

## Delivery Window تنظیمی

`SLE.tblOrderDeliveryTime` فقط یک ردیف فعال `08:00..23:00` دارد. این یک
پنجره تنظیمی است و هیچ ارتباطی با Timestamp تحویل واقعی هر Sale/Customer
اثبات نمی‌کند.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها:

- `Distribution` با شماره مرکب و UUID منبع؛
- `DistributionStatusEvent` با old/new/status/time/operation؛
- `DistributionTeamSnapshot` برای نقش‌های Driver/Distributer/Assistant؛
- `VehicleAssignment` مستقل از Vehicle Master؛
- `SaleDistributionAssignmentEvent` با قابلیت Unassign؛
- `WarehouseExit` و پل `WarehouseExitSale`؛
- `UndeliveredOutcome` با Reason Master؛
- `NgtDistributionCallCrosswalk` با ID و UUID مستقل؛
- `DeliveryEvidence` که منبع، زمان و سطح اطمینان را صریح نگه دارد؛
- `LegacyDistributionPathCrosswalk` با وضعیت unresolved.

Status جاری باید Projection آخرین Event باشد. هیچ API نباید مستقیماً عدد
Status را بدون اعتبارسنجی Transition و ثبت Audit تغییر دهد.

## ابهام‌های باز

1. عنوان انسانی هفت `DistPath` و این‌که در کسب‌وکار «شماره مسیر»، «نوبت حرکت»
   یا طبقه‌بندی دیگری هستند؛ دادهٔ فعلی فقط کد عددی mode-dependent را اثبات می‌کند.
2. دلیل وجود شش Distribution Tombstone در Log و نبود Header جاری.
3. مسیر واقعی ثبت عدم تحویل، چون Master موجود ولی مصرف فعلی صفر است.
4. مسیر عملیاتی برگشت توزیع، چون جدول‌ها و Status مربوطه خالی‌اند.
5. شاهد نهایی دریافت مشتری؛ فیلد `DeliveryDate` در Crosswalkهای NGT فعلی خالی است.
6. معنای عملیاتی یک Truck مشترک برای تمام توزیع‌ها و محل ثبت ناوگان واقعی.

## Golden Caseهای لازم

1. ساخت Distribution با چند Sale؛
2. Assign/Unassign و Event history؛
3. خروج انبار و ارسال؛
4. خاتمه با شاهد مستقل تحویل و بدون آن؛
5. Cancel پس از اجرای جزئی؛
6. عدم تحویل با Reason؛
7. Legacy path بدون Master؛
8. NGT call با ID/UUID هم‌جهت؛
9. Return-distribution capability بدون نمونه فعلی.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_distribution_delivery_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\distribution_delivery_20260826.json
```
