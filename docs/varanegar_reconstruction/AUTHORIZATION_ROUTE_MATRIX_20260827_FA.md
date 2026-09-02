# ماتریس مجوز Route و Commandهای فعال وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Snapshot تجمیعی Clone فقط‌خواندنی؛ بدون هویت و بدون Grant فردی**

## نتیجهٔ اصلی

مجوز وارانگار یک `role` تخت نیست. برای رسیدن به یک Command قابل اجرا، حداقل
پنج لایه مستقل باید هم‌زمان برقرار باشند:

```text
Route/Page access
  AND atomic command permission
  AND feature entitlement
  AND fiscal/DC/data scope
  AND selection/date/workflow/domain guards
```

در مدل Legacy، Admin از ارزیابی Node عبور می‌کند. برای بقیه کاربران، Allow
مستقیم یا گروهی لازم است و هر Deny مستقیم یا گروهی بر Allow غلبه می‌کند؛ مقدار
خنثی مجوز نیست. سیستم NGT نیز RBAC جداگانهٔ Principal/Role/Permission/Catalog
دارد و تا وقتی Crosswalk رسمی وجود ندارد نباید با AccessNode ادغام شود.

## مرز ایمنی و حریم خصوصی

- منبع فقط Clone `NeginPakhsh_WebDev` با وضعیت `READ_ONLY`، `can_update=0` و
  `db_denydatawriter` بود؛
- فقط Config ثابت AccessNode و شمارش‌های تجمیعی حقوق خوانده شد؛
- هیچ نام کاربر/گروه، شناسه فردی، Membership، Grant فردی، URL، رمز یا ردیف
  عملیاتی در Artifact ذخیره نشد؛
- هیچ Command برنامه، Procedure عملیاتی یا Write اجرا نشد؛
- این شمارش‌ها Snapshot Clone هستند و «مجوز User جاری Runtime» را اثبات
  نمی‌کنند.

## پوشش چهار Route باز

در Snapshot مجوز ۱۴۱ کاربر فعال و حذف‌نشده ارزیابی شدند که هفت مورد Admin
هستند. شمارش Allow شامل Admin bypass است.

| Route فعال | AccessNode | Allow مؤثر | Deny صریح | بدون Allow |
|---|---:|---:|---:|---:|
| پیگیری چک‌های دریافتنی | `42 / RchequeTracking` | ۳۵ | ۰ | ۱۰۶ |
| پیگیری چک‌های پرداختنی | `43 / PChequeTracking` | ۲۸ | ۰ | ۱۱۳ |
| اقلام انبار | `109 / StockGoods` | ۵۲ | ۰ | ۸۹ |
| مدیریت توزیع | `412 / DistManagement` | ۳۴ | ۰ | ۱۰۷ |

این اعداد نشان می‌دهند Page visibility با نقش سازمانی عمومی یکی نیست. حتی
دسترسی به خود صفحه نیز برای بخش بزرگی از کاربران خنثی/غیرمجاز است.

## گره‌های فرمان کشف‌شده

چهار Route در مجموع ۴۰ Node دارند: چهار Page node و ۳۶ Command/sub-command.
چهار Command مخفی در فرم چک دریافتی نیز وجود دارد؛ «مخفی» به معنی بلااستفاده
نیست و باید با کد/Feature/Role جداگانه بررسی شود.

### چک دریافتی

- `View`: ۳۷ Allow؛
- `ChangeStatus`: ۳۰ Allow؛
- `Undo`: ۲۹ Allow؛
- `RchequeTracking_Edit` و `RCheque_AdditionalReport`: هرکدام فقط هفت Allow
  (در این Snapshot همان اندازهٔ Adminها) و `IsShow=false`؛
- دو زیرگزارش Remain-returned و Settlement نیز Node مستقل دارند.

### چک پرداختنی

- `View`: ۳۰ Allow؛
- `ChangeStatus`: ۲۹ Allow؛
- `Undo`: ۲۹ Allow.

پس Read، ChangeStatus و Undo سه Capability مستقل‌اند؛ دسترسی به صفحه به‌تنهایی
مجوز تغییر وضعیت یا برگشت History نیست.

### اقلام انبار

- `Edit` (Create/Edit/Delete در قرارداد Runtime): ۲۰ Allow؛
- `BatchEnable`: ۱۵ Allow؛
- `ExtraAction`: ۹ Allow.

این تفکیک تأیید می‌کند که مدیریت Batch و اقدام‌های ویژه نباید داخل یک مجوز
کلی «ویرایش کالا» پنهان شوند.

### مدیریت توزیع

۱۸ Command سطح اول و پنج زیرCommand چاپ پیدا شد. از جمله:

- `AddNew`، `ApprovalSend`، `ApprovalDist`، `DistAfterVch2Sale`،
  `BackToOldStatus`، `RemoveExitFromDist`، `ReviewRemoveExitFromDist` و
  `FreeDist`؛
- `issuanceOutput` تنها Node این چهار زیر‌درخت است که Deny صریح دارد: سه کاربر
  فعال در Snapshot، با ۱۷ Allow مؤثر؛
- `Print` دارای زیرمجوزهای `BeforeExit`، `TeamPakhsh`، `ExitEachFactor`،
  `ExitFactor` و `PrintRetorder` است؛
- `ExportToExcel` جدا از Print است؛
- یک Node با کلید فارسی به‌دلیل سیاست Redaction فقط با Fingerprint حفظ شد و
  تا شاهد مطمئن‌تر نباید نام‌گذاری حدسی شود.

## قرارداد طراحی ERP شخصی

1. منو/Route، خواندن Page و هر Command باید Capability جدا داشته باشند.
2. Approve، reverse، undo، issue exit، remove exit، free/merge، print و export
   مجوز اتمی و Audit event مستقل می‌خواهند.
3. محدودهٔ داده (DC، دفتر فروش، انبار، مشتری، سرپرست، مهلت پرداخت، سازنده و نوع
   سفارش) از مجوز عملکردی جدا ذخیره و ارزیابی شود.
4. مجوز موفق فقط اجازهٔ ورود به Guardهای بعدی است؛ Workflow transition، تاریخ
   عملیاتی، انتخاب ردیف، Feature flag و Validator دامنه نباید دور زده شوند.
5. برای عملیات حساس، سیاست Segregation of Duties صریح تعریف شود؛ کسی که سند
   را می‌سازد لزوماً نباید تأیید، خروج، برگشت وضعیت یا حذف خروج را هم انجام دهد.
6. شناسه‌های Legacy در Crosswalk مهاجرتی نگه داشته شوند، اما کلید مقصد
   Namespaced و پایدار باشد؛ مانند `distribution.exit.issue`.
7. دسترسی مؤثر باید Explainable باشد: پاسخ API علاوه بر Allow/Deny بتواند
   Source permission، scope، feature و guard شکست‌خورده را برای Audit ثبت کند.

## Artifact و بازتولید

- `scripts/sql/extract_varanegar_route_authorization_matrix.py`
- `artifacts/varanegar_analysis/ui/varanegar_route_authorization_matrix_20260827.json`
- ورودی Route: `artifacts/varanegar_analysis/ui/varanegar_menu_form_crosswalk_20260827.json`
- آزمون: `tests/test_varanegar_ui_evidence.py`

گام بعدی این خط: اتصال هر Command node به Method/Handler و Object SQL متناظر،
و سپس ساخت Role template مقصد بدون کپی نام‌ها و استثناهای تاریخی کاربران فعلی.
