# دامنه ۲۲: اعتبارسنجی ساختاری نوع سند و مرز قابلیت فعال

تاریخ استخراج: ۲۰۲۶-۰۸-۲۸  
وضعیت: **۴۵ کاندید ساختاری از ۶۵ نوع؛ ۲۰ نوع Dormant/ناقص؛ اجرای Predicate عمداً صفر**

## نتیجهٔ کوتاه

وجود Row در `ExternalVoucherType` به معنی قابلیت قابل صدور نیست. مسیر واقعی صدور
قبل از Finality، `dbo.usp_DoExternalVoucherTypeValidation` را اجرا می‌کند و نوع
ناسالم را Fail-closed رد می‌کند.

Replay فقط‌خواندنی همان قواعد برای سال ۱۴۰۵ نشان داد:

- ۶۵ نوع تنظیم‌شده و ۱۸ Creator تنظیم‌شده؛
- ۴۵ نوع کاندید ساختاری؛
- ۲۰ نوع نامعتبر ساختاری چون Article مؤثر ندارند؛
- ۱۳ مورد از همان ۲۰ نوع علاوه‌بر نبود Article، View/Creator قابل استفاده هم
  ندارند؛
- هیچ‌یک از ۲۰ نوع در کل تاریخچه، پنجرهٔ سه‌ماهه یا ۳۸۲ Header مسیر جدید استفاده
  نشده است.

پس این ۲۰ مورد خرابی عملیاتی مشاهده‌شده نیستند؛ محتمل است Dormant، Reserved یا
Legacy-incomplete باشند. بااین‌حال ERP مقصد نباید هر ۶۵ Row را خودکار به دکمه و
Command فعال تبدیل کند. این مرز با `R-051` ردیابی شده است.

## Validator مستقر چه چیزهایی را می‌سنجد؟

برای هر نوع انتخابی و سال مالی، Validator این قرارداد را اعمال می‌کند:

1. خود نوع، VoucherType، Creator و View باید قابل Resolve باشند؛
2. View باید پنج ستون پایهٔ `DCId/DCName/SaleOfficeId/VoucherId/VoucherNo` را
   داشته باشد؛
3. برحسب Flagهای Creator، ستون‌های `CustId/SupplierId/ContactId` نیز اجباری‌اند؛
4. همهٔ `VoucherCreatorField`های معرفی‌شده باید در View وجود داشته باشند؛
5. حداقل یک Article مؤثر در بازهٔ `FromAccYear..ToAccYear` لازم است؛
6. Date، Amount و SL هر Article اجباری است؛
7. نام‌های فیلدی Date/Amount/SL/DL/Fifth/Sixth/Seventh باید در Creator registry
   ثبت شده باشند؛
8. مقادیر عددی Ledger باید در Master همان سطح وجود داشته باشند؛
9. هر Article باید Comment component داشته باشد و Field مرجع Comment معتبر باشد؛
10. هر Predicate با Dynamic SQL روی View و شرط `WHERE 1=2 AND (...)` Compile
    می‌شود.

Extractor همهٔ موارد ۱ تا ۹ را از Catalog/Configuration بازسازی کرد، ولی مورد ۱۰
را عمداً اجرا نکرد؛ چون حتی `WHERE 1=2` اجرای Creator view محسوب می‌شود و خارج از
مرز فقط‌خواندنی این تحلیل بود. فقط ۷۱ Predicate متمایز شمارش و متن آن‌ها Hash شد.

## پروفایل سال و سیستم

نتیجه برای هر سه سال ۱۴۰۳، ۱۴۰۴ و ۱۴۰۵ یکسان است: ۶۵ تنظیم‌شده، ۴۵ کاندید و ۲۰
نامعتبر ساختاری.

| سیستم معنایی | نوع تنظیم‌شده | کاندید ساختاری | نامعتبر |
|---|---:|---:|---:|
| حسابداری انبار/خرید | ۱۷ | ۱۴ | ۳ |
| حسابداری مشتریان | ۱۴ | ۱ | ۱۳ |
| فروش | ۲ | ۲ | ۰ |
| خزانه | ۳۰ | ۲۶ | ۴ |
| حقوق | ۲ | ۲ | ۰ |

برای ۴۵ کاندید، هیچ خطای دیگری در ستون پایه/Party، Creator field، Date/Amount/SL،
Ledger master یا Comment contract پیدا نشد. واژهٔ «کاندید» عمدی است: تا Compile
۷۱ Predicate و Golden parity روی Harness ایزوله انجام نشود، آن‌ها Runtime-ready
نیستند.

## نکتهٔ تشخیصی

وقتی صدور با پیام «نام جدول/فیلد/آرتیکل/شرح تعریف نشده» رد می‌شود:

1. ابتدا نوع و سال انتخابی را مشخص کن؛
2. وجود Creator و View را بررسی کن؛
3. Article مؤثر همان سال را بررسی کن؛
4. سپس CreatorField→View column و Ledger codeها را تطبیق بده؛
5. در آخر Predicate را در Harness غیرعملیاتی Compile کن.

نباید مستقیم سراغ دادهٔ سند یا Repair جدول رفت؛ این دسته خطا ابتدا Configuration
contract است. همچنین نبود تاریخچه دلیل حذف نوع نیست.

## قرارداد مقصد

نوع سند باید State صریح داشته باشد:

```text
CONFIGURED_DORMANT
  -> STRUCTURALLY_VALID
  -> PREDICATE_COMPILED
  -> GOLDEN_VERIFIED
  -> OWNER_APPROVED_ACTIVE
```

- UI فقط `OWNER_APPROVED_ACTIVE` را برای Command نشان دهد؛
- ۲۰ نوع فعلی با Provenance حفظ و توسط مالک `dormant/repair/retire` شوند؛
- Type، Creator، Article، Comment و Predicate یک نسخهٔ immutable مشترک داشته
  باشند؛
- Compile/Publish در Harness ایزوله باشد، نه داخل Command مالی؛
- تغییر نسخه روی Batch جدید Snapshot شود و تاریخچه را بازتولید نکند.

## ماتریس Verification

| نیاز | شاهد | نتیجه | Gap |
|---|---|---|---|
| Validator در مسیر صدور است | dependency و ترتیب SQL | PASS | Runtime اجرا نشد |
| Rules ۱..۹ برای سه سال | Catalog/config replay | PASS بازتولید | فقط Snapshot Clone |
| همه ۶۵ نوع قابل صدورند | ۴۵ candidate / ۲۰ invalid | FAIL | Owner disposition لازم |
| Invalidها در عملیات استفاده شده‌اند | History/recent/modern crosswalk | PASS: صفر | حذف خودکار مجاز نیست |
| ۷۱ Predicate Compile می‌شوند | Hash/count؛ execution صفر | FAIL شواهد | Harness ایزوله لازم |

## شواهد و ایمنی

- Artifact:
  `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- Extractor:
  `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`
- Test:
  `tests/test_varanegar_voucher_creation_atomicity_policy.py`
- Risk: `R-051`.

هیچ Procedure یا Creator view اجرا نشد، هیچ Raw predicate/account code/comment
ذخیره نشد و اتصال Clone `READ_ONLY` با `can_update=0` و
`db_denydatawriter=1` بود.
