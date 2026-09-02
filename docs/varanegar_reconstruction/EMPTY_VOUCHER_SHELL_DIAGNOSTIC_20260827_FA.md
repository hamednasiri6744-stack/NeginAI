# تشخیص سند فعال بدون قلم

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Clone فقط‌خواندنی و SQL رسمی؛ اجرای Command صفر**

## نتیجه

تنها `Voucher` فعال بدون `VoucherItem` یک سند مالی Post‌شده یا Header خراب نیست؛
یک Shell دستی در وضعیت ۱ «پیش‌نویس» است. هیچ قلم فعال/حذف‌شده، لینک
`ExternalVoucherHeader` یا اثر بدهکار/بستانکار ندارد و مسیر رسمی دفترکل نیز برای
اثر مالی به `VoucherItem` وابسته است.

بااین‌حال Shell شماره سند منبع دارد. `DoVoucher_SetVoucherNo` در نسخه فعلی سند
بدون قلم را صریحاً رد می‌کند؛ پس شماره‌ی موجود یک Provenance تاریخی حل‌نشده است
و نباید خودکار در مقصد آزاد یا به‌عنوان شماره Posted پذیرفته شود.

```text
Migration state: DRAFT_EMPTY_NUMBERED_SHELL
Ledger effect:    zero
Provenance:       UNKNOWN_SOURCE
Forbidden:        synthesize lines / post / silently reuse source number
```

## پروفایل تجمیعی

- تعداد: ۱؛
- Manual: بله؛ External-linked: خیر؛
- وضعیت جاری و تنها History: Draft؛
- نوع سند: ۵۹، عمومی تأمین‌کننده؛
- سال مالی قدیمی‌تر و DC=1؛
- VoucherNo منبع: موجود، ولی مقدار آن خوانده/ذخیره نشده؛
- قلم فعال یا حذف‌شده: صفر؛ Debit/Credit: صفر.

## مسیر رسمی و Root-cause candidate

- `Usp_Sdsnet_Voucher_Save` هنگام ویرایش، قلم‌های غایب از `#VoucherItems` را
  حذف می‌کند؛
- اگر سند موقت پس از Validation نامعتبر شود، مسیر می‌تواند آن را Draft کند؛
- فراخوانی بازشماری `DoVoucher_SetVoucherNo` در مسیر درج دستی Deploy‌شده Comment
  شده است؛
- `DoVoucher_SetVoucherNo` در صورت نبود قلم، خطا می‌دهد؛
- `Get_GLBook` بدون قلم هیچ اثر Ledger از این Shell نمی‌سازد.

این مسیر توضیح فنی محتمل است، نه اثبات تاریخچه همان یک سند؛ Snapshot فقط یک
رخداد Draft دارد و قصد اپراتور قابل بازیابی نیست.

## تصمیم مقصد

1. Shell بدون ساخت Line وارد Staging/Review شود، نه Ledger.
2. شماره منبع فقط Provenance باشد و به Posted target number تبدیل نشود.
3. آزادسازی/حذف/تکمیل Shell یک Command حسابرسی‌شده با تصمیم حسابدار باشد.
4. شماره Posted فقط پس از حداقل دو قلم، تراز، Dimension validation و Commit
   اتمیک تخصیص یابد.
5. تست empty/unbalanced/retry/fault تضمین کند Draft هیچ‌گاه شماره Posted نگیرد.

## محدودیت و ایمنی

علت تاریخی Shell نامعلوم است. هیچ شماره، کاربر، توضیح، Reference، Account یا
ردیف خام ثبت نشده و هیچ فرم، Procedure یا Transaction عملیاتی اجرا نشده است.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_empty_voucher_shell_diagnostic_contract.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_empty_voucher_shell_diagnostic_contract_20260827.json
```
