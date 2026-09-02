# مرز Watermark صدور حسابداری فروش و Crosswalk دفترکل

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

ثبت حسابداری فروش در وارانگار یک Projection دسته‌ای و مستقل از نهایی‌شدن Sale
است. فروش نهایی می‌تواند Snapshot فروش داشته باشد ولی هنوز وارد حسابداری نشده
باشد؛ همچنین بخشی از تاریخچهٔ قدیمی حسابداری فروش اصلاً به `tblSaleVocherHdr`
وابسته نیست. بنابراین سه وضعیت `Sale finalized`، `Sale snapshot captured` و
`Accounting issued` باید در ERP مقصد جدا باشند.

تمام بررسی فقط‌خواندنی بود. هیچ View، Procedure، فرم یا Command اجرا نشد؛ فقط
Catalog، Definition fingerprint و Aggregateهای ناشناس خوانده شدند.

## پوشش جاری Sale → PreVoucher

- فروش فعال نهایی و شماره‌دار: ۲۱۲٬۷۵۹
- فروش دارای منبع حسابداری Creator فروش: ۲۰۲٬۶۳۶
- خط `PreVoucher` فروش: ۶۲۵٬۸۳۹
- فروش فعال نهایی بدون منبع حسابداری: ۱۰٬۱۲۳
- Source بدون Sale جاری، Source نامتوازن یا Source صادرشده در چند Batch: صفر

تقریباً تمام شکاف، Watermark صدور است:

| ماه تجاری | فروش فعال نهایی | دارای منبع حسابداری | بدون منبع |
|---|---:|---:|---:|
| ۱۴۰۵/۰۳ | ۸٬۹۳۶ | ۸٬۹۳۶ | ۰ |
| ۱۴۰۵/۰۴ | ۱۱٬۰۸۵ | ۱۱٬۰۸۵ | ۰ |
| ۱۴۰۵/۰۵ | ۱۰٬۱۲۲ | ۰ | ۱۰٬۱۲۲ |

از ماه‌های قدیمی فقط یک فروش ۱۴۰۳/۰۱ بدون Source مانده است. پس ۱۰٬۱۲۲ مورد
۱۴۰۵/۰۵ حادثه یا دادهٔ گمشده نام‌گذاری نمی‌شوند؛ این‌ها cohort جاریِ هنوز صادرنشده
هستند. یک outlier قدیمی برای disposition حسابداری جدا می‌ماند.

## Snapshot فروش با Source حسابداری یکی نیست

برای ۲۱۲٬۷۵۹ فروش فعال نهایی:

| Snapshot فروش | Source حسابداری | تعداد | سه‌ماهه |
|---|---|---:|---:|
| ندارد | ندارد | ۴۸۰ | ۴۸۰ |
| ندارد | دارد | ۹٬۰۰۸ | ۱٬۲۸۷ |
| دارد | ندارد | ۹٬۶۴۳ | ۹٬۶۴۲ |
| دارد | دارد | ۱۹۳٬۶۲۸ | ۱۸٬۷۳۴ |

این ماتریس ثابت می‌کند Snapshot ووچر فروش پیش‌شرط فنی Creator حسابداری نیست.
View حسابداری مستقیم `tblSaleHdr/tblSaleItm` را با `NOLOCK` می‌خواند و به
`tblSaleVocherHdr` dependency ندارد.

در کل ۲۶۶٬۱۸۳ Snapshot فروش، تعداد ۷۲٬۵۵۵ مورد Source حسابداری جاری ندارند؛
۶۰٬۶۹۸ مورد از آن‌ها متعلق به Sale لغوشده‌اند. این فقدان Source جاری نباید به
«هیچ‌وقت صادر نشده» یا «سند مالی حذف شده» تبدیل شود؛ Artifact جاری تاریخچهٔ Rule
و Tombstone کامل را ندارد.

## Eligibility جاری Creator فروش

Definition هش‌سنجی‌شدهٔ `dbo.vwCreatePreVoucher_VN_Sale` فقط Saleهایی را انتخاب
می‌کند که:

- `CancelFlag=0` باشند؛
- `SaleNo` داشته باشند؛
- Item حذف‌نشده داشته باشند.

View از `NOLOCK` استفاده می‌کند و Snapshot فروش را نمی‌خواند. به همین علت صفر
Source جاری برای Sale لغوشده، نتیجهٔ Eligibility فعلی است؛ نه اثبات اینکه هیچ
لغوشده‌ای در گذشته حسابداری نشده یا هیچ فرآیند حذف/برگشتی رخ نداده است.

## Crosswalk تا دفترکل

۲۰۲٬۶۳۶ Source فروش به ۱۰۱٬۶۴۹ Batch خارجی متصل‌اند. هر Source دقیقاً یک Batch
دارد؛ Batch گمشده، لینک بدون Journal یا Batch دارای چند Journal صفر و تمام
۲۰۲٬۶۳۶ لینک به دقیقاً یک Journal فعال می‌رسند.

گروه‌بندی Batch تاریخی یکسان نیست:

- ۱۰۱٬۲۷۹ Batch تک‌Source؛
- ۳۷۰ Batch چندSource با ۱۰۱٬۳۵۷ تخصیص Source؛
- بزرگ‌ترین Batch تاریخی ۱٬۱۳۱ Source دارد.

این نتیجه با شکاف نسخهٔ Policy قبلی سازگار است: تنظیم جاری تک‌Source نمی‌تواند
گروه‌بندی تاریخی را بازسازی کند.

۲۷٬۵۹۴ Source جمع بدهکار برابر مبلغ Sale دارند و ۱۷۵٬۰۴۲ برابر نیستند. چون یک
Source حسابداری می‌تواند دریافتنی، فروش، مالیات، تخفیف و بهای تمام‌شده را هم‌زمان
شامل شود، جمع بدهکار قرارداد برابری مستقیم با `Sale.TotalAmount` نیست؛ این
۱۷۵٬۰۴۲ مورد mismatch مالی نام‌گذاری نمی‌شوند. Parity باید بر اساس Rule و خطوط
Golden هر Creator انجام شود.

## مالکیت تراکنش

`dbo.usp_DoPreVoucher` و `dbo.usp_DoExternalVoucher` هر دو به staging وابسته‌اند
ولی Transaction محلی ندارند. مسیر Desktop که قبلاً Hash-pinned شده Transaction
را در Business `DataContext(Transaction.Begin)` مالک است. Caller مستقیم SQL یا
Integration بدون همان مالکیت امن نیست و نسخهٔ وب باید Transaction owner سمت
Server داشته باشد.

## قرارداد پیشنهادی Negin ERP

1. Stateهای `Finalized`, `SnapshotCaptured`, `AccountingEligible`,
   `AccountingIssued`, `Posted` و `Reversed` جدا و versioned باشند.
2. هر Accounting run یک Watermark تجاری، Source snapshot committed، RuleVersion،
   GroupingPolicyVersion و RunId ماندگار کند.
3. «فروش بدون Source در ماه باز» Pending باشد؛ فقط خارج از Watermark و پس از
   Reconciliation به Exception تبدیل شود.
4. Eligibility لغو از تاریخچهٔ Posting جدا باشد؛ Reverse/void باید Event و
   Crosswalk جبرانی داشته باشد، نه حذف شواهد.
5. رابطهٔ Sale → Draft → Batch → Journal با SourceId و idempotency key صریح حفظ
   شود؛ Snapshot فروش FK اجباری حسابداری نباشد.
6. Parity مالی با Golden line rule انجام شود، نه `SUM(Debit)=Sale.TotalAmount`.
7. Creator view بدون `NOLOCK` و تحت snapshot committed خوانده شود.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_sale_accounting_crosswalk_boundary.py`
- `artifacts/varanegar_analysis/domains/sale_accounting_crosswalk_boundary_20260829.json`
- `tests/test_varanegar_sale_accounting_crosswalk_boundary.py`
- `scripts/windows/build_varanegar_sale_accounting_crosswalk_checkpoint_20260829.py`

Definition خام، comment، کد حساب و شناسه یا مقدار Sale/Snapshot/Journal/Customer/
User/Host ذخیره نشده است. Current-state crosswalk، Rule تاریخی، actor، علت حذف یا
درستی semantic خطوط حسابداری را اثبات نمی‌کند.
