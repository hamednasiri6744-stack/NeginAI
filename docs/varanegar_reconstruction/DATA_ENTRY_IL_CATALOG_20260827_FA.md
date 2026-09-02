# کاتالوگ IL تمام فرم‌های Data-entry وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۴۱ فرم پیدا شد؛ صفر خطای Method کسب‌وکاری و صفر Hash mismatch**

## دامنه استخراج

از کاتالوگ ۴۴۵ فرم، همه فرم‌های با اطمینان بالا و شکل `data_entry` یا
`master_detail_entry` انتخاب شدند. شش DLL رسمی مستقیماً از Share Runtime خوانده
شدند، اما هیچ Assembly Load/Execute نشد و هیچ UI/DB/Commandی اجرا نشد. Hash هر
DLL با Binary inventory قبلی برابر بود.

رشته‌های خارج از Allowlist فقط با SHA-256 و طول ذخیره شدند. Config و Resource
payload خوانده نشد.

## نتیجه عددی

- ۱۴۱ فرم در شش Assembly، همگی پیدا شدند؛
- ۳٬۹۷۱ Method body خوانده شد؛
- ۱۳۴ فرم حداقل یک Method با نام Write-like؛
- ۹۹ فرم حداقل یک Method Delete/Remove/Cancel/Reverse/Undo-like؛
- ۱۳۱ فرم Validation-like؛
- ۳۱ فرم Permission-like مستقیم؛
- ۱۰٬۹۶۴ اتصال غیرسیستمی از UI به Entity/Handler/Template/Helper؛
- ۲۰٬۲۸۹ String literal: ۶٬۲۵۹ Business allowlisted، ۱٬۸۳۷ Label فارسی
  allowlisted و ۱۲٬۱۹۳ فقط Fingerprint؛
- ۱۲۷ فرم اولویت بازبینی بالا، ۷ متوسط و ۷ پایین.

Priority بالا «آسیب‌پذیری» یا «ناامن» معنی نمی‌دهد؛ فقط می‌گوید قبل از بازسازی
آن فرم باید Command/Validator/Transaction آن دقیق‌تر Trace شود.

## الگوی معماری کشف‌شده

نام‌های تکرارشونده نشان می‌دهد Template پایه قرارداد رایجی ایجاد می‌کند:

- `SaveCommand` در ۱۱۵ فرم؛
- `CreateNewDataObject` در ۱۰۱ فرم؛
- `DeleteCommand` در ۷۶ فرم؛
- `UIOnPostCommandExecute` در ۶۰ فرم.

پس پیاده‌سازی وب نباید برای هر فرم یک CRUD مستقل و متفاوت بسازد. یک Application
shell مشترک برای Validation، Permission، Context، Expected version، Audit و
Command result لازم است؛ ولی Transaction واقعی هر دامنه باید مستقل Trace شود.

فرم‌های پراتصال، نقاط مناسب تحلیل بعدی هستند: Discount، Order، RetSale،
LoanOrder، SupplierInvoice، FreeInvoice، Customer، Stock Voucher، Goods،
RetOrderSale، Contract Price wizard و Supplier Return.

## تفسیر Permission

۱۰۴ فرم Write-like Method دارند ولی Method مجوز مستقیم در همان Type دیده نشد.
این شاهد «بدون مجوز بودن» نیست؛ بسیاری از فرم‌ها از Base template، Menu node یا
Handler مشترک استفاده می‌کنند. نتیجه درست این است که Permission باید در Call
graph ارث‌بری/Base/Server جداگانه اثبات شود و نبود Method محلی کافی نیست.

## Evidence limit

یک بدنه `InitializeComponent` در
`VN.SDS.MainData.UI.ServerConfig.FormServerConfig` با
`MethodBodyFormatError` قابل Parse نبود. این Method Designer UI است؛ هیچ Method
کسب‌وکاری خطا نداشت. بااین‌حال Field/Label کامل همان فرم از این Artifact ادعا
نمی‌شود.

## مرز نتیجه

نام Method و Call graph وجود مسیر را نشان می‌دهد، نه اینکه کاربر جاری آن را
مجاز دارد، در سه ماه اخیر استفاده شده، Transaction آن Atomic است یا رفتار مقصد
Parity دارد. این‌ها Gateهای مستقل Authorization، Activity و SQL هستند.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_data_entry_il_contracts_20260827.json`
- `scripts/windows/extract_varanegar_data_entry_il_contracts.py`
- `tests/test_varanegar_ui_evidence.py`
