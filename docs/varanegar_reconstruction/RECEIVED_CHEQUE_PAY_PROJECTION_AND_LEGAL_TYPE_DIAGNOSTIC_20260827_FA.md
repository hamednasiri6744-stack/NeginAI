# قرارداد تشخیص Pay Projection و LegalType چک دریافتی

## نتیجه‌ی اول: هشت چک «بدون Pay link» نیستند

در ۱۲٬۶۳۵ چک جاری وضعیت ۷ (واگذار به غیر):

```text
TblCheque.PayId = current-history PayId2       12,627
TblCheque.PayId is null, history PayId2 exists       8
history PayId2 orphan                                0
master/history conflicting link                       0
```

هر هشت مورد دارای `tblChqHist.PayId2` معتبرند و Pay مرتبط در وضعیت تأییدشده
است. بنابراین تعبیر قبلی «هشت Pay link مفقود» غلط بود. قرارداد رسمی دو مرحله
دارد:

| مرحله Pay | مرجع رسمی چک واگذارشده |
|---|---|
| Draft/تأییدنشده (`PayStatusId=1`) | `TblCheque.PayId`؛ Projection انتخاب |
| Approved (`PayStatusId=2`) | `tblChqHist.PayId2`؛ رخداد/مرجع پایدار |

هم View رسمی `dbo.Pay2` و هم
`dbo.USP_SDSNET_PayRCheque_GetList` دقیقاً همین Branch را اجرا می‌کنند.
`DoRCheque_CessionToOther` در زمان انتخاب، Pay را روی Master و سپس History می‌برد؛
`DoRCheque_AddRChequeHistory` هنگام خروج از وضعیت ۷ Master projection را خالی
می‌کند. پس مدل مقصد نباید یک FK منفرد را هم Draft و هم History بداند.

هفت مورد از هشت مورد توالی `1→8→1→7` و یک مورد `1→7` دارند؛ همه‌ی رخدادهای
نهایی PayId2 دارند. ساختن Pay مصنوعی یا Quarantine این هشت مورد می‌تواند لینک
تأییدشده را Duplicate یا جابه‌جا کند.

## نتیجه‌ی دوم: LegalType تهی Unknown است و قابل حدس نیست

در ۵۳ چک جاری وضعیت ۹:

| LegalType | معنا | تعداد | PersonnelId |
|---:|---|---:|---:|
| NULL | نامشخص/Unspecified source state | ۳۵ | ۳۵ |
| ۲ | واگذار به دایره حقوقی | ۱۸ | ۱۸ |

Master رسمی فقط دو مقدار دارد:

- ۱: واگذار به پرسنل؛
- ۲: واگذار به دایره حقوقی.

وجود PersonnelId نوع را تعیین نمی‌کند، چون در هر ۱۸ ردیف نوع ۲ نیز Personnel
وجود دارد. Validator فعلی فقط می‌گوید اگر نوع ۱ باشد Personnel نباید خالی باشد؛
خود LegalType را Mandatory نمی‌کند. همچنین `LegalType=0` پیش از Insert عمداً
به NULL تبدیل می‌شود. هر ۳۵ NULL در بازه‌ی فشرده
`1404/05/25..1404/05/27` هستند و ردیف‌های نوع ۲ از `1404/10` به بعد دیده
می‌شوند. این تفاوت، شاهد Version/source semantics است؛ مجوز حدس نوع ۱ یا ۲ نیست.

## نقص Static مهم در مسیر تأیید گروهی

در Package/SQL Deploy‌شده،
`dbo.usp_sdsnet_RChequeChangeStatus_Save` مقدار `LegalType` را روی Parent سند
تغییر وضعیت ذخیره می‌کند، اما هنگام Confirm و فراخوانی
`DoRCheque_AddRChequeHistory` آرگومان اختیاری `@LegalType` را ارسال نمی‌کند.
در نتیجه History مقدار پیش‌فرض NULL دریافت می‌کند.

این یک شکاف مسیر قابل‌دسترسی در کد Deploy‌شده است، اما Static analysis نرخ وقوع
آن را ثابت نمی‌کند. Parentهای فعلی خالی‌اند، پس برای ۳۵ ردیف تاریخی نمی‌توان
مقدار اصلی را از Parent بازیابی کرد. در مقصد باید Legal routing جزئی از همان
Event تغییر وضعیت و Transaction باشد، نه فیلد موقت فرم/Parent.

## قرارداد مقصد و تشخیص Incident

```text
ChequeCessionDraftSelection       -> mutable, before Pay approval
ChequeCessionApprovedEvent.PayRef -> immutable history authority
ChequeLegalEvent.LegalRoute       -> PERSONNEL | LEGAL_DEPARTMENT | UNKNOWN_SOURCE
```

Incident Pay فقط وقتی است که PayId2 رخداد تأییدشده یتیم، متناقض یا با Pay/State
ناسازگار باشد؛ خالی بودن `TblCheque.PayId` به‌تنهایی Incident نیست. Incident
LegalType وقتی است که Command جدید مقدار انتخاب‌شده را به Event منتقل نکند یا
State/Personnel/Route ناسازگار باشد. NULL تاریخی بدون Source معتبر باید
`UNKNOWN_SOURCE` بماند، نه اینکه خودکار Repair شود.

Golden Caseها باید Draft→Approve، Approve→Undo، خروج از Status 7، انتقال صندوق
قبل از واگذاری، Legal route نوع ۱/۲/Unknown، Retry و Fault بین Parent و History
را پوشش دهند.

## حدود شواهد و ایمنی

Static SQL شکاف آرگومان را ثابت می‌کند، نه تعداد اجرای Runtime آن را. Snapshot
فعلی همه‌ی Parentهای حذف/Archiveشده و Editهای میانی را بازسازی نمی‌کند. هیچ
شناسه، شماره چک/Pay، نام، Comment یا ردیف خام ذخیره نشد و هیچ Form، Procedure،
Transaction یا Mutation اجرا نشد.

## Artifact

- Extractor:
  `scripts/sql/extract_varanegar_received_cheque_projection_and_legal_type_diagnostic_contract.py`
- Artifact:
  `artifacts/varanegar_analysis/ui/varanegar_received_cheque_projection_and_legal_type_diagnostic_contract_20260827.json`
- Validation: `PASS`

