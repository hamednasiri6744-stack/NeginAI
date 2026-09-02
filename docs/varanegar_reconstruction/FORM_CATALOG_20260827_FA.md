# کاتالوگ فرم‌های Runtime وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **کاتالوگ Metadata؛ نه فهرست منوی مجاز کاربر**

## نتیجه

از ۲۹ Assembly هسته، ۴۴۵ نامزد فرم واقعی استخراج شد. ۴۴۲ مورد شاهد قوی
`InitializeComponent + Form base type` دارند و سه مورد با اطمینان متوسط نگه
داشته شدند. هیچ Assembly اجرا، هیچ Resource/User string خوانده و هیچ فرم جدیدی
باز نشد.

توزیع ماژولی:

| خانواده | تعداد فرم |
|---|---:|
| `VN.SDS.Sales` | ۱۳۱ |
| `VN.SDS.MainData` | ۱۲۲ |
| `TreasuryOld` | ۹۶ |
| `VN.SDS.Stock` | ۶۹ |
| `VN.SDS.Treasury` | ۱۳ |
| `VN.SDS.CreateVoucher` | ۸ |
| `VN.SDS.Container` | ۶ |

این توزیع نشان می‌دهد سطح اصلی پیچیدگی محصول در فروش، اطلاعات پایه، خزانه قدیمی
و انبار است. وجود ۹۶ فرم `TreasuryOld` کنار Treasury جدید یک مرز مهاجرت واقعی
است؛ بازسازی باید Compatibility/Strangler plan داشته باشد، نه Cut-over یکباره.

## شکل صفحه‌ها

| شکل | تعداد | برداشت طراحی |
|---|---:|---|
| Data entry | ۱۲۰ | Command form با Validator و Save contract |
| Form عمومی/Legacy | ۱۰۸ | نیازمند بررسی جداگانه |
| Selector | ۷۳ | Lookup API و انتخاب کنترل‌شده |
| Dialog | ۳۴ | Context/Reason/Confirmation کوچک |
| Dual-list assignment | ۲۹ | تخصیص چندبه‌چند با Diff/Audit |
| Master-detail entry | ۲۳ | Aggregate header/line |
| Report/analysis | ۲۰ | Query/read model و Export |
| Workflow/tracking | ۲۰ | State machine و Commandهای مرحله‌ای |
| List | ۱۸ | Projection/Filter/Paging |
| Tree | ۳ | سلسله‌مراتب و Permission/category tree |

۸۱ فرم Method گزارش/چاپ دارند، ۱۹۹ فرم Create/Save/Delete و ۱۲۰ فرم Method
مرتبط با Permission دارند. این اعداد اثبات نمی‌کنند همه برای کاربر جاری فعال‌اند؛
فقط ظرفیت موجود در Runtime را نشان می‌دهند.

## Workflowهای با اولویت بالا

نمونه‌های صریح Metadata:

- Treasury: پیگیری R/PCheque، Guarantee، Bank draft و Receipt management؛
- Distribution: لیست/ورود توزیع، انتخاب فاکتور، Order-to-Dist، Follow، خروج،
  حذف خروج با Reason و تغییر Batch؛
- Sale: Follow voucher، Final date management و Prize follow-up؛
- Stock: اقلام انبار، Cardex/Healthy Cardex، گزارش سری ساخت و سفارش تولید؛
- Posting: External voucher، Manual voucher و Accounting mapping؛
- Reporting: Supplier cardex، Customer cardex، Factor/Return report، Statement،
  Call-center report و Dashboard.

این فهرست برای Backlog مقصد ارزشمند است، اما اولویت پیاده‌سازی باید از حجم سه
ماه، ریسک مالی، نقش واقعی و Golden parity تعیین شود؛ تعداد فرم معیار ارزش نیست.

## نگاشت دامنه‌ای

۳۷۷ فرم با Ruleهای نام‌محور به یک دامنه اولیه نگاشت شدند و ۶۸ فرم عمداً
`unmapped` ماندند. نگاشت Keyword فقط برای برنامه‌ریزی Navigation است؛ مثلاً یک
Cardex مشتری ممکن است هم دامنه Party و هم وصول/فروش را مصرف کند. قبل از ساخت هر
Slice باید Type→Handler→SQL مشابه چهار فرم فعال استخراج شود.

برای هر فرم Artifact موارد زیر را دارد:

- Assembly/family و Base type؛
- Page shape و سطح اطمینان فرم بودن؛
- Domain matchها و Keyword شاهد؛
- وجود Method گزارش، Create/Save/Delete و Permission؛
- محدودیت‌های تفسیر.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_form_catalog_20260827.json`
- `scripts/windows/build_varanegar_form_catalog.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_form_catalog.py `
  --assemblies G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_assembly_contracts_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_form_catalog_20260827.json
```

## Gate بعدی

1. اتصال Form type به MenuConfig/AccessNode و تشخیص Enabled-for-current-role؛
2. استخراج ۲۰ Workflow/Tracking type با IL هدفمند؛
3. استخراج ۲۰ Report form و Query source، بدون ذخیره خروجی ردیفی؛
4. رتبه‌بندی Sliceها با حجم سه‌ماهه، ریسک مالی و وابستگی بین دامنه‌ها؛
5. تبدیل فقط Capabilityهای اثبات‌شده به Route/API مقصد.
