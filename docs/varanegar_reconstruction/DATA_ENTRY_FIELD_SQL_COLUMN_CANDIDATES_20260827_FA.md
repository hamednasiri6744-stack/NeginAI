# نامزدهای فقط‌خواندنی Field/Property به ستون SQL

## نتیجه

از ۸۱۳ فیلد فرم‌های ورود داده، فقط ۷۸ فیلد قبلاً به‌کمک هم‌نامی و حضور در یک
Method به ۱۰۰ فراخوانی Property نسبتاً قوی وصل شده بودند. این مرحله همان ۱۰۰
Property را فقط با متادیتای ستون‌های Clone فقط‌خواندنی تطبیق داد:

- ۸۵ Property حداقل یک ستون هم‌نام و ۱۵ Property هیچ ستون هم‌نامی ندارند؛
- ۷۰ فیلد حداقل یک نامزد ستون و ۵۶ فیلد حداقل یک نامزد دارای شباهت نام Entity/Object دارند؛
- ۱٬۳۳۱ ستون فیزیکی/نمای یکتا نامزد شد؛ ۱۷ Property به سقف ایمنی ۵۰ نتیجه رسید؛
- ۲۸ فراخوانی Property یک Object دقیقاً هم‌نام Entity دارند؛ پس از حذف تکرار
  getter/setter، ۲۱ پیوند Field/Property/Object/Column باقی می‌ماند؛
- Runtime binding، Source column قطعی و Query parameter قطعی همچنان **صفر** است.

## Anchorهای دقیق‌تر ولی هنوز غیرقطعی

قوی‌ترین Name anchors در چهار ناحیه دیده شدند:

| فرم | Object | نمونه ستون‌ها |
|---|---|---|
| `frmCashEdit` | `dbo.RCash` | `RCashAmount`, `RCashComment` |
| `frmChequeEdit` | `dbo.RCheque` | `RChequeNo`, `RChequeDate`, `RChequeAmount`, `SayadNo`, مشخصات شعبه |
| `frmRCashDraftEdit` | `dbo.RCashDraft` | شماره، تاریخ، مبلغ، شرح، شعبه و `VosulDate` |
| `FormCustInfo` / ProductFormula | `dbo.Customer` / `dbo.Goods` | `Address` / `GoodsCode` |

نوع و Nullability کاتالوگ نیز کنار هر نامزد ثبت شده است؛ برای مثال مبلغ نقدی
`money NOT NULL`، مبلغ چک `ud_Money NOT NULL`، شماره صیاد `nvarchar NULL` و
کد کالا `ud_TinyStr NOT NULL` است. این‌ها قرارداد ستون Clone هستند، نه الزام
قطعی UI یا مدل مقصد.

## شاهد منفی مهم

هم‌زمانی Method می‌تواند False positive بسازد. مثلاً فیلد `txtRCashDraftNo`
علاوه بر `dbo.RCashDraft.RCashDraftNo` به تنظیم
`dbo.TRServerConfig.NotInsertDuplicateRCashDraftNo` هم می‌رسد؛ دومی یک Rule
flag است و Source فیلد نیست. بنابراین حتی تطبیق دقیق Entity/Object نیز بدون
ردیابی setter/getter، DataAdapter/ORM و UAT به Binding قطعی ارتقا نمی‌یابد.

## مرز ایمنی و Gate بعدی

- فقط `sys.columns/sys.objects/sys.schemas` و متادیتای PK/FK روی
  `NeginPakhsh_WebDev` خوانده شد؛ هیچ مقدار تجاری یا Definition ماژول ذخیره نشد.
- هیچ Procedure/Function/View/Trigger یا Command برنامه اجرا نشد و UI زنده لمس نشد.
- برای تبدیل هر Anchor به قرارداد مقصد باید زنجیره‌ی کنترل → setter/getter →
  Adapter/SQL parameter → ستون، سپس Requiredness/Validation و Golden UAT با مالک
  دامنه اثبات شود.

منبع ماشین‌خوان:
`artifacts/varanegar_analysis/ui/varanegar_data_entry_field_sql_columns_20260827.json`

