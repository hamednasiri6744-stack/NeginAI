# کاتالوگ State machine چک‌ها و توزیع

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۳ State machine، ۲۲ State، ۲۶ Edge تنظیم‌شده و ۳۴ Edge مشاهده‌شده**

## اصل معماری

وضعیت در وارانگار یک ستون قابل‌ویرایش نیست. قرارداد واقعی ترکیب این دو است:

```text
append-only transition history
        +
versioned current-state pointer
        +
allowed-edge / validator / permission / side effects
```

در ERP مقصد نیز تغییر مستقیم `status_id` ممنوع باشد. هر Transition باید Command
نام‌دار، Expected version، مجوز اتمی، Guard، Transaction و Audit event داشته
باشد. Undo نیز ویرایش آزاد نیست؛ برگشت/جبران آخرین رویداد معتبر است.

## چک دریافتی

### وضعیت‌ها

| ID | معنی منبع | در Inbox فعال |
|---:|---|---|
| ۱ | نزد صندوق | بله |
| ۲ | نزد بانک | بله |
| ۳ | وصولی | خیر؛ State مقصد |
| ۴ | برگشتی | بله |
| ۵ | استرداد | خیر؛ State مقصد |
| ۶ | پیگیری وصول | خیر؛ در Status جاری/History استفاده نشده |
| ۷ | واگذار به غیر | خیر در Inbox فعلی |
| ۸ | انتقال بین صندوق | بله؛ State عبوری با Current usage صفر |
| ۹ | حقوقی | بله |

۱۸ Edge در Workflow مجاز و ۱۵ Edge در History مشاهده شده‌اند؛ هیچ Edge مشاهده‌شده
خارج از Workflow نبود. سه Edge مجاز ولی مشاهده‌نشده عبارت‌اند از `1→9`، `9→1`
و `9→4`. این عدم مشاهده مجوز را باطل نمی‌کند، اما برای Golden test باید سناریوی
مصنوعی/کنترل‌شده داشته باشند.

پرکاربردترین چرخهٔ عبوری `1→8→1` است؛ پس State ۸ را نمی‌توان فقط چون Current
usage صفر است حذف کرد. مسیرهای تجاری اصلی شامل `1→2→3`، `2→4→5`، `1→7` و
`4↔2` هستند.

Integrity زنجیره ۱۰۶٬۱۳۱ رویداد: orphan cheque/status/previous/transition صفر،
و ۸۲٬۳۰۹ رویداد دارای Previous/Transition معتبر بودند. دو علامت نیازمند Review
وجود دارد: هشت Master Pay projection خالی با History Pay معتبر و ۴۹ Settlement
بین مشتری متفاوت؛ هر دو برداشت اولیه‌ی خرابی بعداً با شواهد رسمی رد شدند؛
این‌ها خودبه‌خود خطا اعلام نشده‌اند، اما Quarantine/reconciliation می‌خواهند.

## چک پرداختنی

| ID | معنی منبع | در Inbox فعال | Current usage |
|---:|---|---|---:|
| ۱ | صادره | بله | ۰ |
| ۲ | عودت | خیر | ۱ |
| ۳ | پرداخت | خیر | ۳٬۶۳۷ |
| ۴ | ابطالی | خیر | ۸۱ |
| ۵ | پرداختنی | بله | ۹۵۳ |

هشت Edge تنظیم‌شده و پنج Edge مشاهده شده‌اند. هیچ Edge واقعی خارج Workflow
نبود. Edgeهای مجاز ولی مشاهده‌نشده `1→3`، `3→4` و `5→4` هستند. مسیر غالب
`1→5→3` است؛ مسیرهای عودت/ابطال `5→2→4` و `1→4` نیز مشاهده شدند.

۴٬۶۷۲ چک، ۱۳٬۱۰۸ History event و صفر Current pointer نامعتبر ثبت شده است؛
Current همیشه بیشترین History ID همان چک بوده. ۱۵۵ برگ دفترچه استفاده‌شده بدون
چک جاری یک State رسمی مستقیم از فرم‌اند، نه Orphan قطعی؛ علت تاریخی‌شان
UNKNOWN_SOURCE است و پیش از reuse نیازمند Review هستند.

## مدیریت توزیع

| ID | معنی منبع |
|---:|---|
| ۰ | ابطال شده |
| ۱ | صادر نشده |
| ۲ | خروجی انبار |
| ۳ | ارسال شده |
| ۴ | توزیع شده |
| ۵ | ارسال شده به تبلت |
| ۶ | برگشتی |
| ۷ | خاتمه یافته |

مسیر غالب مشاهده‌شده:

```text
create → 1 صادر نشده
      → 2 خروجی انبار
      → 3 ارسال شده
      → 4 توزیع شده
      → 7 خاتمه یافته
```

مسیرهای برگشت/جانبی واقعی نیز مهم‌اند: `3→2`، `2→1`، `1→0`، `0→1`،
`4→3`، `3→5`، `5→3`، `5→7` و حتی `3→1` با دو رویداد. بنابراین مقصد نباید
Workflow را خطی فرض کند.

۱۹۲٬۵۷۳ رویداد برای ۲۶٬۰۹۲ توزیع ثبت شده است. Status ۶ در Snapshot جاری و
Transitionهای مشاهده‌شده استفاده نشده؛ این شاهد «Legacy/غیرفعال محتمل» است، نه
مجوز حذف Status. برای توزیع، Artifact Edgeهای مشاهده‌شده را دارد اما جدول کامل
Allowed-edge رسمی هنوز ثابت نشده؛ رفتار تاریخی را نباید خودکار Whitelist کرد.

۲۶٬۰۸۶ توزیع بدون Legacy path master هستند و خود Master صفر ردیف دارد؛ پس مسیر
توزیع فعلی احتمالاً از مدل/منبع دیگری تأمین می‌شود. این Crosswalk باید پیش از
طراحی Route master مقصد حل شود.

## قرارداد مقصد

1. `StateDefinition`، `AllowedTransition`، `TransitionEvent` و `CurrentState`
   موجودیت‌های جدا باشند.
2. هر Edge، Permission/required fields/validator/side-effect مستقل داشته باشد.
3. Configured، observed، active-in-form و currently-used چهار بعد جدا بمانند.
4. Source ID در Crosswalk حفظ شود؛ ID مقصد Namespaced و پایدار باشد.
5. Transitionهای مالی با تخصیص پرداخت و Transitionهای توزیع با Exit/Cardex و
   Delivery evidence Reconcile شوند.
6. Edgeهای برگشتی Reason اجباری و SoD قوی‌تر می‌خواهند.
7. Import ناسازگار به Quarantine برود؛ Current pointer از History بازسازی و
   مقایسه شود، نه اینکه کورکورانه Trust شود.

## Artifact و بازتولید

- `scripts/windows/build_varanegar_state_machine_catalog.py`
- `artifacts/varanegar_analysis/ui/varanegar_state_machine_catalog_20260827.json`
- `tests/test_varanegar_ui_evidence.py`
