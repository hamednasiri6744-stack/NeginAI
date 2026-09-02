# کاتالوگ مجوز مغایرت بانکی — ۱۴۰۵/۰۶/۰۵

## نتیجه

Guardهای IL دو Alias قدیمی را نشان می‌دهند و هر دو در کاتالوگ AccessNode Clone
واقعاً وجود دارند:

| Alias Legacy | Parent | Childها |
|---|---|---|
| `TransferList` | `OtherOperation` | `View`, `AddNew`, `Edit`, `Delete` |
| `ReconciliationSetup` | `OtherOperation` | `View`, `Edit`, `Delete` |

Alias اول reuse مجوز Transfer است و نام کسب‌وکاری مناسبی برای مقصد نیست. Alias
دوم نیز `Confirm` مستقل ندارد. پس نمی‌توان از `Edit` اجازهٔ تأیید نهایی یا از
`Delete` سیاست Cancel/Reversal را استنباط کرد.

## شواهد تجمیعی Assignment

برای دو Root و هفت Child، فقط شمارش تجمیعی AccessValue خوانده شد:

- ۶۳ assignment مستقیم با مقدار Allow؛
- ۲۲ assignment گروهی با مقدار Allow؛
- صفر assignment با مقدار Deny؛
- ۳۶ bucket تجمیعی Source × Node × AccessValue.

الگوریتم Effective رسمی نیز فقط به‌صورت Aggregate روی ۱۴۱ کاربر فعال اجرا شد:

- هفت Admin bypass در هر Node؛
- Effective allow برای Nodeهای TransferList/View/AddNew/Edit برابر ۲۷ نفر؛
- Effective allow برای TransferList.Delete و چهار Node شاخه
  ReconciliationSetup برابر ۱۸ نفر؛
- Explicit deny مؤثر صفر؛ بقیه ۱۱۴ یا ۱۲۳ نفر Neutral/no-allow هستند.

شناسه‌ها فقط داخل SQL برای Aggregate پردازش شدند؛ هیچ AppUserId، UserGroupId،
نام، عضویت، identity یا ردیف حق منفرد ذخیره نشد. Assignment countها تعداد کاربر
یکتا نیستند و خروجی Effective نیز مجوز شخص نام‌برده‌ای را افشا/ثابت نمی‌کند.
قرارداد عمومی قبلی همچنان برقرار است: Admin bypass؛ در غیر این صورت
Deny بر Allow مقدم، Neutral فاقد اجازه و حداقل یک Allow مستقیم/گروهی لازم است.

## قرارداد مقصد ERP نگین

Aliasهای Legacy فقط شاهد هستند و نباید Capability مقصد شوند. حداقل Capabilityهای
مجزای زیر لازم‌اند:

- `bank_reconciliation.view`
- `bank_reconciliation.import_statement`
- `bank_reconciliation.match_instrument`
- `bank_reconciliation.unmatch_instrument`
- `bank_reconciliation.confirm`
- `bank_reconciliation.cancel`

اجازهٔ فرمان علاوه بر Capability به scope حساب/سال/DC، تاریخ عملیات، نسخهٔ
Aggregate، وضعیت workflow و validation دامنه‌ای وابسته است. به‌ویژه Edit به
Confirm ارتقا داده نمی‌شود و Cancel جای Reversal سند تأییدشده را نمی‌گیرد.

## UAT لازم پیش از هر Command عملیاتی

حداقل این سناریوها با کاربر تستی نام‌گذاری‌نشده و دادهٔ ایزوله باید اجرا شوند:

1. Admin bypass مجوز Node دارد، اما تاریخ بسته/Scope نامعتبر همچنان Command را می‌بندد؛
2. Direct allow بدون deny و Group allow بدون deny هرکدام نتیجه مجاز می‌دهند؛
3. Neutral بدون allow نتیجه عدم‌اجازه دارد؛
4. Direct یا Group deny بر allow مقدم می‌شود؛
5. دارنده Edit بدون Capability مستقل Confirm نمی‌تواند تأیید کند؛
6. کاربر خارج از BankAccount/Fiscal/DC scope هیچ داده یا Command مؤثری نمی‌بیند؛
7. revoke در Session بعدی/Token refresh اثر می‌کند و cache مجوز قدیمی باقی نمی‌ماند؛
8. stale aggregate version و وضعیت Confirmed حتی با Capability معتبر رد می‌شوند.

این UATها هنوز اجرا نشده‌اند؛ آمار Aggregate فقط انتخاب Fixture و انتظار تست را ممکن می‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_permission_catalog_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_permission_catalog.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_bank_reconciliation_permission_catalog.py `
  --command-guards G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_command_guards_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_permission_catalog_20260827.json
```

وضعیت Artifact: `PASS`؛ دو Alias، هفت Child، ۳۶ bucket Assignment، ۹ Aggregate
Effective node و صفر خطای اعتبارسنجی.
