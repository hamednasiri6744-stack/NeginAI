# قرارداد Parser، نگاشت ردیف، Dedup و Atomicity صورتحساب بانک

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ شاهد IL ایستا، بدون اجرای فایل/فرم/Office/Database command**

## نتیجهٔ اصلی

چهار Method با ۴۰۹ Instruction نشان می‌دهند Import Legacy یک Pipeline اتمیک
نیست. `SaveData` ابتدا Header مغایرت را Commit می‌کند، بعد Parser انتخاب می‌شود و
هر `BankBill.Update` Transaction مستقل خودش را دارد. بنابراین خطای Parse می‌تواند
Header تنها و خطای ردیف میانی می‌تواند Header به‌همراه بخشی از ردیف‌ها را باقی
بگذارد. این نتیجه از Control flow و Transaction contracts است، نه اجرای خرابی.

## رفتار سه Parser

| Parser | Provider | Query | HDR |
|---|---|---|---|
| DBF | Jet dBASE IV | `SQLStatement` خام Profile | خوانده نمی‌شود |
| TXT | Jet Text | `SQLStatement` خام Profile | خوانده نمی‌شود |
| XLS | Jet Excel 8.0 | Query ثابت `Sheet1$` | خوانده نمی‌شود |

XLS آرگومان SQL تنظیم‌شده را Overwrite می‌کند. `HDR` در Setup Load و به هر Parser
پاس داده می‌شود ولی `ldarg.3` در هر سه Method صفر است. برای
`StartRow/Seperator/IsArabic` نیز در Static call operands کل
`TreasuryOld.Forms.dll` هیچ Getter call پیدا نشد. این نبود فقط در Scope همین
Assembly معتبر است و نبود مصرف‌کننده در کل Deployment را ثابت نمی‌کند.

## Schema ردیف Canonical Legacy

| ستون ورودی | Property مقصد | تبدیل |
|---|---|---|
| Date | VocherDate | ToString |
| Comment | VocherDescription | ToString |
| Debit | VocherDebit | Decimal |
| Credit | VocherCredit | Decimal |
| No1 | VocherNo | ToString |
| BaLance | Balance | Decimal |

اگر `Debit != 0` باشد، Debit نوشته و Credit صفر می‌شود؛ در غیر این صورت Credit
نوشته و Debit صفر می‌شود. پس اگر هر دو غیرصفر باشند Credit نادیده گرفته می‌شود و
اگر هر دو صفر باشند هر دو صفر می‌مانند. Row validation مستقلی برای حالت هر دو
غیرصفر مشاهده نشد.

## Dedup Legacy

قبل از Insert دو Predicate رشته‌ای ساخته می‌شود:

- Debit branch: Amount + VocherNo + VocherDate؛
- Credit branch: Amount + VocherNo + VocherDate.

Lookup با `BankBillAdapter.GetBankBillSWhere` انجام می‌شود و اگر Count مثبت باشد
ردیف Skip می‌شود. Scope شامل `ReconcileId` یا `BankAccountId` نیست و Predicate با
String concatenation ساخته می‌شود. بنابراین این منطق نه Query امن است و نه
Idempotency key کامل؛ ممکن است تراکنش مشابه در حساب/Session دیگر را حذف کند.

## قرارداد مقصد

- DBF/TXT نباید SQL خام Profile را اجرا کنند؛ Template نوع‌دار و Server-owned لازم است.
- شش ستون باید پیش از Commit از نظر Schema، نوع، تاریخ، مبلغ و Null اعتبارسنجی شوند.
- هر دو مبلغ غیرصفر باید Reject یا با Policy صریح Owner حل شود.
- Idempotency باید Account + ProfileVersion + Source file/row fingerprint را دربرگیرد.
- Header و همهٔ ردیف‌ها باید در یک Transaction مقصد Commit شوند؛ Parse/Validation
  failure باید صفر Persistence داشته باشد.
- Format=`default` نباید Session خالی بسازد.
- فیلدهای Profile که Parser مصرف نمی‌کند، صرفاً به‌دلیل وجود ستون فعال اعلام نشوند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_statement_parser_row_contract_20260827.json`
- `scripts/windows/extract_varanegar_bank_statement_parser_row_contract.py`
- `tests/test_varanegar_ui_evidence.py`

هیچ Parser، فایل، Excel process، فرم یا فرمان دیتابیس اجرا نشد و هیچ Literal یا
مقدار ردیف تجاری در Artifact ذخیره نشده است.
