# دامنه ۱۴: خروج وجه تأمین‌کننده و چرخه چک پرداختنی

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- منبع: `127.0.0.1 / NeginPakhsh_WebDev`
- دیتابیس `READ_ONLY`، مجوز `UPDATE=0` و عضویت تحلیل‌گر در
  `db_denydatawriter` کنترل شد.
- Extractor:
  `scripts/sql/extract_varanegar_supplier_disbursement_domain.py`
- Artifact:
  `artifacts/varanegar_analysis/domains/supplier_disbursement_and_payable_cheques_20260826.json`

این مرحله ۱۸ جدول، ۱۶۶ FK رسمی، ۱٬۱۷۸ مصرف‌کننده ماژولی، ۵۷ Link ضمنی و ۱۳
قرارداد SQL منتخب را بررسی کرده است. شماره چک/صیاد/حساب، هویت Payee/Supplier،
Comment، User/Host، Credential و ردیف خام پرداخت ذخیره نشده است.

## نتیجه اصلی: Pay پاکت تأییدشده و Instrument فرزند آن است

```text
dbo.Pay (reason, payee, date, fiscal/DC, status)
  ├─ dbo.PCash       [0..1]
  ├─ dbo.PWithdraw   [0..22]
  └─ dbo.PCheque     [0..76]
        ├─ PChequeBookItem
        └─ PChequeHistory [2..4]
              └─ PCheque.PChequeHistoryId = current event

Pay.PayeeId = Supplier.ContactId
  └─ Acc.Usp_GetSupplierRemAmount
```

۳۰٬۳۲۲ Pay وجود دارد و همه `PayStatusId=2` «تأیید شده» هستند. فقط ۱۷٬۳۰۱
مورد ConfirmDate دارند؛ بنابراین ConfirmDate در داده Legacy شرط رسمی تأیید
نیست و Status مرجع است.

در سه ابزار اصلی:

| ابزار | ردیف | Pay یتیم | UUID ناقص/تکراری | مبلغ نامثبت |
|---|---:|---:|---:|---:|
| نقد | ۱٬۶۸۴ | ۰ | ۰ | ۰ |
| برداشت بانکی | ۲۹٬۰۸۳ | ۰ | ۰ | ۰ |
| چک پرداختنی | ۴٬۶۷۲ | ۰ | ۰ | ۰ |

۲۸٬۳۸۴ Pay دقیقاً یک Instrument، ۱٬۴۵۱ Pay چند Instrument و ۲۹ Pay ترکیبی
از بیش از یک نوع ابزار دارند. ۴۸۷ Pay هیچ‌کدام از این سه ابزار را ندارند و از
مسیرهای دیگر مثل چک سایرین/پرداخت گروهی/سند مالی مصرف می‌شوند. پس مدل مقصد
نباید روی Pay یک `PaymentType + Amount` منفرد بگذارد.

## پرداخت‌های مستقیم به تأمین‌کننده

Join رسمی `Pay.PayeeId = Supplier.ContactId` این جمعیت را می‌دهد:

| ابزار | ردیف | Pay | تأمین‌کننده | مبلغ |
|---|---:|---:|---:|---:|
| نقد | ۱۱۸ | ۱۱۸ | ۱۷ | ۴٬۵۹۹٬۳۹۹٬۰۰۰ |
| برداشت | ۱٬۷۲۸ | ۱٬۵۶۰ | ۵۸ | ۵۵۰٬۸۷۴٬۲۱۴٬۲۲۷ |
| چک پرداختنی | ۲٬۶۳۰ | ۳۶۱ | ۴۸ | ۱۵٬۴۱۰٬۸۴۴٬۳۱۷٬۰۹۰ |

این شاهد توضیح می‌دهد چرا دو ردیف `Acc.tblSupSettlement` کل پرداخت‌های
تأمین‌کننده نیستند. Settlement فقط تخصیص به فاکتور است؛ خود خروج وجه از Pay و
Instrument می‌آید و Cardex رسمی هر دو را ترکیب می‌کند.

`RPReason` نیز دامنه عمومی پرداخت است، نه فقط تأمین‌کننده. ۳۹ Reason در داده
مصرف شده؛ از حقوق و کرایه تا هزینه، مشتری و تأمین‌کننده. Reason «پرداخت به
تأمین‌کننده» ۳٬۴۵۳ Pay دارد، اما انتخاب Supplier در Cardex از Payee/Contact
انجام می‌شود. فیلترکردن صرف با Reason، پرداخت‌های واقعی Supplier را جا می‌اندازد.

## هویت و وضعیت چک پرداختنی

۴٬۶۷۲ چک پرداختنی:

- همه UUID یکتا و مبلغ مثبت؛
- همه دقیقاً یک ChequeBookItem معتبر و بدون reuse دارند؛
- ۴٬۴۰۸ مورد Sayad پر؛ مقدار صیاد ذخیره نشده؛
- ۱۲۴ چک Certified؛
- `IsReconciled=1` در داده فعلی صفر؛
- سررسید از `۱۳۹۹/۰۱/۰۱` تا `۱۴۰۷/۰۸/۰۱`.

Master وضعیت:

| کد | نام | History | جاری |
|---:|---|---:|---:|
| ۱ | صادره | ۴٬۶۷۲ | ۰ |
| ۲ | عودت | ۶۴ | ۱ |
| ۳ | پرداخت | ۳٬۶۳۷ | ۳٬۶۳۷ |
| ۴ | ابطالی | ۸۱ | ۸۱ |
| ۵ | پرداختنی | ۴٬۶۵۴ | ۹۵۳ |

Status=1 فقط وضعیت اولیه است. همه چک‌ها با «صادره» آغاز و سپس با Workflow
منتقل شده‌اند؛ آن را نباید به‌عنوان وضعیت جاری قابل‌ماندن در مقصد مدل کرد.

## تاریخچه و Workflow

۱۳٬۱۰۸ History وجود دارد. هر چک حداقل دو و حداکثر چهار Event با میانگین
۲٫۸۰۵۶۵ دارد. برای هر ۴٬۶۷۲ چک:

- History موجود است؛
- `PChequeHistoryId` معتبر و متعلق به همان چک است؛
- Current pointer دقیقاً بزرگ‌ترین HistoryId همان چک است.

تمام ۸٬۴۳۶ Transition مشاهده‌شده در Master Workflow مجازند:

| انتقال | رخداد |
|---|---:|
| ۱ صادره → ۵ پرداختنی | ۴٬۶۵۴ |
| ۵ پرداختنی → ۳ پرداخت | ۳٬۶۳۷ |
| ۵ پرداختنی → ۲ عودت | ۶۴ |
| ۲ عودت → ۴ ابطالی | ۶۳ |
| ۱ صادره → ۴ ابطالی | ۱۸ |

Master سه انتقال مجاز دیگر نیز دارد که در Snapshot مشاهده نشده‌اند:
`1→3`، `5→4` و `3→4`. نبود نمونه مجوز حذف آن‌ها نیست و برای مهاجرت Golden
Case کنترل‌شده لازم دارند.

## اثر وضعیت چک بر کاردکس تأمین‌کننده

Procedure رسمی `Acc.Usp_GetSupplierRemAmount` فقط چک‌های
`PChequeIsCertified=0` را در شاخه Supplier cheque می‌گیرد:

```text
current status 3 (پرداخت) or 5 (پرداختنی) -> BedAmount
current status 2 (عودت)                   -> BesAmount
current status 4 (ابطالی)                 -> no cheque effect
certified cheque                           -> excluded from this branch
```

در چک‌های متصل به Supplier:

- Status 3: ۲٬۰۷۶ چک، مبلغ ۷٬۲۴۹٬۵۷۲٬۴۸۰٬۲۴۸، Certified صفر؛
- Status 4: ۳۲ چک، مبلغ ۷۸۴٬۱۵۸٬۳۴۷٬۱۵۷، شامل ۱۸ Certified و اثر رسمی صفر؛
- Status 5: ۵۲۲ چک، مبلغ ۷٬۳۷۷٬۱۱۳٬۴۸۹٬۶۸۵، شامل ۵۰ Certified؛ مبلغ مؤثر
  non-certified برابر ۳٬۴۸۴٬۶۱۳٬۴۸۹٬۶۸۵ است.

در Snapshot هیچ چک Supplier جاری Status 2 نیست، هرچند Contract رسمی آن را به
عنوان برگشت اثر در BesAmount پشتیبانی می‌کند. این مسیر باید با Golden Case
حفظ شود.

## دسته‌چک و برگ مصرف‌شده

۶۶ دسته‌چک و ۵٬۶۸۷ برگ وجود دارد:

- ۴٬۸۲۷ برگ `IsUsed=1`؛
- ۴٬۶۷۲ برگ به چک فعلی وصل‌اند؛
- برگ یتیم در خود چک و reuse یک برگ بین چند چک: صفر؛
- ۱۵۵ برگ Used هستند ولی PCheque فعلی ندارند.

تحلیل تکمیلی SQL رسمی ثابت کرد این حالت توسط فرم نگهداری برگ پشتیبانی می‌شود:
`usp_sdsnet_PchequeBookItem_Save` مقدار `IsUsed` را مستقیم ذخیره می‌کند و
Validator فقط برگ متصل به PCheque/Transfer را از برداشتن تیک منع می‌کند. هر ۱۵۵
مورد بدون لینک Transfer-family، در ۲۳ دسته‌چک فعال و فاقد متن زمینه‌اند. پس
`SOURCE_USED_UNLINKED` یک State معتبر منبع با `UNKNOWN_SOURCE` است؛ علت تاریخی
هر ردیف قابل اثبات نیست. `IsUsed` پاک یا چک ساختگی ایجاد نشود.

## فعالیت سه‌ماهه و مسیرهای خالی

در `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱`:

| رخداد | تعداد |
|---|---:|
| Pay | ۳٬۴۱۹ |
| Cash instrument | ۱۶۸ |
| Withdrawal instrument | ۳٬۳۹۹ |
| Payable cheque | ۶۰۱ |
| Cheque state event | ۱٬۸۸۳ |

جداول `PChequeRefund`، bulk ChangeStatus و `RPTransferPCheque` فعلاً خالی‌اند؛
بااین‌حال Master Workflow و Procedureها مسیر عودت/ابطال/تغییر وضعیت را ثابت
می‌کنند. جدول خالی مساوی قابلیت غیرفعال نیست.

## قرارداد مدل مقصد

- `Disbursement` برای Pay envelope و Status رسمی؛
- `DisbursementInstrument` پایه و Childهای Cash/Withdrawal/PayableCheque؛
- چند Instrument برای یک Pay و امکان mixed types؛
- `PayableCheque` با هویت حساس جدا و رمزگذاری‌شده؛
- `PayableChequeStateEvent` Append-only؛
- `PayableChequeStateProjection` با CurrentEvent pointer؛
- `ChequeBook` و `ChequeLeaf` با وضعیت Available/Used/Void/Review؛
- `SupplierDisbursementPartyLink` از Payee Contact؛
- `SupplierLedgerEntry` مستقل از Invoice allocation؛
- `SupplierInvoiceAllocation` برای تخصیص اختیاری خروج وجه به فاکتور؛
- `SourceCrosswalk` برای Pay/Instrument/Cheque/History/Leaf.

Command تغییر وضعیت باید Workflow، CurrentVersion، Idempotency Key، Context و
Audit داشته باشد. Update مستقیم Current pointer یا حذف History از UI ممنوع است.

## Golden Caseهای لازم

1. Pay تأییدشده با یک برداشت.
2. Pay با چند برداشت و Pay با ۷۶ چک.
3. Pay ترکیبی از دو نوع Instrument.
4. Pay بدون سه ابزار اصلی و مسیر جایگزین معتبر.
5. صدور چک ۱→۵→۳ و اثر Supplier cardex.
6. ۱→۵→۲→۴ و برگشت اثر عودت.
7. ابطال مستقیم ۱→۴.
8. سه Transition مجاز ولی بدون نمونه فعلی.
9. Certified cheque و حذف از شاخه رسمی Supplier cheque.
10. ۱۵۵ برگ `SOURCE_USED_UNLINKED`؛ حفظ وضعیت، منع چک ساختگی و Review پیش از reuse.
11. Retry تغییر وضعیت بدون History تکراری.
12. Pay Status=2 بدون ConfirmDate Legacy.

## ابهام‌های باز

1. Business reason دقیق ۱۵۵ برگ Used بدون PCheque؛ Schema هیچ Actor/Time ندارد.
2. کاربرد عملی `IsReconciled` که در همه Withdrawal/Cheque فعلی صفر است.
3. مرز Certified cheque با اسناد تضمینی و شاخه دیگری که اثر مالی آن را ثبت می‌کند.
4. مسیرهای جایگزین ۴۸۷ Pay بدون Cash/Withdrawal/PCheque.
5. دلیل نبود Supplier cheque جاری Status 2 و نمونه کنترل‌شده برای اثر BesAmount.
6. قرارداد Reverse پس از Status 3 که Master اجازه `3→4` می‌دهد ولی نمونه ندارد.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_supplier_disbursement_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\supplier_disbursement_and_payable_cheques_20260826.json
```
