# دانش‌نامهٔ ورانگر برای NeginAI

تاریخ بررسی اولیه: ۲۰ مرداد ۱۴۰۵ / ۱۱ اوت ۲۰۲۶

وضعیت: سند زنده؛ فاز نخستِ شناخت سامانه تکمیل شده است و با آزمون سؤال‌های واقعی تکمیل می‌شود.

دفتر دامنه‌به‌دامنه بازسازی ERP و شواهد جدید در
[`docs/varanegar_reconstruction/README_FA.md`](varanegar_reconstruction/README_FA.md)
نگهداری می‌شود. این دانش‌نامه مرجع معنایی عملیات است و دفتر بازسازی، قرارداد
جداول، مهاجرت و ابهام‌های هر دامنه را ثبت می‌کند.

## هدف

هدف این سند، تبدیل شناخت پراکندهٔ جدول‌ها به یک مدل معنایی قابل اتکا از شرکت پخش مویرگی چندشعبه‌ای است؛ یعنی دستیار بداند هر سند چیست، در کدام فرایند ساخته می‌شود، به چه سندهایی وصل است و برای هر سؤال باید از کدام گزارش یا View استفاده کند.

تمام بررسی‌های SQL با اتصال فقط‌خواندنی انجام شده‌اند. هیچ داده‌ای در ورانگر تغییر نکرده است.

## منابع شناخت

این نقشه از چهار منبع مستقل ساخته شده است:

1. متادیتای زندهٔ دیتابیس `NeginPakhsh`: جدول‌ها، Viewها، ستون‌ها، PK/FK و وابستگی Viewها.
2. متادیتای خود نرم‌افزار: ۴۳۳ فرم و ۸۳۶ آیتم منو.
3. فایل‌های مدل گزارش ورانگر در `Review.Win/ReviewTabModelFiles`: ۲۱۶ قرارداد گزارش فعال و نام رسمی فیلدهای فارسی.
4. منابع عمومی رسمی ورانگر: [راهکار پخش مویرگی چندشعبه](https://www.varanegar.com/%D9%86%D8%B1%D9%85-%D8%A7%D9%81%D8%B2%D8%A7%D8%B1-%D9%BE%D8%AE%D8%B4-%D9%85%D9%88%DB%8C%D8%B1%DA%AF%DB%8C-%DA%86%D9%86%D8%AF-%D8%B4%D8%B9%D8%A8%D9%87/) و [راهکارهای همراه پخش](https://www.varanegar.com/%D8%B1%D8%A7%D9%87%DA%A9%D8%A7%D8%B1%D9%87%D8%A7%DB%8C-%D9%87%D9%85%D8%B1%D8%A7%D9%87-%D9%BE%D8%AE%D8%B4-%D9%85%D9%88%D8%A8%D8%A7%DB%8C%D9%84-%D9%88-%D8%AA%D8%A8%D9%84%D8%AA-%DA%A9%D9%84%D8%A7%D9%86/).

منبع رسمی، معماری سطح‌بالای ورانگر را سه بخش «فروش و پخش»، «انبارداری» و «خزانه‌داری» معرفی می‌کند. در شرکت چندشعبه‌ای، داده‌ها متمرکزند و ستاد، مراکز توزیع و شعب از همان سامانهٔ مرکزی استفاده می‌کنند.

## نقشهٔ کل سامانه

شاخه‌های اصلی منو و تعداد آیتم‌های هر شاخه نشان می‌دهد ورانگر فقط یک سیستم فروش نیست:

| حوزه | تعداد آیتم در شاخه | نقش اصلی |
|---|---:|---|
| فروش | ۱۷۸ | درخواست، حواله، فاکتور، برگشت، توزیع و گزارش فروش |
| خزانه‌داری | ۱۴۳ | دریافت/پرداخت، تسویه، چک، بانک، تنخواه و وصول |
| اطلاعات پایه ۱ و ۲ | ۷۹ | کالا، مشتری، اشخاص، مسیرها، انواع سند و قواعد |
| انبار | ۵۵ | اسناد انبار، خروج فروش، برگشت توزیع و انبارگردانی |
| تنظیمات سیستم | ۵۰ | شعب، دسترسی، تاریخ قطعی، سال مالی و تنظیمات عملیاتی |
| کنسول تبلت | ۴۳ | پیش‌فروش، فروش گرم، توزیع و عملیات میدانی |
| کنسول مدیریت فروش | ۴۰ | تور، ابزار فروشنده، ترخیص و پیگیری عملیات |
| حسابداری انبار و خرید | ۴۳ | قیمت‌گذاری، اسناد خرید و انتقال به حسابداری |
| حسابداری مالی و صدور سند | ۲۹ | حساب‌ها، اسناد و اتصال زیرسیستم‌ها به مالی |
| سایر | ۱۷۶ | داشبورد، فروشگاه، B2B، کنترل‌ها، ردیابی و سامانه‌های مکمل |

## ساختار چندشعبه‌ای

در دیتابیس، «شعبه» یک ستون ساده نیست و باید ابعاد زیر از هم جدا بمانند:

- `GNR.tblDC`: مرکز توزیع یا حوزه.
- `GNR.tblSaleOffice`: دفتر فروش.
- `GNR.tblStockDC`: انبار وابسته به مرکز.
- `GNR.tblDCSaleOffice`: پل مرکز توزیع، دفتر فروش و انبار.
- مسیرهای فروش، ویزیت، توزیع و وصول ابعاد جداگانه‌اند و نباید به‌جای یکدیگر استفاده شوند.

در گزارش‌ها باید مشخص باشد سؤال دربارهٔ «مرکز توزیع»، «دفتر فروش»، «انبار» یا «مسیر» است. جمع‌زدن دادهٔ چند شعبه بدون تعیین این سطح می‌تواند پاسخ ظاهراً درست ولی مدیریتیِ غلط تولید کند.

## زنجیرهٔ اصلی فروش تا وصول

```text
مشتری و مسیر
    ↓
درخواست مشتری / سفارش
SLE.tblOrderHdr + SLE.tblOrderItm
    ↓
تبدیل درخواست به حواله و/یا فاکتور
    ├─ حواله فروش: SLE.tblSaleVocherHdr
    └─ فاکتور فروش: SLE.tblSaleHdr + SLE.tblSaleItm
                         ↓
تخصیص به توزیع: SLE.tblDist
                         ↓
خروج و سند انبار: inv.tblExit / inv.tblVocherHdr
                         ↓
دریافت وجه یا اسناد: dbo.Receipt و اجزای نقد/چک/حواله بانکی
                         ↓
اقلام بستانکار/بدهکار مشتری: Acc.tblPayments
                         ↓
تسویه و تخصیص مبلغ به فاکتور: dbo.Settlement
                         ↓
مانده فاکتور، وضعیت تسویه و کاردکس مشتری
```

این زنجیره یک مسیر اجباری و خطی برای همهٔ رکوردها نیست. فروش گرم، فروش حضوری، فاکتور آزاد، فروشگاه، پیش‌دریافت، برگشت فروش، اعلامیه، تخفیف وصول و تعدیلات می‌توانند از شاخه‌های متفاوت وارد چرخه شوند.

## واژه‌نامهٔ عملیاتی دقیق

### درخواست مشتری

درخواست یا سفارش اولیهٔ مشتری است. هدر در `SLE.tblOrderHdr` و اقلام در `SLE.tblOrderItm` قرار دارند. سفارش به مشتری، فروشنده، مرکز توزیع، دفتر فروش، انبار، نوع سفارش و مهلت پرداخت متصل است. یک درخواست می‌تواند بعداً به حواله یا فاکتور تبدیل شود؛ بنابراین «درخواست» برابر «فروش قطعی» نیست.

### حواله فروش

سند عملیاتی فروش برای آماده‌سازی/تحویل کالا است و در `SLE.tblSaleVocherHdr` به درخواست و در صورت صدور فاکتور به `SLE.tblSaleHdr` متصل می‌شود. شمارهٔ آن در گزارش‌ها `SaleVoucherNo` یا با املای قدیمی `SellVocherNo` است.

«حواله فروش» نباید با دو مفهوم دیگر اشتباه شود:

- حواله بانکی (`BankOrder` یا `BankTransfer`) که ابزار دریافت وجه است.
- حواله/سند انبار (`inv.tblVocherHdr`) که گردش موجودی را ثبت می‌کند.

### فاکتور فروش

سند مالی فروش است. هدر در `SLE.tblSaleHdr` و ردیف کالا در `SLE.tblSaleItm` قرار دارد. فاکتور به درخواست، مشتری، فروشنده، مرکز/دفتر فروش، مهلت پرداخت، توزیع و در صورت وجود خروج انبار متصل است.

### دریافت

دریافت (`dbo.Receipt`) سرآیند ورود وجه یا اسناد به خزانه است. اجزای آن می‌توانند نقد، چک، حواله بانکی و سایر ابزارها باشند. یک دریافت می‌تواند هنوز مصرف‌نشده باشد؛ بنابراین «ثبت دریافت» لزوماً به معنی «تسویهٔ فاکتور» نیست.

در دادهٔ واقعی:

```text
ReceiptAmount = RCashAmount + RChequeAmount + RCashDraftAmount
ReceiptRemainAmount = ReceiptAmount - ReceiptExpendedAmount
```

هر دو رابطه روی نمونه‌های خوانده‌شده از `dbo.Receipt2` بدون اختلاف تأیید شدند.

### قلم دریافت/پرداخت مشتری

`Acc.tblPayments` لایهٔ اقلام بدهکار/بستانکار حساب مشتری است. هر قلم می‌تواند به فاکتور، مشتری، نوع پرداخت، چک، حواله بانکی، دریافت، برگشت فروش، اعلامیه یا تعدیل متصل شود. این لایه برای گزارش «اقلام بدهکار و بستانکار» و تحلیل منشأ تسویه مهم‌تر از خود Receipt است.

### تسویه

تسویه یعنی مصرف یا تخصیص یک دریافت، ابزار پرداخت، برگشت، تخفیف یا تعدیل در برابر فاکتور/بدهی. `dbo.Settlement` و نماهای آن این ارتباط را نگه می‌دارند. پس:

```text
دریافت = ورود وجه یا سند به خزانه
تسویه = تخصیص آن وجه/سند/تعدیل به بدهی یا فاکتور
```

انواع تسویه فقط نقد و چک نیستند؛ دادهٔ واقعی شامل واریز، چک، نقد، تخفیف توزیع، تخفیف وصول، تخفیف، گرد کردن، برگشت فروش، بستانکاری و اعلامیه‌های بدهکار/بستانکار است. بعضی انواع اثر مثبت و بعضی اثر منفی دارند؛ علامت باید از `PayTypePlusMinus` یا منطق تأییدشدهٔ View گرفته شود.

### مانده فاکتور

منبع مرجع عملیاتی فعلی `Acc.vwRcvSaleReview` است. رابطهٔ مشاهده‌شده روی ۲۰۰۰ ردیف نمونه:

```text
RemainingAmount = SalesNetAmount - SettlementAmount
```

این رابطه در همهٔ نمونه‌ها برقرار بود. محاسبهٔ مانده با جمع سادهٔ نقد + چک + حواله بانکی معتبر نیست، چون تسویه می‌تواند شامل برگشت، تخفیف، اعلامیه و تعدیلات دیگر باشد.

تعبیر وضعیت‌ها در دادهٔ واقعی:

- «تسویه نشده کامل» و «تسویه شده قسمتی» ماندهٔ مثبت دارند.
- «تسویه شده کامل» معمولاً ماندهٔ صفر دارد، ولی ماندهٔ منفی نیز دیده می‌شود؛ بنابراین شرط صحیح برای تسویهٔ کامل لزوماً `RemainingAmount = 0` نیست.

### کاردکس مشتری

کاردکس، توالی بدهکار/بستانکار اسناد مشتری و ماندهٔ تجمعی را نمایش می‌دهد. گزارش رسمی `dbo.vwReview_RcvAccountCardex2` ستون‌های نوع سند، شماره سند، تاریخ، شماره دریافت، شماره فاکتور، شماره حواله فروش، بدهکار، بستانکار و مانده را دارد. کاردکس با «فهرست فاکتورهای باز» یکی نیست.

### برگشت فروش

برگشت فروش هم بر فروش خالص و هم بر تسویه اثر می‌گذارد. بسته به سؤال، باید بین مقدار/مبلغ کالای برگشتی، سند برگشت و «تسویه از محل برگشت فروش» تفاوت گذاشت.

## نقش‌ها و ابعاد سازمانی

برای پاسخ درست، این نقش‌ها نباید با هم ادغام شوند:

- مشتری (`Cust`)
- فروشنده یا ویزیتور (`Dealer`)
- سرپرست (`Supervisor`)
- مأمور توزیع (`Distributer` و `RealDistributer`)
- راننده (`Driver`)
- کمک‌توزیع‌کننده‌ها (`DistAssistant1/2`)
- مأمور وصول (`ReceiptAgent`)

همچنین «برند»، «تولیدکننده»، «گروه کالا» و «خود کالا» چهار بُعد متفاوت‌اند.

## اکشن‌ها و مجوزهای عملیاتی

علاوه بر منو و فرم، لایهٔ جدیدتر NGT دارای ۳ ماژول، ۷۸ Resource، تعداد ۵۹ نوع Action و ۳۶۹ Permission است. Actionها فقط CRUD عمومی نیستند و بخشی از چرخهٔ واقعی عملیات را نشان می‌دهند:

- عمومی: `View`، `List`، `Add`، `Edit`، `Delete`، `Confirm`، `Print`، `ExportToExcel` و `ImportFromExcel`.
- سفارش و تماس مشتری: تأیید/لغو قلم درخواست، تکثیر قلم، پیش‌نمایش سفارش و لغو تماس.
- تورهای عملیاتی: ایجاد نسخه، فعال‌سازی و تأیید دریافت تور برای پیش‌فروش، فروش گرم، VanSale، توزیع، وصول و MedRep.
- کنترل موجودی و پرداخت: تأیید موجودی توزیع/فروش گرم/VanSale/MedRep و تأیید پرداخت پیش‌فروش، فروش گرم، VanSale، توزیع و وصول.
- اصلاحات حساس: ویرایش مبلغ نقد، مبلغ/اطلاعات چک، مبلغ POS و تخفیف، حذف نقد و حذف موقعیت جغرافیایی.
- همگام‌سازی: دریافت از BackOffice یا سرور Replication.

Resource محوری `Tours` به‌تنهایی ۱۰۸ Permission دارد و پس از آن `RequestItems` و `ProductTemplates` قرار می‌گیرند. این نشان می‌دهد «تور» هستهٔ اتصال عملیات میدانی فروش، توزیع و وصول در نسل جدید ورانگر است و در مدل دانشی نباید فقط به‌عنوان یک جدول جانبی دیده شود.

### معنی مؤثر Grant در Guard وب NGT

تحلیل Static هشت اسمبلی مستقر سرور نشان داد Guard اصلی وب، Direct و Group را
جدا می‌خواند و Union می‌کند، اما هر دو مسیر سه‌پارامتری پیش از ورود به نتیجه
`Grant == 1` را اعمال می‌کنند. مسیر Group برای هر گروه به همان Query مستقیم
سه‌پارامتری Delegate می‌کند. اگر نتیجه خالی باشد دسترسی رد می‌شود؛ سپس Predicate
دفاعی `Grant == -1` نیز وجود دارد، ولی Snapshot فعلی هیچ مقدار `-1` ندارد.

پس ۲٬۰۹۳ مقدار صفر موجود را نباید بدون شاهد «Deny صریح» نامید؛ در Guard مشاهده‌شده
آن‌ها Rowهای حذف‌شده از مجموعه مجازند. Catalog نیز هنگام Guard خوانده نمی‌شود:
مسیر Save انتخاب Catalog را به Permissionهای Atomic هم‌جهت Materialize می‌کند و
هر ۲٬۴۱۵ لینک مستقیم فعلی Atomic متناظر دارد. این نتیجه فقط Guard اصلی و لینک
مستقیم Catalog را ثابت می‌کند؛ پوشش تمام Endpointها، Crosswalk مجوز Legacy و
Recursive catalog hierarchy همچنان باز است. جزئیات بازتولیدپذیر در
`varanegar_reconstruction/domains/16_AUTHORIZATION_LEGACY_AND_NGT_FA.md` ثبت شده است.

پوشش Attribute نیز شمارش شد: از ۷۸۴ Action دارای HTTP/Route attribute، تعداد
۵۹۵ مورد صفت NGT دارند؛ ۲۵۰ مورد Resource+Action و ۳۴۵ مورد Role-only/empty.
پس از احتساب Standard/Claims/Anonymous و base مشترک، ۶۰ Action بدون اعلان صریح
می‌ماند که ۳۸ مورد فعل تغییردهنده دارند. Startup فیلتر Global نام‌دار مجوز
نمی‌سازد. Body مستقیم هر ۶۰ مورد و `MoveNext` هر ۴۳ مورد Async نیز صفر فراخوانی
نام‌دار تصمیم مجوز دارد؛ شش Permission-data call و سه CurrentUser call کنترل
دسترسی تلقی نشدند. Guard مبهم/واگذارشده یا Host policy هنوز رد نشده و رخداد
دسترسی ناشناس ادعا نمی‌شود. برای ERP مقصد، Route manifest و Policy باید
Build-time اجباری و fail-closed باشند.

Role `admin` در Attribute مستقر یک Superuser واقعی است: Predicate دقیق
case-insensitive قبل از Base authorization true برمی‌گرداند، بنابراین
Resource/Action و Authorize استاندارد را دور می‌زند. Snapshot فقط‌خواندنی و بدون
هویت یک Role، سه Assignment و سه Subject فعلی نشان می‌دهد. این شاهد Incident
نیست، اما مدل مقصد باید آن را به Break-glass/JIT با MFA، تأیید دوم، انقضا، Reason،
Audit و SoD تبدیل کند، نه Role دائمیِ عبور از همه Policyها.

## موجودی گزارش‌ها

فایل‌های رسمی Review ورانگر ۲۱۶ تب گزارش فعال دارند:

| گروه گزارش | تعداد تب |
|---|---:|
| فروش (`Sell`) | ۵۷ |
| خزانه‌داری (`Treasury`) | ۳۳ |
| حساب مشتری (`RcvAccount`) | ۲۵ |
| حسابداری انبار (`StockAcc`) | ۱۵ |
| حسابداری خرید/انبار (`WhAccount`) | ۱۵ |
| فروش فروشگاهی (`StoreSales`) | ۱۴ |
| انبار (`Stock`) | ۱۳ |
| اقساط/وام (`Loan`) | ۱۲ |
| حسابداری مالی (`GeneralLedger`) | ۱۰ |
| خرید (`Buy`) | ۸ |
| فاکتور آزاد (`FreeInvoice`) | ۸ |
| اطلاعات پایه (`BaseInformation`) | ۳ |
| تنخواه (`TreasuryFund`) | ۳ |

هر قرارداد نام تب، Entity داده، Stored Procedure و فهرست ستون‌های قابل نمایش را مشخص می‌کند. این قراردادها باید به‌عنوان «زبان رسمی گزارش‌های ورانگر» در بازیابی دانش وزن بالایی داشته باشند.

## منابع مرجع پیشنهادی برای سؤال‌های کلیدی

| نیت سؤال | منبع پیشنهادی | دلیل |
|---|---|---|
| فروش تحلیلی کالا/مشتری/فروشنده | `dbo.SalesReviewFast` | پوشش سریع ردیف کالا، فروش و برگشت |
| مانده و وضعیت فاکتور مشتری | `Acc.vwRcvSaleReview` | دارای مبلغ خالص، مبلغ تسویه، مانده و وضعیت پرداخت |
| تب رسمی فاکتورهای حساب مشتری | `dbo.vwReview_RcvAccountSale2` | انطباق کامل با قرارداد گزارش رسمی؛ کندتر از View عملیاتی |
| اقلام بدهکار/بستانکار مشتری | `Acc.vwRcvPaymentsReview` | اتصال پرداخت، فاکتور، چک، دریافت، برگشت و شعبه |
| گزارش رسمی اقلام حساب مشتری | `dbo.vwReview_RcvAccountPayment2` | انطباق کامل با تب رسمی Payments |
| جزئیات تخصیص تسویه به فاکتور | `dbo.vwReview_RcvAccountSettlement2` | انطباق کامل با تب رسمی Settlements |
| کاردکس مشتری | `dbo.vwReview_RcvAccountCardex2` | بدهکار/بستانکار و ماندهٔ تجمعی |
| دریافت‌های خزانه | `dbo.Receipt2` یا `dbo.vwReview_TreasuryReceipt2` | مبلغ، اجزا، مانده، وضعیت و مأمور وصول |
| اتصال دریافت به فاکتور | `dbo.InvoiceReceipt` | پل `InvoiceId` و `ReceiptId` |
| جزئیات انواع تسویه | `dbo.SettlementFast` | نوع، علامت اثر، سند و فاکتور مرتبط |
| مانده کلی مشتری | `Acc.vwCustomerBalance` | بدهکار، بستانکار و Balance تا تاریخ |
| سفارش‌ها | `SLE.OrdersReview` | سفارش، مشتری، کالا، فروشنده و وضعیت تبدیل |

نکته: `Acc.vwRcvSaleReviewFast` برای فروش سریع مفید است، اما ستون‌های `RemainingAmount`، `PaymentStatus` و `SettlementAmount` را ندارد و برای سؤال مانده/تسویه منبع کافی نیست.

## تاریخ عملیات و تاریخ قطعی؛ قرارداد تشخیص رخداد

`GNR.tblOprDate` تنظیم ساده نیست و چهار حالت مستقل دارد: `OprDate` تاریخ جاری
عملیات، `LastDate` مرز قطعی، `LicenseDate` مجوز ستاد و `IsClosed` بسته‌بودن
سال/زیرسیستم. کلید معنایی آن `DCRef + AccYear + SysRef` است؛ `SysRef`های ۱، ۲،
۳، ۵ و ۷ به‌ترتیب فروش، مالی/خزانه، هزینه شعب، خرید و تنخواه‌اند. ۲۵۶ ماژول
SQL متن‌محور به این جدول اشاره دارند، پس خطای آن می‌تواند در فروش، انبار، خرید،
خزانه، حسابداری، توزیع، POS و NGT ظاهر شود.

قرارداد تشخیصی ۲۰۲۶-۰۸-۲۷ یازده ریسک ثبت کرد: سه بحرانی، هفت بالا و یک متوسط.
مهم‌ترین آن‌ها عبارت‌اند از:

- شش مسیر First-create ستون اجباری `UserRef` را در Insert نمی‌فرستند؛ در نتیجه
  «ویرایش موفق ولی ثبت اول ناموفق» یک امضای تشخیصی معتبر است.
- ساخت ردیف تنخواه در SP تجمیعی اشتباهاً با فیلدهای فروش Guard می‌شود.
- Validation خرید و مالی شرط‌های غیرقابل‌وقوع دارد؛ موفقیت Validation اثبات
  اجرای همهٔ قواعد نیست.
- چهار SP اصلی Update تراکنش صریح ندارند و فرم/Adapter نیز Transaction ownership
  قابل‌مشاهده‌ای نشان نمی‌دهد؛ پس تغییر جزئی چند SysRef ممکن است.
- بازکردن مالی می‌تواند Statement نوع ۱۰۰۵ را بدون Scope سال مالی حذف کند.
- بازکردن فروش می‌تواند وضعیت ۴/۷ توزیع را برای همهٔ سال‌های یک DC جابه‌جا کند،
  Backup سراسری را پاک کند و پیام خطای پیش‌شرط را نادیده بگیرد.
- Adapter هر هشت مسیر Validation/Update را با `System.String.Format` به SQL Text
  تبدیل می‌کند و پارامتر Database واقعی ندارد.

در سه ماه اخیر ۱۶۰ رویداد Log مرتبط ثبت شده که همگی Update بوده‌اند. Artifact
هیچ تاریخ کسب‌وکار، هویت، مقدار تنظیم یا Script خامی نگه نمی‌دارد. Runbook کامل
و Blast radius فعلی در
`FINAL_DATE_INCIDENT_DIAGNOSTIC_PLAYBOOK_20260827_FA.md` ثبت شده است.

صدور سند خارجی این مرز را نیز مصرف می‌کند، اما خرید را از مسیر جداگانهٔ
`ICA.tblICAOprDate.DefeniteDate` می‌سنجد. SQL فعلی `MIN` را فقط روی ردیف‌های
موجود StockDC می‌گیرد و completeness همهٔ انبارها را کنترل نمی‌کند: در Scope
فعال ۱۴۰۵ ده StockDC و هشت ردیف ICA وجود دارد. نبود دو ردیف می‌تواند در صورت
عبور تاریخ هشت ردیف دیگر دیده نشود. `OperationId=5` نیز صریحاً مستثناست؛ دو نوع
حقوق تنظیم شده ولی نمونهٔ تاریخی ندارند. رد Finality پیش از اولین Write است و
Mutation جزئی ندارد. جزئیات و `R-050` در
`domains/21_ACCOUNTING_ISSUANCE_FINALITY_BOUNDARY_FA.md` ثبت شده است.

## صدور سند؛ Snapshot منبع و Rule قابل‌اجرا

در مسیر فعال صدور، `dbo.usp_DoPreVoucher` View هر سازنده را با
`AS vw WITH(NOLOCK)` می‌خواند و نتیجه را در `PreVoucher` ماندگار می‌کند. Transaction
بیرونی Desktop اتمیک‌بودن writeهای صدور را پشتیبانی می‌کند، اما committed و
یکپارچه‌بودن snapshot منبع را تضمین نمی‌کند. رخداد dirty-read تاریخی مشاهده یا
بازسازی نشد؛ این نتیجه از مسیر قطعی کد است.

همین Procedure نام View، Fieldهای تاریخ/مبلغ/ابعاد، Predicateها و recipe شرح را
در یک batch SQL الحاق و اجرا می‌کند. Validator نوع سند نیز یک محل اجرای پویا دارد.
اسکن فقط‌خواندنی ۱۱ دستهٔ fragment، ۷۱ Predicate متمایز و صفر token مشکوک واضح
در snapshot فعلی نشان داد؛ هیچ مقدار خام ذخیره نشد. پاکی فعلی به معنی امن‌بودن
executable configuration نیست. مقصد باید snapshot committed/versioned و Rule DSL
تایپ‌شده و immutable داشته باشد. `R-052` و `R-053` و جزئیات در
`domains/23_DYNAMIC_RULE_SQL_AND_SOURCE_SNAPSHOT_FA.md` ثبت شده‌اند.

Provider مستقر `BeginTransaction()` را بدون Isolation argument اجرا می‌کند. Clone
دارای RCSI و Snapshot روشن است، ولی `NOLOCK` حفاظت committed read را دور می‌زند.
چهار Creator سه‌ماهه به ۵۴ جدول پایه می‌رسند؛ فقط شش جدول rowversion و هیچ جدول
Temporal/Change Tracking وجود ندارد. پس یک transaction عمومی یا نام ستون Modified
جایگزین watermark/version قراردادشدهٔ منبع نیست.

نوشتن Rule به Form مستقر نسبت داده نشد: در اسکن ۶۲ Assembly هیچ Form/Caller یا
literal مربوط پیدا نشد و `ExternalVoucherTypeHandler.SaveCommand` همیشه Validation
failure می‌دهد. با این حال دو Procedure ادمینی بدون پارامتر، Viewها و پنج جدول
Type/Creator/Field/Article/Comment را با پنج محل SQL پویا تغییر می‌دهند. Transaction،
TRY/CATCH، Authorization و Publish version ندارند و شش Trigger فعال مرز اثر را
بزرگ‌تر می‌کند. حساب تحلیل اجازه Execute ندارد؛ actor و فراوانی اجرا نامعلوم است.
جزئیات و `R-054` در
`domains/24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md` ثبت شده است.

مقایسهٔ Child با Schema جاری نشان داد `VoucherTemplateArticleTransfer` هنوز
`VoucherCreatorId` و `ArticleCaption` را در INSERT نام می‌برد، در حالی که این دو
ستون دیگر در `Article` نیستند. پس اگر Child در Schema جاری اجرا شود، بعد از
Mutationهای قبلی Parent در Dynamic SQL شکست می‌خورد و Failure window انتشار جزئی
قطعی است؛ اجرای تاریخی و Authority آن همچنان اثبات نشده‌اند.

شش Trigger جاری برعکس Procedure قدیمی از نظر Column shape کامل‌اند و تغییرات را
به `GNR.tblLog` می‌فرستند. سرویس جداگانهٔ Replication دارای Binary outbox در
`dbo.ReplicationFile` است و اجرای فایل دریافتی همراه ثبت `LastExecLog` در یک
Transaction انجام می‌شود. اما Receipt فقط Range/Watermark دارد و Rule version،
Approval و Content hash ندارد. Clone هیچ ردیف Send/Receive/Outbox نگه نداشته، پس
Delivery چهار Article update سه‌ماهه از این Snapshot اثبات نمی‌شود. جزئیات و
`R-055` در `domains/25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md` است.

Outbox فقط یک حدس بر اساس ترتیب Commit نیست: File-share بعد از Copy از Move نهایی
استفاده می‌کند و FTP پس از Upload، اندازهٔ Remote را می‌خواند، Validation می‌کند
و فایل را Rename می‌کند؛ Helper دیتابیس بعد از Completion برمی‌گردد. بنابراین
پاک‌سازی پیش از تحویل ادعا نمی‌شود. اثر دقیق Helper دیتابیس به‌دلیل متن Obfuscated
اثبات نشد و Size-check نیز جای Content hash را نمی‌گیرد.

همان Artifact نسخهٔ `FluentFTP 32.4.3.0` را نیز Hash-pin کرد. شاخهٔ FTP
Credential را روی Client پیش‌فرض می‌گذارد ولی EncryptionMode، SSL protocol یا
Certificate validation را تنظیم نمی‌کند؛ Default library برابر Encryption=None
است. Zip password وجود دارد اما Hash/HMAC/Signature در مسیر نام‌دار Package صفر
است. چون File-share هم وجود دارد و Config فعال خوانده نشد، این حکم دربارهٔ
قابلیت FTP است نه ادعای استفادهٔ مرکز مشخص. `R-056` این مرز بحرانی را ثبت می‌کند.
Executor نام‌دار نیز `SqlCommand.CommandText` و `ExecuteNonQuery` دارد، Validator
نام‌دار را درون خود صدا نمی‌زند و مسیر فایل پیش از Validator بعدی به Executor
می‌رسد؛ بنابراین Allowlist تایپ‌شدهٔ همگانی پیش از Execute اثبات نشده است.

Lookup Site/DC و Center قبل از Unzip است، اما هر دو Helper یک `string` می‌گیرند،
با `String.Concat` Query می‌سازند و `ExecuteScalar` می‌زنند. Parameterization و
Validation کامل File-name→Lookup اثبات نشد؛ از این شاهد به‌تنهایی Exploit جاری
نتیجه‌گیری نمی‌شود. همچنین Named validator در هر دو مسیر Local/FTP بعد از اولین
Executor call قرار دارد، پس Lookup عددی مرکز جای authenticated center binding یا
Validation پیش از Execute را نمی‌گیرد.

با این حال خطای خود Executor به Receipt موفق تبدیل نمی‌شود: `Execute` Boolean
برمی‌گرداند، Success=`true` و Reject/Exception=`false` دارد؛ Local و FTP روی
نتیجه Branch می‌کنند و مسیر false پیش از `LastExecLog` Rollback می‌شود. بنابراین
ریسک باقی‌مانده اصالت/Scope/ترتیب و Business parity است، نه بلعیده‌شدن سادهٔ
Exception و ثبت Receipt در همان مسیر.

Connector در Execute و Commit خطا را Throw می‌کند، اما Catch متد Rollback هیچ
Throw/Re-throw ندارد. بنابراین تلاش Rollback پیش از Receipt ثابت است، ولی شکست
خود Rollback می‌تواند برای Caller نامرئی بماند و Transaction outcome را Unknown
کند. مقصد باید Connection را پس از Rollback failure قرنطینه و Incident/Receipt
ناموفق پایدار ثبت کند؛ این شاهد در `R-007` است.

File/FTP با Transaction دیتابیس اتمیک نیست: Local پس از Receipt و پیش از Commit
Copy/Delete دارد و FTP فایل‌های محلی و Remote را پیش از Commit حذف می‌کند. پس
Commit failure می‌تواند SQL را Rollback کند در حالی که Input جابه‌جا/حذف شده؛
Retry خودکار از نسخهٔ محفوظ اثبات نشده است. رخداد واقعی دیده نشد. مقصد باید
Package را تا Commit Receipt immutable نگه دارد و Ack/Delete را بعد از Commit
و با State machine بازیافت‌پذیر انجام دهد.

پس از Commit اصلی Local، `ResetReplicationSendTable` یک تراکنش مستقل دوفرمانی
دارد و Boolean موفق/ناموفق می‌دهد، اما Caller نتیجه را `pop` می‌کند. اثر دقیق
SQL مبهم و Failure واقعی اثبات نشده است؛ شکاف قطعی این است که نتیجهٔ ناموفق این
Maintenance به Outcome دریافت Propagate نمی‌شود.

مرز Retry نیز کامل نیست: `ReplicationFile.FileName`،
`ReplicationSend.CenterId` و هویت بازهٔ `tblLogRcv` قید یکتا ندارند. Trigger
رسید فقط کاهش Watermark را رد می‌کند؛ Watermark برابر را می‌پذیرد، پیوستگی بازه
را الزام نمی‌کند و `inserted` را Scalar می‌خواند. پس Monotonic بودن ثابت است،
اما Unique/Replay-safe/Gapless یا Multi-row safe بودن نه. Snapshot رسیدی ندارد،
بنابراین رخداد عملی Duplicate/Gap ادعا نمی‌شود؛ این مرز در `R-006` ثبت شده است.

Local receiver فایل‌ها را از `Directory.GetFiles` و FTP receiver را از Listing
سرور می‌گیرد؛ در دو Receiver و Listing helper، Sort/OrderBy صریح دیده نشد. چون
Trigger نیز Gap را رد نمی‌کند، deterministic range ordering پیش از Execute
اثبات نشده است. Snapshot خالی Receipt وقوع Out-of-order را ثابت نمی‌کند؛ مقصد
باید Metadata Range را parse/sort و Gap/Overlap را پیش از Apply قرنطینه کند.

`ControlLock` نام‌دار در Start/Run، Concurrency lock قطعی نیست: گراف آن Mutex،
Monitor یا DB call ندارد و فقط File existence را لمس می‌کند. از سوی دیگر
`ReplicationSend.CenterId` Unique نیست و Watermark read/update با Queryهای
concatenated انجام می‌شود. پس Per-center sender serialization اثبات نشده و مقصد
باید DB lease/application lock همراه fencing token داشته باشد. Snapshot خالی
وقوع Race را ثابت نمی‌کند. BeginTransaction نیز Overload تک‌رشته‌ای نام
Transaction را می‌گیرد و Isolation override صریح اثبات نشد.

بعد از `Receive`، سرویس یک Script تنظیمی جدا را Lookup و Execute می‌کند و
Transaction سراسری روی Receive+Hook ندارد. Wrapper موجود
`usp_ReplicationAfterReciveAll` نیز بدون Transaction/TRY-CATCH، Log-sort
تراکنشی را با Hook Dynamic `DBCC CHECKIDENT` بدون Transaction ترکیب می‌کند.
نگاشت Config فعال خوانده نشد، پس فعال‌بودن Wrapper ادعا نمی‌شود؛ اما Receipt فایل
به‌تنهایی تکمیل Maintenance را ثابت نمی‌کند. برای ماژول‌های Scoped، Execute-as،
مالک اختصاصی و Permission صریح Object-level صفر بود، ولی Principal/Role سرویس
نامعلوم است و از این صفرها Deny نتیجه‌گیری نمی‌شود. این شاهد `R-055` را دقیق‌تر کرد.

جدول‌های انتقال Audit immutable نیستند: Helper پاک‌سازی پیش از Receive/Send
فراخوانی می‌شود و Procedure مستقرِ سازگار، `tblLogRcv` را با Watermark
`LastExecLog/MAX` حذف می‌کند. Binding دقیق Helper مبهم به Procedure اثبات نشد،
اما صفر Receipt دیگر حتی به‌عنوان تاریخچهٔ کامل قابل فرض نیست. Cleanup عادی یادشده
`tblLog` اصلی را حذف نمی‌کند؛ با این حال سه Procedure ایجاد مرکز قابلیت حذف همان
لاگ را دارند. اجرای آن‌ها ادعا نشده، پس ۱٬۱۳۲ Rule log فقط «باقی‌ماندهٔ Snapshot»
است، نه شمار کامل تغییرات تاریخی.

Hook Identity نام جدول/ستون را از `ColvalueTable` به Dynamic DBCC می‌برد و
`QUOTENAME` در متن آن دیده نشد، اما Clone این جدول را با صفر Row نگه داشته است.
پس در Snapshot حاضر هیچ Identity target فعالی وجود ندارد و ریسک جاری/Exploit
ادعا نمی‌شود؛ Production config parity هنوز اثبات‌نشده است.

## موجودی عملیاتی؛ اصلاح برداشت Cardex-only

`GNR.tblStockGoods.OnHandQty` برابر جمع سادهٔ Cardex نیست. قرارداد رسمی
`dbo.usp_ModifyStockGoods` از `inv.vwHealthyCardexForCheck` شروع می‌کند و تعهدهای
عملیاتیِ هنوز نهایی‌نشده را کم می‌کند: فروش بدون خروج، فروش متصل به خروجِ
تغییرنیافته، سفارش خرید Legacy در Branch فعال، سفارش تأییدشدهٔ اثرگذار، رزرو
جایزه و برگشت خرید با علامت معکوس.

فاصلهٔ ۱٬۵۹۴ کلیدی و ۱۰۴٬۴۷۰ واحدی که قبلاً مغایرت نامیده شده بود، دقیقاً
تعهد فروش فعالِ هنوز خارج‌نشده است. پس از اعمال فرمول کامل، هر ۳۳٬۳۱۴ کلید
سال ۱۴۰۵ با Snapshot برابر و Residual صفر است. این تعهد از ۸۲۱ فروش و ۵٬۱۸۰
ردیف ساخته شده است.

قاعدهٔ تشخیصی: اختلاف `Cardex - OnHandQty` را تا قبل از محاسبهٔ همهٔ مؤلفه‌های
تعهد، خرابی ننام. فقط باقی‌ماندهٔ فرمول کامل `UNEXPLAINED_STOCK_RESIDUAL` است.
همچنین `usp_ModifyStockGoods` را برای Check اجرا نکن؛ Branch پیش‌فرض آن Repair
است، Triggerها را غیرفعال و Snapshot را Update می‌کند. Runbook کامل در
`STOCK_RECONCILIATION_INCIDENT_PLAYBOOK_20260827_FA.md` ثبت شده است.

## مسیر توزیع؛ اصلاح برداشت Orphan-FK

`SLE.tblDist.DistPath` در نصب فعلی نگین FK به `GNR.tblDistPath.ID` نیست.
بررسی Schema، تعریف `SLE.usp_sdsnet_CreateDist` و IL فرم نشان می‌دهد این ستون
یک کد عددی وابسته به حالت تنظیمات است. انتخاب‌گر مسیر نیز
`DistPathTreeNo` را در فیلد می‌نویسد، نه ID مستر. در تنظیمات فعلی هر دو مقدار
`DistPathingType` و `DistLimitType` صفرند؛ این دقیقاً Branch ورود عدد آزاد را
فعال و Lookup را غیرفعال می‌کند.

پس ۲۶٬۰۸۶ Header دارای «ارجاع یتیم» نیستند. هفت کد ۱، ۲، ۳، ۴، ۵، ۱۱ و ۱۲
باید عیناً به‌عنوان `distribution_path_code` و همراه با Mode/Provenance حفظ
شوند. مسئلهٔ باز فقط نام انسانی و سلسله‌مراتب Route است، زیرا Zone/Area/Path
قدیمی خالی‌اند. Join به `tblDistPath.ID`، ساخت Route پیش‌فرض یا محدودکردن
مقادیر به ۱/۲ خطای مهاجرت است. Runbook و شواهد کامل در
`DISTRIBUTION_PATH_RUNTIME_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

## مبلغ برگشت فاکتور؛ اصلاح برداشت Gross به‌جای Net

`SLE.tblRetSaleHdr.TotalAmount` نباید با جمع `SLE.tblRetSaleItm.Amount`
مقایسه شود؛ `Amount` ناخالص است. قرارداد رسمی وارانگار عبارت است از:

```text
AmountNut = Amount - Discount + AddAmount
TotalAmount = SUM(AmountNut)
```

`Discount` جمع `Dis1..3 + OtherDiscount` و `AddAmount` جمع
`Add1..2 + OtherAddition` است. Validator SQL، موجودیت .NET، فرم برگشت و SP
بازمحاسبه این قرارداد را تأیید می‌کنند. بنابراین ۷۳۱ اختلاف قبلی با Gross،
از جمله ۶۹۶ برگشت فعال، هشدار کاذب بود. در هر ۱۴٬۰۹۱ برگشت اختلاف رسمی Net،
فرمول قلم و Rollup اجزا صفر است. Tax و Charge طبق Validator جزو فرمول
`AmountNut` نیستند و مستقل‌اند.

قاعدهٔ تشخیصی: ابتدا نوع عدد را Gross/Net/Tax/Charge/Settlement/Inventory
تفکیک کن؛ فقط نقض `TotalAmount = Σ AmountNut` یا فرمول/اجزای آن Incident مبلغ
است. Runbook کامل در
`SALES_RETURN_AMOUNT_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

## Crosswalk برگشت NGT؛ دو رکورد، دو وضعیت متفاوت

دو برگشت فعال موبایلی هر دو بدون RetSale رسمی جاری‌اند، اما یکسان نیستند: یک
Line هیچ نتیجه‌ی `TourHistory` ندارد؛ Line دیگر نتیجه‌ی دقیق BackOffice UUID/Ref
و Write-back دارد، ولی RetOrder جاری آن پیدا نمی‌شود. اولی
`MOBILE_RETURN_PENDING_OR_UNATTEMPTED` و دومی
`MOBILE_RETURN_HISTORICAL_RESULT_CURRENT_TARGET_MISSING` است. هیچ‌کدام مجوز
ساخت خودکار سند مالی یا انبار نیستند.

لینک `SLE.CustomerCallReturnId` رسماً به مدل عددی `FRU.CustomerCallReturns`
اشاره می‌کند، نه UUID مدل NGT؛ Join مستقیم این دو مدل غلط است. علاوه بر آن،
`NGT_DoReplicateTour` نتیجه‌ی BackOffice را Commit می‌کند و سپس Crosswalk NGT
را Write-back می‌کند؛ پس Reconciliation و Idempotency بین این دو مرحله الزامی
است. Runbook: `NGT_RETURN_CROSSWALK_DIAGNOSTIC_20260827_FA.md`.

## تسویه چک برگشتی؛ مالک چک با Customer تخصیص یکی نیست

۴۹ Payment دارای `RetChequeRef` که Customer آن‌ها با `TblCheque.CustRef` فرق
دارد، خطای داده نیست. هر ۴۹ ردیف به تخصیص اولیه‌ی دقیق همان
`Cheque + Sale + Customer` وصل است؛ ردیف بی‌توضیح و Over-settlement صفر است.
در ۴۸ ردیف Saleدار، Customer پرداخت دقیقاً Customer فاکتور است و هیچ‌کدام
Customer مالک چک نیست. بنابراین این نقش‌ها را جدا نگه دار:

```text
ChequeOwner        = TblCheque.CustRef
AllocationCustomer = tblPayments.CustRef on original ChqRef allocation
InvoiceCustomer    = tblSaleHdr.CustRef
SettlementKey      = RetChequeRef + SaleRef + AllocationCustomer
```

`ManualCustRef` مرجع تخصیص نیست. Procedureهای رسمی مانده را در سطح Cheque و
Sale کنترل می‌کنند و مسیرهای Other-customer/Parent-customer عمداً پایه‌های
حسابداری مرتبط می‌سازند. صرف تفاوت Customer را Incident نکن؛ فقط Allocation
مفقود، ناسازگاری Sale/Customer، بیش‌تسویه یا Reference شکسته Incident است.
Runbook کامل در
`RETURNED_CHEQUE_CROSS_CUSTOMER_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

## مرجع Pay تأییدشده و نوع ارجاع حقوقی چک دریافتی

در وضعیت «واگذار به غیر»، `TblCheque.PayId` مرجع قطعی نیست. مدل خواندن رسمی
برای Draft از Master استفاده می‌کند، اما پس از تأیید، مرجع پایدار
`tblChqHist.PayId2` است. هر ۸ Master gap فعلی از History به Pay تأییدشده حل
می‌شوند؛ Orphan و Conflict صفر است. پس از Master null نه Pay بساز و نه رکورد
را Quarantine کن.

برای وضعیت حقوقی، `LegalType=1` یعنی واگذاری به پرسنل و `LegalType=2` یعنی
واگذاری به دایره حقوقی؛ Null یک حالت مشاهده‌شده‌ی نامشخص است. وجود PersonnelId
نوع را تعیین نمی‌کند، چون در هر دو نوع دیده می‌شود. ۳۵ مورد فعلی باید
`UNKNOWN_SOURCE` بمانند. مسیر Deploy‌شده‌ی تأیید گروهی LegalType را روی Parent
می‌گیرد ولی هنگام ساخت History آن را Forward نمی‌کند؛ این یک ریسک قطعی ایستا
با فراوانی اجرای تاریخی نامعلوم است، نه مجوز اصلاح داده‌ی مبدأ.

Runbook: `RECEIVED_CHEQUE_PAY_PROJECTION_AND_LEGAL_TYPE_DIAGNOSTIC_20260827_FA.md`.

## برگ دسته‌چک پرداختنی؛ Used همیشه به معنی چک جاری نیست

`PChequeBookItem.IsUsed` دو منشأ رسمی دارد: چرخه‌ی چک آن را همراه صدور/عودت/Undo
تغییر می‌دهد، اما فرم نگهداری برگ نیز مقدار را مستقیم ذخیره می‌کند. ۴٬۸۲۷ برگ
Used فعلی دقیقاً از ۴٬۶۷۲ برگ متصل به چک و ۱۵۵ برگ بدون ابزار جاری تشکیل شده
است. ۱۵۵ مورد دوم لینک Transfer-family یا متن زمینه ندارند و در ۲۳ دفترچه فعال
پخش شده‌اند.

مدل مقصد باید آن‌ها را `SOURCE_USED_UNLINKED` با `UNKNOWN_SOURCE` نگه دارد؛
خودکار آزادکردن، ساختن چک یا ادعای «دستی‌بودن قطعی» نادرست است. علت تاریخی به
دلیل نبود Actor/ModifiedDate روی جدول برگ قابل بازیابی نیست. هر تغییر آینده‌ی
برگ باید Actor، Time، Reason و نسخه را در همان Transaction رخداد چک ثبت کند.

Runbook: `PAYABLE_CHEQUE_LEAF_USAGE_DIAGNOSTIC_20260827_FA.md`.

## Fork وضعیت سند حسابداری؛ Pointer رسمی است اما History بعدی بی‌اثر نیست

در ۱٬۰۹۴ سند Manual، Pointer معتبر ولی غیرآخرین است و پس از آن ۱۴٬۹۴۶ رخداد
وجود دارد؛ در ۱٬۰۹۱ سند وضعیت Branch با Current فرق کرده و ۱٬۰۹۰ Pointer هنوز
رخداد اول را نشان می‌دهد. `Voucher2/VoucherFast` وضعیت را از Pointer می‌خوانند،
ولی `DoVoucher_SetVoucherNo` همین اختلاف را خطا می‌داند. پس این‌ها Rollback سالم
اثبات‌شده نیستند؛ `CURRENT_POINTER_HISTORY_FORK/UNKNOWN_OUTCOME` هستند.

`Get_ChangeVoucherStatus` History را پیش از Pointer Update در Transaction درج
می‌کند، اما CATCH آن Rollback صریح ندارد. این یک Root-cause candidate است و
علت تک‌تک رکوردها را ثابت نمی‌کند. در مهاجرت، Pointer را با MAX عوض نکن و Branch
را حذف نکن؛ هر دو را نگه دار تا حسابدار disposition کند. مقصد باید CAS Pointer،
event و numbering را در یک Command اتمیک و Idempotent ثبت کند.

Runbook: `VOUCHER_STATUS_POINTER_DIAGNOSTIC_20260827_FA.md`.

## خرید و رسید؛ Reconciliation باید Component-aware باشد

رابطه‌ی `ICA.tblSupInvInvoiceRelation` فقط Header-level و N:M است. یک رسید به
دو فاکتور متصل است؛ به همین دلیل سنجش per-invoice پنج Receipt-only کاذب می‌ساخت.
در ۳٬۴۲۵ Connected component، هر پنج مورد توسط فاکتور دیگر همان Component
توضیح داده شد و ۳۰٬۰۹۶ گروه کالا با Residual صفر تطبیق یافت.

`ICA.usp_ApplySupInvoice` نیز کل Invoice list و Voucher list را بر Goods جمع
می‌کند. مقصد نباید Relation را Unique یا Line allocation حدسی بسازد؛ فقط Residual
سطح Component قرنطینه می‌شود. Runbook:
`SUPPLIER_RECEIPT_COMPONENT_DIAGNOSTIC_20260827_FA.md`.

هفت Goods مرجوعی Source line مستقیم ندارند، اما هر هفت با Voucher خروج نوع ۵۵
دقیق و دارای Price/Amount غیرصفرند. IL فرم ثابت می‌کند Item grid از
`InvVocherRef` می‌آید و `SupInvoiceRef` فقط Hint اختیاری Source/Price است؛ State
صحیح `OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR` است. فاکتور قبلی فقط
Candidate است و Reassign/Reprice خودکار ممنوع.

سه مسیر Writer می‌توانند Price بسازند/عبور دهند: Legacy/Desktop پارامتر Price،
SDSNET Temp payload و Import رسمی `usp_Convert_RetSupInvoice2` با UnitPrice و
`Qty×UnitPrice`. چون Marker مسیر ایجاد روی رکورد جاری نداریم، منشأ هفت مقدار
غیرصفر همچنان `UNKNOWN_SOURCE` است، نه «دستی» یا «Import».

در ۴٬۶۰۱ Item×Toll نیز ۲۰ Stored TollRef قدیمی از یک Header وجود دارد؛ Ref خام
غایب است اما هر ۲۰ با قاعده رسمی Same-header TollRef یکتا Resolve و در View
سازگاری دیده می‌شوند. Validator فعلی هر ۲۰ را به‌دلیل Scope اشتباه نمی‌بیند.
مسیر Desktop پیام Validator را پیش از Commit مسدود می‌کند، ولی مسیر SDSNET در
UPDATE آن را صدا نمی‌زند و در INSERT Return/Message را Blocking نمی‌کند. شاخه
UPDATE SDSNET Defect `@HdrId` مقدارنگرفته هم دارد، اما Header دارای ۲۰ Ref قدیمی
Legacy است؛ پس آن Defect علت تاریخی این ۲۰ مورد اعلام نمی‌شود.

Grain کنترل Quantity نیز روشن است: ۱۵۶ گروه `(Return,Goods)` سندی به ۱۱۵ گروه
`(SupInvoiceRef,Goods)` تجمعی می‌رسند، چون Validator همه Return headerهای دارای
Source invoice مشترک را جمع می‌کند؛ Current ID فقط Source ref را پیدا می‌کند.
این کنترل تجمعی همچنان هفت Goods نامنطبق را به‌علت `INNER JOIN` نمی‌بیند.
سمت Source به‌ظاهر ردیفی است، ولی Unique index رسمی `(HdrRef,GoodsRef)` دارد و
Duplicate جاری صفر است؛ بنابراین این بخش در Schema مستقر یک کالا/یک ردیف است.

پروفایل سه‌ماههٔ `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` مرز جاری/Legacy را دقیق‌تر کرد:
هر ۵۰ Header و ۳۹۳ قلم از مسیر `IsNew=1` هستند؛ فقط یک Header Source invoice
دارد و پنج گروه آن Source-item match ندارند، درحالی‌که TollRef قدیمی در این
پنجره صفر است. پس نقص Validator SDSNET برای مسیر جاری مادی است، اما ۲۰ TollRef
قابل‌بازیابی یک وضعیت مهاجرتی Legacy است.

## سند فعال بدون قلم؛ Draft shell است نه Ledger خراب

تنها Voucher فعال بدون Item، Manual، وضعیت Draft، بدون External link و با اثر
Debit/Credit صفر است. مسیر دفترکل بدون Item آن را Post نمی‌کند. اما VoucherNo
منبع دارد و Procedure فعلی شماره‌گذاری، سند بی‌قلم را رد می‌کند. پس State مقصد
`DRAFT_EMPTY_NUMBERED_SHELL/UNKNOWN_SOURCE` است: Line نساز، آن را Post نکن و
شماره منبع را بدون تصمیم حسابدار reuse نکن.

مسیر Save می‌تواند قلم‌های حذف‌شده از درخواست را پاک و سند نامعتبر موقت را Draft
کند؛ فراخوانی بازشماری در مسیر دستی Comment شده است. این Root-cause candidate
است، نه تاریخچه اثبات‌شده. Runbook:
`EMPTY_VOUCHER_SHELL_DIAGNOSTIC_20260827_FA.md`.

## مشکل شناسایی‌شده در بازیابی NeginAI

مشکل اصلی فقط کمبود فارسی‌سازی نیست. در `app/reasoning_context.py` نیت‌های فروش به چند طبقهٔ محدود نگاشت می‌شوند و سپس منابع ثابت فروش، پیش از سنجش ارتباط با سؤال مرتب و به شش منبع اول محدود می‌شوند.

در نتیجه پرسش‌های متفاوتی مانند «مانده فاکتور مشتری»، «تسویه فاکتور»، «کاردکس مشتری» و «حواله فروش» تقریباً یک Context اولیه می‌گیرند. Viewهای تخصصی حساب مشتری نیز در کاتالوگ فعلی بعضاً در دسته‌های `finance`، `inventory` یا `workflow_configuration` قرار گرفته‌اند و از Context فروش حذف می‌شوند.

نمونه‌های طبقه‌بندی نادرست یا ناکافی:

- `dbo.vwReview_RcvAccountSale2` در `finance`
- `dbo.vwReview_RcvAccountSettlement2` در `finance`
- `dbo.vwReview_RcvAccountCardex2` در `inventory`
- `dbo.SettlementFast` و `dbo.SettlementFull` در `workflow_configuration`

پس راه‌حل بعدی باید «مسیریابی بر اساس مفهوم و فرایند» باشد، نه بازگشت کور به کل ۳۹۴۵ Object و نه محدودسازی ثابت به چند View عمومی.

### وضعیت اصلاح در ۲۰ مرداد ۱۴۰۵

Router مفهومی در Runtime پیاده‌سازی شد. مسیرهای مستقل `invoice_balance`، `receipt`، `settlement`، `customer_cardex`، `sales_voucher`، `order`، `distribution`، `inventory` و `sales` اکنون هرکدام منابع مرجع، تعریف و مبنای گزارش خود را دارند. ترتیب منابع بر اساس مفهوم سؤال است و جست‌وجوی لغوی فقط نقش گسترش ثانویه دارد.

کاتالوگ ۳۹۴۵ Object نیز همگام شد و طبقه‌بندی Viewهای حساب مشتری، دریافت و تسویه اصلاح گردید. فرانت مسیر تشخیص‌داده‌شده، بازه، مبنای محاسبه و منابع گزارش را کنار پاسخ نمایش می‌دهد.

## مرز تاریخ Return موبایلی و تاریخ فعال سیستم

`NGT.CustomerCallReturns.OperationDate` یک timestamp رویداد در NGT است و
`GNR.tblOprDate` جدول تاریخ فعال/بسته‌ی سیستم بر مبنای DC، سال و `SysRef`؛ این
دو مترادف نیستند. تنظیم `CustomerCallDateBasedOnUniqueId` چهار گزینه دارد و
مقدار جاری `CallDate / تاريخ درخواست` است.

پیاده‌سازی Business و SQL برای همه گزینه‌ها یکسان اثبات نشد: Business در شاخه
`OperationDate` تاریخ خود Return را کپی می‌کند، ولی `dbo.NGT_DoReplicateTour`
در همان گزینه از CallPDate با fallback به TourPDate استفاده می‌کند. `ActiveDate`
در Business از Retriever پشت‌دفتر و در SQL از `GNR.tblOprDate` باز فروش می‌آید.
`ServerDate` در هر دو خانواده از ساعت سرور است. سه CASE SQL هیچ `ELSE` ندارند.

مسیر `SaveTourData` مقدار خالی .NET را رد و `AddDistributionTour` مقدار `now`
را ثبت می‌کند؛ با این حال Default جدول ۱۹۰۰ است و Check/Trigger جلوگیری‌کننده
وجود ندارد. دو ردیف جاری Sentinel ندارند و رخداد غلط‌تاریخ ادعا نشده است. قرارداد
کامل در `NGT_OPERATION_DATE_AND_REPLICATION_SELECTOR_BOUNDARY_20260829_FA.md`
و ریسک `R-060` ثبت شده است.

## مرز تقدم و انتقال تنظیمات NGT

تنظیم مؤثر NGT از یک جدول واحد نمی‌آید. مسیر Business برای Device، Query
Owner-aware روی DeviceSetting و DeviceUser، حذف `IsRemoved`، اتصال به کاربر و
سپس ترکیب یازده گروه App/General/Tracking/PreSale/HotSale/Distribution/Task/
Report/Print/BackOffice/Inquiry را انجام می‌دهد. AppSetting جداگانه با شناسه‌ی
singleton ثابت خوانده می‌شود.

دو اختلاف مهم ثبت شد. اول، `MandatoryCustomerVisit` در Business از DeviceSetting
ولی در View انتقال از AppSettings می‌آید؛ هر ۱۷ پروفایل فعال فعلی با مقدار App
ناسازگارند و دو Device مقدار NULL دارند. دوم، BackOffice زنده تنظیم مرکز را از
`SdsNet_serverConfig` می‌گیرد، اما View انتقال از ServerConfig سراسری Pivot
می‌سازد. در ۱۲ نگاشت، یک خروجی statically omitted، پنج خروجی جاری غایب و هفت
مقایسه‌ی مرکز-به-انتقال ناسازگار است. Procedure زنده ۳۶ و UNPIVOT انتقال ۳۰ نام
خروجی دارد؛ پس از rename مرکز، شش خروجی زنده در انتقال نیست.

View خام همچنین ۲۱۸۴ ردیف متعلق به ۲۳ پروفایل حذف‌شده می‌سازد، ولی مسیر runtime
آن‌ها را فیلتر می‌کند و هیچ DeviceUser فعلی به پروفایل حذف‌شده وصل نیست. ۵۱
DeviceOrderType فعال همچنان به پروفایل حذف‌شده اشاره دارند؛ این یک قرارداد
lifecycle باز است، نه اثبات ارسال به کاربر. سند کامل
`NGT_CONFIGURATION_PRECEDENCE_AND_TRANSPORT_BOUNDARY_20260829_FA.md`، checkpoint
مستقل ۳۹/۳۹ و ریسک `R-061` مرز مقصد را ثبت کرده‌اند.

### سفارش NGT: ذخیره، Replication و Crosswalk

چهار بدنه‌ی WebApi به `TourDomain.SaveTourData` می‌رسند. این بدنه‌ی ۸٬۹۶۰
دستوری transaction صریح دارد و چهار شاخه می‌توانند `ReplicateTour` را با همان
transaction صدا بزنند. `ReplicateTour` با ۱۵٬۵۳۲ دستور، مسیر
`NewReplicateTour → dbo.NGT_DoReplicateTour` و دو `ReplicateToBackOffice` را
ترکیب می‌کند. در مقابل `UpdateTour → UpdateFromNGT` پنج `SaveChangesAsync` و
تغییر IsRemoved دارد، ولی در دو بدنه transaction محلی دیده نشد؛ ambient یا
delegated transaction و رخداد partial-write فعلی اثبات/رد نشده است.

Crosswalk یک‌دانه‌ای نیست: ۲۱۲٬۲۳۱ سفارش فقط تمام Lineهای فعال را نگاشت کرده‌اند؛
۹٬۷۹۵ سفارش فقط Header عددی دارند و هیچ Line فعال نگاشت‌شده ندارند؛ یک سفارش
partial و هفت سفارش Split هستند. ۱٬۱۲۵ OrderId نیز بین ۳٬۳۸۵ Header مشترک‌اند
و حداکثر ۱۳ Header را به یک Order وصل می‌کنند. هر دو راه Header-only و Line-only
در سه ماه اخیر هم‌زمان دیده می‌شوند. جدول Status فعلی صفر ردیف و بدون key است.

سند کامل در
`NGT_ORDER_PERSISTENCE_REPLICATION_AND_CROSSWALK_BOUNDARY_20260829_FA.md` است و
این شواهد به‌جای ساخت ریسک تکراری، `R-033` را تقویت کرده‌اند. Checkpoint مستقل
`varanegar_ngt_order_checkpoint_20260829.json` زنجیره‌ی SQL/IL/Auth/Risk/Trace
را فقط به‌صورت آفلاین و hash-pinned کنترل می‌کند.

### Tour و CustomerCall: state machine و فرمان وب

۶۴٬۵۶۱ Tour و ۲٬۴۷۱٬۲۵۰ CustomerCall جاری نشان می‌دهند PreviousStatus فقط در
۴۵۵ Tour حاضر است و تاریخچه‌ی کامل نیست. IL مسیرهای مستقل Cancel، Deactivate،
Activate، Receive، Send، Close و Finish را اثبات می‌کند؛ Deactivate وضعیت قبلی
را ذخیره و Activate آن را بازمی‌گرداند، ولی بیشتر stateها هیچ previous snapshot
ندارند. تنها جدول status/history نام‌دار این خانواده همان
CustomerCallOrderStatus صفرردیف است.

VisitStatus یک taxonomy خالص نیست: ۷۷۲ Call به «تحویل قسمتی» از
DistributionDeliveryStatus اشاره دارند. همچنین Tour+Customer یکتا نیست؛ ۲۶٬۶۱۳
زوج تکراری، ۵۷٬۳۹۱ Call و بیشینه ۱۴ Call در یک زوج وجود دارد. مقصد باید
VisitAttempt مستقل و stateهای Tour/Call/Visit/Delivery جدا داشته باشد.

از ۲۹ Endpoint تغییر lifecycle، ۲۴ مورد GET و پنج مورد POST هستند؛ همه NGT auth
دارند، پس anonymous incident ادعا نشده، اما GET mutation باید حذف شود. سند کامل
در `NGT_TOUR_CUSTOMER_CALL_STATE_AND_COMMAND_BOUNDARY_20260829_FA.md` و
Checkpoint آن در `varanegar_ngt_tour_call_checkpoint_20260829.json` ثبت می‌شود.

### پرداخت NGT: سربرگ، تخصیص، تأیید تور و رسید

پرداخت و رسید یک موجودیت نیستند. Snapshot فقط‌خواندنی ۳٬۵۲۳ سربرگ فعال و
۳٬۹۱۷ ریز فعال دارد. ۳٬۴۶۶ سربرگ با جمع ریزها برابرند، ولی ۵۷ مورد کم‌تخصیص‌اند:
۱۴ مورد بدون ریز و ۴۳ مورد با جمع ناقص؛ over-allocation فعلی صفر است. این اختلاف
در ۲۴ کارت‌خوان، هفت نقد، ۲۱ چک و پنج «رسید» دیده می‌شود. ۳٬۷۴۵ ریز به سفارش
جاری NGT و ۱۷۲ ریز old-invoice به Sale قدیمی BackOffice وصل‌اند؛ مقصدهای این دو
حالت نباید در یک FK مبهم ادغام شوند.

۲۷۴ پرداخت Crosswalk کامل UUID/Ref/ReceiptNo با Receipt تأییدشده دارند، اما فقط
چهار مبلغ برابر است و ۲۷۰ مبلغ Scope متفاوت دارد. پس identity parity قوی است،
ولی amount equality بین NGT و Receipt قاعده نیست. PaymentApproved نیز معادل وجود
پرداخت نیست: ۳۴۵ تور تأیید، ۴۵۸ تور دارای پرداخت، ۲۶ تأیید بدون پرداخت و ۱۳۹
پرداخت بدون تأیید دیده شد.

IL ثابت می‌کند `SaveTourPaymentChanges` تراکنش Begin/Commit/Rollback مستقل دارد،
پرداخت Cash قبلی را soft-remove، دادهٔ جدید را BulkMerge و Save می‌کند و Amount و
PaidAmount را جمع می‌زند. تنها caller مستقیم آن `UpdateTour` است که پس از پرداخت،
ذخیره موجودی و سفارش را جدا صدا می‌زند و در بدنه خودش transaction محلی ندارد؛
ambient بیرونی و رخداد partial فعلی اثبات نشده است. همچنین ۴۸۲ Bridge فعال عامل
به PaymentTypeOrder حذف‌شده وصل است و فیلتر صریح removed/enabled در بدنه مستقیم
Resolver مشاهده نشد.

سند کامل `NGT_PAYMENT_SETTLEMENT_AND_RECEIPT_BOUNDARY_20260829_FA.md` و checkpoint
مستقل `varanegar_ngt_payment_checkpoint_20260829.json` این مرز را ثبت می‌کنند.
`R-007` و `R-061` توسعه یافته و `R-063` بحرانی افزوده شده است. رجیستر فعلی ۶۳
ریسک، ۳۵ بحرانی، ۲۴۸ اتصال Traceability و صفر ماژول Command-ready دارد.

### Replication پرداخت: Receipt، TourHistory و Crosswalk جاری

مسیر واقعی از `TourDomain.NewReplicateTour` به `dbo.NGT_DoReplicateTour` و سپس
`dbo.NGT_ReplicateTour` می‌رسد. Helper رسید، `Receipt` و ابزارهای نقد، چک/History
و BankOrder را می‌سازد؛ Helper تسویه Allocationهای `Settlement` را ایجاد می‌کند.
هر دو بدون transaction محلی و زیر transaction Procedure بالادست اجرا می‌شوند.
نتیجه‌ی پرداخت در `TourHistory(Type=10)` با UUID/Ref/No ثبت می‌شود.

Snapshot دارای ۴۴۷ History نوع ۱۰ برای ۳۴۴ Payment فعال است. ۲۷۴ Payment دقیقاً
یک History و Crosswalk کامل UUID/Ref/No دارند. ۷۰ Payment دیگر ۱۷۳ History دارند
و در Header جاری فقط شماره رسید نگهداری شده؛ UUID و Ref هر دو خالی‌اند. ۷۲ گروه
تکرار دقیق، بیشینه شش History، دو Payment چندهدف و ۹ History با هدف Receipt مفقود
ثبت شد. این شواهد تکرار History و Crosswalk ناقص را ثابت می‌کنند، نه اینکه هر
History الزاماً یک سند مالی تکراری ساخته باشد.

`TourHistory` برای Type=10 هیچ FK/Trigger یا Unique current-key ندارد؛ Index یکتا
فقط Type=1 را پوشش می‌دهد. SQL نیز Guard یکسان ندارد. Procedure بیرونی پس از
Commit فقط `BackOfficeReceiptNo` را روی Payment می‌نویسد؛ IL مستقر سپس سه setter
UUID/Ref/No و Commitهای دو سوی مرحله‌ی Write-back را نشان می‌دهد، با caveat
branch reachability. در مقصد، Attempt history باید از Current crosswalk جدا و
Command با idempotency key، payload hash، outbox/saga و reconciliation ساخته
شود. سند کامل
`NGT_PAYMENT_REPLICATION_AND_CROSSWALK_IDEMPOTENCY_BOUNDARY_20260829_FA.md` است؛
`R-007` توسعه یافت و `R-064` بحرانی افزوده شد.

### جبران Replication و Rollback NGT

متد `TourDomain.RollBackTour` با ۲۰ دستور IL درخواست نوع ۲۰ می‌سازد. هر دو
Adapter مستقر VnLite و VnSds، `ReplicateResult.EntityUniqueId`ها را در temp table
می‌ریزند، `dbo.NGT_RollBackTour` را اجرا و سپس Commit می‌کنند؛ Catch نیز Rollback
دارد. Procedure فعال transaction محلی ندارد و پاک‌سازی را با Typeهای
`TourHistory` هدایت می‌کند.

خود `TourDomain.RollBackTour` نتیجهٔ Boolean فراخوانی `RetrieveInfo` را با opcode
`pop` دور می‌ریزد. در نتیجه `false` برگشتی Adapter بعد از Catch/Rollback به‌صورت
یک نتیجهٔ قابل بررسی به Caller منتشر نمی‌شود؛ شکست جبران می‌تواند در مرز Business
بی‌سیگنال بماند.

Procedure قدیمی `dbo.USP_NGT_UndoReplicateTour` فعال نیست: `RETURN` پیش از تمام
Mutationها قرار دارد و کل بدنهٔ حذف داخل Comment است. Procedure فعال نیز
`RCashDetail` و `tblChqHist` را پاک نمی‌کند و Payment را فقط از Type=11 حذف
می‌کند؛ Snapshot هیچ Type=11 ندارد. هر ۳۴۲ Receipt موجود Type=10 حداقل یک
Dependency فعال `NO_ACTION` به CashDetail، ChequeHistory یا Payment ابزار مالی
دارد. بنابراین Compensator مستقر برای شکل فعلی Receipt از نظر ساختاری ناقص است؛
وقوع یا فراوانی خطای عملیاتی بدون اجرای کنترل‌شده ادعا نشده است.

در مقصد باید Attempt، CurrentCrosswalk و Compensation state جدا باشند؛ جبران
وابسته به نوع ابزار، FK-aware و ترجیحاً Reversal/Void باشد، نتیجهٔ typed آن تا
Caller منتشر شود و History تا موفقیت کامل حذف نشود. سند کامل
`NGT_REPLICATION_COMPENSATION_AND_ROLLBACK_BOUNDARY_20260829_FA.md` است. `R-065`
بحرانی اضافه شد و رجیستر فعلی ۶۵ ریسک، ۳۷ بحرانی، ۲۵۶ اتصال Traceability و صفر
ماژول Command-ready دارد.

### Replication و Update برگشت NGT

`TourDomain.ReplicateTour` ابتدا `NewReplicateTour` را صدا می‌زند و بعد وارد
Transaction مدیریت‌شده می‌شود. شش setter خطی UUID/Ref/No سفارش و فاکتور برگشت و
دو setter مجموعه شماره سفارش برگشت بعدتر اجرا می‌شوند؛ Commit در IL هم پیش و هم
پس از این setterها وجود دارد. SQL نیز مستقل نشان می‌دهد
`dbo.NGT_DoReplicateTour` نتیجهٔ `NGT_ReplicateTour` را Commit و سپس Crosswalk
ReturnOrder را روی NGT می‌نویسد. Unique index فعالِ بدون فیلتر برای Typeهای ۲/۱۲
`TourHistory` یا Crosswalk خط برگشت وجود ندارد.

دو Line فعال فعلی شامل یک No-history و یک Type=2 historical-result با هدف
RetOrder مفقود است؛ هدف RetOrder جاری صفر است. هیچ‌کدام مجوز Recreate خودکار
نیستند. علاوه بر این، `CustomerCallReturnDomain.UpdateFromNGT` سه SaveChanges و
Caller آن یک SaveChanges دیگر دارد، ولی در هیچ‌کدام Begin/Commit/Rollback دیده
نشد. مقصد باید ReplicationAttempt/Crosswalk/Saga و Aggregate transaction صریح
داشته باشد. سند کامل
`NGT_RETURN_REPLICATION_AND_INGEST_ATOMICITY_BOUNDARY_20260829_FA.md` است؛
`R-066` بحرانی و `R-067` بالا افزوده شد و رجیستر فعلی ۶۷ ریسک، ۳۸ بحرانی، ۲۶
بالا، ۲۶۳ اتصال Traceability و صفر Command-ready دارد.

### Replication فروش و تاریخچهٔ Type=8

۳٬۷۳۱ History نوع ۸ به ۳٬۵۹۳ Order Entity نگاشت می‌شوند. ۱۳۸ Order دقیقاً دو
History کاملاً هم‌Target و هم‌timestamp دارند؛ Multi-target، Target مفقود و
اختلاف Header↔History↔Sale همگی صفر است. پس Duplicate ledger قطعی ولی Duplicate
Sale/Stock/Accounting اثبات‌نشده است. Unique guard مرتبط برای Type=8 History یا
Crosswalk Invoice روی Header NGT وجود ندارد.

IL نشان می‌دهد `NewReplicateTour` پیش از اولین Transaction مدیریت‌شده و پیش از
setterهای UUID/Id/No فاکتور است و Commit در دو سوی setterها دیده می‌شود. مقصد
باید Attempt append-only، CurrentCrosswalk یکتا، Saga/Outbox و Reconciliation
آثار فروش/انبار/حسابداری داشته باشد. سند کامل
`NGT_SALE_REPLICATION_TYPE8_IDEMPOTENCY_BOUNDARY_20260829_FA.md` است؛ `R-068`
بحرانی رجیستر را به ۶۸ ریسک، ۳۹ بحرانی، ۲۶ بالا، ۲۶۷ اتصال و صفر Command-ready
رساند.

## مدل دانشی مورد نیاز دستیار

دانش دستیار باید پنج لایه داشته باشد:

1. **واژه و تعریف:** دریافت، تسویه، مانده، حواله، فاکتور، برگشت، کاردکس و غیره.
2. **چرخهٔ عمر سند:** سند از کجا ایجاد می‌شود، به چه چیزی تبدیل می‌شود و چه وضعیت‌هایی دارد.
3. **روابط داده:** کلیدهای اتصال مشتری، سفارش، فاکتور، حواله، توزیع، دریافت و تسویه.
4. **قرارداد گزارش:** عنوان فارسی، فیلدهای رسمی و View مناسب هر گزارش.
5. **قواعد شرکت نگین پخش:** تعریف فروش، فروش خالص، محدودهٔ شعب، تاریخ مبنا و استثناهای داخلی.

## مرحله‌های بعدی شناخت

1. استخراج و ثبت چرخهٔ وضعیت برای درخواست، حواله، فاکتور، توزیع، دریافت، چک و تسویه.
2. نگاشت تک‌تک ۲۱۶ تب گزارش به View سریع یا Query مرجع و سنجش کارایی.
3. ساخت مجموعه سؤال‌های واقعی کاربران در حوزه‌های فروش، خزانه، انبار، خرید و شعب.
4. ثبت قواعد تأییدشدهٔ شرکت در جدول `definitions`؛ اکنون فقط ۳ تعریف وجود دارد و این برای یک ERP چندشعبه‌ای کافی نیست.
5. اصلاح طبقه‌بندی Objectها و ساخت Router چندمرحله‌ای: تشخیص مفهوم، انتخاب حوزه، انتخاب گزارش مرجع، سپس گسترش محدود در صورت نبود پاسخ.
6. ساخت آزمون طلایی که پاسخ نسخهٔ جدید را با گزارش خود ورانگر مقایسه کند.

## محدودیت‌های این مرحله

- خواندن مستقیم پنجرهٔ برنامه به‌علت خطای فنی ابزار کنترل ویندوز ممکن نشد؛ متادیتای منو/فرم و فایل‌های گزارش مستقل از رابط خوانده شدند.
- تعریف دقیق برخی وضعیت‌ها و قواعد اختصاصی نگین پخش هنوز باید با کاربران مالی، فروش، انبار و وصول تأیید شود.
- `dbo.SettlementFull` به تابعی وابسته است که کاربر فقط‌خواندنی مجوز اجرای آن را ندارد؛ منابع جایگزین قابل‌خواندن شناسایی شده‌اند.
- Router مفهومی و نمایش مبنای گزارش فعال شده‌اند؛ تکمیل قواعد اختصاصی واحدهای شرکت همچنان یک فرایند زنده است.

## Checkpoint قابل‌بازتولید ۲۸ مرداد ۱۴۰۵

شناخت صدور سند و Replication قواعد در
`docs/varanegar_reconstruction/CHECKPOINT_20260828_RULE_REPLICATION_FA.md`
منجمد شد. Bundle ماشین‌خوان ۲۱ منبع را Hash می‌کند و ۳۳ Gate معنایی را کنترل
می‌کند؛ ۵۶ ریسک باز، ۳۱ ریسک بحرانی، ۲۲۱ اتصال Requirement↔Risk و صفر ماژول
Command-ready ثبت شده است. این صفر به معنی نبود شناخت نیست؛ یعنی هنوز هیچ مسیر
نوشتن مقصد بدون تکمیل مجوز، idempotency، fault-injection و reconciliation مجاز
به اجرا نیست.

Footprint سراسری `InsertToLog` نیز منجمد شد: ۱۱۴۲ Trigger فعال روی ۳۷۶ جدول در
شش Schema، با ۱۱۴۰ نشانهٔ Cursor، صفر `TRY/CATCH`، سه نشانهٔ `XACT_ABORT` و صفر
`NOT FOR REPLICATION`. بنابراین Replication logging در مدل منبع یک Side effect
فراگیر نوشتن است؛ در ERP مقصد نباید با CRUD مستقیم و نامرئی بازتولید شود و باید
با Outbox تراکنشی، Idempotency، Fault test و Reconciliation صریح جایگزین شود.
این Footprint وقوع خطای Runtime یا فعالیت اخیر همهٔ جدول‌ها را اثبات نمی‌کند.
توزیع آن نیز Cross-domain است: `dbo=426/140` Trigger/Table،
`GNR=321/107`، `SLE=282/92`، `Acc=53/17`، `inv=45/15` و `ICA=15/5`.
پس Outbox و Inbox مقصد باید Contract مشترک پلتفرمی داشته باشند، هرچند مالک هر
Command و جدول همچنان در Domain خودش باقی بماند.
از نظر Event shape نیز ۱۱۴۰ Trigger تک‌رویدادی Cursor-based هستند: ۳۷۶ Delete،
۳۸۲ Update و ۳۸۲ Insert. فقط دو Trigger بدون Cursor هر سه Event را پوشش می‌دهند؛
پس Harness مقصد باید multi-row و multi-event را مستقل از مسیر عادی یک‌ردیفی
آزمایش کند.
## تکمیل ۲۰۲۶-۰۸-۲۹ — NGT Owner Scope

- Headerها زنجیرهٔ `DataOwnerCenterKey → DataOwnerKey → OwnerKey` دارند و با
  `Guid.Parse` خوانده می‌شوند؛ fallback کامل سه‌سطحی در Snapshot Hierarchy معتبر
  نمی‌سازد، ولی یک DataOwner و مرکز پیش‌فرضش Key مشترک دارند.
- Guard مجوز فقط `OwnerKey` را می‌خواند؛ سازندهٔ تک‌پارامتری همان Key را سه بار
  در AuthorizationDomain پخش می‌کند.
- Direct/Group permission از `GetQuery` خام استفاده می‌کنند. فیلتر Owner در API
  جداگانهٔ `GetQueryByOwner/CalcExtraPredict` است و Application/Data/Center و
  Removed policy را ترکیب می‌کند.
- Clone یک Application/ApplicationOwner/DataOwner، دو Center، ۸۰۷ Principal،
  ۷۸۶ User، هشت Group و ۵۹ Membership دارد. هر ۳۲۴ Grant مؤثر در Application
  Principal خودش است؛ Cross-Application مؤثر صفر است.
- ۵۸ Membership Scope گروه دارند و با Scope پیش‌فرض User متفاوت‌اند؛ یک
  Membership یتیم است. هر دو Center `IsActive=0/IsRemoved=0` هستند ولی همهٔ
  User/Group/Membershipها به آن‌ها ارجاع دارند.
- نتیجه برای مقصد: Permission قابلیت، Owner hierarchy، Data scope و Group scope
  باید یک تصمیم Deny-first واحد، Constraint ضد Cross-Application و Audit نسخه‌دار
  داشته باشند. این مرز با `R-059` باز است و رخداد جاری ادعا نشده است.

## تکمیل ۲۰۲۶-۰۸-۲۹ — تاریخچه سفارش NGT و Target مفقود

- از ۱٬۱۱۸٬۲۴۴ History نوع ۱، تعداد ۱٬۱۱۲٬۷۱۱ با UUID و Ref به همان سفارش
  جاری می‌رسند و ۵٬۵۳۳ مورد با هیچ‌کدام از دو کلید هدفی ندارند؛ حالت تک‌کلیدی و
  تعارض UUID/Ref صفر است.
- این جمعیت ۱٬۰۲۴ جفت هدف مفقود و ۱٬۰۲۲ والد را پوشش می‌دهد. ۱٬۰۲۱ والد همهٔ
  اهدافشان مفقود است و یک والد شانزده‌خطی، پانزده هدف موجود و یک هدف مفقود دارد.
- خطوط و والدها فعال، والدها uncanceled و بدون History فروش Type=8 هستند؛ Crosswalk
  خط با History برابر است. در June–August 2026 نیز ۶۳۴ خط و ۱۱۴ والد دیده می‌شود.
- Unique index فیلترشده Type=1 جلوی History تکراری هر خط را می‌گیرد، ولی وجود
  Target خارجی را تضمین نمی‌کند. IL نیز Replication را پیش از Transaction و سه
  setter سفارش، با Commit در دو سوی write-back نشان می‌دهد.
- `R-069` Critical رجیستر را به ۶۹ ریسک (۴۰ بحرانی)، ۲۷۱ اتصال و صفر
  Command-ready رساند. علت حذف/فقدان ثابت نشده و هیچ recreate خودکاری مجاز نیست.

## تکمیل ۲۰۲۶-۰۸-۲۹ — مسیرهای حذف Target سفارش

- از ۴۰۴ ماژول SQL مرتبط با `SLE.tblOrderHdr`، چهار Procedure حذف مستقیم ایستا
  دارند. فقط `NGT_RollBackTour` به `TourHistory` هم اشاره می‌کند؛ سه مسیر دیگر
  History، خط NGT و Crosswalk سفارش را نمی‌شناسند.
- سه Trigger فعال DELETE هیچ History/Crosswalk NGT را اصلاح نمی‌کنند؛ یکی فقط
  `InsertToLog` عمومی دارد. جدول Non-temporal است و CDC/Change Tracking ندارد.
- دوازده FK فعال و untrusted به Header وصل‌اند: یازده NO_ACTION و یک CASCADE.
  تنها Caller کاتالوگی مستقیم، `usp_sdsnet_Order_Save → usp_sdsnet_Order_Delete`
  است و این نبود Caller، مسیر Application/Dynamic را رد نمی‌کند.
- `R-070` High رجیستر را به ۷۰ ریسک (۴۰ بحرانی، ۲۷ بالا)، ۲۷۵ اتصال و صفر
  Command-ready رساند. نسبت علّی با ۵٬۵۳۳ Target مفقود هنوز ثابت نشده است.

## تکمیل ۲۰۲۶-۰۸-۲۹ — اثبات حذف Targetهای مفقود با Log

- هر ۱٬۰۲۴ Target مفقود Type=1 دقیقاً یک `GNR.tblLog DELETE` با همان OperationId
  دارد؛ صفر Target بدون Log و هر ۵٬۵۳۳ History خط پوشش داده شده‌اند.
- تمام حذف‌ها بعد از آخرین History همان Target هستند: ۲۹۸ همان روز، ۵۳۴ طی ۱–۷
  روز، ۱۹۲ طی ۸–۳۰ روز و صفر بیش از ۳۰ روز؛ بیشینه ۳۵٬۷۸۳ دقیقه است.
- از ۱٬۹۰۷ Delete log باقی‌مانده Header سفارش، همه ID متمایز و اکنون غایب‌اند؛
  ۱٬۰۲۴ مربوط به Type=1 مفقود و ۸۸۳ حذف دیگرند. ۱۱۵ Target در سه ماه اخیر حذف
  شده‌اند.
- metadata به‌صورت ناشناس ۲۳ App، یک DB user، ۲۵ Host، ۴۶۶ Session و ۳۹ جفت
  App/Host دارد؛ نام‌ها ذخیره نشدند و منبع اجرایی واحد اثبات نشد.
- `R-069/R-070` اصلاح شدند: حذف پس از Replication قطعی است، ولی Procedure، علت
  تجاری و مجوز recreate هنوز اثبات نشده است. شمار ریسک‌ها تغییر نکرد.
- هر ۱٬۰۲۴ حذف tail یکسان Item→Visit→Header دارد؛ ۱٬۰۰۸ Visit دقیقاً Log قبلی
  است. این ترتیب Rollback موفق NGT و UndoUserExtraInfo را رد می‌کند و با
  `usp_sdsnet_Order_Delete` و tail ConfirmFreeInvoice سازگار است.
- SaleHeader DELETE قبلی صفر است؛ بنابراین Order_Delete قوی‌ترین نامزد ایستا/لاگ
  است، نه attribution قطعی. ۵۲۴ Target/۵۲۲ والد FreeInvoice هستند، اما Flag
  به‌تنهایی Procedure را تعیین نمی‌کند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — اعمال و اعمال‌مجدد هزینهٔ فاکتور تأمین‌کننده

- پنج Procedure اصلی Apply/ReApply فاکتور تأمین‌کننده تراکنش محلی صریح ندارند؛
  Apply قیمت آیتم حواله را Delete/Insert می‌کند و FastApply پس از آن Status را
  یک می‌کند.
- ReApply پیش از حلقهٔ FastApply، Status و ConfirmDate فاکتورهای منتخب را تغییر
  می‌دهد. این ترتیب پنجرهٔ خرابی ساختاری است، نه شاهد Incident جاری.
- Snapshot جاری دقیقاً سازگار است: ۳٬۲۸۵ فاکتور Applied و ۲۹٬۰۷۸ آیتم همگی
  قیمت دارند؛ ۱۴۱ فاکتور Unapplied و ۱٬۳۵۴ آیتم هیچ قیمت ندارند.
- ۹۵ Price row یتیم و نبود FK مستقیم Price→VoucherItem ثبت شد، اما علت آن‌ها به
  Apply/ReApply نسبت داده نشد.
- IL هش‌سنجی‌شدهٔ چهار Method نشان داد ReApply با DataContext.Query و بدون
  BeginTransaction/Commit صریح در مسیر منتخب می‌رسد؛ Apply جداگانه Commit پس از
  Adapter دارد. Constructor semantics و Branch reachability ادعا نشد.
- `R-071` Critical رجیستر را به ۷۱ ریسک (۴۱ بحرانی، ۲۷ بالا)، ۲۷۹ اتصال و صفر
  Command-ready رساند. مقصد باید Attempt نسخه‌دار، State machine، یک Transaction
  owner، Audit/Outbox و Fault-injection برای هر مرز بازسازی قیمت داشته باشد.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Unapply، حذف فاکتور خرید و برگشت هزینه

- هشت SQL module سه قرارداد تراکنشی متفاوت دارند. Unlink بدون تراکنش محلی، کل
  Header را Status=0/ConfirmDate=NULL می‌کند و سپس Price/UnitPrice آیتم‌های
  Voucher انتخاب‌شده را صفر می‌کند.
- ۱۷ Invoice Unapplied و ۱۹۲ Invoice Applied چندرسیدی‌اند؛ پس Grain Header و
  Voucher باید در مقصد به یک Connected Component صریح تبدیل شود.
- Log رابطه ۳٬۹۰۲ Insert و ۲۱۳ Delete، شامل ۱۵ Delete سه‌ماهه، دارد. آخرین Event
  همهٔ ۳٬۶۸۹ Relation جاری و ۲۰۳ Relation غایب را دقیق توضیح می‌دهد؛ علت و عامل
  حذف از این شاهد معلوم نیست.
- سه جدول Header/Relation/Price Non-temporal و بدون CDC/Change Tracking هستند؛
  فقط Relation Triggerهای lifecycle دارد و تغییر Status/Price Audit متناظر ندارد.
- IL چهار Method/۳۶۹ Instruction نشان داد مسیر Managed رابطه را Save، Operation
  code=3 را Execute و سپس Commit می‌کند؛ Mutation دقیق SaveCommand و Physical
  transaction همهٔ Branchها هنوز اثبات نشده است.
- Snapshot جاری clean است و ۸۳ Zero-price row به Unlink نسبت داده نشد. `R-072`
  High رجیستر را به ۷۲ ریسک (۴۱ بحرانی/۲۸ بالا/۳ متوسط)، ۲۸۳ اتصال و صفر
  Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Undo تخریبی تاریخچهٔ چک پرداختنی

- `DoPCheque_DeleteLastPChequeHistory` پس از کنترل وابستگی سند، آخرین History را
  در تراکنش حذف می‌کند، Pointer جاری و وضعیت مصرف برگ دسته‌چک را عقب می‌برد و
  History جبرانی نمی‌سازد. مسیر Add در مقابل append-first است.
- ۱٬۶۶۸ Delete در Log مانده است: ۱٬۵۳۷ مورد tail دقیق Undo، شامل هر ۷۸ Delete
  سه‌ماهه؛ ۱۱۷ مورد همراه حذف خود چک و ۱۴ مورد partial tail جدا طبقه‌بندی شدند.
- ۴٬۶۷۲ چک و ۱۳٬۱۰۸ History جاری، Pointer و Parent کاملاً سازگار دارند؛ Snapshot
  سالم به معنی کامل‌بودن Audit حذف‌شده نیست.
- از ۱۵٬۱۷۸ History لاگ‌شده، ۴۰۲ ID غایب بدون Delete retained همگی در یک Batch
  تاریخی ۲۰۲۴-۰۳-۲۷ هستند. این Batch به Undo، Migration یا Trigger bypass نسبت
  داده نشد و هیچ مورد سه‌ماهه ندارد.
- IL هش‌سنجی‌شدهٔ پنج Method نشان داد فرم Legacy پیش از Delete تراکنش می‌گیرد و
  Adapter نیز Transaction تو‌در‌تو دارد؛ Undo فرم New یک Instruction stub است.
  انتخاب Runtime فرم و reachability شاخهٔ Reapprove هنوز اثبات نشده است.
- `R-073` High رجیستر را به ۷۳ ریسک (۴۱ بحرانی/۲۹ بالا/۳ متوسط)، ۲۸۷ اتصال و
  صفر Command-ready رساند. مقصد باید Undo را Event جبرانی append-only با
  ExpectedVersion، Idempotency و یک Transaction برای Projection/Leaf/Ledger/Outbox
  پیاده کند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Undo تخریبی چک دریافتی و Projection تریگری

- Undo پس از Validation و داخل Transaction رخداد جاری را Delete می‌کند؛ در
  حالت PreviousStatRef=8 و Status جاری ۱، رخداد وضعیت ۸ قبلی را نیز حذف می‌کند.
  هیچ Event جبرانی ساخته نمی‌شود.
- Trigger حذف، History قبلی را `IsLast=1` و Trigger درج، رخداد قبلی را
  `IsLast=0` می‌کند. پس Current state یک Projection مبتنی بر Trigger است.
- ۱۴٬۷۱۱ Delete retained وجود دارد. ۱٬۵۰۲ فرمان tail دقیق Undo دارند؛ ۲۲ فرمان
  دوحذفی‌اند، پس ۱٬۵۲۴ History حذف‌شده به این نامزدها نسبت داده می‌شود. سه‌ماهه
  شامل ۴۷۱ فرمان و ۴۷۵ ردیف حذف‌شده است.
- ۲۳٬۸۲۲ چک و ۱۰۶٬۱۳۱ History جاری دقیقاً یک IsLast=max دارند و chain mismatch
  صفر است؛ این Snapshot سالم، Audit حذف‌شده را بازیابی نمی‌کند.
- ۲۵۲ History غایب بدون Delete retained در بازه تاریخی ۲۰۲۴-۰۳-۲۷ تا ۲۸ هستند
  و به Undo، Migration یا Trigger bypass نسبت داده نشدند.
- IL شش Method/۷۰۰ Instruction نشان داد هر دو فرم Legacy/New Wrapper
  `DeleteCessionToOther` را زیر Transaction صدا می‌زنند؛ Wrapper و Direct adapter
  هر دو Transaction تو‌در‌تو دارند. انتخاب Runtime فرم/Branch ثابت نشد.
- `R-074` High رجیستر را به ۷۴ ریسک (۴۱ بحرانی/۳۰ بالا/۳ متوسط)، ۲۹۱ اتصال و
  صفر Command-ready رساند. مقصد به Event جبرانی append-only و collapse صریح
  وضعیت گذرای ۸ نیاز دارد.

## تکمیل ۲۰۲۶-۰۸-۲۹ — حذف خود چک دریافتی و پاک‌سازی رسید

- هفت مسیر SQL حذف مستقیم Master چک دارند. `uspCHQDelete` تاریخچه و Master را
  داخل Transaction حذف می‌کند؛ `usp_sdsnet_Receipt_Save` شاخهٔ کامل
  History→Master→Receipt دارد؛ Trigger حذف View فقط Master را مستقیم می‌زند.
- ۳۱ Master DELETE retained وجود دارد که همگی اکنون غایب و با Log خود سازگارند؛
  ۱۱ مورد سه‌ماهه است. هر ۳۱ مورد History-delete lookback همان Session دارند.
- ۲۳ Master و ۲۳ History در ۱۹ Receipt-delete batch هستند؛ هفت Master tail
  به Receipt UPDATE و یک مورد اخیر tail جداافتاده دارد. این Shapeها Procedure،
  کاربر یا علت تجاری را قطعی نمی‌کنند.
- از ۲٬۳۵۱ Receipt DELETE retained، تعداد ۲۳۸ مورد سه‌ماهه است و فقط پنج Batch
  سه‌ماهه شامل پاک‌سازی Master چک بوده‌اند.
- پنج جدول اصلی Non-temporal و بدون CDC/Change Tracking هستند. FKها ترکیبی از
  NO_ACTION/CASCADE‌اند و حذف Master، `tblRChequeLog` را Cascade می‌کند.
- IL فرم Legacy ترتیب Confirmation→DataRow.Delete→RCheque.Update را بدون
  Transaction صریح در Method نشان می‌دهد؛ Method منتخب فرم New فقط Confirmation
  دارد. انتخاب Runtime فرم و Reachability دقیق Trigger اثبات نشده است.
- `R-075` High رجیستر را به ۷۵ ریسک (۴۱ بحرانی/۳۱ بالا/۳ متوسط)، ۲۹۵ اتصال و
  صفر Command-ready رساند. مقصد باید DeleteCheque، DeleteReceipt و Tombstoneهای
  مهاجرتی سه Shape را مستقل نگه دارد.

## تکمیل ۲۰۲۶-۰۸-۲۹ — ماشین حالت سند انبار و Projection موجودی

- Confirm قبل از Transaction اعتبارسنجی و برای هر سند Transaction/Savepoint
  می‌سازد؛ در نبود Transaction محیطی، Commit متن Procedure پیش از After hook
  قرار دارد. `Vocher_Save` می‌تواند همین مسیر را داخل Transaction بیرونی بپیچد.
- Unconfirm نیز Validation پیش‌تراکنشی دارد، اما Cleanup جزئیات/آیتم/Header
  پیوندخوردهٔ نوع ۱۵، After hook و Rollback را زیر Transaction خودش انجام می‌دهد.
- Triggerهای Header/Item مالک Projection به `StockGoods` هستند و هم bypass
  Replication، هم `XACT_ABORT OFF` و هم skip برای انواع ویژه دارند.
- Log retained شامل ۷۵٬۵۶۹ Confirm، ۱۳٬۰۲۱ Unconfirm و ۲۷٬۴۵۰ Delete است؛
  سه‌ماهه به‌ترتیب ۸٬۸۲۲، ۱٬۷۷۱ و ۳٬۲۰۰ رخداد دارد. تمام Deleteها یا پس از
  Unconfirm (۱۰٬۴۵۸) یا never-confirmed (۱۶٬۹۹۲) هستند؛ direct confirmed delete
  صفر است.
- Snapshot فعلی ۹۶٬۵۰۲ سند شامل ۹۶٬۴۹۵ تأییدشده و هفت تأییدنشده دارد. ۱۵
  insert-only absent historical مربوط به March 2024 و صفر مورد سه‌ماهه جدا
  قرنطینه شد.
- IL دو Assembly و ۱۲ Method/۵۹۶ Instruction را فقط ایستا خواند: Adapterها
  Procedure نام‌دار+Commit دارند، ولی `MainConfirmVocher` Writer از مسیر Dynamic
  update+DataContext.Commit می‌رود. Callsite/branch و Physical enlistment ثابت نشد.
- مقایسهٔ ناقص Cardex-only تعداد ۱٬۵۹۴ difference دارد، اما فرمول رسمی آن‌ها را
  دقیقاً تعهد فروش باز می‌شناسد و Residual نهایی صفر است؛ هیچ mismatch جاری به
  Confirm/Unconfirm نسبت داده نشد. `R-076` Critical ثبت شد و رجیستر را به
  ۷۶ ریسک (۴۲ بحرانی/۳۱ بالا/۳ متوسط)، ۳۰۰ اتصال و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — After validation و Failure semantics موجودی

- Confirm مستقیمِ بدون Ambient transaction، Header را پیش از
  `AfterInvVocherHdr` Commit می‌کند. AfterMsg فقط به MsgErr append می‌شود و Guard
  توقف ندارد. Unconfirm After را پیش از Commit اجرا می‌کند، ولی پیام آن نیز Commit
  را متوقف نمی‌کند.
- After هیچ Transaction/RAISERROR/THROW ندارد، ۹ `NOLOCK` دارد و چهار Validator
  را صدا می‌زند. Update وضعیت Batch نوع ۲۰ پیش از Validation رخ می‌دهد.
- چک‌های عمومی OnHand/Cardex برای انواع ۱۲ و ۱۳ skip می‌شوند؛ Cardex فقط در حالت
  confirmed بررسی می‌شود و generated type-15 از Cursor After مسیر Confirm خارج است.
- Matrix کاردکس ۵۰ Rule/۳۰ نوع سند دارد: ۲۷ مثبت، ۲۲ منفی، یک صفر؛ ۲۹ اثر
  OnHand، ۱۵ Damaged و چهار Reserved.
- سه Trigger Projection/Guard فعال‌اند. Guard منفی set-based است، ولی قابلیت
  bypass با Session context و Replication دارد؛ وقوع bypass ادعا نشد.
- Snapshot ۶۷٬۱۶۱ StockGoods، صفر مؤلفهٔ منفی و صفر StockGoodsDetail دارد؛
  فرمول رسمی نیز Residual صفر است. `R-077` Critical رجیستر را به ۷۷ ریسک
  (۴۳ بحرانی/۳۱ بالا/۳ متوسط)، ۳۰۵ اتصال و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — چرخهٔ صدور، لغو و حذف خروج توزیع

- Snapshot شامل ۳۳٬۹۴۵ خروج است: ۲۴٬۰۳۵ فعال و ۹٬۹۱۰ لغوشده. هر خروج فعال
  دقیقاً یک سند انبار نوع ۶۰ دارد و Duplicate یا خروج فعال بدون سند صفر است.
- هر ۹٬۹۱۰ لغو، Delete متناظر سند نوع ۶۰ و صفر Sale link باقی‌مانده دارد؛
  ۹٬۸۹۵ مورد در پنج ثانیه و تمام ۱٬۴۴۲ لغو اخیر نیز در پنج ثانیه جفت شده‌اند.
- Create بدون Transaction/Savepoint محلی، Exit، Sale link، Voucher نوع ۶۰، Item
  و History را پیش از Cardex check می‌نویسد. Remove نیز بدون BEGIN/COMMIT محلی،
  Voucher graph را حذف، Sale را unlink، Exit را soft-cancel و Dist را reset می‌کند.
- سه Procedure جدا توان حذف فیزیکی `tblExit` دارند و فقط مسیر VSA تراکنش محلی
  دارد. Triggerهای حذف فعلی فعال ولی replication-bypassable هستند.
- لاگ ۳۳٬۹۵۳ شناسه دارد؛ هشت خروج و شش توزیع تاریخیِ March 2024 دیگر موجود
  نیستند و پیش از Trigger حذف فعلی‌اند. مورد اخیر و chain break جاری صفر است؛
  هیچ attribution به Procedure/actor ساخته نشد.
- IL سه Assembly هم‌هش و ۱۱ Method/۱٬۲۰۱ Instruction نشان داد UI عادی صدور و
  لغو Context+Commit دارد، اما Business Adapter تازه می‌سازد و enlistment فیزیکی
  Contextهای تو‌در‌تو اثبات نشد. Merge نیز Commit صریح در UI/Adapter منتخب ندارد.
- `R-078` Critical رجیستر را به ۷۸ ریسک (۴۴ بحرانی/۳۱ بالا/۳ متوسط)، ۳۱۰ اتصال
  و صفر Command-ready رساند. رخداد partial issue/cancel/delete جاری ادعا نشد.

## تکمیل ۲۰۲۶-۰۸-۲۹ — تبدیل سفارش به فروش و Projection وضعیت

- Orchestrator تبدیل تراکنش/Try/Catch/Commit/Rollback و شاخهٔ `WithOutRollback`
  دارد، ولی Core سازندهٔ Header/Item تراکنش محلی ندارد. Pointer سفارش، Timing،
  Payment، Batch، ReservedPrize و ItemDetail نیز در همان دامنه تغییر می‌کنند.
- Triggerها جداگانه Detail وضعیت، حذف Payment هنگام لغو و اثر StockGoods را
  مالک‌اند؛ Trigger حذف Replication فعال و bypassable است.
- IL سه Assembly و پنج Method/۱٬۰۵۵ Instruction نشان داد UI فقط delegate می‌کند،
  Business Context+Commit و Adapter نیز Context+Execute+Commit جدا دارد. یک
  overload دیگر Core قدیمی را بدون Commit محلی Query می‌کند؛ overload/branch و
  enlistment فیزیکی مشترک اثبات نشد.
- ۲۷۵٬۹۹۵ Sale شامل ۲۱۴٬۹۷۳ فعال و ۶۱٬۰۲۲ لغوشده است. ۱۸٬۰۰۹ Order چند attempt
  دارند، ولی multiple-active، Pointer dangling و reverse mismatch صفر است.
- از ۲۶٬۶۲۴ اختلاف خام Header/Detail، تعداد ۲۶٬۶۱۸ شکل طبیعی cancellation است؛
  فقط شش active mismatch و سه terminal exception لغوشده، همگی غیرسه‌ماهه، ماند.
- Timing ledger کامل نیست: ۹٬۸۰۹ Order دارای Sale بدون Timing و ۹ Timing بدون Sale.
  Audit شامل ۶۴۰ حذف فیزیکی (۱۱۲ سه‌ماهه) و ۱۸ absent بدون Delete retained، همگی
  غیرسه‌ماهه است؛ هیچ attribution قطعی به Procedure ساخته نشد.
- `R-079` Critical رجیستر را به ۷۹ ریسک (۴۵ بحرانی/۳۱ بالا/۳ متوسط)، ۳۱۶ اتصال
  و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — لغو فروش و پیوند پرداخت/سفارش/خروج

- Procedure لغو تراکنش/Try/Catch/Commit/Rollback محلی دارد و Sale، Order،
  Payment و Detail را مستقیم تغییر می‌دهد؛ dependency مستقیم Exit/Distribution ندارد.
- Triggerهای فعال حذف Payment مستقیم، ثبت Detail پایانی، تغییر Order/Sale و
  Projection موجودی را انجام می‌دهند؛ بنابراین Flag تنها قرارداد لغو نیست.
- ۶۱٬۰۲۲ فروش لغوشده، صفر Payment مستقیم باقی‌مانده، ۳۴٬۴۰۱ پیوند Exit/Dist
  فعال و ۳۴٬۶۳۰ Pointer منتخب Order دارد؛ ۳۴٬۳۹۷ مورد از Orderها فعال‌اند.
- تمام پیوندهای Exit/Dist در گروه Status=3 قرار دارند. این Shape به‌عنوان Rule
  مهاجرت ثبت شد و خرابی یا علت تجاری برای آن ادعا نشد.
- Terminal Detail شامل ۲۶٬۶۱۲ وضعیت ۰، تعداد ۳۴٬۴۰۷ وضعیت ۳ و سه استثنای تاریخی
  است؛ استثنای اخیر صفر است.
- IL سه Assembly و چهار Method/۳۹۰ Instruction نشان داد UI دلیل لغو را می‌گیرد،
  Business delegate باریک است و Adapter Context+Execute بدون Commit/RollBack
  صریح دارد؛ تراکنش محلی SQL مالک اثبات‌شده و enlistment فیزیکی نامعلوم است.
- `R-080` Critical رجیستر را به ۸۰ ریسک (۴۶ بحرانی/۳۱ بالا/۳ متوسط)، ۳۲۲ اتصال
  و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — صدور و لغو برگشت از فروش

- ۱۳٬۹۱۳ برگشت فعال دقیقاً یک Voucher نوع ۱۰ تأییدشده دارند؛ ۱۷۸ لغو هیچ
  Voucher جاری یا Payment ندارند. دو لغو در پنجرهٔ سه‌ماهه است.
- هر ۱۷۸ لغو `VocherFlag=1` را نگه داشته‌اند؛ این Flag تاریخچهٔ صدور است، نه
  اثبات وجود Projection جاری.
- Save، Generate و CancelVoucher هرکدام مالکیت تراکنش/Savepoint متفاوت دارند.
  Generate پس از Insert نیز Validator دارد و CancelVoucher هم Delete و هم Insert
  در Voucher graph انجام می‌دهد.
- CancelHeader بدون تراکنش محلی Flag را Update و PayWithPayment relation را حذف
  می‌کند؛ AfterSave نیز بدون تراکنش محلی Rollback signal دارد.
- IL سه Assembly و پنج Method/۴۰۴ Instruction: UI و Business delegate، Generate
  Adapter Query بدون Commit، و Cancel Adapter Context+Commit بدون RollBack صریح.
- Audit همهٔ ۱۴٬۰۹۱ Header را پوشش می‌دهد و Delete/Absent صفر است؛ سه مسیر حذف
  مستقیم فقط capability هستند. `R-081` Critical رجیستر را به ۸۱ ریسک
  (۴۷ بحرانی/۳۱ بالا/۳ متوسط)، ۳۲۸ اتصال و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Snapshot ووچر فروش و تبدیل معکوس

- ۲۶۶٬۱۸۳ فروش دارای شمارهٔ ووچر دقیقاً ۲۶۶٬۱۸۳ Snapshot دارند؛ mismatch شماره،
  duplicate و orphan Header/Item صفر است. Snapshot شامل ۲٬۱۲۸٬۲۵۳ Item است.
- ۶۰٬۶۹۸ فروش لغوشده Snapshot تاریخی را حفظ کرده‌اند؛ پس لغو Sale معادل حذف
  Snapshot نیست. ۳۲۴ لغو وضعیت ۱ شکل متفاوت و بدون Snapshot دارند.
- ۱۱٬۷۵۰ فروش فعال نهایی، شامل ۱٬۵۳۷ مورد سه‌ماهه، Amount جاری متفاوت از Amount
  Snapshot دارند. این اختلاف فقط stage/version semantics است تا Rule رسمی خلافش
  را ثابت کند و corruption نام‌گذاری نشد.
- FillSaleVocher graph را بدون Transaction محلی می‌سازد و Orchestrator تبدیل
  سفارش مالک تراکنش است. ConvertSaleToVocher مسیر معکوس چندAggregate با تراکنش
  محلی است؛ Rollback تخفیف Snapshot نیز خود تراکنش محلی ندارد.
- IL سه Assembly/چهار Method/۲۴۳ Instruction نشان داد UI delegate، Business
  context+validation و Adapter context+named query دارند، اما Commit/RollBack
  مدیریت‌شدهٔ صریح ندارند؛ مالک قطعی SQL و enlistment فیزیکی نامعلوم است.
- Audit تعداد ۱۸ absent تاریخی و صفر absent اخیر/Delete retained دارد. یک مسیر
  حذف مستقیم فقط capability است. `R-082` Critical رجیستر را به ۸۲ ریسک
  (۴۸ بحرانی/۳۱ بالا/۳ متوسط)، ۳۳۴ اتصال و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Watermark حسابداری فروش و Crosswalk دفترکل

- ۲۰۲٬۶۳۶ فروش فعال نهایی به ۶۲۵٬۸۳۹ خط متوازن PreVoucher، تعداد ۱۰۱٬۶۴۹
  Batch و دقیقاً یک Journal فعال در هر Source link می‌رسند؛ orphan/duplicate و
  source نامتوازن صفر است.
- ۱۰٬۱۲۳ فروش فعال نهایی هنوز Source حسابداری ندارند: ۱۰٬۱۲۲ مورد دقیقاً کل
  ماه باز ۱۴۰۵/۰۵ و فقط یک مورد در ۱۴۰۳/۰۱ است. ماه‌های ۱۴۰۵/۰۳ و ۱۴۰۵/۰۴
  پوشش کامل دارند؛ cohort ماه باز incident نام‌گذاری نشد.
- Snapshot و Accounting دو محور مستقل‌اند: ۹٬۰۰۸ فروش Accounting بدون Snapshot،
  ۹٬۶۴۳ Snapshot بدون Accounting، ۴۸۰ هیچ‌کدام و ۱۹۳٬۶۲۸ هر دو را دارند.
- Creator مستقیم SaleHdr/SaleItm غیرلغوشده و شماره‌دار را با NOLOCK می‌خواند و
  به SaleVocher وابسته نیست. صفر Source لغوشده فقط Eligibility جاری است، نه
  اثبات عدم صدور/برگشت تاریخی.
- ۳۷۰ Batch تاریخی چندSource با ۱۰۱٬۳۵۷ تخصیص و بیشینهٔ ۱٬۱۳۱ Source وجود دارد.
  همچنین ۱۷۵٬۰۴۲ Source متوازن جمع Debit متفاوت از Sale amount دارند؛ هیچ‌یک
  mismatch تلقی نشد و Rule-level parity لازم است.
- `R-083` Critical رجیستر را به ۸۳ ریسک (۴۹ بحرانی/۳۱ بالا/۳ متوسط)، ۳۳۸ اتصال
  و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Template فاکتور و Audit چاپ فیزیکی

- IL سه Assembly/نه Method/۱٬۰۱۱ Instruction نشان داد فرم نام فایل تنظیم‌شده را
  به Crystal می‌دهد؛ Engine Template را Load، Parameterها را Set و Connection
  جاری را روی Table/Subreport اعمال می‌کند. Query/Formula واقعی داخل فایل است.
- شش Template فاکتور با یک Default تنظیم شده‌اند، اما Hash نام هیچ‌کدام در ۸۸
  فایل Report/Rep/CustomReps اسکن‌شده نبود. Runtime failure ادعا نشد؛ مسیر Cache/
  Current directory دیگری ممکن است، ولی Result parity هنوز مسدود است.
- پس از PrintedCompleted، Business برای هر Sale رخداد DocType=2 را در یک Context
  Save و Commit می‌کند؛ Preview و Audit یک عملیات نیستند. RollBack صریح دیده نشد.
- ۳۰۸٬۴۳۲ رخداد چاپ فروش روی ۱۴۴٬۸۴۷ Sale وجود دارد؛ ۳۴٬۸۴۰ Sale تکرار چاپ و
  بیشینه ۲۶ چاپ دارند. ۶۸ هویت چاپ‌شده Sale جاری ندارند، بدون attribution.
- ۱۴۳ رخداد روی ۴۵ Sale اکنون لغوشده بعد از terminal time است؛ فقط دو مورد اخیر.
  unauthorized نام‌گذاری نشد و نیازمند policy صریح VOID/archive است.
- GetList sibling در KindPrint=0 upper bound را با lower bound جایگزین می‌کند؛
  Procedure جایگزین hard-coded نیز بدون caller/literal مستقر فقط capability است.
- `R-084` Critical رجیستر را به ۸۴ ریسک (۵۰ بحرانی/۳۱ بالا/۳ متوسط)، ۳۴۳ اتصال
  و صفر Command-ready رساند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — ماتریس Outcome، پیام و Commit

- ۱۲ Artifact قبلی بدون اتصال تازه به دیتابیس در یک ماتریس مشترک بازپخش شد:
  ۱۰ مسیر فرمان، شش دامنه و ۱۰ کلاس رفتار متفاوت.
- شش مسیر از Message/Result در کنترل شکست استفاده می‌کنند، اما معنای تراکنشی
  آن‌ها یکسان نیست: خطای پیش از Write با Commit، Result ردشده پس از Cleanup،
  پیام Post-commit، پیام Pre-commit بدون Abort و پیام Caller-blocking همگی وجود دارند.
- سه مسیر مالک تراکنش فیزیکی اثبات‌نشده دارند؛ وجود Context یا Commit در چند
  لایه، اشتراک Connection/Transaction را ثابت نمی‌کند.
- لغو فروش یک نمونهٔ مالکیت روشن SQL است؛ ثبت چاپ یک نمونهٔ Partial-success
  طبیعی است که اثر چاپ و Audit آن دو Commit/Outcome مستقل دارند.
- قرارداد مقصد تثبیت شد: `ACCEPTED`، `ACCEPTED_WITH_WARNING`، `REJECTED`،
  `PARTIAL_SUCCESS` و `UNKNOWN` تایپ مستقل‌اند؛ متن نمایش هیچ‌گاه کنترل
  Transaction نیست و فقط دو Outcome پذیرفته‌شده می‌توانند state را جلو ببرند.
- این مرحله ریسک تکراری تازه نساخت؛ هشت ریسک موجود `R-046/R-048/R-077..R-081/
  R-084` را به یک قرارداد cross-domain متصل و قابل‌آزمون کرد. رجیستر همان
  ۸۴ ریسک/۳۴۳ اتصال/صفر Command-ready باقی ماند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Idempotency، Retry و Storage guard

- Signature و Catalog ده فرمان پراثر بررسی شد: هیچ‌کدام `CommandId/RequestId/
  IdempotencyKey` ندارند و شش فرمان شناسهٔ تازه تخصیص می‌دهند.
- هفت جدول هدف مقایسه شد؛ پنج جدول حداقل یک Unique guard معنایی دارند. Guard
  ذخیره‌سازی بخشی از Projection را حفظ می‌کند، اما Receipt و نتیجهٔ نخستین
  فرمان را به Retry برنمی‌گرداند.
- SaleHdr هیچ Unique معنایی برای یک Sale فعال به‌ازای OrderRef ندارد؛ Snapshot
  ۲۱۴٬۹۷۳ گروه فعال و صفر چند-active دارد. سلامت جاری به معنی ایمنی concurrency
  یا crash-after-commit نیست.
- برگشت فروش، خروج فعال، Voucher نوع ۱۰ و امضای خط PreVoucher Guard دارند و
  duplicate جاری‌شان صفر است. cohort فعال RetOrderRef در Snapshot صفر است؛ آن
  Constraint با دادهٔ جاری runtime exercise نشده است.
- PrintedDoc عمداً تکرار را می‌پذیرد: ۵۵٬۷۹۲ گروه repeated و بیشینه ۸۸ رخداد.
  بدون Attempt identity، Retry چاپ از Reprint مجاز قابل تفکیک نیست.
- TourHistory فقط یک Type را Unique می‌کند؛ نوع فروش ۱۳۸ و نوع پرداخت ۷۰ گروه
  duplicate دارد. این شکل ضعف Receipt است، نه اثبات تکرار همهٔ اثرهای مالی.
- Artifact تازه به شواهد `R-006` افزوده شد، بدون ساخت Risk جدید یا تغییر شمارش:
  ۸۴ ریسک، ۵۰ بحرانی، ۳۴۳ اتصال و صفر Command-ready.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Policy Override و تبدیل جزئی سفارش به فروش

- ده ورودی Policy در Wrapper و هشت ورودی مشترک در Core به‌صورت فقط‌خواندنی
  تحلیل شد. این ورودی‌ها Booleanهای هم‌معنی نیستند و قراردادهای متفاوت دارند.
- `chkNotStock=1` اقلام کسری را از مجموعهٔ موقت تبدیل حذف می‌کند؛ اگر قلمی باقی
  بماند تبدیل جزئی ادامه می‌یابد و اگر همه حذف شوند فرمان رد می‌شود.
- `chkNotCPrice=1` Check قیمت قراردادی و `chkNotPrice=1` فقط Check مشروط UserPrice
  را رد می‌کند؛ Check مستقل OrderItemPrice همچنان پیش از Branch اجرا می‌شود.
- اعتبار مشتری/عامل فقط با زوج فلگ `(1,1)` کاملاً bypass می‌شود؛ در سایر ترکیب‌ها
  SQL مقادیر Caller را با تنظیمات DC بازنویسی و Validator را طبق Policy مرکز اجرا
  می‌کند. فلگ سقف ۱ نیز Check سقف مشتری را رد می‌کند.
- `IgnoreValidateExpDate` در Definition فعلی Wrapper فقط declaration است؛ اثر
  Runtime آن اثبات نشد. `WithOutRollback=1` نیز فقط یک شاخهٔ XACT_STATE را guard
  می‌کند و معادل خاموش‌کردن همهٔ Rollbackها نیست.
- IL سه Assembly/نه Method نشان داد فرم گروهی Stock، چهار کنترل اعتبار و سقف را
  از UI می‌گیرد ولی دو فلگ قیمت را صفر می‌فرستد؛ Save معمولی Sale نیز دو قیمت را
  صفر و فقط Stock را از فیلد فرم می‌گیرد.
- قرارداد مقصد تثبیت شد: هیچ `chkNot*` عمومی در API، Policy resolve سمت سرور،
  Command مستقل و مجوزدار برای تبدیل جزئی، Outcome قلم‌به‌قلم و Audit نسخه‌دار.
- فرم گروهی پنج Rule اعتبار/سقف را با نگاشت `۰=Bypass قفل‌شده، ۱=قابل انتخاب،
  ۲=اجرای قفل‌شده` می‌سازد؛ موجودی نگاشت متفاوت `۰=قابل انتخاب، ۱=تبدیل جزئی
  قفل‌شده، ۲=سخت‌گیرانهٔ قفل‌شده` دارد.
- `ApplySetadPermission` در Type منتخب Permission decision ندارد و فقط Enabled
  دکمهٔ Select را از SiteType/DCRef می‌سازد؛ Authorization منو/بازشدن فرم بیرون
  این متد همچنان اثبات‌نشده است.
- Snapshot دو DC دارد: Stock در هر دو ۲ است؛ یک Profile پنج Rule اعتبار/سقف=۲ و
  Profile دیگر پنج مقدار NULL دارد. Getterهای UI Int32 غیرNullable‌اند ولی
  Materialization NULL ثابت نشد؛ SQL نیز Reload را coalesce نمی‌کند و زوج NULL
  می‌تواند Branch Validator را با UNKNOWN رد کند.
- قرارداد مقصد NULL را fail-closed یا owner-resolved می‌کند و برای هر Rule Enum
  مستقل می‌خواهد؛ Default ضمنی مشترک ممنوع شد.
- شاهد تازه `R-079` را تقویت کرد و شمارش ثابت ماند: ۸۴ ریسک، ۵۰ بحرانی، ۳۴۳
  اتصال و صفر Command-ready.

## تکمیل ۲۰۲۶-۰۸-۲۹ — تاریخ عملیات و قطعیت تبدیل سفارش به فروش

- دو مسیر گروهی سفارش، `OperationdDate_Sale` را از Session به `CreateSaleDate`
  می‌فرستند؛ هسته همان تاریخ را در قیمت، CPrice، date-open، EVC و سقف مصرف می‌کند.
- Gate دسکتاپ می‌تواند فرم تاریخ را با مجوز `VN.SDS.Sales/SetOprDate` باز کند یا
  Toolbar را ببندد. این مجوز تغییر تاریخ است، نه مجوز تبدیل سفارش.
- نگاشت positional با SQL و IL حل شد: FetchReason=2 ستون‌های `LastDate,OprDate`
  می‌دهد و خروجی دوم، یعنی OprDate، وارد Session می‌شود.
- برای نوع معمولی، دورهٔ بسته یا تاریخ `<=LastDate` رد می‌شود؛ انواع ۱۰۰۷/۱۰۰۸
  Check date-open را skip می‌کنند، ولی مصرف‌های دیگر تاریخ باقی‌اند.
- هر دو نوع ویژه پیکربندی شده‌اند، اما Order/Sale فعلی و سه‌ماههٔ آن‌ها در Clone
  صفر است؛ capability حفظ شد ولی active behavior نام‌گذاری نشد.
- نبود رکورد مرزی در Procedure منتخب رد صریح ندارد و با منطق NULL می‌تواند
  fail-open شود. Snapshot فعلی SysRef=1 سه ردیف سالانه، دو بسته و یک باز، بدون
  تاریخ خالی دارد؛ قابلیت ساختاری به‌عنوان رخداد جاری گزارش نشد.
- قرارداد مقصد: تاریخ typed و Server-side، دقیقاً یک Boundary، fail-closed روی
  missing/duplicate/closed/non-forward، مجوز جداگانهٔ SetOperationDate و Golden
  case برای استثنای ۱۰۰۷/۱۰۰۸. شاهد به `R-079` افزوده شد و شمارش ثابت ماند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Authorization و Scope تبدیل سفارش به فروش

- Type دقیق فرم تبدیل و هفت متد منتخب UI/Business/Adapter هیچ Call نام‌دار
  Permission/Access ندارند؛ نبود Gate در BaseForm/Menu بیرونی ادعا نشد.
- Helper حقوق نوع سفارش فقط View/New/Edit/Delete/Cancel/Confirm/Unconfirm را دارد.
  ده Callsite UI آن همگی در دو فرم List هستند و فرم تبدیل Callsite ندارد.
- Wrapper یک Scope ناحیه مشتری دارد که فقط با کلید سراسری `AreaAccess=1` فعال
  می‌شود. Clone صفر کلید فعال و GeneralConfig=false دارد؛ Projection دسترسی دو
  ردیف دارد ولی Gate جاری از صرف وجود آن ساخته نمی‌شود.
- Core UserRef را می‌پذیرد اما Authorization dependency نام‌دار ندارد؛ Actor
  ورودی، جای Principal احراز‌شده و Action decision را نمی‌گیرد.
- مقصد چهار Action جدا برای تبدیل عادی، تبدیل جزئی، Override اعتبار و تعیین تاریخ
  با Scope اجباری DC/Office/OrderType/CustomerArea/Order/StockDC می‌خواهد.
- شواهد به `R-079` متصل شد و Baseline شمارشی ثابت ماند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — مالکیت DataContext و شکاف EVC/Conversion

- `Application.DataAccess.dll` ثابت کرد Enum برابر Begin=0/No=1 و Constructor
  پیش‌فرض DataContext حالت No است. Commit/Rollback بدون DbTransaction no-op است.
- هر Context به‌صورت پیش‌فرض Provider و Connection تازه می‌سازد؛ ۵۹ Assembly
  مدیریت‌شده اسکن و هیچ Setter سفارشی Provider/ConnectionFactory/Transactional-
  Context پیدا نشد.
- Adapter تبدیل `DataContext(Begin)` می‌سازد و Commit واقعی دارد؛ Wrapper با
  `@@TRANCOUNT>0` به همان Transaction می‌پیوندد.
- Discount V2 آماده‌سازی EVC را با `DataContext(No)` انجام و Commit no-op می‌کند؛
  سپس Metadata token دقیق، رفتن V2 به overload تراکنش‌دار Adapter را ثابت کرد.
- بنابراین EVC preparation و Sale conversion دو Connection/مرز دوام جدا دارند؛
  امکان partial preparation ثبت شد، نه رخداد تاریخی.
- قرارداد مقصد یک Unit of Work تزریق‌شده برای Policy/EVC/Sale/Projection/Outbox
  می‌خواهد. شاهد به `R-079` وصل شد و شمارش ثابت ماند.

## تکمیل ۲۰۲۶-۰۸-۲۹ — EVC و fallback دو محاسبه‌ای Discount V2

- `FormOrderToSale.AcceptCommandDiscountV2` تنها callsite تایپ‌شدهٔ ورودی V2 است.
- clone فعلی یک کلید `IsDiscountV2Active` دارد ولی enabled count صفر است؛ مسیر V2
  capability موجود است، نه رفتار فعال فعلی clone.
- در ۵۹ Assembly فقط constructor، setter فلگ `CalcForDiscountV2` را صدا می‌زند
  و مقدار اولیه صفر است؛ setter تایپ‌شدهٔ دیگری پیدا نشد.
- Wrapper در مقدار صفر staging را روی connection تبدیل دوباره می‌سازد و
  `usp_FillEVCByOrder` را اجرا می‌کند؛ پس خروجی V2 و محاسبهٔ نهایی فروش یک محاسبه
  و یک connection نیستند.
- runtime جدول `#SaleItemPaymentUsance` را می‌سازد، اما writer مربوط به Sharp
  در `#SaleSaleItemPaymentUsance` درج می‌کند. هیچ SQL module یا managed CREATE
  literal برای نام دوگانه پیدا نشد؛ وقوع تاریخی خطا ادعا نشد.
- قرارداد مقصد `PricingSnapshotId` immutable، یک Unit of Work و contract test
  نام staging می‌خواهد. هفت تست focused سبز شد و finding به `R-079` متصل شد.
- فرضیهٔ cache سراسری رد شد: `globalCalcData` فقط `ldfld/stfld` دارد و
  `GetInstance` نمونهٔ تازه می‌سازد؛ نام field به معنی static/process-global نیست.
- مسیر منتخب بارگذاری V2 در IL دارای ۳۵ call مستقیم DataContext است (۱۷+۱ در
  Initial و ۱۷ در Extract)؛ latency واقعی اندازه‌گیری نشد، ولی query-budget و
  cache نسخه‌دار DC/date برای مقصد لازم شد.
- فرضیهٔ synchronous UI رد شد: `AcceptCommandDiscountV2` از
  `SodorFactor_BackgroundWorker_DoWork` می‌آید و progress/cancellation signal دارد؛
  latency واقعی هنوز اندازه‌گیری نشده است.
- cancellation پیش از call هر تبدیل چک می‌شود و DbCommand.Cancel/CancellationToken
  ندارد؛ توقف batch بین سفارش‌هاست و commitهای قبلی را برنمی‌گرداند.
- هنگام فعال‌بودن V2، checkbox بدون permission نام‌دار می‌تواند کل CalcData را
  JSON+GZip با OrderNo/OprDate در deployment-adjacent path ذخیره کند؛ encryption
  call دیده نشد و directory فعلی روی share موجود نبود.
- debug checkbox observer-only نیست: قبل از promotion جدید، `SLE.usp_DoEVC` legacy
  را روی همان staging اجرا می‌کند؛ اثر نهایی بدون integration test ادعا نشد.

## تکمیل ۲۰۲۶-۰۸-۲۹ — Dataset و consistency موتور Discount V2

- QueryHelper دقیقاً ۴۲ template دارد: ۱۷ Rule/reference، ده order-request و ۱۵
  sale/return/diagnostic؛ ۴۴ dependency شامل سه temp و ۴۱ object پایدار است.
- هر ۴۱ dependency پایدار در clone حل شد (۴۰ table/یک view) و scale جمعی
  پارتیشن‌ها ۷٬۹۱۹٬۲۷۲ ردیف است؛ این عدد activity نیست.
- ۲۷ template دارای ۳۱ String.Format slot است؛ write/exec و SELECT-star منتخب صفر
  است و raw SQL در Artifact ذخیره نشد.
- Clone RCSI و Snapshot Isolation را روشن دارد، اما EVC Context=No و ۳۵ read مستقل
  یعنی snapshot کل محاسبه تضمین نشده است؛ statementها می‌توانند نسخه‌های زمانی
  متفاوت Price/Discount/Stock/Order را ببینند.
- قرارداد مقصد: PricingSnapshotId/AsOfVersion واحد، parameter binding، cache نسخه‌دار
  Rule data و عدم cache کردن request state.

## تکمیل ۲۰۲۶-۰۸-۲۹ — موتور واقعی Discount V2 و قواعد اجرایی

- سه اسمبلی مستقل موتور شناسایی و hash-pin شد: `DiscountV2.dll`،
  `DicountV2SqlServer.dll` و `DicountV2SqlServerSDS.dll`؛ مجموعاً ۷۱۳ Type و
  ۷٬۱۵۶ Method دارند. ۲۲ Method مرزی/۳٬۷۴۳ Instruction بدون Load/Execute بررسی شد.
- Pipeline اصلی از validation و payment-usance به update-price، دو عبور از statute
  engine، special-value، اعمال روی item/header، تخفیف امانی، دوره‌ای و جایزه می‌رود.
- `SqlCondition` واقعاً از Rule خوانده، escape و با `sp_executesql` و پارامترهای
  `@EvcId/@Result` اجرا می‌شود؛ Metadata صرف یا Predicate تفسیرشدهٔ امن نیست.
- `InitialCalcData` و `ExtractCalcDataFromDB` هر دو Helper نوع SDS را قبل از
  `CalcData` می‌سازند؛ پس Temp rewrite در مسیر منتخب واقعاً تزریق شده است.
- چهار Rewrite دقیق ثبت شد. Rewrite عمومی `sle.tblEvc` پیش از دو نام تخصصی است و
  برای lowercase آن‌ها را زودتر تغییر می‌دهد. Corpus فعلی base-name صفر دارد؛
  ۷۹۳ شرط از قبل temp و ۵۲ شرط `EvcItemFull` هستند، پس finding آینده‌نگر است.
- Advanced validation روی candidateها loop می‌زند و برای هر Rule یک GetValue/
  `sp_executesql` جدا دارد؛ شاخه Include یک read و delete staging اضافه می‌کند.
  پس N+1 به candidate count وابسته است و بدون telemetry عدد runtime ادعا نشد.
- Constructor منتخب `CalcData` مقدار BackOfficeType را ۱ می‌گذارد و Gate همان
  ۱ را به Advanced validation می‌فرستد؛ پس Loop در مسیر order-to-sale خاموش نیست.
- Helper نوع SDS context تزریق‌شده را نگه می‌دارد و Validate آن را ترجیح می‌دهد؛
  در این مسیر همان DataContext بدون transaction EVC است. Queryهای N+1 یک connection
  دارند ولی calculation-wide snapshot ندارند.
- منبع اصلی `SLE.tblDiscount` دارای ۵٬۰۹۸ Rule، ۸۴۵ شرط غیرخالی، ۶۲۶ شرط فعال و
  فقط ۴۴ Hash متمایز است. متن خام و شناسه Rule در Artifact ذخیره نشد.
- اسکن واژگانی Snapshot فعلی DML نوشتنی، DDL/Permission یا primitive خارجی/تأخیر
  پیدا نکرد؛ این نتیجه پاکی نسبی دادهٔ فعلی است و design boundary اجرای متن را
  حذف نمی‌کند.
- مقصد باید ۴۴ خانواده را به AST/DSL نوع‌دار، نسخه‌دار، چهارچشمی و پارامتری
  تبدیل کند و هر خانواده Golden Case و Evaluation Trace داشته باشد.
- پروفایل بدون Literal، چهار جدول پایدار، یک Temp و ۲۳ نام ستون Catalog را در
  Vocabulary شرط‌ها یافت؛ این مجموعه Scope اولیه DSL مقصد است.
- در سه ماه منتخب فقط دو خانواده/سه Rule Advanced اثر retained دارند: ۴۷۱ ردیف
  Discount روی ۳۸ فروش، معادل ۰٫۱۵۶۸٪ از ۳۰۰٬۳۶۱ اثر Rule. این دو خانواده اولویت
  Golden Case موج اول‌اند؛ ۴۲ خانواده بدون اثر به‌طور خودکار حذف‌شده تلقی نمی‌شوند.
- هر دو خانوادهٔ مصرف‌شده روی `EvcItemFull` و با `EXISTS` کار می‌کنند؛ خانوادهٔ
  ۴۴۸ ردیفی `ID` و خانوادهٔ ۲۳ ردیفی `ID/BrandName` را لمس می‌کند. مقدار/برند
  خام استخراج نشد، بنابراین فقط sensitivity به برند ثابت است.
- از ۶۲۶ Flag فعال Advanced، فقط ۵۷ Rule در تاریخ فعلی date-effective هستند و
  به ۱۶ خانواده تعلق دارند. ۲۶۷ Rule/۳۶ خانواده با بازه سه‌ماهه date-overlap
  دارند، اما Flag فعلی برای بازسازی فعال‌بودن تاریخی کافی نیست.
- DeactivationLog مجموعاً ۱٬۳۱۳ رخداد یکتای فقط «به غیرفعال» دارد و activation
  ثبت نمی‌کند. در Advancedها ۲۱۸ رخداد قبل و دو رخداد داخل پنجره است؛ یک Rule
  فعال فعلی Log قدیمی دارد، پس reactivation ناقص است.
- دو Rule خانواده `ID` که ۴۴۸ اثر دارند هنوز فعال‌اند؛ Rule brand-sensitive با
  ۲۳ اثر داخل پنجره غیرفعال شده است. این علت inactive فعلی آن را توضیح می‌دهد.
- ۷۹۳ Rule/۹ خانواده به `#tblTempEvc + tblDiscount + tblDisSale + tblOrderHdr`
  وابسته‌اند و ۴۱ Rule امروز effective دارند، ولی اثر retained سه‌ماهه‌شان صفر
  است. ۵۲ Rule/۳۵ خانواده به `EvcItemFull` وابسته‌اند و هر سه Rule/۴۷۱ اثر مصرف‌شده
  در همین خوشه‌اند.
- DSL مقصد به دو Context مستقل `CurrentBasketPredicate` و
  `HistoricalRuleUsagePredicate` تقسیم شد؛ نبود اثر خوشه تاریخی حذف آن را مجاز
  نمی‌کند، چون Rule ممکن است ارزیابی و رد شده باشد.
- مسیر ساخت شرط نیز روشن شد: فرم تخفیف یک Condition dialog اختصاصی باز می‌کند،
  Filter بصری را به Where تبدیل، روی EVC temp با چهار Execute پویا اعتبارسنجی،
  سپس در `SqlCondition` ذخیره می‌کند. BaseForm ارث‌برده هنگام Init با
  `HasPersmission` فقط Enabled دکمه‌ها را تعیین می‌کند و Clickها Visible/Enabled
  را می‌سنجند؛ Internal command و Business recheck ندارند. پس این یک UI gate است،
  نه مجوز Service/API. این شاهد الزام DSL امن و تفکیک Draft/Review/Publish است.
  Lookup مجوز نیز فقط Cache نشست `UserPermissionS` را با Class/Key یا NodeId
  می‌خواند و هیچ DB round trip ندارد؛ تولید Flag `HasAccess` باید جدا بررسی شود.
- مجوز بیرونی فرم نیز `DiscountRules/404` با چهار Node مستقل
  `View/New/Edit/Delete` است. هرکدام در Snapshot ناشناس ۱۵ Effective allow دارند،
  اما Review/Publish مستقل وجود ندارد و برابری Aggregate هویت‌های یکسان را ثابت
  نمی‌کند. مقصد باید انتشار را از Edit جدا و در API enforce کند.

## Baseline نهایی مرحله ۱۵ ساعته — ۲۰۲۶-۰۸-۲۹

- ۳۶ Checkpoint همان روز همگی PASS و ۵۲۹ تست آفلاین روی ۴۳ فایل سبز شدند.
- پوشش نهایی در هفت محور فروش/توزیع، خزانه، انبار/خرید، سند/Rule،
  مجوز/تاریخ/Feature، گزارش مرجع و Transaction/Replication ثبت شده است.
- Baseline ریسک ۸۴ مورد (۵۰ Critical، ۳۱ High، سه Medium)، ۳۴۳ نگاشت و صفر
  Module آماده Command است؛ صفر آخر عمداً حفظ شده و نباید با شناخت زیاد اشتباه شود.
- Artifact مرجع:
  `artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json`.
- ادامه ۲۵ ساعته باید روی Truth tableهای باقیمانده، Golden Caseهای ناشناس و UAT
  ایزوله متمرکز بماند، نه اجرای فرم/Procedure روی سیستم عملیاتی.

## ادامه ۲۵ ساعته — کنترل Drift و Gap Map آغازین

- هر ۴۵ ورودی Manifest تحویل ۱۵ ساعته دوباره Hash شد و Drift صفر بود؛ ۳۶/۳۶
  Checkpoint، ۸۴ ریسک، ۳۴۳ نگاشت و صفر Module آمادهٔ Command حفظ شد.
- مهم‌ترین شکاف `G25-REPORT-IDENTITY-SCOPE-PARITY` است: ۲۰ سطح گزارش و ۱۷۵
  Golden Case آفلاین موجودند، اما Result parity، Binding دقیق SQL/پارامتر و Scope
  مؤثر برای هر ۲۰ گزارش صفر/اثبات‌نشده است.
- این Finding ریسک تازه نساخت و به `R-002/R-023/R-031` متصل شد. قرارداد مقصد باید
  Source-of-Truth، Grain، Formula، Scope، BusinessDate، Watermark و Reconciliation
  gate نسخه‌دار داشته باشد.

## ادامه ۲۵ ساعته — Binding گزارش‌های مرجع موجودی

- `RPT-15` شامل ده مسیر گزارش StockGoods از ۴۱ Candidate نامی به ده Procedure دقیق
  تبدیل شد؛ IL ایستا و Catalog READ_ONLY برای هر ده Method→Object و مجموعه پارامتر
  تطابق کامل دارند. Catalog جمعاً ۵۲ پارامتر و ۴۴ dependency اعلام‌شده دارد.
- این ده خروجی Source-of-Truth واحد نیستند؛ کاردکس Batch/Stock، فاکتور آزاد، سفارش
  و فروش باز، رزرو و تشخیص اصلاح موجودی Projectionهای مشتق با Grain متفاوت‌اند.
- Query identity/declared parameters تأیید شد؛ Scope مؤثر Runtime، Formula و Result
  parity هنوز اثبات‌نشده است. طرح UAT فقط طراحی و اجرا نشده است.
- Finding به ریسک‌های موجود `R-002/R-008/R-021/R-023/R-031/R-034` متصل شد و
  شمارش ریسک ۸۴ باقی ماند.

## ادامه ۲۵ ساعته — گزارش برگشت و مالکیت Template خارجی

- `RPT-11` از L3 نامی اصلاح شد: ۲۴ SQL candidate، Binding دادهٔ گزارش نیستند.
  فرم فایل پیکربندی را resolve و موتور خارجی `ShowReportFact` را صدا می‌زند؛ Query،
  Subreport و Formula داخل Template هستند.
- چهار Method/۱۱ Call مسیر File/Engine/AccYear/DC/PrintedCompleted را تأیید کردند،
  اما Template دقیق، Formula، cancel/delete semantics و Result parity باز ماند.
- Candidate binding رد شد و ریسک جدید ساخته نشد؛ `R-084` و ریسک‌های Drift/Report/
  return-net reuse شدند.

## ادامه ۲۴ ساعته — کاردکس سلامت و Print attempt

- `RPT-18` از ۸۵ Candidate به Master=`ICA.USP_VchHealthyCardex_GetList` و
  Detail=`ICA.USP_VchHealthyCardexDetails_GetList` رسید؛ ۱۸ پارامتر و چهار
  dependency Catalog ثبت شد.
- Master دارای `@Where` و Dynamic SQL است؛ مقصد باید آن را Filter AST کند. رخداد
  Injection جاری ادعا نشده است.
- IL مسیر چاپ ابتدا IDها، سپس `InsertInTotblSdsNetPrintDoc` و بعد `ShowReport` را
  فراخوانی می‌کند؛ پس PrintDoc، Attempt-before-render است نه success audit.
- Preview/Export/PhysicalPrint در مقصد سه قرارداد جدا هستند. Result parity و
  Runtime transaction همچنان اثبات‌نشده و Risk count برابر ۸۴ است.

## ادامه ۲۴ ساعته — چاپ Batch و Partial Success

- `RPT-09` هفت مسیر Render دارد؛ فقط چهار مسیر پس از `PrintedCompleted` Completion
  command دارند و سه مسیر Render-only هستند.
- Orchestrator با ۷۲۰ Instruction، نه Dispatch/Delay ترتیبی و بدون DataContext یا
  Rollback Batch است؛ خروجی‌های قبلی می‌توانند قبل از شکست بعدی کامل/Commit شوند.
- دو Completion path به Commit و صفر Rollback محلی می‌رسند. مقصد باید Outcome،
  Idempotency، Retry و Outbox را per-item نگه دارد و Mixed result را Boolean نکند.
- پنج Golden Case برای موفقیت کامل، شکست میانی، audit-failure، preview و retry ثبت
  شد. Result parity صفر و Risk count ۸۴ باقی ماند.

## ادامه ۲۴ ساعته — کاردکس تأمین‌کننده، مشتری و ارز

- `RPT-05/07/08` از مجموع ۴۵۵ Candidate نامی به شش Method، پنج شیء SQL دقیق،
  ۳۹ پارامتر و ۶۶ dependency رسیدند.
- مسیر Customer مرکزی یک درخواست Fararu است و با Query محلی یکی نیست؛ fallback
  بی‌صدای محلی در ERP مقصد ممنوع است.
- Cardex به‌عنوان Projection مشتق از Ledger تعریف شد، نه منبع مجاز CRUD حسابداری.
  Scope تاریخ/DC/طرف/دفتر و Currency/rate باید صریح و نسخه‌دار باشد.
- شش Golden Case و Playbook اختلاف ثبت شد؛ Formula، owner golden values و Result
  parity همچنان اثبات‌نشده، Risk count برابر ۸۴ و اجرای عملیاتی صفر است.

## ادامه ۲۴ ساعته — گزارش سفارش تولید

- `RPT-13` از چهار Candidate به Query دقیق
  `dbo.USP_SDSNET_ProductionOrderReport`، هشت پارامتر و پنج dependency رسید.
- Scope گزارش بازه تاریخ تولید، انبار مبدأ/مقصد، بازه کالا، نوع حساب و مشتری است.
  نبود `AccYear/UserRef` در امضا، مجوز را ثابت نمی‌کند و در مقصد باید بیرونی enforce شود.
- Export فقط رخداد فایل خارجی و Projection گزارش از facts سفارش/آیتم است؛ هیچ mutation
  مجاز نیست. شش Golden Case افزوده شد و Result parity صفر و Risk count ۸۴ ماند.

## ادامه ۲۴ ساعته — گزارش مرکز تماس

- `RPT-06` از Gap با صفر Candidate به binding دقیق
  `dbo.USP_CallCenter_ProductCustomer_Report`، چهار پارامتر و ۱۰ dependency رسید.
- `@Type` discriminator شاخه مشتری/کالا است، اما mapping مقدار آن اثبات نشده و در
  مقصد باید enum allowlisted با رد مقدار ناشناخته باشد.
- دو mode باید schema/grain جدا، Scope deny-first و watermark مستقل داشته باشند.
  شش Golden Case ثبت شد؛ Result parity صفر و Risk count ۸۴ باقی ماند.

## ادامه ۲۴ ساعته — جزئیات تولید و سری‌ساخت

- `RPT-14` از صفر Candidate با زنجیره inheritance/generic به
  `dbo.usp_sdsnet_BatchNo_GetList`، ۱۸ پارامتر و ۱۸ dependency متصل شد.
- دو mode دارای/بدون موجودی با FetchReason جدا می‌شوند؛ مقدار mapping هنوز اثبات
  نشده و unknown باید fail-closed باشد.
- on-hand/damaged و production/expiry date مستقل‌اند. Export فایل خارجی است؛ شش
  Golden Case ثبت شد، Result parity صفر و Risk count ۸۴ باقی ماند.

## ادامه ۲۴ ساعته — Selectorهای گزارش انبار

- `RPT-16` یک modal parameter selector و `RPT-17` یک report route orchestrator است؛
  هیچ‌کدام Query یا result set مستقل ندارند.
- `RPT-17` به `RPT-14/RPT-15` route می‌کند. parity خود selector روی outcome، enum،
  Scope propagation و route است، نه totals داده.
- enum/resource ناشناخته fail-closed و multi-route outcome باید per-route باشد.
  شش Golden Case ثبت شد و Risk count ۸۴ ماند.

## ادامه ۲۴ ساعته — Host و Zoom داشبورد

- `RPT-03` میزبان permission/refresh/layout پنج widget و `RPT-04` پوسته zoom/drag
  است؛ هیچ‌کدام Query، Formula یا Result set مستقل ندارند.
- parity میزبان روی composition و per-widget state است؛ parity داده برای هر child
  widget جدا و هنوز اثبات‌نشده است.
- watermark سراسری و atomicity بین widgetها ادعا نمی‌شود. شش Golden Case ثبت شد و
  Risk count ۸۴ باقی ماند.

## ادامه ۲۴ ساعته — Crystal Viewer خزانه

- `RPT-01/RPT-02` Viewer سندهای Crystal آماده‌اند و مالک Query/Template/Formula نیستند؛
  connection rebinding به‌تنهایی هویت Query را ثابت نمی‌کند.
- RPT-02 چندسندی است، print/export visibility و close lifecycle دارد؛ authorization
  واقعی باید در export service/trusted spooler نیز enforce شود.
- parity به هر caller/template منتقل شد. شش Golden Case ثبت و Risk count ۸۴ حفظ شد.

## ادامه ۲۴ ساعته — Closure Ledger بیست گزارش

- هر ۲۰ Surface به Artifact معتبر ownership متصل شد: هشت exact-query و دوازده
  viewer/template/shell/selector/orchestrator/bank boundary.
- Ownership بسته شد، اما Result parity، owner golden values، command readiness و
  implementation/pilot readiness همگی عمداً صفر ماندند.
- بسته‌های بانک و فاکتور موجود reuse شدند؛ تحلیل بسته‌شده تکرار نشد و Risk count ۸۴ است.

## ادامه ۲۴ ساعته — Command Readiness Ledger

- ۱۴ ماژول به ۱۳ Artifact معتبر فرمان نگاشت شدند؛ ده orchestrator command، ۱۱ trace
  ایستا و ۷۷ Golden Case مصنوعی pin شد.
- دو Artifact قدیمی بدون validation فقط design input هستند و readiness gate نیستند.
- هر پنج ضلع authorization/transaction/mutation/outcome-retry/golden runtime هنوز
  صفر است؛ command-ready و pilot-ready صفر و Risk count ۸۴ باقی ماند.
# الحاقیه ۱۴۰۵/۰۶/۰۷ — مرز Golden Case/UAT

دفتر `varanegar_golden_uat_evidence_ledger_20260829.json` نشان می‌دهد ۷۷ Golden Case فرمان فقط طراحی synthetic هستند. برای ۱۴ ماژول فرمان، اجرای معتبر، parity اثر و تأیید مالک صفر است. برای ۲۰ سطح گزارش نیز با وجود بسته‌شدن مالکیت فنی، result parity و Golden Value مالک صفر است. پس هیچ مسیر فرمان/گزارش UAT-ready یا pilot-ready اعلام نمی‌شود و شمار ریسک ۸۴ ثابت است.

ماتریس `varanegar_expert_incident_playbook_20260829.json` ده کلاس رخداد اصلی را به روش واحد evidence-first متصل می‌کند. خروجی تشخیص فقط یکی از «رفتار طبیعی»، «بدهی داده»، «Bug» یا «اثبات‌نشده» است و بدون شواهد رخداد مشخص، علت قطعی ادعا نمی‌شود. هر نیاز به write، اجرای عملیاتی، repair یا persistence داده حساس یک stop condition است.

baseline نهایی مرحله ۲۵ ساعته همهٔ checkpointها، تست کامل، ریسک ۸۴تایی و traceability با ۳۴۳ نگاشت را یکجا ممیزی می‌کند. تکمیل به دامنهٔ شناخت فقط‌خواندنی محدود است؛ runtime parity و owner acceptance همچنان دروازهٔ خارجی‌اند.

ادامهٔ ۲۴ساعته از همین baseline، outcome/lineage حسابداری را اولویت داد. چهار External Voucher دارای مسیر Procedure دقیق و transaction owner ایستای قوی‌اند؛ confirm/unconfirm انبار route ambiguity دارد؛ save/cancel دستی هنوز candidate-only است. مهم‌ترین قاعدهٔ تشخیصی این بخش آن است که business-error ممکن است با durable cleanup همراه باشد، پس پیام خطا به‌تنهایی Rollback را ثابت نمی‌کند و retry باید read-back محور باشد.

اصلاح بعدی نشان داد `FormManualVoucherDataEntry2.InternalCancelCommand` فقط `Form.Close` است و فرمان لغو مالی محسوب نمی‌شود. Save به `ManualVoucherHandler.GetInstance` و generic `TypeSpecRow.SaveCommand` می‌رسد، ولی transaction owner و Procedure دقیق پشت generic path هنوز resolve نشده‌اند.

استخراج مستقیم PE/CLR بعدی binding جنریک را کامل کرد: ManualVoucher به `IBusinessHandler<ManualVoucherAdapter,…>` و سپس `BaseDataV2Adapter` می‌رسد. UI یک context با `Transaction.Begin` می‌سازد و context-taking Insert/Update/Delete هرکدام Commit دارند؛ UI و generic handler Commit ندارند و Rollback صریح در مسیرهای انتخاب‌شده نیست. persistence مبتنی بر entity metadata است و Procedure نام‌دار ManualVoucher دیده نشد.

Inventory حسابداری اصلاح شد: از هفت candidate، `accounting.manual_voucher.cancel` به‌عنوان UI-close حذف شد و شش مسیر باقی ماند. Manual Save اکنون design-level outcome/transaction contract دارد، اما branch runtime، authorization و effect parity هنوز صفر/اثبات‌نشده‌اند.

در readiness delta، حسابداری به چهارمین ماژول دارای outcome/retry target contract طراحی‌شده تبدیل شد. این تغییر فقط design coverage است؛ شمار command-ready، pilot-ready و runtime-proven همچنان صفر است.

برای شش فرمان حسابداری ۴۲ Golden/UAT case طراحی شد. هر فرمان denial، stale، duplicate command id، fault injection، scope، success و یک حالت ویژه دارد. caseهای transfer اثر durable همراه business-error را الزاماً read-back می‌کنند و خانوادهٔ false مربوط به Manual Cancel حذف شده است. همهٔ caseها `DESIGNED_NOT_EXECUTED` هستند.

برای ۲۰ سطح گزارش نیز ۸۸ fixture طراحی شد: ۸۰ case پایه و هشت partial-failure برای سطح‌های command-bearing. assertionها ownership-aware هستند؛ shell/selector فقط route و filter propagation دارد و value parity مستقل برای آن‌ها ادعا نمی‌شود. اجرا، result parity و owner approval همچنان صفر است.

Playbook تخصصی حسابداری پنج رخداد پرریسک را با روش evidence-first پوشش می‌دهد: transfer با اثر durable، fork در pointer/history، shell شماره‌دار بدون line، نتیجهٔ مبهم Manual Save و UI-close اشتباه‌گرفته‌شده با لغو مالی. قرارداد ERP مقصد ۹ بخش دارد: state machine، command schema، deny-first authorization، unit of work، idempotency، typed outcome، immutable lineage، quarantine و acceptance gate چهل‌ودو case. این طراحی تشخیص یا repair رخداد واقعی را ادعا نمی‌کند.

دلتا‌ی Traceability ادامه، هفت بستهٔ شاهد را به ۱۰ قرارداد نیازمندی، ۲۶ پیوند ماژولی و ۳۶ پیوند شاهد-ریسک روی ۱۶ ریسک موجود متصل کرد. این دلتا الحاقی است: ثبت پایهٔ ۸۴ ریسک و ۳۴۳ انتساب تغییر نکرد، ریسک تازه و ارتقای runtime readiness هر دو صفر ماندند.

Wave-01 ادامه یک baseline میانی و صریحاً غیرنهایی است. نتیجهٔ موج، مجموعهٔ اصلاحات حسابداری، ۴۲ Golden حسابداری، ۸۸ fixture گزارش، پنج Playbook و قرارداد ۹بخشی را یکجا pin می‌کند؛ اولویت بعدی خزانه، توزیع و تطبیق بین‌ماژولی است.

در موج خزانه، ۱۲ فرمان به envelope چهارحالته outcome/retry متصل شدند: هفت مسیر ایستای legacy و پنج فرمان طراحی بانکی. Delete چک transaction owner اثبات‌شده ندارد، Undo branch/form مبهم است و replication می‌تواند crosswalk split-effect داشته باشد. design coverage ماژول از false به true رسید، اما runtime readiness صفر ماند. برای این دامنه ۸۴ Golden Case و شش Playbook تخصصی طراحی شد.

دلتا‌ی Traceability خزانه چهار Artifact را به هفت نیازمندی و ۹ ریسک موجود متصل می‌کند. ثبت ۸۴/۳۴۳ ثابت است و نه ریسک تازه، نه closure و نه ارتقای runtime ادعا نمی‌شود.

در موج توزیع، چهار فرمان Create/Issue/Merge/Remove به outcome envelope متصل شدند. هر چهار مسیر idempotency صریح ندارند و enlistment فیزیکی transaction آنها اثبات نشده است؛ Merge حتی در UI/Adapter مالک صریح ندارد. design coverage از پنج به شش ماژول رسید، اما runtime readiness صفر ماند. ۲۸ Golden Case و پنج Playbook، late-cardex، partial graph cleanup و historical absence را پوشش می‌دهند.

دلتا‌ی Traceability توزیع چهار شاهد را به هفت نیازمندی و ۹ ریسک موجود متصل کرد. Risk/Traceability پایه ۸۴/۳۴۳ و promotion صفر باقی ماند.

در موج تطبیق بین‌ماژولی، هفت لبهٔ Command Receipt، فروش/منبع حسابداری، منبع/Batch/Journal، توزیع/فروش، توزیع/خروج، خروج/سند نوع ۶۰ و پرداخت NGT/رسید BackOffice به یک قرارداد ده‌بخشی متصل شدند. قرارداد ۱۰ invariant، شش وضعیت و هشت علت قرنطینه دارد. مهم‌ترین قواعد منفی: برابری مبلغ پرداخت/رسید invariant هویت نیست، Batch چندمبدأیی مجاز است، نبود فیزیکی خروج مدرک ابطال نیست و `MAX(id)` وضعیت جاری را اثبات نمی‌کند.

برای این هفت لبه ۳۵ Golden Case و هفت Playbook نه‌مرحله‌ای طراحی شد. همهٔ Caseها اجرا‌نشده‌اند و تشخیص رخداد، repair، retry، owner approval، runtime parity و readiness صفر باقی ماند. Delta ردیابی سه شاهد را به ۱۰ نیازمندی، ۲۱ پیوند ماژولی و ۳۰ پیوند روی ۱۰ ریسک موجود وصل کرد؛ ثبت پایهٔ ۸۴/۳۴۳ تغییر نکرد.

بازرتبه‌بندی بعدی `reporting_documents` را به‌عنوان شکاف اول انتخاب کرد: هشت سطح Command-bearing و هشت Fixture شکست جزئی داشتند، ولی outcome/retry ماژولی absent بود. Envelope تازه پنج outcome را بین Request، Render، Physical Confirmation، Completion/Audit، File Delivery و Treasury Receipt جدا می‌کند. Preview Completion نمی‌سازد و Export نباید ERP fact را تغییر دهد.

شواهد چاپ فروش ۳۰۸٬۴۳۲ رخداد، ۳۴٬۸۴۰ سند چندبارچاپ‌شده و ۱۴۳ رخداد پس از ابطال نهایی را نشان می‌دهد؛ بدون Request identity اینها Bug تلقی نمی‌شوند. design coverage از شش به هفت ماژول رسید، ۵۶ Golden Case و شش Playbook ساخته شد و پنج شاهد به ۱۰ نیازمندی و هشت ریسک موجود وصل شدند. اجرا، owner approval، readiness و ثبت پایهٔ ۸۴/۳۴۳ همچنان صفر/ثابت‌اند.

در موج قواعد قیمت‌گذاری، هفت مسیر مقصد تعریف شد: Save/Close قیمت زمینه‌ای، تغییر اولویت، Save/Close تخفیف، Compile شرط و Allocate/Save تخفیف خطی. مجوز Toolbar/Session Snapshot مرجع نهایی نیست و Application Service باید author/publisher capability و Scope را deny-first بازبینی کند. Ruleها نسخه‌های immutable با چرخهٔ `DRAFT/VALIDATED/PUBLISHED/CLOSED` هستند؛ Copy فقط Draft جدید می‌سازد و قاعدهٔ استفاده‌شده حذف فیزیکی نمی‌شود.

دو setter برای `SqlCondition` و چهار اجرای پویای Validation در شواهد ایستا دیده شد؛ مقصد متن SQL اجرایی را ذخیره یا اجرا نمی‌کند و فقط AST/DSL نسخه‌دار و Allowlist‌شده با Compile/Explain بدون اثر می‌پذیرد. اولویت یک Tuple قطعی با Stable tie-breaker است. `GenerateLinearDiscountId` دقیقاً `MAX(Id)+1` دارد و با Allocator اتمیک و Unique constraint جایگزین می‌شود.

۶۴ Golden Case قبلی reuse و ۲۸ Case Delta ساخته شد؛ مجموع طراحی Pricing برابر ۹۲ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی اضافه شد. پوشش طراحی Outcome/Retry از هفت به هشت ماژول رسید، اما Runtime effect parity، owner approval، command readiness و pilot readiness صفر و ثبت پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت ماند.

در موج Integration/Migration، شش قرارداد مقصد برای POS Receipt، NGT Sale، NGT Payment، Compensation، Rule Package و Migration Slice تعریف شد. مدل مرحله‌ای Stage/Validate/Apply/Reconcile/Acknowledge/Quarantine مانع یکی‌گرفتن Transport completion با Business success می‌شود. Package identity، Content hash، Scope، Sequence و Previous receipt hash immutable هستند و هر Item، Effect، Crosswalk و Ack Receipt مستقل دارد.

Graph انتقال POS با ۵۰۰ Node و ۱۶۰ Frontier باز به سقف ایمنی رسیده و Mutation set کامل نیست. در NGT Sale، ۱۳۸ موجودیت چند History به همان Target و صفر Multi-target دارند؛ پس تکرار History به‌تنهایی Duplicate effect نیست. Compensation فرمان append-only جدید است و History اصلی را پاک نمی‌کند. Migration دوازده Slice مرتب دارد و فقط از Checkpoint پایدار Resume می‌شود.

۳۴ Golden Case موجود reuse و ۳۵ Case Delta ساخته شد؛ مجموع طراحی Integration برابر ۶۹ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی اضافه شد. پوشش طراحی Outcome/Retry از هشت به نه ماژول رسید، اما Runtime، UAT، owner approval، command readiness و pilot readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

در موج پیکربندی، پنج قرارداد مقصد برای General، Web Service، Accounting Article Template، override محدوده‌دار و rollback تعریف شد. نسخه‌ها immutable و دارای چرخهٔ `DRAFT/VALIDATED/PUBLISHED/PARTIALLY_ACKNOWLEDGED/SUPERSEDED/RETIRED` هستند. تقدم با tuple قطعی family/scope/effective-window/published-version/stable-version-id حل می‌شود؛ `TOP 1` بدون ترتیب مجاز نیست و null به `INHERIT/EXPLICIT_NULL/VALUE` تفکیک می‌شود.

شاهد ایستا ۹۷ resolver چندجدولی، ۱۴ resolver با `TOP 1` بدون `ORDER BY`، هجده mismatch App/Device، ۵۱ ارجاع فعال به Setting حذف‌شده و هفت mismatch معنایی delivery را pin کرد. این اعداد رفتار مؤثر production را اثبات نمی‌کنند. secret value در payload/result/audit ممنوع است و فقط hash ارجاع vault مجاز است. انتشار version/pointer/audit/outbox اتمیک، ack هر مصرف‌کننده مستقل و rollback فقط با انتشار نسخهٔ تازه از محتوای پیشین انجام می‌شود.

۵۴ Golden Case موجود reuse و ۲۸ Case Delta ساخته شد؛ مجموع طراحی پیکربندی ۸۲ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی اضافه شد. پوشش طراحی Outcome/Retry از نه به ده ماژول رسید، اما Runtime effect parity، UAT، owner approval، command readiness و pilot readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

در موج هویت و مجوزدهی، شش قرارداد مقصد برای policy نسخه‌دار، capability مستقیم، عضویت گروه، data scope، revoke همراه با `SessionEpoch` و break-glass تعریف شد. تصمیم deny-first است: deny صریح بر allow مستقیم، گروهی، inherited یا admin مقدم است و Application/Owner، action capability و data scope مستقل بررسی می‌شوند. Principal فقط با opaque reference hash وارد receipt می‌شود؛ نام، شناسه، credential، membership row و permission value ممنوع است.

شاهد ایستا ۷۸۴ endpoint، ۶۰ endpoint بدون declaration روشن، ۳۸ endpoint تغییردهنده در همان گروه، صفر manual decision نام‌دار، admin short-circuit، سه subject منتسب به آن نقش و ۵۸ ناسازگاری scope را pin کرد. Permission repository owner-filtered نیست. اینها قرارداد ریسک‌اند و مجوز مؤثر production یا هویت هیچ فردی را اثبات نمی‌کنند.

۱۸۴ Case provisional قبلی reuse و ۴۲ Case Delta ساخته شد؛ مجموع طراحی هویت/مجوز ۲۲۶ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی اضافه شد. پوشش طراحی Outcome/Retry از ۱۰ به ۱۱ ماژول رسید، اما effective grant، authenticated UAT، owner approval، production assignment، runtime parity، command readiness و pilot readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

در موج Organization Context، شش قرارداد مقصد برای Save/Delete سال عملیاتی، Save/Delete رابطهٔ StockDC، انتشار پنجرهٔ تاریخ و فعال‌سازی snapshot تعریف شد. `ContextSnapshotId` immutable سازمان، سال عملیاتی، سال مالی، DC، دفتر فروش، انبار، پنجرهٔ تاریخ، calendar/timezone policy و نسخهٔ relation را برای تمام عمر یک فرمان pin می‌کند؛ re-read از ambient session وسط فرمان مجاز نیست.

timestamp رخداد، مرز باز/بسته، selector تاریخ سند/Replication و ساعت Server چهار مفهوم مستقل‌اند. شاهد ایستا ۶۴۳ method منتخب تاریخ، ۱۱ SQL consumer، پنج consumer جدول global، سه profile با OperationDate تهی و یک profile با OperationDate پس از LastDate را pin کرد. permission تغییر تاریخ در server command بازبینی نمی‌شود. اینها نتیجهٔ رخداد production نیستند.

۶۴ Golden Case قبلی reuse و ۳۵ Case Delta ساخته شد؛ مجموع طراحی Context برابر ۹۹ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی اضافه شد. پوشش طراحی Outcome/Retry از ۱۱ به ۱۲ ماژول رسید، اما runtime Context parity، owner approval، command readiness و pilot readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

در موج Master Data، ۱۰ قرارداد مقصد برای Customer/Goods/Supplier/POS Subscriber، قرنطینهٔ duplicate، انتشار Crosswalk نسخه‌دار و Merge برگشت‌پذیر تعریف شد. تطبیق بر اساس indicatorهای ضعیف مانند barcode/contact/name/route proof هویت نیست؛ sentinel، ambiguity و conflict باید قرنطینه شوند. Crosswalk با source system، entity type، mode، target و policy namespace می‌شود و Merge به approval مستقل، تطبیق کامل، redirect برگشت‌پذیر و حفظ provenance تاریخی نیاز دارد.

شاهد ایستا سه فرم، ۴۰ method منتخب، پنج method دارای Commit، ۱۴۲ candidate ورودی و ۶۲ candidate بدون متن ایستای کامل را pin کرد. ۲۶٬۰۸۶ مقدار path در هفت code وجود دارد، ولی route master row متناظر صفر است؛ بنابراین تنها تفسیر مجاز `MANUAL_INTEGER_CODE` است. این شمارش‌ها رفتار مؤثر production یا هویت هیچ رکوردی را اثبات نمی‌کنند و مقدار خام barcode/contact/PII در Artifactها ذخیره نشده است.

۱۱۴ Golden Case موجود reuse و ۳۵ Case Delta ساخته شد؛ مجموع طراحی Master Data برابر ۱۴۹ است. هفت Playbook و Delta ردیابی پنج‌شاهده/ده‌نیازمندی با ۴۰ پیوند ماژولی و ۵۰ پیوند ریسک اضافه شد. پوشش طراحی Outcome/Retry از ۱۲ به ۱۳ ماژول رسید، اما اجرای Merge، runtime effect parity، UAT، owner approval، command readiness و pilot readiness صفر و ثبت پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت ماند.

در موج Platform، سه فرمان Blueprint یعنی `approve/reject/retry_job` با Release Publish، Release Rollback و Restore Drill Attestation به شش قرارداد provider-neutral متصل شدند. Commit کنترل، Audit و Outbox هرگز به‌تنهایی Deployment/Restore/Job خارجی را ثابت نمی‌کند؛ تأیید اثر به Receipt سلامت، reconciliation و external-effect نیاز دارد و Rollback یک فرمان تازه با حفظ تاریخ است.

اسکن ایستا ۸۵۳ فایل استقرار و صفر reference بیرونی را pin کرد، اما route پویا یا محیط بیرونی را رد نمی‌کند. Stack، Database، Hosting، RPO/RTO، ظرفیت و مالک استقرار همچنان تصمیم‌گیری‌نشده‌اند و Proposal موجود Approval نیست. ۴۲ Golden Case و هفت Playbook طراحی شد؛ پوشش Outcome/Retry از ۱۳ به هر ۱۴ ماژول رسید، اما اجرا، Runtime parity، owner approval، command readiness و pilot readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

ممیزی تجمیعی بعدی نشان داد هر ۱۴ ماژول Outcome/Retry target contract و Authorization design دارند، اما فقط ۱۲ ماژول شاهد static/design برای Transaction و Mutation دارند؛ `identity_authorization` و `integration_migration` در این دو بُعد target-design باقی مانده‌اند. مجموع obligation طراحی Golden با Platform برابر ۱۲۲۹ و Playbookهای موج ادامه ۷۸ است.

هیچ Case اجرا یا Owner-approved نشده و Runtime authorization، atomicity، effect parity و retry parity در هر ۱۴ ماژول صفر است. مالکیت هر ۲۰ سطح گزارش بسته شده، ولی Result/Formula parity و Owner Golden Value صفر است. شش Gate خارجی Runtime، UAT/Owner، Report parity و Stack/Hosting/RPO/RTO/Owner حفظ شده و بستهٔ تجمیعی صریحاً non-final است.

مرز تکمیلی Transaction/Mutation برای دو ماژول باقیمانده ابهام عبارت `static/design` را رفع کرد: هر شش فرمان Identity دارای `transaction_owner` مقصد و هر شش فرمان Integration دارای `atomic_unit` و Effect Receipt مقصد هستند؛ بنابراین Target transaction/effect design برای هر ۱۲ فرمان ثبت شده است. این پوشش قراردادی به معنی اثبات رفتار Legacy یا Runtime نیست.

complete legacy/static proof برای هر ۱۲ فرمان صفر است. در Identity، ۳۸ endpoint تغییردهنده بدون declaration روشن و ۵۸ scope mismatch؛ و در Integration، ۱۶۰ frontier باز POS، ۳۴۲ compensation blocker candidate و شش Gate انتقال Rule باقی است. Implementation، Runtime atomicity/effect parity، UAT و Owner approval صفر، و پایهٔ ۸۴ ریسک/۳۴۳ انتساب بدون تغییر است.

نقشهٔ بعدی شش Gate خارجی را dependency-aware مرتب کرد. `CG-06` ریشهٔ تصمیم Platform است، زیرا Stack/Database/Hosting، RPO/RTO، محیط ایزوله و نقش مالک استقرار ظرف اثبات Runtime را تعیین می‌کنند. `CG-05` یک مسیر محدود موازی است: با وجود مالکیت بستهٔ ۲۰/۲۰، Fixture و Owner-approved formula/grain/scope/rounding/null و receipt مقایسه هنوز وجود ندارد؛ shell نیز Query owner فرض نمی‌شود.

پس از آن `CG-01` برای authorization/scope، `CG-02` برای rollback و partial-failure atomicity و `CG-03` برای mutation/result/external-effect/readback قرار دارند. `CG-04` Gate نهایی است و تنها پس از پذیرش پنج Gate دیگر می‌تواند ۱۲۲۹ obligation طراحی را به اجرای UAT و approval مالک تبدیل کند. هر Gate چهار جزء Evidence packet و Acceptance rule دارد، اما تا پیش از پذیرش کامل Promotion برابر `NONE`، تمام محورهای Runtime و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

برای ریشهٔ `CG-06` یک قرارداد Evidence intake هشت‌اسلاتی تعریف شد: Stack، Database، Hosting/Network، نقش پاسخ‌گوی Deployment، RPO، RTO، محیط ایزوله و Recovery drill/receipt policy. وابستگی‌ها صریح‌اند؛ محیط ایزوله پس از Architecture/Owner و Policy Drill پس از Hosting/Owner/RPO/RTO/Environment پذیرفته می‌شود.

هر Packet یازده Field مرجعی و Hash دارد. `PROPOSAL` هرگز Approval نیست و Approval ناقص، دو Approval جاری متعارض، تصمیم Superseded یا Dependency تصویب‌نشده پذیرفته نمی‌شوند. PII، Credential/Secret، Endpoint/Connection string، قرارداد خام فروشنده و مقدار خام تجاری ممنوع است. اکنون ۰/۸ Slot انتخاب و صفر Packet پذیرفته شده؛ CG-06 باز، Runtime/Restore/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

برای `CG-05` بیست سطح گزارش بر اساس مالک واقعی نتیجه partition شدند: ۱۱ Result owner، دو Command-only و هفت Routing/View. هشت سطح فرمان دارند و شش سطح هم‌زمان Result owner هستند؛ بنابراین Receipt فرمان، Idempotency یا Partial-failure در این شش سطح هرگز جای Formula/Result parity را نمی‌گیرد.

Result parity packet چهارده Field مرجعی/Hash برای Fixture، Legacy/Target digest، Row-key set، Formula، Grain، Scope، Rounding، Null، Watermark، Difference manifest و Owner approval دارد. پذیرش نیازمند Frozen isolated input، Policy تصویب‌شده و صفر اختلاف توضیح‌نداده‌شده است. Shell/Viewer/Selector/Orchestrator به Query owner ارتقا داده نمی‌شود. اکنون ۸۸ Fixture و ۵۶ Case فرمان فقط طراحی‌اند؛ اجرا، Packet پذیرفته، Result parity، Owner approval و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

برای `CG-01` چهارده Packet ماژولی authenticated authorization/scope تعریف شد. هر Packet پانزده Field مرجعی/Hash و هشت دسته سناریو دارد: Allow معتبر، تقدم Deny، Capability مفقود، Scope ناسازگار، Session epoch پس از Revoke، SoD، Break-glass و تفاوت UI visibility با Server enforcement. UI guard و Count equality هیچ‌کدام Effective authorization را ثابت نمی‌کنند.

اجرای این قرارداد به پذیرش ۸/۸ Slot CG-06 و محیط ایزوله وابسته است؛ اکنون ۰/۸ است. در Identity، ۶۰ declaration gap، ۳۸ mutating gap و ۵۸ scope mismatch باقی است، اما به Incident عمومی همهٔ ماژول‌ها تعمیم داده نمی‌شود. ۲۲۶ Case و هفت Playbook طراحی‌اند؛ Packet پذیرفته، Runtime authorization، Approval و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

برای `CG-02` ده مرز Fault-injection در هر ۱۴ ماژول تعریف شد. دوازده ماژول Legacy-static یا Target design دارند؛ Identity و Integration فقط Target design دارند و Complete legacy/static proof آنها صفر است. مرزها از mid-mutation تا pre-Audit/Outbox، post-Commit/pre-Ack، شکاف DB/external effect، rollback failure، concurrency، stale version و retry امتداد دارند.

Packet Atomicity هفده Field مرجعی/Hash دارد. Rollback call، Catch یا Boolean return موفقیت Rollback را ثابت نمی‌کند؛ Commit بدون Ack تا Readback immutable برابر Unknown outcome است و DB/external system Atomic commit مشترک ندارند مگر مستقل اثبات شود. اجرای CG-02 پس از CG-06 می‌تواند موازی با CG-01 باشد. اکنون Runtime atomicity، Packet/Approval و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

برای `CG-03` ده لایهٔ اثر در هر ماژول جدا شد: DB mutation، Audit، Outbox/Job، External effect، Result، Readback، Retry، Compensation، Crosswalk/Provenance و Reconciliation/Quarantine. دوازده ماژول شاهد static/design دارند و Identity/Integration فقط Target design؛ Runtime effect parity صفر است.

Packet Effect parity نوزده Field مرجعی/Hash دارد. Commit/Audit/Outbox اثر خارجی را ثابت نمی‌کند، Result موفق بدون Readback Mutation set را ثابت نمی‌کند و Retry باید Outcome قبلی را پیش از اثر تازه reconcile کند. Compensation append-only است و History اصلی را پاک نمی‌کند. اجرای CG-03 به CG-06 و CG-02 وابسته است؛ اکنون Packet/Approval/Runtime parity/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

`CG-04` Gate نهایی Owner-UAT است و به پنج Gate و ۷۰ Slot/Packet بالادست وابسته شد: ۸ Platform، ۲۰ Report و سه مجموعهٔ ۱۴ماژولی Authorization/Atomicity/Effect. برای هر ماژول Packet شانزده‌فیلدی و نه بُعد پذیرش برای Obligation، Receipt، Difference/Risk، Approval و Promotion/Rollback تعریف شد.

Artifact/Test آفلاین PASS یا Golden design اجرای UAT نیست. Approval باید Run/Difference/Risk/Snapshot دقیق را ارجاع دهد و Approved exception صفر اختلاف محسوب نمی‌شود. CG-04 فقط با اجرای ۱۲۲۹ Obligation، ۱۴ Packet نهایی و Approval پاسخ‌گو بسته می‌شود. اکنون پذیرش ۰/۷۰، اجرا/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

شش قرارداد Intake اکنون در یک ماتریس تحویل/پذیرش یکپارچه شده‌اند. کل زنجیره ۸۴ واحد پذیرش دارد: ۸ Slot در CG-06، بیست Surface در CG-05 و چهار دستهٔ ۱۴ماژولی در CG-01/02/03/04. نه Edge مستقیم وابستگی ثبت شده و همه تا پذیرش Gate مبدأ مسدودند.

تحویل فقط با Packet set دقیق، immutable و `ACCEPTED_CURRENT` معتبر است. Proposal، پذیرش جزئی، Reference بدون Hash، شاهد Stale/Superseded، Approval فاقد نقش پاسخ‌گو، اختلاف توضیح‌نداده‌شده، Payload خام/هویتی و Promotion زودهنگام رد می‌شوند. اکنون پذیرش ۰/۸۴، Gate بسته صفر، Handoff پذیرفته صفر و Readiness صفر است؛ نقش‌ها نوع مسئولیت‌اند نه هویت شخص، و پایهٔ ۸۴/۳۴۳ تغییر نکرده است.

Triage آفلاین Graph ایستای POS نشان داد Graph ذخیره‌شده با ۵۰۰ گره و ۱۰۳۹ Edge به سقف ایمنی رسیده و صف ۱۶۰عضویِ توسعه‌نیافته بدون identity manifest باقی مانده است. این صف با ۱۵۱ ماژول callable موجود در مرز عمق سه یکی نیست. مرز عمق سه ۱۸۳ گره دارد و در callableهای آن ۴۴ Transaction signal، چهار TRY/CATCH و چهار Dynamic-SQL signal ثبت شده است؛ اینها مالکیت تراکنش یا Rollback را ثابت نمی‌کنند.

از ۱۷۹ unresolved، تعداد ۱۶۸ مورد pseudo-tableهای `inserted/deleted` هستند و یازده مورد Alias/Type/Name برای پیگیری ایستا باقی می‌مانند. یازده SCC چرخه‌ای با ۶۸ گره—شامل ۴۸ Trigger، نوزده Table و یک Procedure—ریسک Cascade و Transaction ownership را برجسته می‌کند. ۴۸ Write target فقط lower bound است؛ هیچ DB connection تازه، اجرای SQL، Definition یا مقدار خامی استفاده نشد و Runtime parity/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

در CG-05 از بیست Surface فقط یازده Result owner مستقل‌اند: هشت Query-bound، دو Template-owned و یک Bank typed read/summary. برای ۹ Surface شکل ایستای Grain موجود است، اما دو Template تا استخراج Query/Subreport/Formula دارای Grain ناشناخته‌اند. یازده Formula بانک نیز Design هستند و Runtime parity یا Approval مالک را ثابت نمی‌کنند.

ماتریس Formula/Grain چهارده بُعد و ۱۲۳ الزام سطحی دارد: Stable key/Grain، Business date/Watermark، Scope، Status/Cancel/Delete، Null، Sign، Decimal/Rounding stage، Unit/Currency/Rate، Ordering/Pagination/Total، Opening/Closing، Mode، Template internals، Master-detail و Version identity. پنجاه Golden fixture مربوط به این ۱۱ سطح طراحی شده اما اجرا صفر است. Packet بیست‌فیلدی باید Source/Target receipts، Key sets و Delta manifest را به نسخه‌های Policy متصل کند. اکنون پذیرش ۰/۱۱، اجرا ۰/۵۰، Formula approval/Result parity/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

Triage دقیق Identity نشان داد ۶۰ Endpoint بدون declaration شامل ۳۱ POST، شش PUT، یک DELETE و ۲۲ GET است. در ۳۸ Mutation، سی مورد هیچ Named signal، پنج مورد فقط Authorization data و سه مورد فقط Identity context دارند؛ Named authorization decision صفر است. این شواهد Gap verification است و anonymous reachability یا Incident را ثابت نمی‌کند.

هر ۵۸ Scope mismatch مشاهده‌شده از `membership_user_scope_mismatch` است. Admin short-circuit، Permission repository بدون owner filter و سه Resource/Action mapping مفقود جدا نگه داشته شدند؛ mapping مفقود Fail-closed availability gap است نه Grant. هفت Lane با مجموع ۱۳۹ واحد مرکب برای Endpoint، Scope، Mapping، Admin policy، Repository و Route تعریف شد؛ disposition و آزمون هر Endpoint دوباره‌شماری نشده است. پذیرش ۰/۱۳۹، ۱۸۴ Role UAT فقط طراحی، Runtime authorization/Security approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

یک Addendum تشخیصی بدون تکرار بیست Playbook عملیاتی موجود ساخته شد. هشت Scenario جدید Metadata drift، تمرکز Scope mismatch، POS graph truncation و SCC cascade، Report keyset/grain mismatch، Template formula unknown، Null/Sign/Rounding/Currency policy delta و Packet supersession را پوشش می‌دهند. هر سناریو حداقل ده Step، Evidence request، Role escalation و Stop condition دارد.

خروجی تشخیص فقط `EXPECTED_BOUNDARY`، `STATIC_EVIDENCE_GAP`، `DATA_OR_CONFIGURATION_DEBT`، `CONTRACT_OR_IMPLEMENTATION_DEFECT` یا `UNPROVEN` است. هیچ Runtime diagnosis، Repair، Replay، Grant، Query/Command execution یا Approval synthesis انجام نشده؛ Packet acceptance و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

ممیزی Golden/UAT روشن کرد که ۱۲۲۹ یک Snapshot معتبر ولی قدیمی‌تر است: ۱۱۸۷ Design ماژولی و ۴۲ Design پلتفرم. پنج ماژول Artifactهای جدید با `existing_reused` دقیقاً برابر Base دارند: Organization +۳۵، Identity +۴۲، Configuration +۲۸، Master Data +۳۵ و Integration +۳۵. Delta غیرتکراری دقیق ۱۷۵ و lower bound فعلی طراحی ۱۴۰۴ است.

پلتفرم دوباره‌شماری نشد. Pricing، Distribution، Treasury، Accounting و Reporting به‌دلیل mismatch در reuse-base، Case-set باریک‌تر یا overlap حل‌نشده صفر به lower bound اضافه می‌کنند تا Crosswalk سطح Case/semantic obligation ساخته شود. ۱۴۰۴ نه Final exhaustive count است و نه Execution/Approval؛ UAT اجرا، Owner approval و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.
## Golden/UAT Cross-Gate Refinement ـ ۲۰۲۶-۰۸-۲۹

برای جلوگیری از تورم شمارش، ۳۲ سناریوی دقیق Identity/POS/Report/Handoff به‌عنوان refinement تعهدهای موجود ثبت شدند، نه Case افزایشی. هر سناریو شرط Pass/Failure، حالت پیش‌فرض `UNPROVEN` و پنج Receipt لازم دارد. lower bound طراحی ۱۴۰۴ ثابت است و هیچ اجرا، پذیرش یا ارتقای آمادگی از این طراحی استنتاج نمی‌شود.

Crosswalk پنج ماژول unresolved نشان داد baseline فقط Count تجمیعی نیست و از هفت منبع می‌توان ۵۱۱ Case ID یکتا بازسازی کرد. مجموعهٔ جدید ۳۰۲ Case یکتا دارد؛ ۶۴ ID قیمت‌گذاری دقیقاً reuse است، اما ۴۴۷ baseline و ۲۳۸ newer unmatched باقی می‌مانند. ۳۰ تطبیق action+kind صرفاً کاندید است، نه معادل‌بودن معنایی؛ بنابراین عدد ۱۴۰۴ افزایش نمی‌یابد.

در ۳۰ کاندید Distribution/Treasury، Action و Kind برابر است ولی فقط ۵ Outcome label و صفر Assertion list برابری کامل دارند. پس هیچ Semantic alias خودکار پذیرفته نمی‌شود؛ همهٔ موارد نیازمند disposition نقش پاسخ‌گو هستند و شمارش/آمادگی تغییر نمی‌کند.

صف باقیمانده ۲۰۸ Case در ۳۴ Action است: ۲۰۳ مورد Alias نسخه‌دار Action/Surface می‌خواهند و ۵ مورد Action موجود با Kind یا multiplicity پوشش‌داده‌نشده دارند. هیچ موردی پیش از disposition سطح Case به عدد ۱۴۰۴ اضافه نمی‌شود.

پنج Kind/Multiplicity gap با ۱۳ Case پایهٔ نزدیک cross-check شد. سه مورد Kind تازه و دو مورد failure-stage multiplicity هستند؛ هیچ Outcome یا Assertion برابری کامل ندارد. بنابراین همه نیازمند disposition مالک و اثر شمارشی صفرند.

۲۰۳ Case نیازمند Alias در ۲۹ Action گروه‌بندی شد؛ هر Action هفت Case، دو نقش پاسخ‌گو و ده فیلد evidence دارد. هیچ Packet یا Case disposition پذیرفته نشده و شباهت نام به‌تنهایی پذیرش را منتقل نمی‌کند.

برای تحویل evidence، همین ۲۹ Packet بدون تغییر مجموعهٔ ۲۰۳ Case در پنج اولویت risk-first مرتب شدند: P0=۷/۴۹، P1=۸/۵۶، P2=۶/۴۲، P3=۵/۳۵ و P4=۳/۲۱. اولویت فقط ترتیب review است؛ ۵۸ role assignment به معنای انتساب مالک حقیقی نیست و acceptance/execution/readiness همچنان صفر است.

جست‌وجوی baseline برای هفت Packet P0 سه Packet دارای کاندید و چهار Packet explicit-none داد. یک Action دقیق stock-voucher فقط در scope ماژول Inventory موجود است؛ پنج reference دیگر lifecycle-family برای reverse bank-reconciliation و delete received-cheque هستند. مجموعاً شش Action/۹۲ Case/۳۷ kind-overlap صرفاً shortlist داوری‌اند و Semantic equivalence یا پذیرش ایجاد نمی‌کنند.

مقایسهٔ case-pair شش کاندید P0 تعداد ۶۶ جفت هم‌نوع ساخت؛ ۲۰ جفت Failure Injection است. precondition دقیق صفر، outcome دقیق دو، assertion-list دقیق صفر و full match صفر است. پس حتی دو outcome برابر received-cheque نیز بدون هم‌ارزی شرط و assertion قابل reuse نیستند.

۲۰ جفت Failure Injection به سه Packet داوری تبدیل شد. فقط دو stage label برابر و ۱۸ نگاشت generic-to-detailed است؛ ۱۵ baseline pair retry/convergence، ۱۵ pair منع partial effect و هفت pair حساس به audit/outbox دارند. بدون receipt تراکنش، durable write-set، rollback/unknown outcome و retry هیچ Alias پذیرفته نمی‌شود.

۴۶ جفت غیرخطای P0 در شش کنترل تفکیک شدند. outcome vocabulary جدید فقط هشت label جهانی در برابر ۲۳ عبارت baseline دارد؛ `REJECTED_NO_EFFECT` در ۲۳ جفت و committed-original-once در ۱۱ جفت متمرکز است. دو label برابر `COMMITTED` نیز assertion/full match ندارند و قابل پذیرش خودکار نیستند.

مقایسهٔ دوازده خانوادهٔ assertion/effect روی ۶۶ جفت، صفر family-set برابر، ۶۵ overlap و یک no-overlap نشان داد. Audit/Outbox جدید ۶۶/۶۶ در برابر پایه ۵۰/۱۴، Source immutability جدید/پایه ۰/۵۳ و Transaction ۶/۲۹ است؛ بنابراین تفاوت صرفاً واژگانی نیست و disposition اثر لازم است.

Packetization جاری P0 برای هفت Action/۴۹ Case کامل است، ولی هر هفت semantic disposition باز است. چهار Packet بدون کاندید به Alias یا New-Action decision و سه Packet کاندیددار به equivalence decision بیرونی نیاز دارند؛ این مرز از هر ادعای acceptance/readiness جلوگیری می‌کند.

در P1، هشت Packet/۵۶ Case بررسی شد. قرارداد state-machine بانکی چهار نگاشت صریح `CancelSession`/`ConfirmSession`/`MatchInstrument`/`UnmatchInstrument` به capabilityهای baseline دارد که در مجموع ۷۶ Case و ۲۴ kind-overlap دارند؛ چهار Action حسابداری/خزانهٔ دیگر در baseline بازسازی‌شده explicit-none هستند. این command-to-capability mapping فقط شاهد shortlist است و بدون برابری precondition/outcome/assertion/effect، semantic equivalence یا پذیرش ایجاد نمی‌کند.

Comparator سطح Case برای چهار نگاشت بانکی P1 تعداد ۵۵ جفت هم‌نوع ساخت: Authorization پنج، Concurrency هفت، Failure Injection نوزده، Idempotency یازده، Scope نه و Success چهار. هیچ precondition، outcome، assertion-list یا ترکیب کامل برابری ندارد؛ بنابراین حتی lineage صریح state-machine نیز مجوز reuse نیست و همهٔ dispositionها باز می‌مانند.

در ۱۹ جفت Failure Injection بانکی P1، هیچ fault-stage برابری وجود ندارد. baseline برای ۱۵ جفت retry/convergence، برای ۱۶ جفت منع partial effect و برای ۹ جفت حساسیت audit/outbox را صریح می‌کند؛ در نتیجه برچسب‌های عمومی جدید نمی‌توانند تفاوت state-transition، link، cardex، cleanup و audit/outbox را بپوشانند.

در ۳۶ جفت کنترل P1، واژگان جدید سه label جهانی در برابر شانزده عبارت baseline دارد. ۲۱ جفت زیر `REJECTED_NO_EFFECT` و ۱۱ جفت زیر committed-original-once فشرده شده‌اند؛ outcome exact صفر است و همهٔ جفت‌ها به mapping صریح effect/denial/commit نیاز دارند.

در خانواده‌های assertion/effect P1، هر ۵۵ جفت overlap دارد ولی family-set برابر صفر است. عدم‌تقارن ۲۵۵/۸۰ assignment و تضاد Source immutability ۰/۵۵، Transaction ۰/۲۵ و Version concurrency ۵۵/۰ نشان می‌دهد lineage بانکی صریح، قرارداد اثر معادل تولید نکرده است.

Packetization جاری P1 برای هشت Action/۵۶ Case کامل است ولی semantic disposition هر هشت Packet باز می‌ماند. چهار explicit-none نیازمند Alias/New-Action decision و چهار نگاشت بانکی نیازمند Semantic-equivalence decision هستند؛ named owner، acceptance، اجرا، additive و readiness صفر است.

در P2، شش Action/۴۲ Case به پنج Packet کاندیددار و یک explicit-none تفکیک شد. هفت family Action شامل ۸۷ Case پایه و ۳۸ kind-overlap است؛ category normalization محدود برای مقایسهٔ pricing استفاده شد و هیچ exact action یا پذیرش معنایی ایجاد نکرد.

Comparator P2 تعداد ۷۳ جفت هم‌نوع از هفت Candidate ساخت؛ یک validate-transition candidate بدون kind قابل‌مقایسه ماند. دو outcome برابر در خانوادهٔ چک دیده شد، اما precondition/assertion/full exact صفر است و هیچ reuse خودکاری پذیرفته نمی‌شود.

در ۱۵ جفت Failure Injection P2، فقط دو stage label برابر است و سیزده جفت تفاوت stage دارد. baseline در ۱۰ جفت retry/convergence، ۱۰ جفت no-partial-effect و ۱۳ جفت audit/outbox sensitivity را صریح می‌کند؛ این اختلاف‌ها پذیرش family alias را مسدود می‌کنند.

در ۵۸ جفت کنترل P2، واژگان جدید شش label جهانی در برابر ۲۳ عبارت baseline دارد. ۳۸ جفت زیر `REJECTED_NO_EFFECT` فشرده شده‌اند؛ تنها دو outcome label عیناً برابر است، ولی assertion/full exact صفر است و ۵۶ جفت به mapping صریح effect/denial/commit نیاز دارد. این تطابق اسمی به acceptance یا readiness تبدیل نمی‌شود.

در خانواده‌های assertion/effect P2، از ۷۳ جفت فقط ۶۴ جفت overlap دارند، ۹ جفت بدون overlap و family-set برابر صفر است. عدم‌تقارن ۴۲۰/۹۷ assignment و تضاد Transaction ۰/۴۶، Version concurrency ۷۳/۱۴ و Outbox ۷۳/۱۴ نشان می‌دهد شباهت policy/lifecycle، قرارداد اثر معادل تولید نکرده است.

Packetization جاری P2 برای شش Action/۴۲ Case کامل است ولی semantic disposition هر شش Packet باز می‌ماند. یک explicit-none نیازمند Alias/New-Action decision و پنج candidate family نیازمند Semantic-equivalence decision هستند؛ named owner، acceptance، اجرا، additive و readiness صفر است.

در شروع P3، پنج Action گزارش/۳۵ Case به شش candidate reference و ۳۱ Case پایه متصل شد. دو سطح statement، سه command ثبت completion چاپ و یک export-file فقط candidate family هستند. normalization نسخه/هم‌زمانی و failure/partial-failure برای مقایسه، تفاوت Print، Export، Completion و Mutation یا نیاز به Result parity را حذف نمی‌کند؛ ۲۶ kind-overlap بدون پذیرش معنایی ثبت شد.

Comparator سطح Case برای شش candidate P3 تعداد ۳۸ جفت ساخت: شش Authorization، دو Concurrency، هجده Failure Injection، شش Idempotency و شش Success. هیچ precondition، outcome، assertion-list یا full exact وجود ندارد؛ expected-arrayهای پایه فقط assertion هستند و نبود outcome label نباید به تطابق ساختگی تبدیل شود.

در ۱۸ جفت Failure Injection P3، پانزده Case جدید Render/Completion/Partial در برابر شش failure contract پایه قرار گرفت و fault-stage دقیق صفر ماند. هر ۱۸ جفت recovery و unknown/partial disposition دارد؛ ۱۵ جفت Audit/Outbox و ۱۲ جفت File/Print/Completion-sensitive است. بنابراین normalization خطا هیچ مجوزی برای یکی‌کردن stage یا durable effect ایجاد نمی‌کند.

در ۲۰ جفت کنترل P3، سمت جدید سه outcome label جهانی دارد، اما baseline فقط assertion-array و outcome label خالی دارد. هشت جفت rejected-no-effect و شش جفت committed-original-once هستند؛ outcome/assertion/full exact صفر است و نبود label پایه نمی‌تواند Result/File parity یا semantic equivalence بسازد.

ماتریس effect ویژهٔ گزارش P3 شانزده خانواده دارد. هر ۳۸ جفت overlap عمومی دارد ولی family-set دقیق صفر و عدم‌تقارن ۱۷۴/۶۷ است. File/Artifact، Render/Completion و Per-item outcome در سمت جدید هرکدام ۳۸ جفت را پوشش می‌دهند، درحالی‌که baseline فقط ۶/۰/۰ دارد؛ Result/Content parity صریح نیز جدید/پایه ۰/۲ است. این gap نشان می‌دهد command-effect و report-result parity دو Gate جدا هستند.

Packetization جاری P3 برای پنج Action/۳۵ Case کامل است، اما هر پنج semantic disposition و Result parity باز می‌ماند. همهٔ Packetها به تصمیم مشترک Effect-equivalence و Frozen-fixture Result/Content parity نیاز دارند؛ named owner، acceptance، اجرا، additive و readiness صفر است.

در شروع P4، سه Export/۲۱ Case به سه candidate پایه و ۱۴ Case reference متصل شد: یک Read statement و دو Export-file. مالکیت ۳/۳ بسته است، اما Result parity هر سه applicable و proven صفر است؛ ownership closure یا kind-overlap ده‌تایی نمی‌تواند برابری export/result را ثابت کند.

Comparator P4 تعداد ۱۴ جفت ساخت: سه Authorization، شش Failure، دو Idempotency و سه Success. Precondition/outcome/assertion/full exact و Result parity همگی صفر است. دو جفت Read بانکی فقط دسترسی و happy-path را هم‌تراز می‌کنند و هیچ Export artifact یا result parity را ثابت نمی‌کنند.

Failure adjudication P4 فقط شش جفت برای دو Export-file دارد؛ Read بانکی فاقد failure/export pair است. هر شش baseline pair retry/recovery، partial-file quarantine، source immutability و file sensitivity دارد، ولی با stageهای Render/Completion/Partial جدید برابر نیست. نبود pair بانکی شکاف شواهد است، نه اثبات.

در هشت جفت کنترل P4، سه outcome label جدید در برابر baseline بدون outcome label صریح قرار دارد. سه rejected-no-effect و دو committed-original-once فقط واژگان طراحی‌اند؛ هر هشت جفت به تفکیک Read/Export/File/Result نیاز دارد و Result parity صفر می‌ماند.

ماتریس effect P4 هجده خانواده دارد: family-set دقیق صفر و عدم‌تقارن ۶۴/۲۱ است. File/Render/Per-item جدید ۱۴/۱۴/۱۴ در برابر baseline ۱۲/۲/۰، Result/Content parity صریح ۰/۴، Presentation integrity برابر ۲/۰ و Pinned query/watermark برابر ۶/۱ است. این تفاوت‌ها نیاز به Fixture/value parity مستقل را تأیید می‌کند.

Packetization P4 برای سه Export/۲۱ Case کامل است، اما یک Read candidate و دو Export-file همچنان به تصمیم Export-effect و Frozen-fixture Result parity نیاز دارند. semantic disposition، Result parity، acceptance، اجرا، additive و readiness هر سه Packet صفر است.

ماتریس cross-lane همهٔ P0 تا P4 را بدون تکرار تحلیل‌ها تجمیع کرد: ۲۹ Packet/۲۰۳ Case، ۲۰ candidate-bearing و ۹ explicit-none. مسیر تصمیم ۹ Alias/New-Action، ۱۲ Semantic Equivalence، پنج Effect+Result و سه Export+Result است. از ۲۴۶ جفت فقط چهار outcome label برابر است و assertion/full/effect exact صفر؛ بنابراین هیچ Promotion خودکار مجاز نیست.

صف intake بیرونی این ۲۹ مسیر را به چهار قرارداد تحویل تبدیل می‌کند: Alias/New Action، Semantic Equivalence، Report Command Effect+Result و Export Effect+Result. توزیع caseها ۶۳/۸۴/۳۵/۲۱ است و برایشان ۲۹۰ receipt و ۱۵۰ اتصال gate تعریف شده است. این اعداد فقط حجم تعهد دریافت مدرک‌اند؛ مالک نام‌گذاری‌شده، receipt دریافت‌شده یا پذیرفته‌شده، semantic closure، result parity، UAT، owner approval و readiness همچنان صفر است و lower bound طراحی ۱۴۰۴ باقی می‌ماند.

برای جلوگیری از ورود مدرک مبهم یا حساس، ۲۹۰ requirement به slotهای یکتا گسترش یافت. هر slot چهارده metadata، gateهای قابل‌اعمال، چهارده کد رد و ماشین وضعیت هشت‌حالته دارد. فقط `ROLE_ACCEPTED` می‌تواند در closure بعدی لحاظ شود و آن هم به‌تنهایی equivalence یا readiness نیست. وضعیت فعلی همهٔ slotها `MISSING` است و هیچ receipt خارجی در artifact ذخیره نشده است.

Worklist نقش‌محور ۱۳ نوع نقش را پوشش می‌دهد. چون هر Packet دو نقش پاسخ‌گو دارد، ۲۹ Packet/۲۰۳ Case/۲۹۰ slot به ۵۸/۴۰۶/۵۸۰ assignment تبدیل می‌شود؛ این تکرار مسئولیت است، نه افزایش scope. انتساب واقعی به roster ده‌فیلدی و conflict-of-interest attestation وابسته است. همهٔ worklistها فعلاً `UNASSIGNED_NAMED_OWNER` هستند و هیچ نام یا دادهٔ هویتی ذخیره نشده است.

اولین activation design روی P0 ساخته شد: هفت Packet/۴۹ Case، چهار مسیر Alias/New Action و سه مسیر Semantic. سه کاندید ۶۶ جفت دارد که فقط دو outcome label برابر و full/effect exact صفر است. هر Packet ده receipt، دو نقش، پنج gate و هفت prerequisite دارد؛ همهٔ آن‌ها بازند و activation فقط برای جمع‌آوری مدرک redacted تعریف شده، نه اجرای وارانگار.

Sequencing باقی‌مانده P1 تا P4 شامل ۲۲ Packet/۱۵۴ Case، ۱۷ کاندید و پنج explicit-none است. توزیع مسیر ۵/۹/۵/۳ و بار شواهد ۲۲۰ receipt، ۴۴ role و ۱۱۵ gate assignment است. هشت Packet گزارش/Export در P3/P4 به CG-05 وابسته‌اند؛ موفقیت فرمان، چاپ یا ساخت فایل هیچ‌گاه جای برابری frozen-fixture در value/rowset/render/file را نمی‌گیرد.

ممیزی classifier نشان داد receipt مرکب failure-stage/per-item-outcome به‌علت تک‌کلاسه‌بودن فقط زیر Transaction قرار می‌گرفت و CG-05 را از دست می‌داد. مدل receipt به class-set و union gate اصلاح شد: ۱۴ slot چندکلاسه و ۲۷ slot CG-05 داریم؛ پنج مورد P3 هم‌زمان CG-02/03/05/04 هستند. ماتریس P3/P4 اکنون هشت Packet/۵۶ Case را به ۲۰ بُعد و ۱۶۰ disposition وصل می‌کند. File/Render/Per-item جدید هرکدام ۵۲ جفت دارد، پایه ۱۸/۲/۰ و Result parity صریح جدید/پایه ۰/۶ است؛ بنابراین closure همچنان صفر است.

برای همان هشت فرمان P3/P4، قرارداد Frozen Fixture/Output تمام ۵۶ Case را با سه schema شانزده‌فیلدی Fixture، Output و Comparison پوشش می‌دهد. ۵۱۲ field assignment، ۱۶ سمت Capture، ۵۶ acquisition assignment، ۱۶۰ اتصال بُعد parity و ۲۷ receipt زیر CG-05 تعریف شده است. این فقط قرارداد metadata است؛ هیچ مقدار تجاری، خروجی واقعی، Capture، Comparison، Acceptance یا Runtime proof ثبت نشده است.

Playbook اختلاف Result parity ده سناریو و حداقل ۱۰۰ step را به ۷۲ Packet assignment، ۵۰۴ Case cross-link و ۳۴ parity-dimension link تبدیل می‌کند. چهار outcome میان match مبتنی بر hash پذیرفته‌شده، استثنای versioned و owner-approved، شاهد نامعتبر/کهنه و اختلاف توضیح‌نداده‌شده تفکیک می‌شوند. وضعیت فعلی `DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION` است؛ Repair، Replay، Recapture، Promotion، Execution و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

ممیزی زنجیرهٔ تست یک چرخهٔ self-reference را آشکار کرد: نتیجهٔ رسمی ورودی Bundleها بود، اما Runner نهایی پس از ثبت `FAIL` راه bootstrap صریح نداشت. Runner با حالت recovery غیرپیش‌فرض، شمارندهٔ exclusion و الزام نتیجهٔ نهاییِ full-glob/zero-exclusion اصلاح شد. تنها re-extract متصل به Share شبکه نیز از suite آفلاین حذف و با آزمون محلی parse/static-IL contract جایگزین شد؛ hashهای pin‌شده و منع Load/Execute حفظ شد. اجرای کامل بازیابی‌شده روی ۳۰۸ فایل، ۱۵۰۹ تست و exclusion صفر PASS شد.

ماتریس داوری P3/P4 چهار Outcome را برای هشت Packet/۵۶ Case به ۳۲ Route و ۲۲۴ Outcome-to-Case assignment تبدیل کرد. دوازده Promotion Guard برای هر Packet، یعنی ۹۶ assignment، زنجیرهٔ Manifest، Case-set، دو سمت Capture، key/grain، ۱۶۰ بُعد parity، ۲۷ Receipt CG-05، اختلاف، Exception policy، SoD، Version/Expiry، CG-04 UAT و تصمیم مستقل Readiness را کنترل می‌کنند.

فقط Match مبتنی بر hash پذیرفته‌شده می‌تواند وارد بازبینی پذیرش CG-05 شود و همان نیز Closure خودکار نیست. Exception حتی با Owner approval Result parity محسوب نمی‌شود و به Risk acceptance جداگانه نیاز دارد؛ شاهد stale تصمیم نمی‌سازد و اختلاف توضیح‌نداده‌شده Hard Block است. اکنون Route داوری‌شده، ورود به Review، Closure، Owner approval، UAT، Command readiness و Pilot readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

قرارداد Comparison Adapter مقصد برای همان هشت Packet/۵۶ Case، هشت Profile دارد. هر Profile یک Input envelope هجده‌فیلدی و Receipt خروجی هجده‌فیلدی را از دوازده مرحلهٔ canonicalization عبور می‌دهد؛ در مجموع ۲۸۸ field assignment، تعداد ۹۶ stage assignment، شانزده Error code و شش Typed status تعریف شده است. این قرارداد به ۱۶۰ بُعد parity، تعداد ۲۷ Receipt زیر CG-05 و ۹۶ Promotion Guard متصل است.

Digest با SHA-256 و domain separation طراحی شده، type tagها و Null/Missing/Empty/Zero/Unknown متمایزند، Decimal فقط با Scale/Rounding policy نسخه‌دار canonical می‌شود، Float serialization ممنوع است و Set hash از Order hash جداست. کلید Idempotency پنج جزء نسخه/Profile، Fixture، Legacy output، Target output و Dimension-set دارد؛ ورودی تکراری Receipt hash قبلی را برمی‌گرداند و همان Key با ورودی متفاوت Conflict است.

Persist فقط برای Reference، Hash، Count دسته‌ای، Status و Receipt مجاز است؛ Row/Item، مقدار تجاری، شناسه، فایل، پارامتر، Credential، SQL/Rule و Endpoint خام ممنوع‌اند. Implementation، Request، Run، Receipt، Parity، Execution و Readiness صفر است؛ پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ تغییر نکرده است.

بستهٔ آزمون Adapter همان هشت Profile را با دوازده بردار canonical مثبت و شانزده بردار خطای منفی پوشش می‌دهد؛ در مجموع ۲۸ بردار، ۲۲۴ انتساب Profile-to-Vector و دوازده digest مورد انتظار داریم. digestها فقط از tokenهای مصنوعی، JSON canonical، SHA-256 و domain separation ساخته شده‌اند و taxonomy خطاهای منفی دقیقاً با شانزده Error code قرارداد Adapter هم‌تراز است.

اصالت Receipt یک قرارداد جدا از Result parity است: شانزده فیلد metadata، هشت نتیجهٔ verification، شش وضعیت چرخهٔ کلید، هشت قاعدهٔ rotation و ده مرحلهٔ verification تعریف شده است. الگوریتم امضا و key provider هنوز انتخاب نشده‌اند و باید با تصمیم مستقل Platform/Security بسته شوند؛ Artifact هیچ private/public key material، signature bytes، credential یا مقدار تجاری ندارد. فقط `AUTHENTIC_CURRENT` مجوز ورود به داوری مستقل را دارد و حتی آن نیز نتیجهٔ برابر، CG-05 closure، UAT یا readiness را ثابت نمی‌کند. Signing، Verification، Acceptance، Parity و Execution همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

Harness مرجع آفلاین برای بردارهای Comparison Adapter، دوازده بردار مثبت را در هر هشت Profile به ۹۶ محاسبهٔ domain-separated SHA-256 تبدیل کرد و همه PASS شدند. شانزده بردار منفی در هر Profile نیز فقط به‌صورت ۱۲۸ lint عضویت taxonomy بررسی و PASS شدند؛ این بخش fault injection یا اجرای Adapter نیست. نتیجه فقط بازتولیدپذیری digest مصنوعی و هم‌ترازی کد خطا را ثابت می‌کند، نه رفتار ERP یا Result parity.

Decision Record رمزنگاری چهار Candidate الگوریتم RSA-PSS، ECDSA P-256، Ed25519 و ML-DSA مهاجرتی را کنار چهار الگوی KMS غیرقابل‌استخراج، HSM، Keystore پلتفرم و Signing Service مستقل قرار می‌دهد. چهارده معیار برای هر هشت Candidate، یعنی ۱۱۲ انتساب، و ده Gate مالک/امنیت/انطباق/Threat Model/Provider/Benchmark/Rotation-DR/Crypto Agility/UAT تعریف شد. مطابق FIPS 186-5، SP 800-57، RFC 8017/8032، NIST CSWP 39upd1 و FIPS 204، انتخاب باید محیط‌محور و نسخه‌دار باشد؛ هیچ Candidate خودکار انتخاب نشد. Key، Signature، Signing/Verification، Adapter runtime، Receipt acceptance، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

Reference Codec مصنوعی محدودیت lint-only خطاها را به اجرای محلی قرارداد ارتقا داد: هشت Baseline سالم ۸/۸ و شانزده Mutation تک‌فیلدی برای هر Profile، یعنی ۱۲۸/۱۲۸ اجرای منفی، Error code و Typed status مورد انتظار را برگرداندند. ترتیب شانزده خطا ثابت و fail-fast است و در حالت چندخطایی اولین خطای قرارداد انتخاب می‌شود. Codec فقط Boolean، Count، Status و token مصنوعی دارد، I/O و Receipt emission ندارد و Trigger ناشناخته را رد می‌کند.

این یک Reference implementation محدود است، نه Adapter عملیاتی ERP مقصد. بنابراین فقط `reference_codec_implementation_count=1` شد؛ Operational adapter implementation/run، Legacy/Target capture، Receipt، Acceptance، Result parity، CG-05، UAT و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

مرز مجوز Capture ایزوله اکنون برای هشت Packet/۵۶ Case صریح است: هر Packet دو Channel جدا برای `LEGACY_REFERENCE` و `TARGET_CANDIDATE` دارد و تأیید یک سمت به دیگری سرایت نمی‌کند. شانزده Channel با schema درخواست ۲۴فیلدی و Redaction attestation هجده‌فیلدی، چهارده Gate و ۲۲۴ assignment، شش Role و ۹۶ assignment و پنج قاعدهٔ SoD تعریف شد.

Gateها Scope/Case/Dimension دقیق، محیط ایزوله، Read-only بودن Legacy، non-production بودن Target، منع egress، allowlist فرمان، توکن جدا، time-window/attempt/TTL محدود، SoD، Policy pinning، scan fail-closed، persistence فقط hash/count/status/reference، نابودی مواد موقت و abort/revoke/incident را کنترل می‌کنند. چهارده دسته شامل مقدار تجاری، Row، هویت/PII، Credential، SQL/Rule، فایل، Endpoint، Session، Key/Signature، نمونهٔ خام، Screenshot و Backup/Log ممنوع است. همهٔ Channelها `NOT_REQUESTED`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ Authorization، Capture، Attestation، Receipt، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

ماتریس Handoff، شانزده Capture Channel را به هشت Pair Legacy/Target و هشت Adapter Profile متصل می‌کند. ۲۷ Receipt slot زیر CG-05 اکنون ۵۴ Channel link و بیست بُعد parity تعداد ۳۲۰ Channel link دارد؛ Profile-to-Channel نیز شانزده link است. Envelope بیست‌فیلدی فقط Authorization/Attestation/Custody reference، hash مجموعه‌های Case/Dimension/Receipt، hash manifest و Policy version و expiry/status را می‌پذیرد.

دوازده Gate برای هر Pair، یعنی ۹۶ assignment، فعال‌بودن مجوز دو سمت، پذیرش مستقل Redaction، برابری Case/Dimension set، pin شدن Profile/Policy، scan دسته‌های ممنوع، نابودی مواد موقت، custody معتبر و Idempotency بدون تعارض را الزام می‌کند. Payload transfer صریحاً ممنوع است. همهٔ Pairها `NOT_READY_NO_AUTHORIZED_CAPTURE` و Gateها `UNMET` هستند؛ Ready handoff، Adapter request، Comparison، Receipt، Parity، CG-05 و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

زنجیرهٔ Custody برای ۵۴ اتصال Channel-to-Receipt به requirementهای مستقل گسترش یافت. هر requirement schema بیست‌فیلدی، نه State، دوازده Transition، ده Gate و چهار Role دارد؛ در کل ۵۴۰ Gate assignment و ۲۱۶ Role assignment داریم. مسیر عادی `MISSING → CREATED_HASH_ONLY → TRANSFER_PENDING → IN_CUSTODY → REVIEW_PENDING → ACCEPTED_CURRENT` است و Expired/Revoked/Superseded برای Handoff معتبر نیستند.

Retention با هشت Rule نسخه‌دار و محدود است: expiry تمدید خودکار ندارد، revocation Gate وابسته را باز می‌کند، supersession لینک hash دوطرفه می‌خواهد، مواد موقت پیش از پذیرش نابود می‌شوند و disposition فقط hash-only tombstone و lineage را نگه می‌دارد. دوازده Rejection code شکست Authorization/Redaction/Hash/SoD/Policy/Expiry/Revocation/Supersession/Raw/Destruction/Chain/Replay را پوشش می‌دهند. همهٔ requirementها `MISSING`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ Receipt، Accepted evidence، Handoff، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

اثر Invalidation اکنون با گراف صریح پوشش داده می‌شود. دوازده علت شامل expiry/revoke مجوز، رد/انقضای Redaction، expiry/revoke/supersede Custody، شکست hash chain، drift در Manifest/Case/Policy/Profile، اصالت نامعتبر و اختلاف نتیجهٔ تازه به ۵۴ requirement و ۶۴۸ assignment وصل‌اند. گراف ۵۴ Edge requirement-to-pair، تعداد ۵۴ requirement-to-profile، تعداد ۵۴ requirement-to-slot، تعداد ۹۶ pair-to-promotion-guard و ۲۷ slot-to-packet دارد؛ جمع ۲۸۵ Edge است.

هشت Reopen action به ترتیب Custody را non-current، Handoff را باز، Request Adapter را cancel/quarantine، Receipt را invalidate، Promotion Guard را باز، Recapture و Readjudication مستقل را لازم و Readiness را Block می‌کند. Reacceptance، Recapture، Replay یا Repair خودکار مجاز نیست. همهٔ ۶۴۸ assignment `NO_EVENT_OBSERVED` هستند؛ Invalidation، Reopen، Reacceptance، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

Freshness شواهد با Evaluator مرجع بدون I/O و Clock ثابت آزمون شد. چهار نوع Capture Authorization، Redaction Attestation، Custody Receipt و Comparison Handoff، هشت Outcome و دوازده Vector دارد؛ ۴۸/۴۸ اجرای مصنوعی PASS شد. `valid_from` inclusive و `expires_at` exclusive است؛ Timestamp باید timezone-aware باشد، Interval معکوس و Clock نامطمئن fail-closed است، Policy mismatch مستقل گزارش می‌شود و Revocation/Supersession بر زمان مقدم‌اند.

برای ۵۴ Custody requirement و چهار نوع Artifact تعداد ۲۱۶ Freshness obligation ساخته شد. وضعیت همه `MISSING_TEMPORAL_EVIDENCE` و Real clock evaluation صفر است. حتی `CURRENT` نیز فقط زمان‌مندی را ثابت می‌کند و Acceptance، Handoff، Parity یا CG-05 نیست. Current evidence، Accepted freshness، Handoff، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

ریسک R-019 با یک قرارداد مستقل برای شاهد تمرین Backup/Restore مقصد دقیق‌تر شد. چهارده ماژول به شش کلاس دارایی ـ store تراکنشی، فایل/شیء، تنظیم/سیاست، audit/outbox/inbox/idempotency، read model/search و ارجاع کلید/secret/external ـ وصل شدند؛ در نتیجه ۸۴ تعهد بازیابی داریم. این طبقه‌بندی وجود Backup را از توان Restore جدا می‌کند و هیچ‌کدام را از روی طراحی استنباط نمی‌کند.

دوازده سناریوی تمرین برای هر ماژول، یعنی ۱۶۸ انتساب، full isolated restore، point-in-time، خرابی یا کمبود قطعه، drift نسخه، نبود ارجاع کلید، replay پیام، rebuild نمای خواندنی، reconciliation بین‌ماژولی، نقض RPO/RTO و abort/cleanup/repeat را پوشش می‌دهد. هدف‌های RPO/RTO هنوز تصویب نشده‌اند و service start یا schema load نتیجهٔ موفق محسوب نمی‌شود؛ موفقیت نیازمند reconciliation و شاهد اندازه‌گیری‌شده است.

قرارداد هجده فیلد هدف، بیست فیلد شاهد، چهارده Gate با ۱۹۶ انتساب و پنج Role با ۷۰ انتساب دارد. همهٔ هدف‌ها `UNAPPROVED`، سناریوها `UNEXECUTED`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند. هیچ Backup set ساخته یا خوانده نشده، Restore در Production ممنوع است و Restore run/pass/reconcile، Owner approval، Recovery readiness، Command readiness و Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

DAG بازیابی از `depends_on` چهارده ماژول Blueprint محاسبه شد: ۳۸ Edge در هفت موج قرار می‌گیرد و `platform` تنها عضو موج صفر است. هر Edge به‌صورت ماشینی بررسی شد که upstream در موجی زودتر از downstream قرار دارد. موازی‌سازی فقط میان اعضای یک موج بدون Edge وابستگی مجاز است و Wave promotion به reconcileشدن موج‌های پیشین وابسته است، نه صرفاً شروع یا بالا آمدن سرویس.

ده مرحلهٔ بازیابی برای هر ماژول ۱۴۰ انتساب می‌سازد. چهار بُعد Reference/Pointer، Aggregate/Content hash، Outbox/Inbox/Idempotency/Watermark و Invariant مالی/عملیاتی برای هر ۳۸ Edge، ۱۵۲ تعهد تطبیق ایجاد می‌کند. چهارده Gate در هفت موج ۹۸ انتساب و پنج Role در هفت موج ۳۵ انتساب دارد؛ Receipt تطبیق بیست فیلد و نه Outcome دارد.

Read model منبع authoritative Restore نیست، Replay پیش از تطبیق Idempotency ممنوع است، `blocking_unknown` یا اختلاف بازبینی‌نشده Service enablement را می‌بندد و Production restore و promotion خودکار ممنوع‌اند. همهٔ موج‌ها `NOT_STARTED_NO_AUTHORIZED_REHEARSAL`، Stageها `UNEXECUTED`، Edgeها `UNRECONCILED_NO_RESTORE_EVIDENCE`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ Restore، Reconciliation، Enablement و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Blueprint چهارده ماژول در مجموع ۴۹ فرمان دارد. قرارداد یکنواخت قابلیت‌اعتماد هر فرمان را به Envelope بیست‌ودوفیلدی، Receipt idempotency بیست‌فیلدی، Outbox شانزده‌فیلدی و Inbox چهارده‌فیلدی متصل کرد. Evidence فقط hash/reference/count/status است و payload یا مقدار تجاری خام اجازهٔ persistence ندارد.

چهارده Failure stage برای هر فرمان، یعنی ۶۸۶ انتساب، از رزرو Key و transaction میانی تا Commit نامعلوم، گم‌شدن response، انتشار/مصرف تکراری و Recovery replay را پوشش می‌دهد. هشت بُعد convergence برای ۴۹ فرمان ۳۹۲ انتساب دارد؛ شانزده Gate تعداد ۷۸۴ و پنج Role تعداد ۲۴۵ انتساب می‌سازد. ده Outcome میان commit نخست، replay برابر، key/payload conflict، rollback، commit unknown، publication pending، duplicate consumer و quarantine تفکیک می‌کند.

قاعدهٔ قطعی این است که same-key/same-fingerprint Receipt نخست را برگرداند و same-key/different-fingerprint Conflict شود؛ attempt یا retry Key را تغییر نمی‌دهد. Effect، Receipt و Outbox باید یک transaction owner داشته باشند، Commit نامعلوم پیش از reconciliation قابل retry کور نیست، duplicate consumer اثر تازه نمی‌سازد و Replay بازیابی تا تطبیق Restore/Watermark بسته می‌ماند. Implementation، Fault injection، Replay proof، Outbox atomicity، Inbox convergence، Unknown reconciliation، Owner approval و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

برای روشن‌کردن مالکیت تراکنش، ۳۸ Edge ماژولی در سطح ۴۹ فرمان به ۱۵۹ تعهد Command-to-Participant تبدیل شد. چهار Pattern `LOCAL_ATOMIC_SINGLE_MODULE`، `LOCAL_ATOMIC_WITH_TRANSACTIONAL_OUTBOX`، `DURABLE_SAGA_WITH_IDEMPOTENT_COMPENSATION` و `MANUAL_QUARANTINED_RECOVERY_FOR_NONCOMPENSABLE_EFFECT` برای هر فرمان، جمعاً ۱۹۶ Candidate، ثبت شد و هیچ‌کدام خودکار انتخاب نشد.

مرز تراکنش ۱۸ فیلد، Receipt گام Saga بیست فیلد و Receipt جبران ۱۸ فیلد دارد. دوازده Failure stage برای ۴۹ فرمان ۵۸۸ انتساب، شانزده Gate تعداد ۷۸۴ و شش Role تعداد ۲۹۴ انتساب ایجاد می‌کند. ده Outcome بین Commit/Rollback محلی، Commit نامعلوم، پیشرفت Saga، نیاز/موفقیت/شکست Compensation و Partial invariant تفکیک می‌کند.

Distributed transaction پیش‌فرض نیست، cross-module direct table write ممنوع است و موفقیت Child/Participant موفقیت Parent محسوب نمی‌شود. Effect خارجی فقط پس از Commit و Receipt پایدار محلی، Commit نامعلوم فقط پس از reconciliation، و Compensation به‌عنوان Business action مستقلِ idempotent/versioned/audited مجاز است؛ Effect غیرقابل‌جبران یا نامعلوم قرنطینه و مالک انسانی می‌خواهد. Pattern selection، مالک نام‌دار، Fault run، Runtime atomicity، Saga/Compensation acceptance و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Authorization مقصد ۴۹ فرمان را به دوازده بُعد وصل می‌کند: Principal/Session، Tenant، Organization، Fiscal/Operation context، Location، Action/Capability، Resource/Row owner، Aggregate state، Threshold، SoD، Policy freshness/deny-wins و Repository enforcement. این مدل ۵۸۸ انتساب دارد. چهارده Negative case برای هر فرمان، یعنی ۶۸۶ انتساب، مسیرهای session نامعتبر، scope mismatch، state/threshold، self-approval، admin bypass، stale policy، client-only bypass و bulk mixed-scope را پوشش می‌دهد.

Decision Trace بیست‌ودو فیلد فقط hash/reference/status نگه می‌دارد. شانزده Gate برای ۴۹ فرمان ۷۸۴ انتساب و پنج Role تعداد ۲۴۵ انتساب دارد؛ ده Outcome یک Allow جاری و کامل را از انواع Deny جدا می‌کند. Default deny و explicit deny-wins است؛ Admin یا Role name bypass ندارد، UI/Route مجوز نیست، Service check بدون Repository scope کافی نیست، self-approval و partial bulk success ممنوع و stale/revoked policy مردود است.

دو baseline تاریخی Role/SoD و Route Authorization مطابق قالب قدیمی فیلد `validation` ندارند؛ هویت Artifact و schema آن‌ها pin شد و فقط منابع جاری ملزم به `PASS` هستند. هیچ حق تجمیعی Legacy یا وجود کد/Route به Grant مقصد تبدیل نشد. Implementation، Authenticated UAT، Allow/Deny receipt، Repository scope proof، Route-to-repository coverage، Runtime authorization و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

ده کانال Evidence شامل Command/Auth/Transaction/Idempotency/Error/Report/Recovery/Migration/Security/Observability برای ۴۹ فرمان به ۴۹۰ انتساب متصل شد. چهارده کلاس Credential، Token، PII، Identifier، Commercial value، Payment، Payload، SQL/Rule، File، Endpoint، Key/Signature، Stack/Dump و Backup/Log/Message/Export raw در هر کانال، یعنی ۱۴۰ سیاست، `DENY_PERSIST_FAIL_CLOSED` هستند. فقط هشت کلاس domain-separated hash، opaque reference، aggregate count، status، version hash، time boundary، role type و boolean gate مجاز است.

Redaction attestation بیست فیلد و Retention record شانزده فیلد دارد. چهارده Negative vector در ده کانال ۱۴۰ انتساب، شانزده Gate تعداد ۱۶۰ و پنج Role تعداد ۵۰ انتساب می‌سازد. Unknown field یا nested payload، Stack/argument خام، metric label حساس یا بی‌کران، trace baggage غیرallowlist، hash بدون domain separation، endpoint/file/backup/message/export body و scanner/schema failure همگی emission را می‌بندند.

Expiry خودکار تمدید نمی‌شود، revoked/superseded evidence قابل‌پذیرش نیست و disposition فقط hash-only tombstone و lineage را نگه می‌دارد. هیچ Log، Trace، Backup، Message، Export، File یا Runtime sample خوانده نشد. Implementation، Sample scan، Attestation، Retention approval، Disposition proof، Incident closure و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

برای آزمون بازتولیدپذیر قرارداد Redaction، یک Reference Validator خالص و بدون I/O ساخته شد. Envelope دقیقاً هشت فیلد domain hash، opaque reference، aggregate count، status، version hash، observed-at timezone-aware، role type و gate boolean دارد. Field ناشناخته/تو‌در‌تو، field-set ناقص، hash/reference/type نامعتبر و سیزده گروه فیلد ممنوع fail-closed رد می‌شوند.

ده Baseline مصنوعی ۱۰/۱۰ PASS و چهارده Mutation تک‌فیلدی برای هر ده کانال، یعنی ۱۴۰/۱۴۰، Error code مورد انتظار را برگرداندند؛ جمع اجرای مصنوعی ۱۵۰/۱۵۰ است. هر Mutation دقیقاً یک فیلد اضافه می‌کند و هیچ payload واقعی ندارد. این نتیجه فقط رفتار Reference contract را ثابت می‌کند، نه Sanitizer یا Logging pipeline عملیاتی.

`reference_validator_implementation_count=1` است، اما Operational logging/redaction implementation، Runtime sample scan، Accepted attestation، Command readiness و Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Cutover مقصد چهارده ماژول را در دوازده فاز Scope/Authorization، Snapshot boundary/manifest، Target baseline، Initial import، Delta capture/apply، Module/Cross-module reconciliation، Blocking-unknown closure، Owner approval، Rollback/Reentry و Source-fence/Target-enablement پوشش می‌دهد؛ جمع فازها ۱۶۸ انتساب است. دوازده بُعد Count/Hash/Reference/Pointer/Financial/Inventory/Payment/Lifecycle/Watermark/Report/Quarantine/Unknown نیز ۱۶۸ انتساب دارد.

Snapshot manifest بیست‌ودو فیلد، Delta batch receipt بیست فیلد و Cutover decision هجده فیلد دارد. هجده Gate در چهارده ماژول ۲۵۲ انتساب و شش Role تعداد ۸۴ انتساب می‌سازد. Delta range باید monotonic، gapless، non-overlapping و ordered باشد؛ Replay همان Batch فقط Receipt قبلی را برمی‌گرداند و Snapshot/Delta boundary نباید loss یا double-apply داشته باشد.

Clone یا Snapshot تاریخی هرگز بدون Authorization/Watermark جاری و Delta reconciliation «Live» نیست. `blocking_unknown` برای Schedule waive نمی‌شود، Operator نمی‌تواند reconciliation یا cutover خود را تأیید کند و Target writes پیش از Source fence و Receipt نهایی فعال نمی‌شود. Snapshot/Delta capture/read/apply، Reconciliation، Cutover، Write enablement و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

مرز محیط مقصد چهار کلاس دارد: Legacy عملیاتی فقط Reference خواندنی و هرگز Command target نیست؛ Sandbox فقط Candidate دادهٔ مصنوعی، UAT فقط Candidate ایزوله و Owner-authorized، و Production تا Promotion مستقل مسدود است. ۴۹ فرمان در چهار محیط ۱۹۶ assignment دارند و همگی `NOT_AUTHORIZED` هستند.

چهارده Write fence در چهار محیط ۵۶ انتساب و دوازده Negative case در ۴۹ فرمان ۵۸۸ انتساب دارد. Execution token بیست فیلد و به Environment/Module/Command/Tenant/Context/Resource/Fingerprint/Idempotency/Expected-version/Auth/Transaction/Redaction/Time/Single-use/Independent approval مقید است. هجده Gate تعداد ۸۸۲ و شش Role تعداد ۲۹۴ انتساب می‌سازد.

Environment از hostname/path/connection string استنباط نمی‌شود؛ Token Sandbox/UAT در Production قابل Replay نیست، expired/revoked/used/superseded مردود است، Break-glass/Admin تأیید مستقل را دور نمی‌زند و UAT success Production را خودکار promote نمی‌کند. هیچ Endpoint، Credential، Principal، Connection یا Token انتخاب/خوانده/صادر نشد و Token/Connection/Run/Fence attestation/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد انتشار مقصد دو گذار Sandbox→UAT و UAT→Production را برای چهارده ماژول به ۲۸ انتساب متصل می‌کند. هشت کلاس دارایی شامل بستهٔ برنامه، migration پایگاه‌داده، configuration/policy، authorization policy، report/document، observability/runbook، SBOM/provenance/signature و rollback/forward-fix/recovery است؛ مجموع آن‌ها ۱۱۲ انتساب و دوازده مرحلهٔ release تعداد ۱۶۸ انتساب دارد.

Release manifest بیست‌ودو فیلد، Change receipt بیست فیلد و Rollback receipt هجده فیلد دارد. دوازده Failure case در چهارده ماژول ۱۶۸ انتساب، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ انتساب می‌سازد. همان Artifact digest باید بدون rebuild میان محیط‌ها عبور کند؛ UAT acceptance هرگز Production approval نیست، invalid signature/provenance/SBOM و هر `blocking_unknown` promotion را fail-closed می‌بندد و Production operator حق self-approval ندارد.

بالا آمدن فرایند یا برنامه به‌تنهایی success نیست و Health/SLO و invariant کسب‌وکار باید جدا تأیید شوند. Migration بدون compatibility و rollback boundary مجاز نیست و rollback ناامن نباید دادهٔ forward-only را نابود کند؛ در چنین وضعی فقط forward-fix یا recovery کنترل‌شده قابل داوری است. هیچ secret یا endpoint در evidence قرار نمی‌گیرد و auto-promotion، auto-rollback و auto-readiness ممنوع است. Manifest/Artifact verification/Deploy/Promotion/Production approval/Rollback/Health acceptance/Owner approval/Command readiness/Pilot readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Observability مقصد دوازده کلاس Availability، Latency، Typed error/outcome، Saturation، Queue/Outbox/Inbox lag، Transaction unknown/partial effect، Idempotency conflict/replay، Authorization deny/scope mismatch، Reconciliation/result parity، Business invariant، Dependency/integration و Backup/restore freshness را برای چهارده ماژول به ۱۶۸ انتساب متصل می‌کند. دوازده مرحله از فریز scope/formula تا closure مستقل Incident نیز ۱۶۸ انتساب دارد.

SLI receipt و SLO policy هرکدام هجده فیلد، Alert receipt بیست فیلد و Incident receipt بیست‌ودو فیلد دارد. چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ انتساب ایجاد می‌کند. Process running معادل success نیست، Technical health معادل Business invariant نیست و Missing/Stale telemetry هرگز Healthy فرض نمی‌شود.

Label/Log/Trace حساس یا بی‌کران ممنوع است؛ SLO باید error budget و burn window کوتاه و بلند داشته باشد. Alert بدون Owner/Route/Runbook actionable نیست، Restart خودکار Incident را نمی‌بندد و Severity یا residual difference بدون Evidence کاهش یا waive نمی‌شود. هیچ Metric/Log/Trace/Health sample واقعی خوانده یا query نشد، Alert ارسال و Incident ایجاد نشد؛ SLI implementation/SLO approval/Alert route/Rehearsal/Runtime incident/Health receipt/Closure/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Configuration/Policy مقصد ده Scope از Global default و Environment تا Tenant/Organization/Fiscal/Location/Channel/Module/Feature-flag/Emergency override را برای چهارده ماژول به ۱۴۰ انتساب متصل می‌کند. دوازده نوع Business/Auth/Pricing/Accounting/Inventory/Payment/Report/Workflow/Retention/Integration/Feature-flag/Observability policy و دوازده مرحلهٔ change lifecycle هرکدام ۱۶۸ انتساب دارند.

Snapshot بیست‌ودو فیلد، Change receipt بیست‌وچهار، Evaluation trace بیست و Emergency override بیست فیلد دارد. چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و هفت Role تعداد ۹۸ انتساب ایجاد می‌کند. تغییر درجا یا حذف تاریخچه ممنوع است؛ precedence باید قطعی و deny-wins، effective-time پس از approval و rollback فقط فعال‌کردن یک نسخهٔ immutable باشد.

Secret/Endpoint/Sensitive value فقط reference می‌شود؛ UAT acceptance مجوز Production نیست، Feature flag حق bypassکردن Authorization/SoD/invariant ندارد و Emergency override باید زمان‌دار، جداگانه تأییدشده، قابل‌لغو و reconcileشده باشد. Stale cache یا partial fleet activation سالم نیست. هیچ Config/Feature flag/Secret/Cache عملیاتی خوانده و هیچ Change/Rollback/Override اجرا نشد؛ Snapshot/Evaluation/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Data provenance دوازده کلاس Master/Transaction/Accounting/Inventory/Payment/Rule/Auth/Config/Event/Read-model/Evidence/Archive را برای چهارده ماژول به ۱۶۸ انتساب متصل می‌کند. هشت Authority class از Write model و Immutable ledger/event تا Projection/Cache/Export/Hash evidence/Archive/Quarantine تعداد ۱۱۲ و دوازده مرحلهٔ rebuild lifecycle تعداد ۱۶۸ انتساب دارد.

Provenance receipt بیست‌وچهار فیلد، Rebuild receipt بیست‌ودو، Drift receipt بیست و Retention disposition هجده فیلد دارد. چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ انتساب ایجاد می‌کند. Read model، Cache، Report و Export منبع حقیقت نیستند؛ Direct repair بدون اصلاح authoritative ممنوع و rebuild فقط از Source/version/snapshot/watermark معتبر مجاز است.

Gap/Overlap/Fork/Unknown یا Partial rebuild، publication/read-switch را می‌بندد؛ replay اثر تازه نمی‌سازد و همان Source/recipe/version باید Digest یکسان تولید کند. Deletion باید Retention مالی و lineage tombstone را حفظ کند و Evidence فقط hash/reference است. هیچ Dataset/Table/Row/Schema/Sample عملیاتی خوانده و هیچ Rebuild/Replay/Repair/Delete/Read-switch اجرا نشد؛ Lineage/Drift/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

برای عملیاتی‌کردن قواعد طراحی بدون تماس با محیط واقعی، Reference evaluator خالص Promotion/Rollback ساخته شد. Envelope دقیقاً Decision type، دو Artifact digest، هجده boolean و دو Count غیرمنفی دارد؛ field اضافه/کم، type نادرست و digest نامعتبر fail-closed است. سه Baseline UAT/Production/Rollback و بیست‌وسه Mutation منفرد، جمعاً ۲۶/۲۶، نتیجهٔ مورد انتظار دادند.

تقدم نتیجه Schema، Digest format/equality، Supply chain، Test evidence، Environment token، Change window، Migration/Recovery، Canary/Kill switch، Redaction/Retention، Blocking unknown، Residual difference، Health/SLO/Business invariant، UAT acceptance، Production approval، Role separation و Rollback safety است. UAT بدون Production approval پذیرفته می‌شود اما مجوز Production نیست؛ rollback ناامن به `FORWARD_FIX_REQUIRED_ROLLBACK_UNSAFE` می‌رود.

فقط hash ثابت، boolean و count مصنوعی پردازش شد و هیچ Manifest/Artifact/Registry/Environment/Receipt عملیاتی خوانده نشد. Build/Deploy/Promotion/Rollback/Health-check اجرا نشد؛ Reference implementation یک، Operational implementation/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Monetary/Quantity/Temporal چهارده بُعد Amount/Quantity scale، Currency/minor unit، Rate source/direction، Rounding mode/stage/order، Tax، Discount allocation، Unit conversion، Base/secondary/packaging quantity، Canonical instant/timezone، Business/document/posting date، Fiscal period و Calendar presentation را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده invariant و دوازده مرحله هرکدام ۱۶۸ انتساب دارند.

Numeric policy بیست‌ودو فیلد، Calculation receipt بیست‌وچهار و Conversion و Temporal/Fiscal receipt هرکدام بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ انتساب ایجاد می‌کند. Binary float، precision/scale/rounding ضمنی، residual گمشده، exchange rate بی‌نسخه/جهت/زمان و unit conversion میان dimensionهای ناسازگار ممنوع است.

Canonical instant، timezone/offset، business date، document date و posting date قابل‌جایگزینی نیستند؛ DST مبهم/ناموجود fail-closed و posting در fiscal period بسته/نامعلوم ممنوع است. Jalali/Gregorian صرفاً نمایش نسخه‌دار است و authoritative instant نیست. هیچ مبلغ/مقدار/نرخ/تاریخ/timestamp عملیاتی خوانده و هیچ Calculation/Conversion/Posting اجرا نشد؛ Policy/Receipt/Reconciliation/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Monetary/Temporal با `Decimal` و بدون I/O ساخته شد. شش vector rounding تفاوت HALF_UP/HALF_EVEN و مرزهای مثبت/منفی را، چهار allocation روش largest remainder و tie-break پایدار را، چهار conversion نسبت‌های دقیق، سه reversal حفظ sign/scale و سه temporal baseline تفکیک instant/business/posting date را پوشش می‌دهد.

چهارده negative vector روی type/format/non-finite/scale/mode، weight set/total، denominator، timestamp naive، timezone ناشناخته، offset mismatch، fiscal period بسته و calendar authoritative اجرا شد. ۲۰/۲۰ مثبت و ۱۴/۱۴ منفی، جمعاً ۳۴/۳۴، PASS و سیزده Error code متمایز ثبت شد.

تمام Amount/Weight/Rate/Date/Timestampها ثابت و مصنوعی‌اند و نتیجه صرفاً رفتار Reference را ثابت می‌کند، نه موتور Pricing/Accounting/Inventory/Treasury یا Posting عملیاتی. Operational read/run/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Concurrency ده بُعد Expected version، Command fingerprint/idempotency، repository CAS، invariant version set، sequence scope، lease owner، fencing token، deadlock retry، unknown commit و bulk mixed-version را برای ۴۹ فرمان به ۴۹۰ انتساب متصل می‌کند. شش Strategy candidate برای هر فرمان ۲۹۴ انتساب دارد و هیچ‌کدام خودکار انتخاب نشده است.

Concurrency receipt بیست‌ودو، Conflict receipt هجده و Lease/Fencing receipt بیست فیلد دارد. چهارده Failure case تعداد ۶۸۶، هجده Gate تعداد ۸۸۲ و شش Role تعداد ۲۹۴ انتساب ایجاد می‌کند. Idempotency key کنترل concurrency نیست؛ authoritative update باید expected-version و repository-level compare-and-swap داشته باشد و affected count غیر از یک typed conflict است.

Lost update/last-write-wins، write skew/phantom، sequence تکراری، lease منقضی/لغوشده و fencing token کهنه ممنوع است. Deadlock retry هویت command/idempotency را حفظ می‌کند، unknown commit پیش از retry باید reconcile شود و Read model stale precondition authoritative نیست. هیچ Version/Transaction/Lock/Lease/Fence عملیاتی خوانده و هیچ Command/Conflict/Retry اجرا نشد؛ Strategy/Proof/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Concurrency ترتیب تصمیم را executable کرد: Schema، Idempotency receipt، Unknown commit، Deadlock/timeout retry، Expected version، CAS cardinality، Business invariant version set، Sequence، Lease، Fencing، Bulk policy و Commit. Receipt موجود با fingerprint برابر Replay است و پیش از version ارزیابی می‌شود؛ Receipt با fingerprint متفاوت Conflict است.

سه baseline Commit/Replay/Retry و سیزده mutation منفی، جمعاً ۱۶/۱۶، PASS شد و چهارده Outcome متمایز ثبت شد. Unknown commit حتی هم‌زمان با علامت retry به Reconciliation می‌رود؛ Deadlock فقط پیش از commit و با همان Command identity قابل retry است؛ CAS match صفر یا چندگانه از version mismatch جداست.

فقط version/count/boolean/sequence/fence ثابت و مصنوعی پردازش شد. هیچ Version/Transaction/Lock/Lease/Fencing token عملیاتی خوانده و هیچ Command/Conflict/Retry اجرا نشد؛ Reference implementation یک، Operational implementation/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Master data دوازده کلاس Party/Customer، Supplier، Item/Service، Unit/Packaging، Warehouse/Route، Organization/Fiscal، Account/Cost-center، Bank/Payment/Terminal، User/Employee، Price/Tax classification، Document/Numbering/Workflow و External alias را برای چهارده ماژول به ۱۶۸ انتساب متصل می‌کند. چهارده بُعد Identity تعداد ۱۹۶ و دوازده مرحلهٔ lifecycle تعداد ۱۶۸ انتساب دارد.

Identity receipt بیست‌ودو فیلد، Merge receipt بیست‌وچهار و Supersession و Cross-reference receipt هرکدام بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ انتساب ایجاد می‌کند. Uniqueness باید Tenant/Organization/Context scope داشته باشد؛ normalization نباید distinct entityها را collapse کند و fuzzy score یا یک attribute حق auto-merge ندارد.

Merge باید survivor/loser، protected differences، field resolution، downstream impact، immutable-history strategy و unmerge plan داشته باشد. Supersession حذف یا reuse هویت نیست؛ lifecycle stateها قابل‌جایگزینی نیستند و alias/cross-reference باید acyclic و unambiguous باشد. هیچ Identifier/Code/Name/PII/Master record عملیاتی خوانده و هیچ Create/Merge/Unmerge/Supersession/Propagation اجرا نشد؛ Receipt/Reconciliation/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Capacity دوازده بُعد Workload envelope، Inflight، Queue/backpressure، Timeout، Retry، Circuit breaker، Rate limit، Resource pool، Batch/payload، Dependency bulkhead، Graceful degradation و Overload recovery را برای چهارده ماژول به ۱۶۸ انتساب متصل می‌کند. دوازده مرحلهٔ lifecycle نیز ۱۶۸ انتساب دارد.

Capacity policy بیست‌ودو فیلد، Timeout/Retry budget بیست، Overload receipt بیست‌ودو و Degradation receipt بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ انتساب ایجاد می‌کند. Inflight/Queue/Batch/Payload/Pool بی‌کران ممنوع و timeout هر hop باید در parent budget باشد؛ retry به idempotency، attempt/elapsed budget، backoff، jitter و unknown-commit guard نیاز دارد.

Queue overflow نباید effect را خاموش حذف/reorder کند؛ Rate limit باید scope/fairness را حفظ کند و dependency به bulkhead نیاز دارد. Degraded mode حق bypassکردن Authorization یا invariant مالی/انبار/پرداخت ندارد و stale read current authoritative نیست. هیچ Traffic/Metric/Queue/Resource/Dependency عملیاتی خوانده و هیچ Load/Fault/Overload/Degradation/Recovery اجرا نشد؛ Policy/Rehearsal/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Capacity ترتیب تصمیم Schema، Blocking unknown، Unknown commit، Timeout budget، Concurrency limit، Queue backpressure، Retry safety/budget، Dependency/circuit، Degradation invariant، Recovery drain/reconciliation و Acceptance را executable کرد. شش baseline Capacity/Backpressure/Retry/Circuit/Degradation/Recovery و سیزده mutation منفی، جمعاً ۱۹/۱۹، PASS شد.

Parent budget، elapsed time، local timeout و downstream timeout جدا هستند؛ `elapsed + local <= parent` و `downstream <= local` باید برقرار باشد. Retry فقط با idempotency، backoff/jitter و attempt limit پذیرفته می‌شود و Unknown commit همیشه Reconciliation می‌خواهد. Queue full Backpressure typed است، نه حذف خاموش.

فقط Budget/Count/Boolean/State ثابت و مصنوعی پردازش شد. هیچ Traffic/Metric/Queue/Resource/Dependency عملیاتی خوانده و هیچ Load/Fault/Overload/Degradation/Recovery اجرا نشد؛ Reference implementation یک، Operational implementation/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Numbering دوازده بُعد Tenant/Organization/Fiscal/Document scope، Series/version/format، Surrogate-vs-human number، Allocation stage، Uniqueness/monotonicity، Gap/Void، Reservation expiry، Sequence/Fencing، Offline range، Fiscal rollover، Reversal lineage و Reprint marking را برای چهارده ماژول به ۱۶۸ انتساب متصل می‌کند. دوازده مرحله نیز ۱۶۸ انتساب دارد.

Series policy و Allocation receipt هرکدام بیست‌ودو فیلد، Void receipt هجده و Rollover receipt بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ انتساب ایجاد می‌کند. شمارهٔ انسانی database surrogate نیست و scope باید Tenant/Organization/Fiscal/Document type/Series version را مشخص کند.

Gap پنهان/حذف/reuse نمی‌شود و Void ledger immutable می‌خواهد؛ Reservation منقضی یا abandoned نیز reuse نمی‌شود. Preview/Draft/Print پیش از stage مصوب شماره نمی‌گیرد، unknown commit شمارهٔ دوم نمی‌سازد، Offline range باید non-overlap/scoped/expiring/reconciled باشد و Reversal original reference را حفظ کند. هیچ Number/Series/Gap/Identifier عملیاتی خوانده و هیچ Reserve/Commit/Void/Offline/Rollover اجرا نشد؛ Policy/Receipt/Reconciliation/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Numbering ترتیب Schema، Scope/Series/Fiscal، Idempotency receipt، Unknown commit، Sequence version، Fencing، Rollover، Draft، Void، Monotonicity، Offline range و Reserve/Commit را executable کرد. هفت baseline Commit/Draft/Reserve/Replay/Void/Offline/Rollover و سیزده mutation منفی، جمعاً ۲۰/۲۰، PASS شد.

Replay receipt با fingerprint برابر پیش از sequence version ارزیابی می‌شود و Unknown commit هر allocation تازه را می‌بندد. Draft نتیجهٔ `NUMBER_NOT_ALLOCATED` دارد؛ Reservation منقضی بدون Void receipt مردود و با آن Gap immutable است. Candidate شماره باید از آخرین Commit بزرگ‌تر و در Offline range معتبر باشد؛ Rollover با reservation باز یا Gap reconcileنشده رد می‌شود.

فقط State/Version/Number/Range ثابت و مصنوعی پردازش شد. هیچ Document number/Series/Gap/Identifier عملیاتی خوانده و هیچ Reserve/Commit/Void/Offline/Rollover اجرا نشد؛ Reference implementation یک، Operational implementation/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد File integrity چهارده بُعد Ingress authorization، Name/path/storage key، Declared/detected type، Size/count/ratio limit، Digest/provenance، Archive safety، Malware/active content، Quarantine، Extraction/derivative، DLP، Download auth، Encryption/signed URL، Retention/tombstone و Export manifest/formula injection را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده stage تعداد ۱۶۸ انتساب دارد.

File manifest و Scan receipt هرکدام بیست‌ودو فیلد و Quarantine و Disposition receipt هرکدام بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ انتساب ایجاد می‌کند. Extension/MIME اعلامی بدون magic/content sniffing trusted نیست؛ path traversal، absolute/reserved path، symlink، zip-slip، recursion/bomb و parser resource بی‌کران ممنوع است.

Scanner error/timeout/unknown یا signature stale نتیجهٔ Clean نیست؛ Quarantine اجازهٔ preview/download/export/parse ندارد. Sanitized derivative جای Original immutable را نمی‌گیرد و Download دوباره Scope/Authorization/TTL/Revocation را بررسی می‌کند؛ CSV formula/active content نیز کنترل می‌شود. هیچ File/Attachment/Archive/Import/Export/Body عملیاتی باز یا خوانده و هیچ Scan/Parser/Quarantine اجرا نشد؛ Provider/Receipt/Release/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference validator فرادادهٔ فایل، تقدم تصمیم را به‌صورت Schema، Name/Path، Size، Digest، Media type، Archive safety، Scan/DLP/Quarantine، Download authorization، Derivative lineage، Export formula، Retention و Acceptance executable می‌کند. این تقدم مانع می‌شود که یک receipt یا authorization ظاهراً معتبر، خطای بنیادی path/hash/archive را بپوشاند.

پنج مسیر حفاظتی شامل پذیرش فایل پاک، quarantine بدافزار، quarantine نتیجهٔ scanner ناشناخته، منع دسترسی quarantine و پذیرش derivative پاک‌سازی‌شده است. چهارده mutation منفی نیز schema اضافی، traversal، oversize، hash نامعتبر، MIME mismatch، سه مرز archive و zip-slip، authorization یا signed-link نامعتبر، lineage/digest derivative، formula injection و retention کهنه را پوشش می‌دهد؛ مجموع ۱۹/۱۹ PASS و چهارده Outcome متمایز است.

این evaluator هیچ byte از فایل یا archive نمی‌خواند و هیچ scanner، parser، quarantine، download، export یا disposition عملیاتی را صدا نمی‌زند. Reference implementation یک، operational implementation/read/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

قرارداد قفل دورهٔ مالی چهارده بُعد Scope تقویم/دفتر، state machine، Soft/Hard close، سه تاریخ سند، ترتیب زیردفترها، هزینه و ارزش‌گذاری موجودی، دریافتنی/پرداختنی، بانک، مالیات، حقوق/دارایی/accrual/FX، Adjustment/Reversal، حاکمیت Reopen، reconciliation و lineage شواهد را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده مرحله ۱۶۸ انتساب دارد.

Fiscal lock policy بیست‌وچهار فیلد و Close، Reopen و Adjustment receipt هرکدام بیست‌ودو فیلد دارند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هفت role تعداد ۹۸ انتساب ایجاد می‌کند. Guard دوره باید در مسیرهای command، import، batch، integration و storage یکسان باشد و Document date به‌تنهایی Posting را مجاز نمی‌کند.

Hard close به ترتیب وابستگی و reconciliation موجودی، دریافتنی/پرداختنی، بانک، مالیات، حقوق، دارایی، accrual، FX، trial balance، control total و numbering rollover نیاز دارد. Late entry فقط Adjustment صریح و reversible است. Reopen باید reason، impact، scope، expiry، SoD و token کمینه/یک‌بارمصرف داشته باشد؛ Reclose همهٔ وابستگی‌های متاثر را دوباره ارزیابی و receipt قدیم و جدید را بدون بازنویسی با supersession متصل می‌کند.

هیچ Period/Ledger/Document/Balance/Entry عملیاتی خوانده و هیچ Close/Reopen/Adjustment/Reversal/Posting اجرا نشد. Policy/Receipt/Approval/Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator دورهٔ مالی ترتیب Schema، Scope، Version، State، پوشش همهٔ مسیرهای Lock، Blocking unknown، وابستگی Close، اتمی‌بودن Numbering rollover، Adjustment، Reopen، Reclose و Acceptance را executable می‌کند. این تقدم اجازه نمی‌دهد receipt بعدی، scope/version/state نامعتبر یا مسیر دورزنندهٔ lock را پنهان کند.

پنج مسیر مثبت Soft close، Hard close، Adjustment، Reopen و Reclose و هجده mutation منفی، جمعاً ۲۳/۲۳، PASS و نوزده Outcome متمایز ثبت شد. Mutationها lock bypass، unknown، subledger/control total/numbering، adjustment class/balance/reversal، reopen impact/SoD/token/break-glass و reclose rerun/lineage را پوشش می‌دهند.

فقط Boolean/State/Version ثابت و مصنوعی پردازش شد. هیچ Period/Ledger/Document/Balance/Entry عملیاتی خوانده و هیچ Close/Reopen/Adjustment/Reversal/Posting اجرا نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Integration/Webhook چهارده بُعد Endpoint/Owner/Direction، TLS/mTLS، Signature/Key rotation، Canonicalization/Digest، Schema/Compatibility، Tenant/Organization/Environment/Audience، Timestamp/Nonce/Replay، Message ID/Inbox/Outbox، Correlation/Order، Ack/Retry/Unknown delivery، Capacity، Poison/Quarantine/Dead-letter/Redrive، Payload protection و Observability/Reconciliation را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Endpoint policy و Inbound receipt هرکدام بیست‌وچهار فیلد و Outbound و Dead-letter receipt هرکدام بیست‌ودو فیلد دارند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هفت role تعداد ۹۸ انتساب ایجاد می‌کند. Signature باید method/path/content-type/payload digest/timestamp/nonce/audience را bind کند و key ناشناخته/منقضی/revoked fail-closed است.

Message ID با fingerprint متفاوت reuse نمی‌شود و Unknown delivery پیش از retry reconcile می‌شود. Retry به idempotency، attempt/elapsed budget، backoff و jitter نیاز دارد. Poison message نه حذف خاموش می‌شود نه بی‌نهایت retry؛ Quarantine و Dead-letter رمزگذاری‌شده می‌خواهد. Redrive باید reason/scope/authorization/idempotency/cap/loop guard و post-redrive reconciliation داشته باشد.

هیچ Endpoint/Certificate/Key/Message/Payload/Dead-letter عملیاتی خوانده و هیچ Send/Receive/Ack/Retry/Quarantine/Redrive اجرا نشد. Provider/Receipt/Approval/Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator پیام Integration ترتیب Schema، Transport، Signature/Key، Canonical digest، Schema compatibility، Scope، Timestamp/Nonce/Replay، Message ID/Dedup، Ordering، Blocking unknown، Payload policy، Delivery state، Retry/Unknown، Poison/Dead-letter، Redrive و Acceptance را executable می‌کند.

هشت baseline Inbound/Replay/Ack/Unknown/Retry/Poison/DLQ/Redrive و بیست‌ویک mutation منفی، جمعاً ۲۹/۲۹، PASS و بیست‌وسه Outcome متمایز ثبت شد. Unknown delivery هرگز success یا retry کور نیست؛ Retry بدون idempotency/budget، Poison بدون quarantine، DLQ بدون encryption و Redrive بدون authorization/cap/loop guard fail-closed است.

فقط Boolean/State/Identifier ثابت و مصنوعی پردازش شد. هیچ Endpoint/Certificate/Key/Message/Payload/Dead-letter عملیاتی خوانده و هیچ Network/Broker action اجرا نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Output integrity چهارده بُعد Template identity، Data snapshot، Renderer، Font/RTL، Locale/Calendar/Numeric، Page/Label media، Pagination/Grouping، Barcode، QR، Authorization/Redaction/Watermark، Preview/Copy/Reprint، PDF/Signature، Printer delivery و Custody/Accessibility/Golden parity را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Output policy و Render manifest هرکدام بیست‌وچهار فیلد، Print receipt بیست‌ودو و Barcode verification بیست فیلد دارد. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هفت role تعداد ۹۸ انتساب ایجاد می‌کند. Template/query/snapshot/renderer/dependency/font/locale/calendar/timezone/rounding باید pin شود و شکل‌دهی RTL/Bidi و embedding بخشی از parity فارسی است.

Barcode و QR بدون payload policy، check digit، quiet zone، contrast/DPI و machine decode معتبر نیستند. Preview/Draft/Copy/Reprint باید watermark و original lineage داشته باشد. PDF به archival profile/searchable text/metadata/digest/signature نیاز دارد و Unknown print delivery پیش از retry reconcile می‌شود. Visual match به‌تنهایی Semantic/Machine-scan/Business Golden parity نیست.

هیچ Template/Data snapshot/Document/PDF/Barcode/Print receipt عملیاتی خوانده و هیچ Render/Print/Scan/Sign/Download/Delivery اجرا نشد. Provider/Receipt/Approval/Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Output ترتیب Schema، Template/Data، Renderer/Dependency، Font/RTL، Locale/Numeric، Layout/Pagination، Barcode/Machine scan، QR، Authorization/Redaction، Copy/Watermark/Lineage، PDF/Archival/Digest/Signature، Accessibility، Blocking unknown، Print delivery و Acceptance را executable می‌کند.

شش baseline File/Print/Unknown/Preview/Reprint/No-barcode و بیست‌ویک mutation منفی، جمعاً ۲۷/۲۷، PASS و هجده Outcome متمایز ثبت شد. ACK چاپ پس از تمام gateهای محتوایی است؛ Unknown delivery نیاز به reconciliation دارد و هیچ نقص font/RTL/layout/barcode/PDF با ACK پوشانده نمی‌شود.

فقط Boolean/State ثابت و مصنوعی پردازش شد. هیچ Template/Snapshot/Document/Output/Barcode/Receipt عملیاتی خوانده و هیچ Render/Print/Scan/Sign اجرا نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Privacy چهارده بُعد Data inventory، Subject identity، Purpose/Legal basis، Notice، Consent، Minimization، Sensitive data، Access/Correction/Portability، Erasure/Restriction/Objection، Retention/Disposition، Processor/Sharing/Transfer، Automated decision، Breach و Accountability را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Privacy policy بیست‌وچهار، Consent receipt بیست‌ودو، Rights receipt بیست‌وچهار و Disposition receipt بیست‌ودو فیلد دارد. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هشت role تعداد ۱۱۲ انتساب ایجاد می‌کند. Authorization فنی Purpose/Legal basis/Consent نیست و Consent باید granular، اثبات‌پذیر، منقضی‌شونده و قابل withdrawal باشد.

Rights workflow به identity/representative verification متناسب، alias/merge/downstream discovery، third-party redaction و conflict resolution نیاز دارد. Erasure نباید legal hold یا obligation متعارض را دور بزند؛ disposition باید backup/downstream/tombstone/verification را پوشش دهد. Sharing و automated decision نیز scope/notice/explanation/review می‌خواهند.

این قرارداد jurisdiction-neutral است و مشاورهٔ حقوقی نیست. هیچ Person/Subject/Identifier/Contact/Employee/Financial/Sensitive data عملیاتی خوانده و هیچ Consent/Rights/Disposition/Sharing/Breach action اجرا نشد؛ Provider/Receipt/Legal approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Privacy ترتیب Schema، Inventory/Subject linkage، Purpose/Basis/Jurisdiction، Notice، Consent/Withdrawal، Minimization/Sensitive guard، Rights identity/Representative، Record discovery، Third-party redaction، Legal hold/Conflict، Sharing scope، Automated decision، Breach، Retention/Disposition، Blocking unknown و Acceptance را executable می‌کند.

نه baseline مثبت/حفاظتی و بیست‌ویک mutation منفی، جمعاً ۳۰/۳۰، PASS و بیست‌ودو Outcome متمایز ثبت شد. Withdrawal پیش از processing، identity/discovery پیش از rights response و legal hold/conflict پیش از erasure ارزیابی می‌شود؛ Sharing و automated decision نیز scope و human review می‌خواهند.

این evaluator jurisdiction-neutral و غیرمشاورهٔ حقوقی است و فقط Boolean/Action ثابت و مصنوعی پردازش می‌کند. هیچ PII/Sensitive data عملیاتی خوانده و هیچ Privacy action اجرا نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Approval governance چهارده بُعد Request identity، Policy version، Threshold/Quorum/Sequence، Qualification، SoD، Conflict، Delegation scope، Delegate acceptance/revocation، Substitution، Escalation، Decision lineage، Break-glass، Invalidation/Reapproval و Execution token/effect reconciliation را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Approval policy و Decision receipt هرکدام بیست‌وچهار فیلد و Request و Delegation receipt هرکدام بیست‌ودو فیلد دارند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هشت role تعداد ۱۱۲ انتساب ایجاد می‌کند. Authorization به‌تنهایی Threshold/Quorum/Sequence/SoD نیست و Delegation باید Action/Organization/Amount/Risk/Time/Qualification scope داشته باشد.

Timeout/Reminder/Escalation هرگز تصمیم خودکار نیست. تغییر fingerprint/version/amount/effect یا policy/role/risk تصمیم قبلی را invalidate می‌کند. Break-glass به incident/justification/scope/limit/expiry/post-review و Execution token به single-use/scope/fence و decision-command-effect reconciliation نیاز دارد.

هیچ User/Role/Approval request/Decision/Delegation/Token/Effect عملیاتی خوانده و هیچ Approve/Reject/Delegate/Escalate/Break-glass/Execute اجرا نشد. Provider/Receipt/Approval/Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Approval ترتیب Schema، Request/Policy/Threshold، Qualification/SoD/Conflict، Delegation scope/acceptance/expiry/revocation، منع Auto-decision، Blocking unknown، Escalation، Break-glass، Execution token/effect، Quorum/Sequence و Acceptance را executable می‌کند.

شش baseline Approve/Reject/Delegate/Escalate/Break-glass/Execute و بیست‌وسه mutation منفی، جمعاً ۲۹/۲۹، PASS و شانزده Outcome متمایز ثبت شد. Delegation منقضی/revoked، timeout auto-decision، SoD conflict، break-glass بدون incident/review و token غیر single-use/scoped/fenced fail-closed است.

فقط Boolean/Action ثابت و مصنوعی پردازش شد. هیچ Workflow/User/Role/Request/Decision/Delegation/Token/Effect عملیاتی خوانده یا اجرا نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Tax/Fiscalization چهارده بُعد Jurisdiction/Regime، Registration، Document schema، Classification، Tax calculation، Discount/Rounding/Currency، Fiscal number/UUID/Timestamp، Signature/Certificate، Clearance/Contingency، Submission outcomes، Correction/Cancellation، Human/Machine output parity، Retention/Inspection و Cross-system reconciliation را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Policy و Fiscal document manifest هرکدام بیست‌وچهار فیلد و Submission و Correction receipt هرکدام بیست‌ودو فیلد دارند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هشت role تعداد ۱۱۲ انتساب ایجاد می‌کند. مبلغ حسابداری به‌تنهایی fiscal compliance نیست؛ regime/registration/schema/rate/exemption/withholding/rounding/number/UUID/timestamp/signature باید pin شود.

Ack/Warning/Rejection/Unknown provider نتیجه‌های متمایزند. Unknown پیش از retry reconcile می‌شود و retry هویت و payload را عوض نمی‌کند. Contingency offline باید محدود/منقضی/reconciled باشد و Correction/Cancellation lineage اصلی را نگه دارد. Human PDF/QR/Barcode باید با machine payload برابر باشد.

این قرارداد jurisdiction-neutral و غیرمشاورهٔ حقوقی/مالیاتی/حسابداری است. هیچ Taxpayer identifier/Document/Tax value/Payload/Certificate/Key/Provider receipt عملیاتی خوانده و هیچ Fiscalize/Sign/Submit/Retry/Correct/Cancel اجرا نشد؛ Provider/Receipt/Professional approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Tax ترتیب Schema، Regime/Registration، Schema/Identifier/Classification، Tax calculation/Rounding، Fiscal identity، Digest/Signature/Certificate، Idempotency/Payload identity، Human/Machine/Archive parity، Blocking unknown، Provider outcome، Contingency، Correction/Cancellation و Reconciliation را executable می‌کند.

هشت baseline Draft/Ack/Warning/Rejection/Unknown/Contingency/Correction/Cancellation و بیست‌ویک mutation منفی، جمعاً ۲۹/۲۹، PASS و نوزده Outcome متمایز ثبت شد. Provider ACK پس از gateهای محتوایی است و control-total reconciliation می‌خواهد؛ Unknown، Contingency و Correction مسیر typed مستقل دارند.

این evaluator jurisdiction-neutral و غیرمشاورهٔ حقوقی/مالیاتی/حسابداری است و فقط Boolean/Provider-state مصنوعی پردازش می‌کند. هیچ Taxpayer/Document/Value/Payload/Certificate/Provider عملیاتی خوانده یا فراخوانی نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

قرارداد Inventory چهارده بُعد Item/UOM/Warehouse scope، Lot/Serial identity، Expiry dates، Stock states، On-hand/Reservation invariants، Negative stock/Backdate، Cost method، Cost layer lineage، Landed cost، Transfer in transit، Count variance، FEFO/Recall/Quarantine، Period revaluation و Stock/GL reconciliation را برای چهارده ماژول به ۱۹۶ انتساب متصل می‌کند. دوازده Stage تعداد ۱۶۸ انتساب دارد.

Inventory policy بیست‌وچهار فیلد و Stock movement، Cost layer و Reconciliation receipt هرکدام بیست‌ودو فیلد دارند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هشت role تعداد ۱۱۲ انتساب ایجاد می‌کند. Expired/Recalled/Quarantined/Damaged stock قابل allocation نیست و Negative stock/Backdate/Late receipt/Unknown commit fail-closed است.

Cost method/version/effective time/currency/scale/rounding باید pin شود؛ cost layer quantity نباید duplicate/cross-scope/negative شود. Landed cost basis/total/residual، Transfer source/destination/in-transit owner، Count freeze/blind/variance approval و Stock/Cost/GL control totals باید reconcile شوند.

هیچ Item/Lot/Serial/Stock/Quantity/Cost/Value/Ledger عملیاتی خوانده و هیچ Move/Reserve/Transfer/Count/Cost/Revalue/Reconcile اجرا نشد. Provider/Receipt/Approval/Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

Reference evaluator Inventory ترتیب Schema، Scope، Lot/Serial/Date، Version/Idempotency، Unknown commit، State/Quantity، Negative policy، Blocking unknown، Expiry/Quarantine، Cost layer، Landed cost، Transfer، Count، Period revalue، Reconciliation و Acceptance را executable می‌کند.

هفت baseline Movement/Allocate/Cost/Transfer/Count/Revalue/Reconcile و بیست‌ویک mutation منفی، جمعاً ۲۸/۲۸، PASS و بیست‌ودو Outcome متمایز ثبت شد. Unknown commit پیش از state/cost، Expiry پیش از allocation و cost-layer lineage/quantity پیش از valuation acceptance ارزیابی می‌شود.

فقط Boolean/Operation ثابت و مصنوعی پردازش شد. هیچ Item/Lot/Serial/Stock/Quantity/Cost/Value/Ledger عملیاتی خوانده یا تغییر داده نشد؛ Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## افزوده دانش: Procure-to-Pay / Three-Way Match — ۲۰۲۶-۰۹-۰۱

مدل مقصد باید تطبیق را روی line identity صریح میان PO، goods receipt یا service entry و supplier invoice انجام دهد. ordered/received/accepted/invoiced/returned/open quantity، قیمت، tax/freight، currency scale/rounding و نسخه tolerance همگی باید pin و hash-linked باشند. duplicate invoice، unknown commit، tolerance breach، partial/over/under و unresolved hold fail-closed هستند. release استثنا approval مستقل می‌خواهد و payment eligibility نباید period، duplicate، hold، bank/sanction یا reconciliation gate را دور بزند. purchase accrual، AP subledger، inventory/expense و GL باید در cutoff مشترک reconcile شوند. این دانش design-only است و ادعای رفتار runtime یا readiness ندارد.
## افزوده دانش: Order-to-Cash / Credit / Collections — ۲۰۲۶-۰۹-۰۱

در مدل مقصد، customer scope، نسخه سفارش و pricing، credit exposure، allocation/delivery، invoice/return lineage، cash custody و allocation باید صریح و versioned باشند. credit override و dispute/write-off approval مستقل می‌خواهند؛ unknown commit، cash مبهم، allocation نامتوازن و credit breach fail-closed هستند. aging/ECL و revenue recognition باید cutoff/period مشترک داشته باشند و AR subledger، cash/bank، revenue/deferred revenue، tax، inventory/cost و GL reconcile شوند. این نتیجه design-only است و رفتار runtime یا readiness را ثابت نمی‌کند.
## افزوده دانش: Workforce / Time / Payroll — ۲۰۲۶-۰۹-۰۱

دامنه worker/employment/organization/position/cost-center و effective-dated contract پایه payroll است. time/attendance/leave، formula/statutory versions، scale/rounding/residual، retro/off-cycle/original lineage، payslip numbering/redaction و payment token/approval باید pin شوند. termination بدون final settlement و access revocation بسته نیست. privacy/legal basis/minimization و SoD اجباری است و liability/expense/accrual/tax/benefit/cash/GL باید در cutoff مشترک reconcile شوند. این دانش design-only است و داده پرسنلی یا رفتار runtime را ثابت نمی‌کند.
## نقطه انتقال ادامه ۱۰ساعته — ۲۰۲۶-۰۹-۰۱

برای ادامه از سیستم دیگر، ابتدا `docs/varanegar_reconstruction/VARANEGAR_10H_CONTINUATION_HANDOFF_20260901_FA.md` و سپس `artifacts/varanegar_analysis/varanegar_10h_continuation_handoff_checkpoint_20260901.json` خوانده شود. freshness با `scripts/windows/audit_varanegar_checkpoint_freshness.py` و settle کامل با `scripts/windows/settle_varanegar_analysis_chain_20260831.ps1` کنترل می‌شود. هر ادعای runtime/UAT/provider/owner approval خارج از این کپسول است.
## افزوده دانش: Fixed Asset Lifecycle / Depreciation — ۲۰۲۶-۰۹-۰۱

هویت asset/category/book/scope/custodian/tag، acquisition و CIP lineage، component parent-child و نسخه cost/life/residual/method باید pin شوند. depreciation convention/proration/suspension/catch-up/rounding، impairment/reversal و revaluation reserve fail-closed هستند. transfer/disposal بدون scope، proceeds، gain/loss، derecognition و original lineage بسته نیست. NBV منفی یا accumulated depreciation بیش از basis مردود است و asset register/depreciation subledger/reserves/GL باید در cutoff مشترک reconcile شوند. این دانش design-only است.
## نقشه ادامه دامنه‌های ERP مقصد — ۲۰۲۶-۰۹-۰۱

دفتر `artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_register_20260901.json` منبع canonical انتخاب دامنه بعدی است. بسته Project/Job/Contract Costing/Revenue/Billing شکاف P0 را در سطح طراحی و بردار مصنوعی بسته است. P1: Budget/Planning، Intercompany/Consolidation، Lease Accounting و Service/Field-Service/Warranty/Maintenance. P2: CRM pre-order و certified analytics/regulatory reporting. این اولویت architectural است و جای owner approval یا UAT را نمی‌گیرد.
## invariant سراسری سبد قراردادها — ۲۰۲۶-۰۹-۰۱

Artifact `artifacts/varanegar_analysis/varanegar_target_erp_contract_portfolio_invariant_audit_20260901.json` مرجع canonical سلامت ۵۴ قرارداد مقصد است. هر قرارداد باید PASS، بدون failed check، با شناسه یکتا، scope/limits، safety صفر، runtime/provider/receipt/readiness صفر، manifest تازه و lower bound برابر ۱۴۰۴ باشد. شمارنده اجرای synthetic/reference/vector runtime محسوب نمی‌شود؛ action run-count دامنه باید صفر بماند. صفر finding فقط سلامت داخلی design را ثابت می‌کند.
## افزوده دانش: Manufacturing / MRP / Shop-floor / Quality — ۲۰۲۶-۰۹-۰۱

BOM/recipe/routing version/effectivity و plant/resource scope، MPS/MRP/pegging/netting/time-fence و lead-time/lot-size/yield/scrap باید pin شوند. production order release، material issue/backflush/return، labor/machine/output، genealogy و quality hold/release fail-closed هستند. WIP state/concurrency و standard/actual/overhead/variance باید versioned باشند و WIP/material/labor/inventory/COGS/GL در cutoff مشترک reconcile شوند. هیچ رفتار runtime ثابت نشده است.
## ممیزی همه checkpointها — ۲۰۲۶-۰۹-۰۱

برای تحویل یا ادامه، علاوه بر ممیزی chain رأس، فرمان `scripts/windows/audit_varanegar_checkpoint_freshness.py ... --all-checkpoints` اجرا شود. این حالت recursive است و orphan checkpointهای معتبر زیرپوشه‌ها را نیز وارد کنترل hash/size/validation می‌کند. snapshot فعلی ۲۵۰ checkpoint، صفر stale و صفر JSON نامعتبر در ۷۶۹ JSON دارد.
