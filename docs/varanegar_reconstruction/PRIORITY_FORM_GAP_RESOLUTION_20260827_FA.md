# حل شکاف فرم‌های اولویت‌بالای وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **چهار فرم به‌عنوان پنجرهٔ فرعی تأیید شد؛ ورودی سه فرم هنوز حل نشده است**

## نتیجهٔ اصلی

هفت فرمِ اولویت‌بالا با دو شاهد مستقل بررسی شدند: پیکربندی ثابت
`FormInfo/Menu/AccessNode` در Clone فقط‌خواندنی و Call graph سازنده‌ها در DLLهای
Runtime. هیچ‌یک از هفت فرم در پیکربندی ثابت Route پیدا نکردند. این نبودن به‌تنهایی
اثبات فرم مرده نیست.

معیار «پنجرهٔ فرعی» فقط فراخوانی `ctor` از Type متفاوت بود؛ Reference به متدهای
خود فرم Launcher شمرده نشد. با این معیار چهار مورد حل شد:

- `frmBankReconciliationList → frmBankReconciliation` برای جزئیات تطبیق بانک؛
- `frmChequeSettingMain/frmPay/frmPayList/frmPayNew/frmTransferList/frmTransferListNew → frmChek`؛
- `frm3013/frm3017 → frmList` برای انتخاب‌های گزارش Legacy؛
- `frmReconciliationSetup → frmReconciliation` برای اجرای تطبیق.

سه ورودی ریشه‌ای هنوز حل نشده‌اند:

- `TreasuryOld.Forms.frmBankReconciliationList`؛
- `TreasuryOld.Forms.frmReconciliationSetup`؛
- `VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict`.

برای خوشه مغایرت بانکی، Source Model مستقل ساخته شد. این مدل ثابت می‌کند
`frmBankReconciliationList/frmReconciliationSetup` به Aggregate چندجدولی و
لینک چندنوعی خزانه متصل‌اند، ولی Entry point ریشه آن‌ها همچنان حل‌نشده است؛
نبود Entry point با نبود قابلیت کسب‌وکار یکی نیست. جزئیات در
`BANK_RECONCILIATION_SOURCE_MODEL_20260827_FA.md` ثبت شده است.

### فیلدهای مستقیم و ارثی

متادیتای Field هفت فرم نیز بدون Load/Execute استخراج شد. شش فرم Treasury مجموعاً
۲۲۹ Field مستقیم دارند. `FormSpecialOptionsDistrict` در کلاس خودش صفر Field دارد
و ۸۸ Field گزارش‌شدهٔ آن فقط از Base framework می‌آید؛ بنابراین از نام این فرم
نمی‌توان فیلد، Binding یا Command دامنه‌ای مقصد را حدس زد. جزئیات و محدودیت‌ها در
`PRIORITY_FORM_DECLARED_FIELDS_20260827_FA.md` ثبت شده است.

ارزیابی تکمیلی `FormSpecialOptionsDistrict` نیز صفر Business method، صفر Route،
صفر Launcher/Reference بیرونی و صفر Candidate برای چهار الگوی محدود نامی در
کاتالوگ Clone داد. این فرم اکنون «پوسته یا قابلیت پویا و حل‌نشده» است؛ شواهد برای
حذف قطعی یا ساخت Schema مقصد کافی نیست. سند:
`SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_20260827_FA.md`.

### اسکن سراسری Entrypoint

برای حذف احتمال Launcher در ماژول‌های خارج از کاتالوگ Core، هر ۶۲ فایل .NET
بستهٔ فعال—including Setting، POS، Tablet، Report، Framework و Container—اسکن
شد. ۷٬۶۵۰ Type و ۸۱٬۴۷۳ Method body بررسی شد. هر ۱۹۱ اشارهٔ IL به سه Target،
اشارهٔ داخلی خود همان Type بود؛ اشارهٔ بیرونی، `newobj` بیرونی، نام Type دقیق در
رشته، نام کامل/کوتاه تعبیه‌شده داخل String طولانی‌تر، Inheritance edge یا Resource
خارجی صفر بود. سه Resource یافت‌شده فقط
Resource نام‌همسان خود فرم‌ها هستند.

بنابراین وضعیت هر سه مورد اکنون
`ENTRYPOINT_STILL_UNRESOLVED_AFTER_ALL_ASSEMBLY_IL_SCAN` است. دو خطای Parse
شناخته‌شده فقط در `InitializeComponent` فرم‌های نامرتبط ServerConfig و Dashboard
Designer ثبت شد؛ اختلاف Hash و خطای غیرمنتظره صفر است. این دو Blind spot در
Artifact حفظ شده‌اند و نتیجه را به «فرم مرده» ارتقا نمی‌دهند.

اسکن تکمیلی کل Deployment نیز ۸۵۳ فایل و ۵۹۸٬۵۵۸٬۴۳۱ بایت را برای فقط سه
نام Type بررسی کرد. Matchها صرفاً در اسمبلی تعریف‌کننده و کپی `.disable` همان
بودند؛ Plugin، Config، Manifest یا Binary بیرونی با reference دقیق صفر است.
این absence، نام ساخته‌شده/رمزشده یا route محیط دیگر را رد نمی‌کند. جزئیات در
`DEPLOYMENT_ROOT_REFERENCE_SCAN_20260827_FA.md` ثبت شده است.

برای این سه مورد، نبود Constructor بیرونی و نبود Route ثابت فقط محدودهٔ جست‌وجو
را به Reflection، Resource، Base/Event، Action menu یا پیکربندی خارج از Clone
کاهش می‌دهد؛ حذف آن‌ها از ERP مقصد هنوز مجاز نیست.

## شواهد عددی

- هفت Type هدف و ده فرم والد بررسی شد؛
- ۵۰ Reference دقیق Type ثبت شد، اما فقط ۲۰ Edge سازندهٔ غیرخودی Launcher معتبر بود؛
- چهار Target از Parent قابل اثبات و سه Root هنوز نامشخص است؛
- در Clone: صفر FormInfo، صفر Menu route و صفر AccessNode برای هفت Target؛
- ۱۸ Type لایهٔ دادهٔ خزانه‌داری ردیابی شد و هر ۱۸ Type پیدا شد؛
- صفر خطای Method body و صفر اختلاف Hash منبع ثبت شد.

## ناسازگاری Namespace و Assembly

`TreasuryOld.DataLayer.PdtReport` با وجود Namespace لایهٔ داده، داخل
`TreasuryOld.Forms.dll` تعریف شده است و ۱۶ Method body دارد. این یک شاهد مهم
برای بازسازی است: مرزهای Namespace قدیمی با مرز Deployment/مالکیت واقعی برابر
نیستند. در ERP مقصد، Report query/service نباید صرفاً به‌دلیل نام Legacy در UI
قرار گیرد.

## پیامد برای ERP شخصی نگین

چهار فرم حل‌شده Route مستقل نمی‌خواهند و باید زیر Capability و Context والد
مدل شوند. سه Root حل‌نشده تا زمان شاهد بیشتر در Backlog با وضعیت
`entrypoint_unresolved` می‌مانند. هیچ Command، جدول یا Permission مقصد نباید از
روی نام مبهم `frmList` یا `SpecialOptionsDistrict` حدس زده شود.

## حدود اطمینان

- Call graph ایستا Reflection، Resource، Interface dispatch و Feature branch
  زمان اجرا را کامل نمی‌بیند.
- `write_like` فقط Heuristic نام Method است و اثر واقعی یا اجازهٔ نوشتن را ثابت
  نمی‌کند.
- Route ثابتِ صفر، Route پویا یا Parent launcher را رد نمی‌کند.
- این مرحله هیچ DLL را Load/Execute نکرد، هیچ کنترل UI را فعال نکرد و هیچ دادهٔ
  عملیاتی یا مجوز فردی نخواند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_routes_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_call_graph_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_root_entrypoints_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_deployment_root_reference_scan_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_declared_fields_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_special_options_district_assessment_20260827.json`
- `scripts/sql/extract_varanegar_priority_gap_routes.py`
- `scripts/windows/extract_varanegar_priority_gap_call_graph.py`
- `scripts/windows/extract_varanegar_root_entrypoints.py`
- `scripts/windows/extract_varanegar_deployment_root_reference_scan.py`
- `scripts/windows/extract_varanegar_priority_gap_declared_fields.py`
- `scripts/sql/extract_varanegar_special_options_district_assessment.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی دیگر اسکن استاتیک عمومی نیست؛ آن مسیر در ۶۲ اسمبلی و ۸۵۳ فایل بسته
کامل شده است. برای بستن سه Root باید telemetry فقط‌خواندنی یک Session واقعی،
پیکربندی محیط عملیاتی کنترل‌شده یا sign-off مالک دربارهٔ dead/legacy بودن آن‌ها
گرفته شود؛ تا آن زمان هر سه با عدم‌قطعیت صریح حفظ می‌شوند.
