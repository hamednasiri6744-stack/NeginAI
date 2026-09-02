# تشخیص وضعیت برگ دسته‌چک پرداختنیِ مصرف‌شده و بدون چک جاری

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Clone فقط‌خواندنی، SQL رسمی؛ اجرای Command صفر**

## نتیجه

۱۵۵ برگ `PChequeBookItem` با `IsUsed=1` و بدون `PCheque` جاری، FK یتیم یا
خرابی قطعی نیستند. خود مسیر رسمی نگهداری برگ دسته‌چک اجازه می‌دهد مقدار
`IsUsed` مستقیماً از فرم ذخیره شود و Validator فقط وقتی برداشتن تیک را منع
می‌کند که برگ در `PCheque` یا `Transfer` استفاده شده باشد.

بنابراین مدل درست دو منشأ برای Used دارد:

```text
Cheque lifecycle  -> IsUsed مشتق‌شده از صدور/عودت/Undo چک
Leaf maintenance  -> IsUsed مستقیم و بدون PCheque/Transfer
```

این کشف به معنی اثبات «دستی‌بودن» تک‌تک ۱۵۵ سابقه نیست. جدول برگ هیچ ستون
زمان/کاربر تغییر ندارد، هیچ‌یک از ۱۵۵ مورد متن `IssuedFor` یا `Comment` ندارد
و Snapshot فعلی حذف تاریخی یک چک را بازسازی نمی‌کند. نام دقیق حالت مقصد باید
`SOURCE_USED_UNLINKED` با Provenance برابر `UNKNOWN_SOURCE` باشد.

## تطبیق عددی

| سنجه | تعداد |
|---|---:|
| همه برگ‌ها | ۵٬۶۸۷ |
| برگ Used | ۴٬۸۲۷ |
| متصل به چک جاری | ۴٬۶۷۲ |
| Used بدون چک جاری | ۱۵۵ |
| دسته‌چک درگیر | ۲۳ |
| لینک Transfer/Archive/RPTransfer در این ۱۵۵ | ۰ |
| متن IssuedFor/Comment در این ۱۵۵ | ۰ |

رابطه‌ی `4,827 = 4,672 + 155` دقیق است؛ پس فاصله‌ی شمارشی توضیح‌پذیر است، ولی
علت تاریخی هر سطر Auditپذیر نیست. همه‌ی ۱۵۵ مورد در دسته‌چک‌های فعال‌اند.

## قراردادهای رسمی SQL

- `usp_sdsnet_PchequeBookItem_Save` مقدار `IsUsed` را مستقیماً از staging فرم
  روی برگ ذخیره می‌کند؛
- `usp_sdsnet_PChequeBookItem_BeforeSave` برداشتن تیک را فقط هنگام وجود
  `PCheque` یا `Transfer` منع می‌کند و متن Validation مسیر دستی را صریحاً
  متمایز می‌کند؛
- `BeforePCheque` هنگام انتخاب برگ، آن را Used می‌کند؛
- `DoPCheque_AddPChequeHistory` برای وضعیت عودت (`2`) برگ را آزاد و برای سایر
  وضعیت‌ها Used می‌کند؛
- `DoPCheque_DeleteLastPChequeHistory` پس از Undo، وضعیت برگ را بازحساب می‌کند.

پس `Cheque + CurrentHistory + ChequeLeaf` یک مرز Transaction و Consistency واحد
است و در ERP وب نباید توسط CRUDهای مستقل نوشته شود.

## تصمیم تشخیصی و مهاجرت

1. نبود PCheque جاری به‌تنهایی Incident نیست.
2. `IsUsed` خودکار پاک نشود و PCheque ساختگی تولید نشود.
3. مقصد سه حالت مستقل `AVAILABLE`، `LINKED_TO_CHEQUE` و
   `SOURCE_USED_UNLINKED` داشته باشد.
4. ۱۵۵ حالت سوم با `UNKNOWN_SOURCE` وارد و پیش از آزادسازی مجدد به مسئول خزانه
   ارجاع شود.
5. Command آینده باید رخداد، Current projection و Leaf state را در یک
   Transaction نسخه‌دار و Idempotent ثبت کند.
6. مقصد از این پس Actor، Timestamp، Reason و Source version را برای تغییر دستی
   برگ اجباری کند.

## سطح اطمینان و محدودیت

- پشتیبانی رسمی حالت Used مستقیم: **اطمینان بالا؛ SQL Deploy‌شده**.
- شمارش و نبود لینک جاری: **اطمینان بالا؛ Aggregate روی Clone فقط‌خواندنی**.
- علت تاریخی تک‌تک ۱۵۵ برگ: **نامعلوم و غیرقابل استنتاج از Snapshot**.

هیچ شماره چک/برگ، حساب بانکی، کاربر، توضیح یا ردیف خام در Artifact ذخیره نشده
و هیچ فرم، Procedure یا Transaction عملیاتی اجرا نشده است.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_payable_cheque_leaf_usage_diagnostic_contract.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_payable_cheque_leaf_usage_diagnostic_contract_20260827.json
```
