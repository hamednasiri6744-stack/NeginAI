# پوشش سراسری Call contract فرم‌های وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۴۴۲ فرم با اطمینان بالا؛ همه پیدا شدند و صفر خطای Method کسب‌وکاری**

## پوشش کامل‌تر Runtime

این Artifact هر ۴۴۲ Form candidate با اطمینان بالا را در هفت فایل UI/Container
پوشش می‌دهد. سه Candidate با اطمینان متوسط عمداً وارد ادعای پوشش نشده‌اند.
Assemblyها فقط به‌صورت PE metadata/IL خوانده شدند و Raw IL یا متن رشته‌های
غیر-Allowlist در خروجی Compact ذخیره نشد.

## نتیجه عددی

- ۱۰٬۳۸۶ Method body و ۱۵٬۹۹۷ Call مستقیم First-party؛
- ۳۹۰ فرم با نام Method Write-like و ۲۹۷ با Delete/Reverse-like؛
- ۳۵۸ فرم با Validation-like و ۱۲۲ با Permission-like محلی؛
- ۱۱۲ فرم دارای Report/Print/Export-like؛
- ۱۱۲ فرم دارای Transaction/Commit signal مستقیم؛
- ۲۸۰ فرم با بیش از یک خانواده ماژولی وقتی `Setting` هم شمرده شود؛
- ۱۱۱ فرم چندماژولی کسب‌وکاری پس از حذف `Setting` زیرساختی؛
- صفر Type گمشده، صفر Hash mismatch و فقط یک خطای Designer
  `InitializeComponent` که قبلاً ثبت شده بود.

`Write-like` یک Heuristic نام Method است و برابر تعداد Command واقعی یا مجوز
Write نیست. Event handlerهایی مانند RowUpdated نیز ممکن است در این گروه باشند؛
هر مسیر برای Command شدن به Handler/SQL/Authorization evidence نیاز دارد.

## ساختار صفحه‌ها

پوشش شامل ۱۱۹ Data-entry، ۲۲ Master-detail، ۱۰۷ Form عمومی، ۷۳ Selector، ۳۴
Dialog، ۲۹ Dual-list assignment، ۲۰ Workflow، ۲۰ Report و ۱۸ List است. بنابراین
ERP مقصد فقط مجموعه فرم‌های ثبت نیست؛ Selector، Assignment، Queue، Report و
Dialog قراردادهای مجوز و Context مستقل دارند.

## Coupling واقعی

پس از حذف `Setting`، دو ترکیب غالب `MainData+Sales` در ۵۱ فرم و
`MainData+Stock` در ۳۳ فرم‌اند. شش فرم `MainData+Sales+Stock` را هم‌زمان صدا
می‌زنند. RetSale، SupplierInvoice، FreeInvoice، StockVoucher، SupplierReturn و
LoanRegistration چهار خانواده را درگیر می‌کنند؛ Statement data-entry نیز
MainData/Stock/Treasury/TreasuryOld را وصل می‌کند.

این Coupling دلیل انتخاب Modular Monolith اولیه است: Transaction و Trace داخلی
را می‌توان یکپارچه نگه داشت، ولی مالکیت داده و Interface ماژول‌ها صریح می‌ماند.
شکستن زودهنگام به Microservice هزینه هماهنگی و Atomicity را بالا می‌برد.

## ۲۲ فرم بدون Call مستقیم First-party

این فرم‌ها مرده یا بی‌اثر اعلام نمی‌شوند. رفتار ممکن است در Base class، Interface،
Reflection، ORM، Event یا Resource/config باشد. آن‌ها یک Evidence limit و صف
بررسی جدا هستند.

## مرز نتیجه

این Artifact ظرفیت Static Runtime را نشان می‌دهد، نه منوی مجاز User جاری،
فعالیت سه‌ماهه، Atomicity یا برابری مقصد. برای هر Command مادی همچنان
Route/Permission، Context/State، SQL و Golden test لازم است.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_all_form_call_contracts_20260827.json`
- `scripts/windows/extract_varanegar_all_form_call_contracts.py`
- `tests/test_varanegar_ui_evidence.py`
