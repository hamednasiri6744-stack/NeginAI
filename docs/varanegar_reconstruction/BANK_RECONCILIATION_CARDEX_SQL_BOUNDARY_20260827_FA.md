# مرز SQL ثبت کاردکس تطبیق بانکی — ۱۴۰۵/۰۶/۰۵

## نتیجه

مسیر نهایی تأیید تطبیق بانکی از
`TreasuryOld.DataLayer.ReconcileAdapter.UpdateBankAccountCardex` به فرمان ذخیره‌شده
`dbo.DoReconcile_UpdateBankAccountCardex` می‌رسد. این نتیجه از دو شاهد مستقل آمده است:

1. literal محدود و allowlist‌شده در IL همان اسمبلی DataAccess؛
2. موجودیت، امضا و وابستگی‌های ثبت‌شده در کاتالوگ Clone فقط‌خواندنی.

در این Artifact هیچ متن تعریف روال، مقدار رکورد تجاری، connection string یا اجرای
روال خوانده/ثبت/اجرا نشده بود. Artifact مکمل
`BANK_RECONCILIATION_CONFIRM_CARDEX_SEMANTICS_20260827_FA.md` بعداً Definition را
فقط در حافظه و Redacted Parse کرد و Defect حداکثر یک Link را اثبات کرد.

## امضای کاتالوگی

| پارامتر | نوع | جهت |
|---|---|---|
| `@ReconcileId` | `int` | ورودی |
| `@ErrorNo` | `tinyint` | خروجی |

روال از دید کاتالوگ به این موجودیت‌ها وابسته است:

- `dbo.ReconcileItem`
- `dbo.BankBill`
- `dbo.PCheque`
- `dbo.PWithdraw`
- `dbo.RBankDraft`
- `dbo.RCashDraft`
- `dbo.RCheque`
- `dbo.Transfer`

وابستگی `ud_id` نیز در metadata دیده می‌شود؛ چون object قابل resolve نیست، فقط به‌عنوان وابستگی نوع/نام کاتالوگی نگهداری شده و معنای تجاری برای آن استنباط نشده است.

## قرارداد هدف ERP نگین

- API نباید نام یا اجرای مستقیم روال قدیمی را در اختیار client قرار دهد.
- فرمان عمومی هدف `bank_reconciliation.confirm` است.
- ورودی repository فقط `reconcile_id` تایپ‌شده است؛ خطای خروجی legacy باید در adapter به خطای دامنه‌ای پایدار نگاشت شود.
- application service مالک تنها transaction تأیید است؛ repository حق commit مستقل ندارد.
- تغییر وضعیت تطبیق، اثرات کاردکس، audit و outbox باید در یک تراکنش محلی اتمیک باشند.
- پس از commit، برابری اثر روی هشت خانواده موجودیت بالا باید با golden case و parity query کنترل شود.
- اجرای مستقیم روال legacy از web مجاز نیست؛ این روال شاهد رفتار است، نه قرارداد عمومی آینده.

## محدودیت شاهد

- وابستگی کاتالوگی همه شاخه‌های dynamic SQL احتمالی را ثابت نمی‌کند.
- Clone خالی/قدیمی ممکن است با محیط عملیاتی drift داشته باشد؛ این سند جای UAT و مقایسه واقعی را نمی‌گیرد.
- ترتیب دقیق Updateها از این Artifact اولیه نتیجه‌گیری نمی‌شود؛ سند مکمل شش Branch
  و Return زودهنگام را از Definition جاری Clone ثبت کرده است.
- هیچ فرم، command، stored procedure یا transaction اجرا نشده است.

## فایل‌ها و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_cardex_sql_boundary_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_cardex_sql_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_bank_reconciliation_cardex_sql_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_cardex_sql_boundary_20260827.json
```

وضعیت Artifact: `PASS`؛ یک command IL، یک procedure، دو پارامتر و ۹ وابستگی کاتالوگی، بدون mismatch منبع یا خطای اعتبارسنجی.
